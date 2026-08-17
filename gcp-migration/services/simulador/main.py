"""
simulador — Simulador de telemetría en tiempo real (GCP Cloud Run).

Equivalente a ado-simulador-telemetria Lambda. Lee viajes pre-procesados
desde Cloud Storage (viajes_consolidados.json) y simula múltiples buses
avanzando simultáneamente por sus rutas.

Se invoca via Cloud Scheduler cada 1 minuto con un HTTP POST.
Genera BURST_COUNT registros por bus espaciados TICK_INTERVAL segundos.
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.firestore_utils import batch_write_items, put_item, query_by_field
from shared.gcs_utils import read_json_from_gcs
from shared.spn_catalog import cargar_catalogo_spn, valor_fuera_de_rango
from shared.config import config
from shared.constants import (
    SPN_RENDIMIENTO, SPN_TASA_COMBUSTIBLE,
    SPN_TEMPERATURA_MOTOR, SPN_PRESION_ACEITE,
    SPN_VOLTAJE_BATERIA, SPN_NIVEL_ANTICONGELANTE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADO MobilityIA — Simulador (GCP)")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STEP_SECONDS = config.STEP_SECONDS
BURST_COUNT = config.BURST_COUNT
TICK_INTERVAL = config.TICK_INTERVAL
DESFASE_PCT = int(os.environ.get("DESFASE_PCT", "0"))

# Auto-ticket rules
_AUTO_TICKET_RULES = [
    {"field": "temperatura_motor_c", "condition": "gt", "threshold": 125,
     "componente": "sistema_refrigeracion", "diagnostico": "Temperatura del motor por encima del umbral operativo seguro"},
    {"field": "presion_aceite_kpa", "condition": "lt", "threshold": 120,
     "componente": "circuito_aceite", "diagnostico": "Presión de aceite del motor por debajo del umbral mínimo seguro"},
    {"field": "voltaje_bateria_v", "condition": "lt", "threshold": 22,
     "componente": "sistema_electrico", "diagnostico": "Voltaje de batería por debajo del umbral operativo"},
    {"field": "nivel_anticongelante_pct", "condition": "lt", "threshold": 25,
     "componente": "sistema_refrigeracion", "diagnostico": "Nivel de anticongelante críticamente bajo"},
]

# SPN → flat field mapping
_SPN_FLAT_NAMES = {
    "84": "velocidad_kmh", "190": "rpm", "91": "pct_acelerador",
    "521": "pct_freno", "183": "tasa_combustible_lh", "185": "rendimiento_kml",
    "184": "ahorro_instantaneo_kml", "96": "nivel_combustible_pct",
    "110": "temperatura_motor_c", "175": "temperatura_aceite_c",
    "100": "presion_aceite_kpa", "98": "nivel_aceite_pct",
    "111": "nivel_anticongelante_pct", "168": "voltaje_bateria_v",
    "513": "torque_pct", "917": "odometro_km", "247": "horas_motor_h",
    "1761": "nivel_urea_pct", "1099": "balata_del_izq_pct",
    "1100": "balata_del_der_pct", "1101": "balata_tras_izq1_pct",
    "1102": "balata_tras_der1_pct", "1103": "balata_tras_izq2_pct",
    "1104": "balata_tras_der2_pct",
}

# Cached data
_viajes_data = None


def _load_viajes():
    """Load consolidated trips from GCS (cached).

    Handles both formats:
      - {"viajes": [...], "metadata": {...}}  (wrapped)
      - [...]  (raw list)
    """
    global _viajes_data
    if _viajes_data is None:
        logger.info("Loading viajes from GCS...")
        raw = read_json_from_gcs(config.GCS_BUCKET, config.GCS_VIAJES_KEY)
        if isinstance(raw, dict) and "viajes" in raw:
            _viajes_data = raw["viajes"]
        elif isinstance(raw, list):
            _viajes_data = raw
        else:
            raise ValueError(f"Unexpected viajes format: {type(raw)}")
        logger.info(f"Loaded {len(_viajes_data)} viajes")
    return _viajes_data


def clasificar_consumo(spn_valores: dict) -> str:
    """Classify fuel consumption state from SPN values."""
    spn_rend = spn_valores.get(str(SPN_RENDIMIENTO))
    if spn_rend is not None:
        val = spn_rend.get("valor")
        if val is not None:
            val = float(val)
            if val >= 3.0:
                return "EFICIENTE"
            if val >= 2.0:
                return "ALERTA_MODERADA"
            return "ALERTA_SIGNIFICATIVA"

    spn_tasa = spn_valores.get(str(SPN_TASA_COMBUSTIBLE))
    if spn_tasa is not None:
        val = spn_tasa.get("valor")
        if val is not None:
            val = float(val)
            if val <= 30.0:
                return "EFICIENTE"
            if val <= 50.0:
                return "ALERTA_MODERADA"
            return "ALERTA_SIGNIFICATIVA"

    return "SIN_DATOS"


def _get_frame_for_bus(viaje: dict, bus_index: int, ahora: float) -> dict:
    """Select the current frame for a bus based on elapsed time."""
    frames = viaje["frames"]
    total_frames = len(frames)
    duracion = viaje["duracion_segundos"]

    if total_frames == 0 or duracion == 0:
        return frames[0] if frames else {}

    desfase_segundos = int(duracion * (DESFASE_PCT / 100.0) * bus_index)
    elapsed = (int(ahora) * STEP_SECONDS // TICK_INTERVAL) + desfase_segundos
    posicion_en_viaje = elapsed % duracion

    # Binary search for closest frame
    lo, hi = 0, total_frames - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if frames[mid]["segundos_desde_inicio"] <= posicion_en_viaje:
            lo = mid
        else:
            hi = mid - 1

    return frames[lo]


def _build_firestore_item(viaje: dict, frame: dict, catalogo_spn: dict, timestamp_iso: str) -> dict:
    """Build a Firestore document from a trip + frame."""
    spn_valores = {}
    alertas_spn = []
    campos_planos = {}

    for spn_key, spn_data in frame.get("spn_valores", {}).items():
        spn_id = int(spn_key)
        valor = spn_data.get("valor", 0)
        nombre = spn_data.get("name", f"SPN_{spn_id}")
        unidad = spn_data.get("unidad", "")

        fuera, mensaje = valor_fuera_de_rango(catalogo_spn, spn_id, float(valor))

        spn_valores[spn_key] = {
            "valor": valor,
            "name": nombre,
            "unidad": unidad,
            "fuera_de_rango": fuera,
        }

        if fuera:
            alertas_spn.append({
                "spn_id": spn_id,
                "name": nombre,
                "valor": valor,
                "unidad": unidad,
                "mensaje": mensaje,
            })

        flat_name = _SPN_FLAT_NAMES.get(spn_key)
        if flat_name:
            campos_planos[flat_name] = valor

    estado_consumo = clasificar_consumo(spn_valores)
    autobus = str(viaje["autobus"])

    item = {
        "autobus": autobus,
        "timestamp": timestamp_iso,
        "viaje_id": viaje["viaje_id"],
        "operador_cve": viaje.get("operador_cve", ""),
        "operador_desc": viaje.get("operador_desc", ""),
        "viaje_ruta": viaje.get("viaje_ruta", ""),
        "viaje_ruta_origen": viaje.get("viaje_ruta_origen", ""),
        "viaje_ruta_destino": viaje.get("viaje_ruta_destino", ""),
        "latitud": frame.get("latitud", 0),
        "longitud": frame.get("longitud", 0),
        "spn_valores": spn_valores,
        "alertas_spn": alertas_spn,
        "estado_consumo": estado_consumo,
        "doc_id": f"{autobus}_{timestamp_iso}",
        **campos_planos,
    }

    return item


def _generate_auto_tickets(items: list[dict], timestamp_iso: str) -> int:
    """Auto-generate maintenance tickets for critical conditions."""
    tickets_created = 0

    for item in items:
        autobus = item.get("autobus", "")
        estado = item.get("estado_consumo", "")

        if estado != "ALERTA_SIGNIFICATIVA":
            continue

        triggered_rules = []
        for rule in _AUTO_TICKET_RULES:
            val = item.get(rule["field"])
            if val is None:
                continue
            val = float(val)
            if rule["condition"] == "gt" and val > rule["threshold"]:
                triggered_rules.append(rule)
            elif rule["condition"] == "lt" and val < rule["threshold"]:
                triggered_rules.append(rule)

        alertas_spn = item.get("alertas_spn", [])
        if not triggered_rules and len(alertas_spn) < 3:
            continue

        # Check existing active alerts
        existing = query_by_field(
            config.FIRESTORE_COLLECTION_ALERTAS,
            field="autobus",
            value=autobus,
            limit=1,
        )
        active_exists = any(a.get("estado") == "ACTIVA" for a in existing)
        if active_exists:
            continue

        componentes = list({r["componente"] for r in triggered_rules}) or ["revision_general"]
        diagnostico_parts = [r["diagnostico"] for r in triggered_rules[:3]]
        diagnostico = ". ".join(diagnostico_parts) if diagnostico_parts else (
            f"El autobús {autobus} presenta múltiples señales fuera de rango."
        )

        nivel_riesgo = "ELEVADO" if len(triggered_rules) >= 2 else "MODERADO"
        urgencia = "ESTA_SEMANA" if nivel_riesgo == "ELEVADO" else "PROXIMO_SERVICIO"

        now_dt = datetime.now(timezone.utc)
        alert_item = {
            "alerta_id": str(uuid.uuid4()),
            "timestamp": timestamp_iso,
            "autobus": autobus,
            "tipo_alerta": "MANTENIMIENTO",
            "nivel_riesgo": nivel_riesgo,
            "diagnostico": diagnostico,
            "urgencia": urgencia,
            "componentes": componentes,
            "numero_referencia": f"OT-{now_dt.year}-{now_dt.month:02d}{now_dt.day:02d}-{autobus}",
            "estado": "ACTIVA",
            "agente_origen": "auto-simulador",
            "viaje_ruta": item.get("viaje_ruta", ""),
            "operador_desc": item.get("operador_desc", ""),
        }

        try:
            put_item(config.FIRESTORE_COLLECTION_ALERTAS, alert_item, doc_id=alert_item["alerta_id"])
            tickets_created += 1
            logger.info(f"Auto-ticket created for bus {autobus}: {nivel_riesgo}")
        except Exception as e:
            logger.error(f"Failed to create auto-ticket for {autobus}: {e}")

    return tickets_created


@app.post("/simulate")
async def simulate():
    """
    Ejecuta un ciclo de simulación (burst de 6 ticks).
    Invocado por Cloud Scheduler cada minuto.
    """
    try:
        viajes = _load_viajes()
        catalogo = cargar_catalogo_spn(config.GCS_BUCKET, config.GCS_CATALOGO_KEY)

        ahora = time.time()
        total_items = 0
        total_tickets = 0
        last_tick_items = []

        for tick in range(BURST_COUNT):
            tick_time = ahora + (tick * TICK_INTERVAL)
            tick_dt = datetime.fromtimestamp(tick_time, tz=timezone.utc)
            timestamp_iso = tick_dt.isoformat()

            items_for_tick = []

            for bus_index, viaje in enumerate(viajes):
                frame = _get_frame_for_bus(viaje, bus_index, tick_time)
                item = _build_firestore_item(viaje, frame, catalogo, timestamp_iso)
                items_for_tick.append(item)

            # Write batch to Firestore
            if items_for_tick:
                batch_write_items(config.FIRESTORE_COLLECTION_TELEMETRIA, items_for_tick)
                total_items += len(items_for_tick)

            # Last tick items for auto-ticket evaluation
            if tick == BURST_COUNT - 1:
                last_tick_items = items_for_tick

        # Generate auto-tickets from last tick
        if last_tick_items:
            total_tickets = _generate_auto_tickets(last_tick_items, timestamp_iso)

        result = {
            "status": "ok",
            "buses_simulados": len(viajes),
            "ticks": BURST_COUNT,
            "items_escritos": total_items,
            "tickets_generados": total_tickets,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(json.dumps(result))
        return result

    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "simulador"}
