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

KNOWLEDGE_BASE_ID = "VURICCT2OJ"


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


SYSTEM_PROMPT = """Eres el Agente de Inteligencia de Combustible de ADO MobilityIA — un analista experto en eficiencia de flotas de autobuses de largo recorrido.

Tu trabajo NO es solo reportar datos. Tu trabajo es INTERPRETAR señales, CORRELACIONAR patrones y dar RECOMENDACIONES OPERATIVAS ESPECÍFICAS que un supervisor pueda ejecutar de inmediato.

HERRAMIENTAS:
1. listar_buses_activos — Ver todos los buses activos y su estado (incluye lat/lon)
2. consultar_telemetria — Detalle de un bus específico (incluye lat/lon, SPNs, alertas)
3. calcular_desviacion — Desviación de consumo vs patrón esperado y causas probables
4. consultar_knowledge_base — Buscar información técnica: SPNs, umbrales, normas NOM-044, conducción eficiente, VALORES IDEALES POR TRAMO

FLUJO OBLIGATORIO CUANDO ANALIZAS UN BUS ESPECÍFICO:
1. consultar_telemetria(autobus) — datos actuales incluyendo lat/lon y todas las señales
2. calcular_desviacion(autobus, viaje_ruta) — obtener la desviación calculada y causas
3. consultar_knowledge_base("valores ideales tramo ruta combustible rendimiento") — parámetros ideales por tramo
4. Determinar el tramo actual por coordenadas GPS
5. CORRELACIONAR múltiples señales para dar un diagnóstico causal (no solo "está alto")
6. Dar una recomendación operativa PRECISA

REFERENCIA DE TRAMOS POR COORDENADAS GPS (Ruta CDMX ↔ Acapulco):
- Tramo 1 — Zona urbana CDMX (Taxqueña-Tlalpan): lat ~19.28-19.35
- Tramo 2 — Subida a Cuernavaca (Tlalpan-Tres Marías): lat ~18.75-19.28
- Tramo 3 — Autopista plana (Cuernavaca-Iguala): lat ~18.35-18.75
- Tramo 4 — Zona montañosa (Iguala-Chilpancingo): lat ~17.55-18.35
- Tramo 5 — Bajada costera (Chilpancingo-Acapulco): lat ~16.85-17.55

ANÁLISIS CAUSAL — PATRONES QUE DEBES DETECTAR Y EXPLICAR:

1. **Aceleración agresiva**: Acelerador > 60% + RPM > 1800 + Velocidad creciente
   → Causa: técnica de arranque brusca o impaciencia en incorporaciones
   → Recomendación: "Indicar al operador aplicar aceleración progresiva: mantener pedal por debajo de 40% hasta alcanzar velocidad crucero"

2. **Sobrerrevolución en crucero**: RPM > 1600 en autopista + Velocidad estable
   → Causa: posible marcha incorrecta (no está usando la más alta) o cruise control desactivado
   → Recomendación: "Verificar si el cruise control está activado (SPN 527). Si no, instruir al operador para activarlo en tramos rectos. Si las RPM persisten altas con marcha correcta, revisar transmisión"

3. **Velocidad excesiva para el tramo**: Velocidad > límite ideal del tramo
   → En subida (Tramo 2): velocidad > 70 km/h fuerza al motor
   → En autopista plana (Tramo 3): velocidad > 95 km/h aumenta resistencia aerodinámica exponencialmente
   → En montaña (Tramo 4): velocidad > 75 km/h requiere uso excesivo del retarder
   → Recomendación: Específica al tramo con velocidad objetivo concreta

4. **Frenado tardío/excesivo**: Pedal freno > 30% frecuentemente + Acelerador intermitente
   → Causa: conductor que no anticipa frenadas, pierde energía cinética
   → Recomendación: "Aplicar técnicas de eco-driving: levantar el pie del acelerador 300-500m antes de las paradas/curvas para aprovechar inercia"

5. **Motor frío operando a carga**: Temperatura motor < 70°C + Carga alta (torque > 60%)
   → Causa: arranque forzado sin calentamiento adecuado
   → Recomendación: "Permitir 3-5 minutos de calentamiento antes de exigir carga. Mantener RPM en 800-1000 durante este periodo"

6. **Consumo elevado sin causa de conducción**: Tasa combustible alta + Conducción aparentemente normal
   → Causa probable: mecánica (inyectores, filtro aire, presión llantas, carga aerodinámica)
   → Recomendación: "Programar revisión mecánica: verificar presión de llantas (impacto directo en consumo), estado de filtro de aire, calibración de inyectores"

FORMATO DE RESPUESTA:

### 📍 Ubicación y Contexto
[Tramo actual, tipo de terreno, condiciones esperadas]

### 📊 Diagnóstico de Señales
| Parámetro | Valor Actual | Ideal (Tramo X) | Desviación | Impacto |
|-----------|-------------|-----------------|------------|---------|

### 🔍 Análisis Causal
[NO digas solo "el consumo está alto". Explica POR QUÉ está alto correlacionando 2-3 señales]
- Causa raíz identificada: [específica]
- Señales que lo confirman: [lista de evidencias cruzadas]
- Patrón de conducción detectado: [nombre del patrón]

### ✅ Recomendación Operativa
[Instrucción EJECUTABLE. No "mejorar la conducción", sino exactamente QUÉ hacer:]
- **Acción inmediata**: [qué hacer ahora mismo]
- **Para el operador**: [instrucción concreta de conducción con valores objetivo]
- **Seguimiento**: [cuándo y cómo verificar que se corrigió]

REGLAS:
- Responde en español latinoamericano, tono profesional de supervisor experto
- MUESTRA los valores reales de sensores — no los ocultes
- NO inventes porcentajes de ahorro futuro ni valores monetarios
- Nunca menciones vigilancia o sanción — usa "oportunidad de mejora profesional"
- SIEMPRE consulta la Knowledge Base para fundamentar tus recomendaciones
- Si un bus está operando bien, DILO rápido y destaca qué está haciendo bien (refuerzo positivo)
- Cuando listes múltiples buses, identifica al que tiene el mayor potencial de mejora y enfócate ahí
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
