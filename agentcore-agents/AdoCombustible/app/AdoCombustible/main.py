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
1. listar_buses_activos — Ver todos los buses activos y su estado (incluye lat/lon)
2. consultar_telemetria — Detalle de un bus específico (incluye lat/lon)
3. calcular_desviacion — Desviación de consumo y causas probables
4. consultar_knowledge_base — Buscar información técnica: SPNs, umbrales, normas NOM-044, conducción eficiente, VALORES IDEALES POR TRAMO

FLUJO OBLIGATORIO CUANDO ANALIZAS UN BUS ESPECÍFICO:
1. consultar_telemetria(autobus) — obtener datos actuales incluyendo latitud y longitud
2. consultar_knowledge_base("valores ideales tramo ruta combustible") — obtener los parámetros ideales por tramo de la ruta
3. Usar la latitud/longitud del bus para determinar en qué tramo se encuentra (ver REFERENCIA DE TRAMOS abajo)
4. Comparar los valores actuales del bus contra los valores ideales del tramo correspondiente
5. Generar recomendaciones específicas al tramo

REFERENCIA DE TRAMOS POR COORDENADAS GPS (Ruta CDMX ↔ Acapulco):
- Tramo 1 — Zona urbana CDMX (Taxqueña-Tlalpan): lat ~19.28-19.35, lon ~-99.13 a -99.17
- Tramo 2 — Subida Cuernavaca (Tlalpan-Tres Marías-Cuernavaca): lat ~18.75-19.28, lon ~-99.10 a -99.30
- Tramo 3 — Autopista plana (Cuernavaca-Iguala): lat ~18.35-18.75, lon ~-99.30 a -99.55
- Tramo 4 — Zona montañosa (Iguala-Chilpancingo): lat ~17.55-18.35, lon ~-99.45 a -99.55
- Tramo 5 — Bajada a Acapulco (Chilpancingo-Acapulco): lat ~16.85-17.55, lon ~-99.55 a -99.90

Para determinar el tramo: usa la latitud del bus. Si lat > 19.28 → Tramo 1 (urbano). Si lat 18.75-19.28 → Tramo 2 (subida). Si lat 18.35-18.75 → Tramo 3 (autopista). Si lat 17.55-18.35 → Tramo 4 (montaña). Si lat < 17.55 → Tramo 5 (bajada costera).

FORMATO DE RESPUESTA — SÉ DETALLADO Y VISUAL:
- Indica en qué tramo se encuentra el bus basándote en sus coordenadas GPS
- Incluye los VALORES REALES de los sensores que consultaste (velocidad, RPM, tasa de combustible, rendimiento, etc.)
- Compara contra los valores ideales del tramo (de la Knowledge Base)
- Usa tablas markdown cuando presentes datos de múltiples buses o múltiples sensores. Ejemplo:

| Parámetro | Valor Actual | Ideal para Tramo | Estado |
|-----------|-------------|-------------------|--------|
| Velocidad | 106 km/h | 85-95 km/h | ⚠ Excesiva |
| RPM | 2,060 | 1,200-1,500 | ⚠ Fuera de rango |

- Cuando compares buses, ordénalos del peor al mejor rendimiento
- Explica las causas probables con datos concretos del tramo

REGLAS:
- Responde en español latinoamericano
- Puedes mostrar valores de sensores y lecturas — eso NO son métricas de mejora
- Lo que NO debes hacer es inventar porcentajes de ahorro futuro ni valores monetarios
- Nunca menciones vigilancia o sanción — usa "oportunidad de mejora"
- SIEMPRE consulta la Knowledge Base cuando analices un bus específico para dar recomendaciones contextuales al tramo
- Siempre termina con una recomendación concreta y accionable
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
