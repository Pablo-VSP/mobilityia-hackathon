"""
tool-generar-recomendacion — Generación de recomendaciones preventivas de mantenimiento.

Maintenance Agent Tool invocado por Bedrock AgentCore. Recibe parámetros de
diagnóstico (autobus, diagnostico, nivel_riesgo, urgencia, componentes),
genera un registro de alerta en DynamoDB_Alertas con UUID v4 y número de
referencia OT, enriquecido con contexto del autobús desde DynamoDB_Telemetria.

Requisitos: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 11.4, 11.7
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from ado_common.dynamo_utils import query_latest_records, put_item
from ado_common.response import build_agent_response, build_error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables (Req 11.6, 11.7)
DYNAMODB_TABLE_TELEMETRIA = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
DYNAMODB_TABLE_ALERTAS = os.environ.get("DYNAMODB_TABLE_ALERTAS", "ado-alertas")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_param(event, name, default=None):
    """Extract a named parameter from a Bedrock AgentCore event."""
    params = event.get("parameters", [])
    for p in params:
        if p.get("name") == name:
            return p.get("value", default)
    return default


def _parse_componentes(raw_value):
    """Parse componentes from a comma-separated string or JSON array string.

    Bedrock AgentCore may send componentes as:
      - A comma-separated string: "sistema_refrigeracion,bomba_agua"
      - A JSON array string: '["sistema_refrigeracion","bomba_agua"]'

    Args:
        raw_value: The raw string value from the event parameters.

    Returns:
        List of component strings, stripped of whitespace.
    """
    if raw_value is None:
        return []

    raw_value = str(raw_value).strip()
    if not raw_value:
        return []

    # Try JSON array first
    if raw_value.startswith("["):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [str(c).strip() for c in parsed if str(c).strip()]
        except (json.JSONDecodeError, TypeError):
            pass

    # Fall back to comma-separated
    return [c.strip() for c in raw_value.split(",") if c.strip()]


def _generate_numero_referencia(autobus):
    """Generate a reference number in the format OT-{YYYY}-{MMDD}-{autobus}.

    Uses the current UTC date.

    Args:
        autobus: Bus economic number.

    Returns:
        String like 'OT-2026-0423-1001'.
    """
    now = datetime.now(timezone.utc)
    return f"OT-{now.year}-{now.month:02d}{now.day:02d}-{autobus}"


def _enrich_from_telemetria(autobus):
    """Query DynamoDB_Telemetria for the latest record of a bus to enrich
    the alert with viaje_ruta and operador_desc.

    Args:
        autobus: Bus economic number.

    Returns:
        Tuple of (viaje_ruta, operador_desc). Defaults to empty strings
        if the query fails or returns no records.
    """
    try:
        records = query_latest_records(DYNAMODB_TABLE_TELEMETRIA, autobus, limit=1)
        if records:
            latest = records[0]
            viaje_ruta = latest.get("viaje_ruta", "")
            operador_desc = latest.get("operador_desc", "")
            return str(viaje_ruta), str(operador_desc)
    except Exception as exc:
        logger.warning(json.dumps({
            "action": "enrich_from_telemetria",
            "autobus": autobus,
            "error": str(exc),
            "message": "No se pudo enriquecer la alerta con datos de telemetría",
        }))

    return "", ""


# ---------------------------------------------------------------------------
# Lambda handler (Req 9.1–9.6, 11.4, 11.7)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the generar-recomendacion tool.

    Invoked by Bedrock AgentCore as a Maintenance Agent Action Group tool.

    Flow:
      1. Parse autobus, diagnostico, nivel_riesgo, urgencia, componentes
         from event parameters (Req 9.1).
      2. Generate alerta_id (UUID v4) and numero_referencia (Req 9.2).
      3. Query DynamoDB_Telemetria for latest bus record to enrich with
         viaje_ruta and operador_desc (Req 9.4).
      4. Build alert item with tipo_alerta=MANTENIMIENTO, estado=ACTIVA,
         agente_origen=ado-agente-mantenimiento (Req 9.3).
      5. PutItem to ado-alertas table (Req 9.1).
      6. Return confirmation with alerta_id, numero_referencia, autobus,
         nivel_riesgo, urgencia, and human-readable message (Req 9.5).
      7. On DynamoDB write failure: return error response and log in JSON
         structured format (Req 9.6).

    Args:
        event: Bedrock AgentCore event with parameters list.
        context: Lambda context (unused).

    Returns:
        Dict in Bedrock AgentCore Action Group response format.
    """
    logger.info(json.dumps({
        "action": "lambda_handler",
        "event_keys": list(event.keys()) if isinstance(event, dict) else "not_dict",
    }))

    # --- 1. Parse parameters (Req 9.1) ---
    autobus = _get_param(event, "autobus")
    diagnostico = _get_param(event, "diagnostico")
    nivel_riesgo = _get_param(event, "nivel_riesgo")
    urgencia = _get_param(event, "urgencia")
    componentes_raw = _get_param(event, "componentes")

    if not autobus:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_autobus_parameter",
        }))
        return build_error_response("Parámetro 'autobus' es requerido.", 400)

    if not diagnostico:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_diagnostico_parameter",
        }))
        return build_error_response("Parámetro 'diagnostico' es requerido.", 400)

    autobus = str(autobus).strip()
    diagnostico = str(diagnostico).strip()
    nivel_riesgo = str(nivel_riesgo).strip() if nivel_riesgo else "MODERADO"
    urgencia = str(urgencia).strip() if urgencia else "PROXIMO_SERVICIO"
    componentes = _parse_componentes(componentes_raw)

    logger.info(json.dumps({
        "action": "parse_params",
        "autobus": autobus,
        "nivel_riesgo": nivel_riesgo,
        "urgencia": urgencia,
        "componentes_count": len(componentes),
    }))

    # --- 2. Generate IDs (Req 9.2) ---
    alerta_id = str(uuid.uuid4())
    numero_referencia = _generate_numero_referencia(autobus)
    timestamp = datetime.now(timezone.utc).isoformat()

    # --- 3. Enrich from telemetria (Req 9.4) ---
    viaje_ruta, operador_desc = _enrich_from_telemetria(autobus)

    # --- 4. Build alert item (Req 9.1, 9.3) ---
    alert_item = {
        "alerta_id": alerta_id,
        "timestamp": timestamp,
        "autobus": autobus,
        "tipo_alerta": "MANTENIMIENTO",
        "nivel_riesgo": nivel_riesgo,
        "diagnostico": diagnostico,
        "urgencia": urgencia,
        "componentes": componentes,
        "numero_referencia": numero_referencia,
        "estado": "ACTIVA",
        "agente_origen": "ado-agente-mantenimiento",
        "viaje_ruta": viaje_ruta,
        "operador_desc": operador_desc,
    }

    # --- 5. Write to DynamoDB (Req 9.1) ---
    try:
        put_item(DYNAMODB_TABLE_ALERTAS, alert_item)
    except Exception as exc:
        # Req 9.6 — log error in JSON structured format and return error response
        logger.error(json.dumps({
            "action": "put_item_alertas",
            "table": DYNAMODB_TABLE_ALERTAS,
            "alerta_id": alerta_id,
            "autobus": autobus,
            "error": str(exc),
        }))
        return build_error_response(
            f"Error al crear la recomendación para el autobús {autobus}: {str(exc)}",
            500,
        )

    # --- 6. Return confirmation (Req 9.5) ---
    mensaje = (
        f"Recomendación preventiva creada exitosamente para el autobús {autobus}. "
        f"Número de referencia: {numero_referencia}. "
        f"Nivel de riesgo: {nivel_riesgo}. Urgencia: {urgencia}."
    )

    response_body = {
        "alerta_id": alerta_id,
        "numero_referencia": numero_referencia,
        "autobus": autobus,
        "nivel_riesgo": nivel_riesgo,
        "urgencia": urgencia,
        "mensaje": mensaje,
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "alerta_id": alerta_id,
        "numero_referencia": numero_referencia,
        "autobus": autobus,
        "nivel_riesgo": nivel_riesgo,
        "urgencia": urgencia,
    }))

    return build_agent_response(response_body)
