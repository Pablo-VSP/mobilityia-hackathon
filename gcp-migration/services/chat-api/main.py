"""
chat-api — API de chat unificada (GCP Cloud Run).

Recibe prompts del frontend, enruta al agente correcto (combustible/mantenimiento)
y retorna la respuesta. Soporta invocación a ambos agentes simultáneamente.
"""

import asyncio
import json
import logging
import os
import sys

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADO MobilityIA — Chat API (GCP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def _detect_agent(prompt: str) -> str:
    """Detect which agent to invoke based on keywords."""
    lower = prompt.lower()
    score_m = sum(1 for kw in _KW_MANTENIMIENTO if kw in lower)
    score_c = sum(1 for kw in _KW_COMBUSTIBLE if kw in lower)
    return "mantenimiento" if score_m > score_c else "combustible"


async def _invoke_agent_service(url: str, prompt: str, timeout: float = 120.0) -> dict:
    """Call an agent Cloud Run service."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{url}/invoke", json={"prompt": prompt})
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/chat")
async def chat(request: Request):
    """
    Chat endpoint — routes to appropriate agent(s).

    Body: {"prompt": "...", "agente": "combustible|mantenimiento|ambos"}
    """
    body = await request.json()
    prompt = body.get("prompt", "").strip()
    agente = body.get("agente", "").strip().lower()

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "prompt requerido"})

    # Route to agent(s)
    if agente == "ambos":
        # Invoke both agents in parallel
        try:
            results = await asyncio.gather(
                _invoke_agent_service(config.AGENTE_COMBUSTIBLE_URL, prompt),
                _invoke_agent_service(config.AGENTE_MANTENIMIENTO_URL, prompt),
                return_exceptions=True,
            )

            respuestas = []
            for i, result in enumerate(results):
                agent_name = "combustible" if i == 0 else "mantenimiento"
                if isinstance(result, Exception):
                    respuestas.append(f"**[{agent_name.title()}]** Error: {str(result)[:200]}")
                else:
                    texto = result.get("respuesta", "Sin respuesta.")
                    respuestas.append(f"## Agente de {agent_name.title()}\n\n{texto}")

            combined = "\n\n---\n\n".join(respuestas)
            return {
                "respuesta": combined,
                "agente_usado": "ambos",
                "session_id": f"chat-{os.urandom(8).hex()}",
            }

        except Exception as e:
            logger.error(f"Dual agent error: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)[:500]})

    # Single agent
    if agente not in ("combustible", "mantenimiento"):
        agente = _detect_agent(prompt)

    agent_url = (
        config.AGENTE_COMBUSTIBLE_URL if agente == "combustible"
        else config.AGENTE_MANTENIMIENTO_URL
    )

    try:
        result = await _invoke_agent_service(agent_url, prompt)
        return {
            "respuesta": result.get("respuesta", "Sin respuesta."),
            "agente_usado": agente,
            "session_id": f"chat-{os.urandom(8).hex()}",
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"Agent HTTP error: {e}")
        return JSONResponse(status_code=502, content={"error": f"Agent returned {e.response.status_code}"})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)[:500]})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "chat-api"}
