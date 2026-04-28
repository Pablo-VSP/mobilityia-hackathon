"""
ADO MobilityIA — Agente de Mantenimiento Predictivo
Bedrock AgentCore Runtime + Strands Agents
"""

import json
import boto3
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

_lambda_client = boto3.client("lambda", region_name="us-east-2")
_bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name="us-east-2")

KNOWLEDGE_BASE_ID = "4OAVLRB8VI"


def _invoke_lambda(function_name: str, parameters: list[dict]) -> dict:
    payload = {"parameters": parameters}
    response = _lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    result = json.loads(response["Payload"].read())
    try:
        body_str = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        return json.loads(body_str)
    except (KeyError, TypeError):
        return result


@tool
def consultar_knowledge_base(consulta: str) -> str:
    """Busca información técnica en la base de conocimiento de ADO MobilityIA.

    Contiene manuales técnicos, catálogo de SPNs, códigos de falla,
    patrones de eventos mecánicos, y normativa NOM-044 de emisiones.

    Args:
        consulta: Pregunta o tema a buscar (ej: código SPN 110, temperatura motor normal)
    """
    try:
        response = _bedrock_agent_client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": consulta},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                }
            },
        )
        results = []
        for item in response.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            source = item.get("location", {}).get("s3Location", {}).get("uri", "")
            score = item.get("score", 0)
            results.append({
                "contenido": content[:1000],
                "fuente": source,
                "relevancia": round(float(score), 3) if score else 0,
            })
        return json.dumps({"resultados": results, "total": len(results)}, ensure_ascii=False, default=str)
    except Exception as e:
        log.error(f"Error consultando KB: {e}")
        return json.dumps({"error": str(e), "resultados": []}, ensure_ascii=False)


@tool
def consultar_obd(autobus: str) -> str:
    """Consulta señales de diagnóstico OBD y salud mecánica de un autobús.
    Retorna SPNs de mantenimiento, tendencias, balatas y fallas recientes.

    Args:
        autobus: Número económico del autobús (ej: 7309, 7311)
    """
    params = [{"name": "autobus", "value": str(autobus)}]
    return json.dumps(_invoke_lambda("tool-consultar-obd", params), ensure_ascii=False, default=str)


@tool
def predecir_evento(autobus: str) -> str:
    """Predice riesgo de evento mecánico usando modelo ML o heurística.

    Args:
        autobus: Número económico del autobús (ej: 7309)
    """
    params = [{"name": "autobus", "value": str(autobus)}]
    return json.dumps(_invoke_lambda("tool-predecir-evento", params), ensure_ascii=False, default=str)


@tool
def buscar_patrones_historicos(codigo: str, modelo: str = "", marca_comercial: str = "") -> str:
    """Busca patrones en historial de fallas por código.

    Args:
        codigo: Código de falla (ej: 100, 32, 158)
        modelo: Modelo del bus para priorizar (ej: VOLVO). Opcional.
        marca_comercial: Marca comercial (ej: DIAMANTE). Opcional.
    """
    params = [{"name": "codigo", "value": str(codigo)}]
    if modelo:
        params.append({"name": "modelo", "value": str(modelo)})
    if marca_comercial:
        params.append({"name": "marca_comercial", "value": str(marca_comercial)})
    return json.dumps(_invoke_lambda("tool-buscar-patrones-historicos", params), ensure_ascii=False, default=str)


@tool
def generar_recomendacion(autobus: str, diagnostico: str, nivel_riesgo: str, urgencia: str, componentes: str) -> str:
    """Genera recomendación preventiva de mantenimiento y la registra.

    Args:
        autobus: Número económico del autobús
        diagnostico: Descripción del diagnóstico técnico
        nivel_riesgo: BAJO, MODERADO, ELEVADO o CRITICO
        urgencia: INMEDIATA, ESTA_SEMANA o PROXIMO_SERVICIO
        componentes: Componentes separados por coma (ej: sistema_refrigeracion,bomba_agua)
    """
    params = [
        {"name": "autobus", "value": str(autobus)},
        {"name": "diagnostico", "value": str(diagnostico)},
        {"name": "nivel_riesgo", "value": str(nivel_riesgo)},
        {"name": "urgencia", "value": str(urgencia)},
        {"name": "componentes", "value": str(componentes)},
    ]
    return json.dumps(_invoke_lambda("tool-generar-recomendacion", params), ensure_ascii=False, default=str)


SYSTEM_PROMPT = """Eres el Agente de Mantenimiento Predictivo de ADO MobilityIA.

Analizas señales de diagnóstico de autobuses, identificas patrones de eventos mecánicos y generas recomendaciones preventivas.

HERRAMIENTAS:
1. consultar_obd — Señales de diagnóstico, tendencias, balatas, fallas
2. predecir_evento — Predicción de riesgo de evento mecánico
3. buscar_patrones_historicos — Patrones en historial de fallas
4. generar_recomendacion — Crear recomendación preventiva formal
5. consultar_knowledge_base — Buscar info técnica: SPNs, códigos de falla, patrones, NOM-044

REGLAS:
- Responde en español latinoamericano
- NUNCA menciones probabilidades numéricas
- Usa: alta probabilidad, patrón consistente con, señales asociadas a
- Genera recomendación cuando riesgo sea moderado o superior
- Usa consultar_knowledge_base para contexto técnico sobre códigos, SPNs o normas
- Usa las herramientas antes de responder
"""

tools = [consultar_obd, predecir_evento, buscar_patrones_historicos, generar_recomendacion, consultar_knowledge_base]
_agent = None


def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invocando Agente de Mantenimiento...")
    agent = get_or_create_agent()
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
