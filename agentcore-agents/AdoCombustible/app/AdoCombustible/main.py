"""
ADO MobilityIA — Agente de Inteligencia de Combustible
Bedrock AgentCore Runtime + Strands Agents + Knowledge Base RAG
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
    """Invoca una Lambda tool y retorna el body parseado."""
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
    """Busca información en la base de conocimiento de ADO MobilityIA.

    Contiene manuales técnicos, catálogo de SPNs, códigos de falla,
    normas de conducción eficiente, umbrales de consumo por ruta,
    y normativa NOM-044 de emisiones.

    Usa esta herramienta cuando necesites contexto técnico sobre:
    - Significado de un código SPN o de falla
    - Umbrales normales de consumo por ruta
    - Normas de conducción eficiente
    - Regulaciones ambientales (NOM-044)

    Args:
        consulta: Pregunta o tema a buscar en la base de conocimiento
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
def consultar_telemetria(autobus: str, ultimos_n_registros: int = 10) -> str:
    """Consulta los últimos registros de telemetría de un autobús.
    Retorna variables actuales, alertas activas e historial reciente.

    Args:
        autobus: Número económico del autobús (ej: 7311, 7309)
        ultimos_n_registros: Registros recientes (default 10, max 50)
    """
    params = [
        {"name": "autobus", "value": str(autobus)},
        {"name": "ultimos_n_registros", "value": str(ultimos_n_registros)},
    ]
    return json.dumps(_invoke_lambda("tool-consultar-telemetria", params), ensure_ascii=False, default=str)


@tool
def calcular_desviacion(autobus: str, viaje_ruta: str) -> str:
    """Calcula la desviación del consumo de combustible respecto al patrón esperado.

    Args:
        autobus: Número económico del autobús (ej: 7311)
        viaje_ruta: Nombre de la ruta (ej: ACAPULCO COSTERA - MEXICO TAXQUENA)
    """
    params = [
        {"name": "autobus", "value": str(autobus)},
        {"name": "viaje_ruta", "value": str(viaje_ruta)},
    ]
    return json.dumps(_invoke_lambda("tool-calcular-desviacion", params), ensure_ascii=False, default=str)


@tool
def listar_buses_activos(viaje_ruta: str = "") -> str:
    """Lista autobuses con telemetría activa en los últimos 5 minutos, ordenados por severidad.

    Args:
        viaje_ruta: Filtrar por ruta (opcional). Vacío para ver todos.
    """
    params = []
    if viaje_ruta:
        params.append({"name": "viaje_ruta", "value": str(viaje_ruta)})
    return json.dumps(_invoke_lambda("tool-listar-buses-activos", params), ensure_ascii=False, default=str)


SYSTEM_PROMPT = """Eres el Agente de Inteligencia de Combustible de ADO MobilityIA.

Analizas el consumo de combustible de la flota de autobuses y generas alertas accionables.

HERRAMIENTAS:
1. listar_buses_activos — Ver todos los buses activos y su estado
2. consultar_telemetria — Detalle de un bus específico
3. calcular_desviacion — Desviación de consumo y causas probables
4. consultar_knowledge_base — Buscar información técnica: SPNs, umbrales, normas NOM-044, conducción eficiente

REGLAS:
- Responde en español latinoamericano
- NUNCA menciones porcentajes de ahorro ni valores numéricos de mejora
- Usa: mejora significativa, reducción notable, oportunidad de optimización
- Nunca menciones vigilancia o sanción
- Usa consultar_knowledge_base cuando necesites contexto técnico sobre SPNs, umbrales o normas
- Usa las herramientas de telemetría antes de responder sobre buses específicos
"""

tools = [consultar_telemetria, calcular_desviacion, listar_buses_activos, consultar_knowledge_base]
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
    log.info("Invocando Agente de Combustible...")
    agent = get_or_create_agent()
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
