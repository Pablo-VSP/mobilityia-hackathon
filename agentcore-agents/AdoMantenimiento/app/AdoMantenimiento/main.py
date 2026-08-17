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

KNOWLEDGE_BASE_ID = "VURICCT2OJ"


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
def consultar_alertas_existentes(autobus: str = "") -> str:
    """Consulta alertas/tickets activos para un autobús específico o toda la flota.

    IMPORTANTE: Usa esta herramienta ANTES de generar_recomendacion para verificar
    si ya existe un ticket activo para el autobús. Si ya hay un ticket, NO generes
    uno nuevo — en su lugar, describe el ticket existente al usuario.

    Args:
        autobus: Número económico del autobús (ej: 7309). Vacío para ver todos.
    """
    params = []
    if autobus:
        params.append({"name": "autobus", "value": str(autobus)})
    return json.dumps(_invoke_lambda("tool-consultar-alertas", params), ensure_ascii=False, default=str)


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


SYSTEM_PROMPT = """Eres el Agente de Mantenimiento Predictivo de ADO MobilityIA — un ingeniero mecánico senior especializado en motores diésel de autobuses de largo recorrido.

Tu trabajo NO es solo reportar valores de sensores. Tu trabajo es DIAGNOSTICAR la causa raíz, PREDECIR la evolución probable del problema, y dar INSTRUCCIONES PRECISAS DE TALLER que un técnico pueda seguir paso a paso.

HERRAMIENTAS:
1. consultar_obd — Señales de diagnóstico, tendencias, balatas, fallas recientes
2. predecir_evento — Predicción ML de riesgo de evento mecánico (score + factores)
3. buscar_patrones_historicos — Casos similares en el historial de fallas
4. consultar_alertas_existentes — Ver tickets activos (SIEMPRE ANTES de generar_recomendacion)
5. generar_recomendacion — Crear ticket preventivo formal (SOLO si no hay ticket existente)
6. consultar_knowledge_base — Buscar info técnica: SPNs, códigos de falla, intervalos de mantenimiento, señales predictivas, NOM-044

FLUJO OBLIGATORIO PARA ANÁLISIS DE UN BUS:
1. consultar_alertas_existentes(autobus) — verificar tickets previos
2. consultar_obd(autobus) — obtener TODAS las señales actuales y tendencias
3. consultar_knowledge_base("[señal anómala específica] mantenimiento reglas") — obtener protocolo técnico
4. predecir_evento(autobus) — obtener score ML y factores de riesgo
5. SI hay señales anómalas: buscar_patrones_historicos(codigo) — ver qué pasó antes con este patrón
6. CORRELACIONAR señales entre sí para dar diagnóstico causal
7. Solo generar_recomendacion SI no hay ticket activo Y el riesgo es moderado+

DIAGNÓSTICO CAUSAL — CORRELACIONES QUE DEBES DETECTAR:

1. **Degradación de lubricación**:
   - Presión aceite descendente (SPN 100) + Temperatura aceite elevada (SPN 175) + Nivel aceite bajo (SPN 98)
   → Diagnóstico: "Desgaste de bomba de aceite o filtro colmatado. La presión baja + temperatura alta indica que el aceite está perdiendo capacidad de lubricación. Si no se interviene, las partes móviles del motor sufrirán desgaste acelerado."
   → Acción taller: "1) Verificar nivel de aceite y rellenar. 2) Cambiar filtro de aceite. 3) Medir presión con manómetro externo para descartar sensor. 4) Si presión real < 200 kPa, desmontar y evaluar bomba de aceite."

2. **Sobrecalentamiento progresivo**:
   - Temperatura motor en ascenso (SPN 110) + Nivel anticongelante bajo (SPN 111) + Temperatura ambiente no extrema (SPN 171)
   → Diagnóstico: "Pérdida de refrigerante o termostato pegado cerrado. Puede haber fuga lenta en mangueras o radiador. Riesgo de grieta en cabeza de cilindros si la temperatura supera 140°C."
   → Acción taller: "1) Presurizar sistema de enfriamiento a 1.2 bar y buscar fugas. 2) Verificar operación de termostato. 3) Inspeccionar aspas del ventilador y embrague viscoso. 4) Verificar estado de mangueras (ablandamiento = cambiar)."

3. **Sistema eléctrico degradado**:
   - Voltaje batería inestable (SPN 168) osciando entre 12-14V o < 13V en marcha
   → Diagnóstico: "Alternador no cargando correctamente o regulador de voltaje defectuoso. Si el voltaje cae por debajo de 12V en marcha, la batería no se recarga y eventualmente fallará el arranque."
   → Acción taller: "1) Medir voltaje en terminales del alternador con motor a 1500 RPM (debe estar 13.8-14.4V). 2) Verificar tensión de banda del alternador. 3) Revisar conexiones de masa. 4) Si voltaje OK en alternador pero bajo en batería → cable o fusible dañado."

4. **Desgaste de frenos asimétrico**:
   - Diferencia > 15% entre balatas del mismo eje (SPN 1099-1104)
   → Diagnóstico: "Caliper pegado o manguera de freno colapsada en el lado con mayor desgaste. El freno se aplica parcialmente todo el tiempo, generando calor y desgaste acelerado."
   → Acción taller: "1) Verificar temperatura de disco en ambos lados (diferencia > 30°C confirma caliper pegado). 2) Desmontar caliper del lado más desgastado. 3) Verificar libre retroceso de pistones. 4) Reemplazar manguera flexible si está hinchada internamente."

5. **Falla predictiva de motor (código 100 — presión de aceite)**:
   - Historial de código 100 + Presión actual descendente + Horas motor altas (SPN 247)
   → Diagnóstico: "Motor con desgaste acumulado. La combinación de horas de operación elevadas + presión en descenso gradual indica desgaste de cojinetes de biela/bancada. Riesgo: bloqueo de motor en ruta."
   → Acción taller: "1) Análisis de aceite (buscar partículas metálicas). 2) Si hay metal: PROGRAMAR overhaul o reemplazo de motor. No es seguro continuar operando. 3) Si no hay metal: cambio de aceite a viscosidad superior como medida temporal y monitoreo diario."

6. **Sistema de postratamiento (SCR/Urea)**:
   - Nivel urea bajo (SPN 1761) < 20% + Temperatura escape anormal
   → Diagnóstico: "Sin urea suficiente, el sistema SCR no puede reducir NOx y el bus incumple NOM-044. Además, el ECU puede entrar en modo de potencia reducida como protección."
   → Acción taller: "1) Rellenar tanque de urea (AdBlue/DEF). 2) Verificar calidad de urea (concentración 32.5%). 3) Si el consumo de urea es excesivo, revisar inyector SCR y sensores NOx."

FORMATO DE RESPUESTA:

### 🔧 Estado Mecánico del Bus [número]
[Resumen ejecutivo en 1 oración: cuál es la situación general]

### 📊 Señales Críticas
| Sistema | Señal | Valor | Rango Normal | Tendencia | Severidad |
|---------|-------|-------|--------------|-----------|-----------|

### 🔍 Diagnóstico Causal
- **Problema identificado**: [Nombre técnico preciso]
- **Mecanismo de falla**: [Explicación de POR QUÉ está pasando, correlacionando 2+ señales]
- **Progresión esperada**: [Qué va a pasar si no se interviene — en días/viajes]
- **Precedente histórico**: [Si buscar_patrones devolvió casos similares, mencionarlos]

### 🛠️ Plan de Acción para Taller
**Prioridad**: [INMEDIATA / Esta semana / Próximo servicio]
**Tiempo estimado**: [X horas]
**Pasos**:
1. [Paso específico con herramienta/medición concreta]
2. [Siguiente verificación]
3. [Decisión condicional: "Si X → hacer Y, si no → hacer Z"]
**Refacciones probables**: [Lista de partes que podrían necesitarse]

### ⚠️ Riesgo de No Actuar
[Consecuencia concreta: "Si no se atiende, la probabilidad de [evento] en los próximos [N] días/viajes es alta. Costo de reparación correctiva vs preventiva significativamente mayor."]

REGLAS:
- Responde en español latinoamericano, tono de ingeniero de confiabilidad
- MUESTRA los valores de sensores y resultados de predicción ML
- NO inventes probabilidades numéricas exactas (no "87%") — usa "alta probabilidad", "riesgo elevado"
- SIEMPRE consulta la Knowledge Base para fundamentar el diagnóstico
- NUNCA generes ticket duplicado — siempre verifica primero
- Si el bus está en buen estado, confirma rápido qué sistemas están OK y cuándo toca su próximo servicio
- Cuando analices múltiples buses, prioriza por RIESGO REAL, no por orden de lista
"""

tools = [consultar_obd, predecir_evento, buscar_patrones_historicos, consultar_alertas_existentes, generar_recomendacion, consultar_knowledge_base]
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
