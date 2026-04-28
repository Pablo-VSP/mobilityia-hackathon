"""
ADO MobilityIA — Agente de Mantenimiento Predictivo
Bedrock AgentCore Runtime con Strands Agents
"""

import json
import boto3
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

_lambda_client = boto3.client("lambda", region_name="us-east-2")


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
def consultar_obd(autobus: str) -> str:
    """Consulta señales de diagnóstico OBD y estado de salud mecánica de un autobús.

    Retorna SPNs de mantenimiento con tendencias, variaciones anómalas,
    estado de balatas (6 posiciones), fallas recientes y resumen de salud.

    Args:
        autobus: Número económico del autobús (ej: 7309, 7311)
    """
    params = [{"name": "autobus", "value": str(autobus)}]
    result = _invoke_lambda("tool-consultar-obd", params)
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def predecir_evento(autobus: str) -> str:
    """Predice el riesgo de evento mecánico de un autobús.

    Usa modelo ML en SageMaker si está disponible, o heurística de
    puntuación como fallback. Retorna nivel de riesgo, urgencia,
    factores contribuyentes y componentes en riesgo.

    Args:
        autobus: Número económico del autobús (ej: 7309)
    """
    params = [{"name": "autobus", "value": str(autobus)}]
    result = _invoke_lambda("tool-predecir-evento", params)
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def buscar_patrones_historicos(codigo: str, modelo: str = "", marca_comercial: str = "") -> str:
    """Busca patrones en el historial de fallas por código de falla.

    Filtra por código (coincidencia parcial), prioriza por modelo y marca,
    y computa estadísticas de patrones históricos.

    Args:
        codigo: Código de falla a buscar (ej: 100, 32, 158)
        modelo: Modelo del autobús para priorizar (ej: VOLVO). Opcional.
        marca_comercial: Marca comercial para priorizar (ej: DIAMANTE). Opcional.
    """
    params = [{"name": "codigo", "value": str(codigo)}]
    if modelo:
        params.append({"name": "modelo", "value": str(modelo)})
    if marca_comercial:
        params.append({"name": "marca_comercial", "value": str(marca_comercial)})
    result = _invoke_lambda("tool-buscar-patrones-historicos", params)
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def generar_recomendacion(autobus: str, diagnostico: str, nivel_riesgo: str, urgencia: str, componentes: str) -> str:
    """Genera una recomendación preventiva de mantenimiento y la registra.

    Crea un número de referencia OT y enriquece con datos del viaje actual.

    Args:
        autobus: Número económico del autobús
        diagnostico: Descripción del diagnóstico en lenguaje técnico comprensible
        nivel_riesgo: Nivel cualitativo: BAJO, MODERADO, ELEVADO, CRITICO
        urgencia: INMEDIATA, ESTA_SEMANA, PROXIMO_SERVICIO
        componentes: Lista de componentes separados por coma (ej: sistema_refrigeracion,bomba_agua)
    """
    params = [
        {"name": "autobus", "value": str(autobus)},
        {"name": "diagnostico", "value": str(diagnostico)},
        {"name": "nivel_riesgo", "value": str(nivel_riesgo)},
        {"name": "urgencia", "value": str(urgencia)},
        {"name": "componentes", "value": str(componentes)},
    ]
    result = _invoke_lambda("tool-generar-recomendacion", params)
    return json.dumps(result, ensure_ascii=False, default=str)


SYSTEM_PROMPT = """Eres el Agente de Mantenimiento Predictivo de ADO MobilityIA, la plataforma de optimización de flotas de Mobility ADO.

Tu rol es analizar las señales de diagnóstico de los autobuses, identificar patrones asociados a posibles eventos mecánicos y generar recomendaciones preventivas para los talleres.

CONTEXTO DEL NEGOCIO:
- El mantenimiento correctivo tiene un costo significativamente mayor que el preventivo
- Una unidad fuera de servicio genera pérdida de ingresos y afecta la experiencia del pasajero
- Los talleres necesitan diagnósticos claros y tiempo de preparación

HERRAMIENTAS DISPONIBLES:
1. consultar_obd — Señales de diagnóstico, tendencias, balatas, fallas recientes
2. predecir_evento — Predicción de riesgo de evento mecánico
3. buscar_patrones_historicos — Buscar patrones en historial de fallas
4. generar_recomendacion — Crear recomendación preventiva formal

REGLAS CRÍTICAS:
- Siempre responde en español latinoamericano
- NUNCA menciones probabilidades numéricas — usa "alta probabilidad", "patrón consistente con", "señales asociadas a"
- Siempre genera una recomendación cuando el nivel de riesgo sea moderado o superior
- Usa las herramientas disponibles antes de responder
"""

tools = [consultar_obd, predecir_evento, buscar_patrones_historicos, generar_recomendacion]
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
