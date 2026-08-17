"""
agente-combustible — Agente de Inteligencia de Combustible (GCP Cloud Run).

Usa Gemini 1.5 Flash con function calling nativo. Los tools son funciones
locales que consultan Firestore directamente (sin Lambdas intermedias).
Incluye RAG con FAISS in-memory para Knowledge Base.
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

import google.generativeai as genai

from shared.firestore_utils import query_latest_records, scan_recent
from shared.spn_catalog import cargar_catalogo_spn, obtener_spn
from shared.gcs_utils import read_json_from_gcs, read_bytes_from_gcs
from shared.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADO MobilityIA — Agente Combustible (GCP)")

# ---------------------------------------------------------------------------
# Gemini configuration
# ---------------------------------------------------------------------------
genai.configure()  # Uses GOOGLE_API_KEY env var or ADC

# ---------------------------------------------------------------------------
# FAISS RAG — Knowledge Base in-memory
# ---------------------------------------------------------------------------
_faiss_index = None
_kb_documents = None


def _load_knowledge_base():
    """Load FAISS index and documents from GCS into memory."""
    global _faiss_index, _kb_documents
    if _faiss_index is not None:
        return

    try:
        import faiss

        # Load pre-computed FAISS index
        index_bytes = read_bytes_from_gcs(config.GCS_BUCKET, config.GCS_EMBEDDINGS_KEY)
        # Write to temp file for faiss to read
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(index_bytes)
            temp_path = f.name
        _faiss_index = faiss.read_index(temp_path)
        os.unlink(temp_path)

        # Load document texts
        _kb_documents = read_json_from_gcs(config.GCS_BUCKET, config.GCS_KB_TEXTS_KEY)
        logger.info(f"Knowledge Base loaded: {len(_kb_documents)} documents, index size: {_faiss_index.ntotal}")

    except Exception as e:
        logger.warning(f"FAISS KB not available (will skip RAG): {e}")
        _faiss_index = None
        _kb_documents = []


def search_knowledge_base(query: str, top_k: int = 5) -> list[dict]:
    """Search the knowledge base using FAISS similarity search."""
    _load_knowledge_base()

    if _faiss_index is None or not _kb_documents:
        return [{"contenido": "Knowledge Base no disponible.", "fuente": "", "relevancia": 0}]

    try:
        # Generate embedding for query using Gemini
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query",
        )
        query_embedding = np.array([result["embedding"]], dtype=np.float32)

        # Search FAISS
        distances, indices = _faiss_index.search(query_embedding, top_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0 or idx >= len(_kb_documents):
                continue
            doc = _kb_documents[idx]
            results.append({
                "contenido": doc.get("text", "")[:1000],
                "fuente": doc.get("source", ""),
                "relevancia": round(1.0 / (1.0 + float(dist)), 3),
            })

        return results

    except Exception as e:
        logger.error(f"KB search error: {e}")
        return [{"contenido": f"Error en búsqueda: {e}", "fuente": "", "relevancia": 0}]


# ---------------------------------------------------------------------------
# Tools — funciones locales (reemplazan Lambda invocations)
# ---------------------------------------------------------------------------

def consultar_telemetria(autobus: str, ultimos_n_registros: int = 10) -> dict:
    """Consulta los últimos registros de telemetría de un autobús."""
    records = query_latest_records(
        config.FIRESTORE_COLLECTION_TELEMETRIA,
        autobus,
        limit=min(ultimos_n_registros, 50),
    )

    if not records:
        return {"status": "sin_datos", "autobus": autobus, "mensaje": f"No hay datos para el autobús {autobus}."}

    catalogo = cargar_catalogo_spn(config.GCS_BUCKET, config.GCS_CATALOGO_KEY)
    latest = records[0]

    # Build variables actuales
    variables = []
    spn_valores = latest.get("spn_valores", {})
    for spn_key, spn_data in spn_valores.items():
        try:
            spn_id = int(spn_key)
        except ValueError:
            continue
        valor = spn_data.get("valor")
        if valor is None:
            continue
        spn_info = obtener_spn(catalogo, spn_id)
        variables.append({
            "spn_id": spn_id,
            "nombre": spn_info["name"] if spn_info else spn_data.get("name", f"SPN_{spn_id}"),
            "valor": valor,
            "unidad": spn_info["unidad"] if spn_info else spn_data.get("unidad", ""),
            "fuera_de_rango": spn_data.get("fuera_de_rango", False),
        })
    variables.sort(key=lambda v: v["spn_id"])

    return {
        "status": "success",
        "autobus": autobus,
        "timestamp": latest.get("timestamp", ""),
        "viaje_ruta": latest.get("viaje_ruta", ""),
        "operador_desc": latest.get("operador_desc", ""),
        "latitud": latest.get("latitud", 0),
        "longitud": latest.get("longitud", 0),
        "estado_consumo": latest.get("estado_consumo", ""),
        "variables_actuales": variables,
        "alertas_activas": latest.get("alertas_spn", []),
        "registros_consultados": len(records),
    }


def calcular_desviacion(autobus: str, viaje_ruta: str) -> dict:
    """Calcula desviación de consumo respecto al patrón esperado."""
    records = query_latest_records(
        config.FIRESTORE_COLLECTION_TELEMETRIA,
        autobus,
        limit=20,
    )

    if not records:
        return {"status": "sin_datos", "autobus": autobus}

    # Calculate average rendimiento for this bus
    rendimientos = []
    for r in records:
        rend = r.get("rendimiento_kml")
        if rend:
            try:
                rendimientos.append(float(rend))
            except (ValueError, TypeError):
                pass

    if not rendimientos:
        return {"status": "sin_datos", "autobus": autobus, "mensaje": "Sin datos de rendimiento."}

    avg_rendimiento = sum(rendimientos) / len(rendimientos)

    # Reference for route (from manual ambiental)
    rendimiento_ref = 3.7  # km/L (ruta pivote CDMX-Acapulco)

    desviacion_pct = ((rendimiento_ref - avg_rendimiento) / rendimiento_ref) * 100

    # Analyze contributing factors
    latest = records[0]
    factores = []
    if float(latest.get("pct_acelerador", 0) or 0) > 60:
        factores.append("Aceleración agresiva (pedal > 60%)")
    if float(latest.get("rpm", 0) or 0) > 1800:
        factores.append("RPM elevadas (> 1800, posible marcha incorrecta)")
    if float(latest.get("velocidad_kmh", 0) or 0) > 95:
        factores.append("Velocidad excesiva (> 95 km/h, mayor resistencia aerodinámica)")

    if desviacion_pct <= 0:
        clasificacion = "EFICIENTE"
    elif desviacion_pct < 15:
        clasificacion = "DESVIACION_LEVE"
    elif desviacion_pct < 30:
        clasificacion = "DESVIACION_MODERADA"
    else:
        clasificacion = "DESVIACION_SIGNIFICATIVA"

    return {
        "status": "success",
        "autobus": autobus,
        "viaje_ruta": viaje_ruta,
        "rendimiento_actual_kml": round(avg_rendimiento, 2),
        "rendimiento_referencia_kml": rendimiento_ref,
        "desviacion_porcentaje": round(desviacion_pct, 1),
        "clasificacion": clasificacion,
        "factores_contribuyentes": factores,
        "registros_analizados": len(records),
    }


def listar_buses_activos(viaje_ruta: str = "") -> dict:
    """Lista buses con telemetría activa en los últimos 5 minutos."""
    timestamp_limit = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    records = scan_recent(config.FIRESTORE_COLLECTION_TELEMETRIA, timestamp_limit)

    # Keep latest per bus
    now_iso = datetime.now(timezone.utc).isoformat()
    latest_by_bus: dict[str, dict] = {}
    for r in records:
        bus = r.get("autobus", "")
        ts = r.get("timestamp", "")
        if ts > now_iso:
            continue
        if viaje_ruta and r.get("viaje_ruta", "") != viaje_ruta:
            continue
        if bus not in latest_by_bus or ts > latest_by_bus[bus].get("timestamp", ""):
            latest_by_bus[bus] = r

    buses = []
    for bus, r in latest_by_bus.items():
        buses.append({
            "autobus": bus,
            "viaje_ruta": r.get("viaje_ruta", ""),
            "operador_desc": r.get("operador_desc", ""),
            "estado_consumo": r.get("estado_consumo", ""),
            "latitud": r.get("latitud", 0),
            "longitud": r.get("longitud", 0),
            "velocidad_kmh": r.get("velocidad_kmh", 0),
            "rendimiento_kml": r.get("rendimiento_kml", 0),
            "spns_fuera_de_rango": len(r.get("alertas_spn", [])),
        })

    # Sort by severity
    estado_order = {"ALERTA_SIGNIFICATIVA": 0, "ALERTA_MODERADA": 1, "EFICIENTE": 2, "SIN_DATOS": 3}
    buses.sort(key=lambda b: estado_order.get(b["estado_consumo"], 9))

    return {"status": "success", "total_buses": len(buses), "buses": buses}


def consultar_knowledge_base_tool(consulta: str) -> dict:
    """Busca información en la base de conocimiento."""
    results = search_knowledge_base(consulta, top_k=5)
    return {"resultados": results, "total": len(results)}


# ---------------------------------------------------------------------------
# Gemini function declarations
# ---------------------------------------------------------------------------
_TOOL_FUNCTIONS = {
    "consultar_telemetria": consultar_telemetria,
    "calcular_desviacion": calcular_desviacion,
    "listar_buses_activos": listar_buses_activos,
    "consultar_knowledge_base": consultar_knowledge_base_tool,
}

_GEMINI_TOOLS = [
    genai.protos.Tool(function_declarations=[
        genai.protos.FunctionDeclaration(
            name="consultar_telemetria",
            description="Consulta los últimos registros de telemetría de un autobús. Retorna variables actuales, alertas y estado de consumo.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "autobus": genai.protos.Schema(type=genai.protos.Type.STRING, description="Número económico del autobús (ej: 7311, 7309)"),
                    "ultimos_n_registros": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Registros recientes (default 10, max 50)"),
                },
                required=["autobus"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="calcular_desviacion",
            description="Calcula la desviación del consumo de combustible respecto al patrón esperado para la ruta.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "autobus": genai.protos.Schema(type=genai.protos.Type.STRING, description="Número económico del autobús"),
                    "viaje_ruta": genai.protos.Schema(type=genai.protos.Type.STRING, description="Nombre de la ruta"),
                },
                required=["autobus", "viaje_ruta"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="listar_buses_activos",
            description="Lista autobuses con telemetría activa en los últimos 5 minutos, ordenados por severidad.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "viaje_ruta": genai.protos.Schema(type=genai.protos.Type.STRING, description="Filtrar por ruta (opcional)"),
                },
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="consultar_knowledge_base",
            description="Busca información técnica en la base de conocimiento: SPNs, umbrales, normas NOM-044, conducción eficiente.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "consulta": genai.protos.Schema(type=genai.protos.Type.STRING, description="Pregunta o tema a buscar"),
                },
                required=["consulta"],
            ),
        ),
    ])
]

SYSTEM_PROMPT = """Eres el Agente de Inteligencia de Combustible de ADO MobilityIA — un analista experto en eficiencia de flotas de autobuses de largo recorrido.

Tu trabajo es INTERPRETAR señales, CORRELACIONAR patrones y dar RECOMENDACIONES OPERATIVAS ESPECÍFICAS.

HERRAMIENTAS:
1. listar_buses_activos — Ver todos los buses activos y su estado
2. consultar_telemetria — Detalle de un bus específico
3. calcular_desviacion — Desviación de consumo vs patrón esperado
4. consultar_knowledge_base — Buscar información técnica

REGLAS:
- Responde en español latinoamericano, tono profesional
- MUESTRA los valores reales de sensores
- NO inventes porcentajes de ahorro futuro ni valores monetarios
- Nunca menciones vigilancia o sanción
- SIEMPRE usa las herramientas antes de responder
- Si un bus está bien, dilo rápido con refuerzo positivo
"""


# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------

async def invoke_agent(prompt: str) -> str:
    """Invoke Gemini with function calling loop."""
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        tools=_GEMINI_TOOLS,
    )

    chat = model.start_chat()
    response = chat.send_message(prompt)

    # Function calling loop (max 10 iterations)
    for _ in range(10):
        # Check if model wants to call a function
        if not response.candidates:
            break

        parts = response.candidates[0].content.parts
        function_calls = [p for p in parts if p.function_call.name]

        if not function_calls:
            # No more function calls — extract final text
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
            return "\n".join(text_parts) if text_parts else "No se pudo generar una respuesta."

        # Execute all function calls
        function_responses = []
        for fc_part in function_calls:
            fn_name = fc_part.function_call.name
            fn_args = dict(fc_part.function_call.args)

            logger.info(f"Calling tool: {fn_name}({fn_args})")

            fn = _TOOL_FUNCTIONS.get(fn_name)
            if fn:
                try:
                    result = fn(**fn_args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"Tool '{fn_name}' not found"}

            function_responses.append(
                genai.protos.Part(function_response=genai.protos.FunctionResponse(
                    name=fn_name,
                    response={"result": json.dumps(result, ensure_ascii=False, default=str)},
                ))
            )

        # Send function responses back to model
        response = chat.send_message(function_responses)

    # Fallback: extract whatever text is available
    if response.candidates:
        parts = response.candidates[0].content.parts
        text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
        return "\n".join(text_parts) if text_parts else "Se alcanzó el límite de iteraciones."

    return "No se pudo completar el análisis."


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.post("/invoke")
async def invoke_endpoint(request: Request):
    """Invoke the fuel agent with a prompt."""
    body = await request.json()
    prompt = body.get("prompt", "").strip()

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "prompt requerido"})

    try:
        response_text = await invoke_agent(prompt)
        return {"respuesta": response_text, "agente": "combustible"}
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)[:500]})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agente-combustible"}
