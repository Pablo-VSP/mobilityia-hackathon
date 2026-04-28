"""
ado-chat-api — API de chat con streaming para agentes de AgentCore.

Usa Lambda Function URL con RESPONSE_STREAM para enviar la respuesta
del agente en tiempo real al frontend via Server-Sent Events (SSE).

El frontend consume con:
  const response = await fetch(CHAT_URL, { method: 'POST', body: ... });
  const reader = response.body.getReader();

Endpoints:
  POST (Function URL) — body: {"prompt": "...", "agente": "combustible|mantenimiento"}
  POST /chat (API Gateway) — fallback sin streaming
"""

import json
import logging
import os
import re
import uuid

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
RUNTIME_ARN_COMBUSTIBLE = os.environ.get(
    "RUNTIME_ARN_COMBUSTIBLE",
    "arn:aws:bedrock-agentcore:us-east-2:084032333314:runtime/AdoCombustible_AdoCombustible-BJ7Uvb4ozE",
)
RUNTIME_ARN_MANTENIMIENTO = os.environ.get(
    "RUNTIME_ARN_MANTENIMIENTO",
    "arn:aws:bedrock-agentcore:us-east-2:084032333314:runtime/AdoMantenimiento_AdoMantenimiento-2sL9qkC3yK",
)
REGION = os.environ.get("AWS_REGION_OVERRIDE", "us-east-2")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agentcore", region_name=REGION)
    return _client


# ---------------------------------------------------------------------------
# Agent routing
# ---------------------------------------------------------------------------

_KW_MANTENIMIENTO = {
    "mantenimiento", "preventivo", "predictivo", "falla", "fallas",
    "obd", "diagnóstico", "diagnostico", "temperatura", "presión",
    "presion", "aceite", "anticongelante", "batería", "bateria",
    "balata", "balatas", "freno", "frenos", "urea", "motor",
    "riesgo", "evento", "mecánico", "mecanico", "recomendación",
    "recomendacion", "taller", "componente", "refrigeración",
    "refrigeracion", "voltaje",
}

_KW_COMBUSTIBLE = {
    "combustible", "consumo", "rendimiento", "eficiencia", "gasolina",
    "diesel", "ahorro", "desviación", "desviacion", "conductor",
    "conducción", "conduccion", "aceleración", "aceleracion",
    "velocidad", "rpm", "crucero", "cruise", "ruta", "viaje",
    "flota", "activos", "buses",
}


def _detect_agent(prompt):
    lower = prompt.lower()
    score_m = sum(1 for kw in _KW_MANTENIMIENTO if kw in lower)
    score_c = sum(1 for kw in _KW_COMBUSTIBLE if kw in lower)
    return "mantenimiento" if score_m > score_c else "combustible"


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _json_response(body, status_code=200):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def _parse_request(event):
    """Extract prompt and agente from various event formats."""
    # OPTIONS preflight
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    if method == "OPTIONS" or event.get("httpMethod") == "OPTIONS":
        return None, None, "OPTIONS"

    body_raw = event.get("body", "{}")
    if isinstance(body_raw, str):
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            return None, None, "INVALID_JSON"
    else:
        body = body_raw or {}

    prompt = body.get("prompt", "").strip()
    agente = body.get("agente", "").strip().lower()
    if agente not in ("combustible", "mantenimiento"):
        agente = _detect_agent(prompt) if prompt else "combustible"

    return prompt, agente, "OK"


def _clean_sse_text(raw_text):
    """Clean SSE data format and remove thinking tags."""
    if raw_text.startswith("data:"):
        parts = re.findall(r'data:\s*"((?:[^"\\]|\\.)*)"\s*', raw_text)
        text = "".join(
            p.replace('\\"', '"').replace("\\n", "\n") for p in parts
        ).strip()
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
        return text
    return raw_text


# ---------------------------------------------------------------------------
# Streaming handler (for Lambda Function URL with RESPONSE_STREAM)
# ---------------------------------------------------------------------------

def handler_streaming(event, response_stream, context):
    """Streaming handler — sends SSE events as the agent generates text.

    This is the entrypoint when invoked via Lambda Function URL with
    InvokeMode=RESPONSE_STREAM.
    """
    prompt, agente, status = _parse_request(event)

    if status == "OPTIONS":
        response_stream.write(b"")
        response_stream.close()
        return

    if not prompt:
        response_stream.write(json.dumps({"error": "prompt requerido"}).encode())
        response_stream.close()
        return

    runtime_arn = (
        RUNTIME_ARN_COMBUSTIBLE if agente == "combustible"
        else RUNTIME_ARN_MANTENIMIENTO
    )
    session_id = f"chat-{uuid.uuid4().hex[:24]}-stream"

    logger.info(json.dumps({
        "action": "chat_stream_request",
        "agente": agente,
        "prompt_length": len(prompt),
    }))

    try:
        client = _get_client()
        resp = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=json.dumps({"prompt": prompt}).encode("utf-8"),
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="application/json",
        )

        # Send metadata first
        meta = json.dumps({"agente": agente, "session_id": session_id})
        response_stream.write(f"data: {meta}\n\n".encode("utf-8"))

        body_stream = resp.get("response") or resp.get("body") or resp.get("Body")
        in_thinking = False

        if body_stream is not None:
            if hasattr(body_stream, "read"):
                raw = body_stream.read()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                cleaned = _clean_sse_text(raw)
                if cleaned:
                    chunk_data = json.dumps({"text": cleaned})
                    response_stream.write(f"data: {chunk_data}\n\n".encode("utf-8"))
            elif hasattr(body_stream, "__iter__"):
                for event_obj in body_stream:
                    text = ""
                    if isinstance(event_obj, dict):
                        for key in ["PayloadPart", "chunk", "Chunk"]:
                            part = event_obj.get(key, {})
                            if isinstance(part, dict):
                                for bkey in ["bytes", "Bytes", "payload"]:
                                    data = part.get(bkey)
                                    if data:
                                        text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                                        break
                        if "bytes" in event_obj and not text:
                            data = event_obj["bytes"]
                            text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                    elif isinstance(event_obj, bytes):
                        text = event_obj.decode("utf-8")
                    elif isinstance(event_obj, str):
                        text = event_obj

                    if not text:
                        continue

                    # Parse SSE data lines
                    for line in text.split("\n"):
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        # Extract the quoted string
                        match = re.match(r'data:\s*"((?:[^"\\]|\\.)*)"\s*$', line)
                        if not match:
                            continue
                        token = match.group(1).replace('\\"', '"').replace("\\n", "\n")

                        # Skip thinking blocks
                        if "<thinking" in token:
                            in_thinking = True
                            continue
                        if "</thinking>" in token:
                            in_thinking = False
                            continue
                        if in_thinking:
                            continue

                        if token:
                            chunk_data = json.dumps({"text": token})
                            response_stream.write(f"data: {chunk_data}\n\n".encode("utf-8"))

        # Send done signal
        response_stream.write(b"data: [DONE]\n\n")

    except Exception as exc:
        error_data = json.dumps({"error": str(exc)[:300]})
        response_stream.write(f"data: {error_data}\n\n".encode("utf-8"))

    response_stream.close()


# ---------------------------------------------------------------------------
# Standard handler (for API Gateway — non-streaming fallback)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Non-streaming handler for API Gateway requests."""
    prompt, agente, status = _parse_request(event)

    if status == "OPTIONS":
        return _json_response({})
    if status == "INVALID_JSON":
        return _json_response({"error": "JSON inválido"}, 400)
    if not prompt:
        return _json_response({"error": "prompt requerido"}, 400)

    runtime_arn = (
        RUNTIME_ARN_COMBUSTIBLE if agente == "combustible"
        else RUNTIME_ARN_MANTENIMIENTO
    )
    session_id = f"chat-{uuid.uuid4().hex[:24]}-dashboard"

    logger.info(json.dumps({
        "action": "chat_request",
        "agente": agente,
        "prompt_length": len(prompt),
    }))

    try:
        client = _get_client()
        resp = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=json.dumps({"prompt": prompt}).encode("utf-8"),
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="application/json",
        )

        chunks = []
        body_stream = resp.get("response") or resp.get("body") or resp.get("Body")

        if body_stream is not None:
            if hasattr(body_stream, "read"):
                raw = body_stream.read()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                chunks.append(raw)
            elif hasattr(body_stream, "__iter__"):
                for event_obj in body_stream:
                    text = ""
                    if isinstance(event_obj, dict):
                        for key in ["PayloadPart", "chunk", "Chunk"]:
                            part = event_obj.get(key, {})
                            if isinstance(part, dict):
                                for bkey in ["bytes", "Bytes", "payload"]:
                                    data = part.get(bkey)
                                    if data:
                                        text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                                        break
                        if "bytes" in event_obj and not text:
                            data = event_obj["bytes"]
                            text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                    elif isinstance(event_obj, bytes):
                        text = event_obj.decode("utf-8")
                    elif isinstance(event_obj, str):
                        text = event_obj
                    if text:
                        chunks.append(text)

        respuesta = _clean_sse_text("".join(chunks).strip())
        if not respuesta:
            respuesta = "El agente procesó la solicitud pero no generó una respuesta de texto."

        return _json_response({
            "respuesta": respuesta,
            "agente_usado": agente,
            "session_id": session_id,
        })

    except Exception as exc:
        return _json_response({
            "respuesta": f"Error conectando con el agente: {str(exc)[:300]}",
            "agente_usado": agente,
            "session_id": session_id,
            "error": True,
        }, 502)
