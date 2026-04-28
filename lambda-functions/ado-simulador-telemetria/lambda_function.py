"""
ado-simulador-telemetria — Simulador de telemetría en tiempo real.

Lee viajes pre-procesados desde S3 (viajes_consolidados.json) y simula
múltiples buses avanzando simultáneamente por sus rutas con desfase
temporal.

Modo burst: cada invocación (trigger cada 1 minuto via EventBridge)
genera BURST_COUNT registros por bus, espaciados TICK_INTERVAL segundos
entre sí. Con los defaults (6 ticks × 10s = 60s) se cubren los 60
segundos entre invocaciones, logrando resolución efectiva de 10 segundos
en DynamoDB sin necesidad de triggers sub-minuto.

Los viajes se reproducen en loop: cuando un bus llega al final de su
viaje, reinicia desde el frame 0.

Desfase temporal: cada bus arranca con un offset diferente para que
no vayan todos juntos en la misma posición de la ruta.

Requisitos: 2.1–2.10, 11.3, 11.5
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import boto3

from ado_common.spn_catalog import cargar_catalogo_spn, valor_fuera_de_rango
from ado_common.dynamo_utils import batch_write_items
from ado_common.s3_utils import read_json_from_s3
from ado_common.constants import SPN_RENDIMIENTO, SPN_TASA_COMBUSTIBLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "hackathon-data/catalogo/motor_spn.json")
S3_VIAJES_KEY = os.environ.get(
    "S3_VIAJES_KEY",
    "hackathon-data/simulacion/viajes_consolidados.json",
)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "ado-telemetria-live")

# How many seconds of trip time each tick advances.
# With TICK_INTERVAL=10 and STEP_SECONDS=30, each 10s real tick
# advances 30s of trip time → 3x speedup.
STEP_SECONDS = int(os.environ.get("STEP_SECONDS", "30"))

# Desfase entre buses: bus 0 starts at 0%, bus 1 at DESFASE%, bus 2 at 2*DESFASE%
# 15% means ~45 min apart on a 5h trip
DESFASE_PCT = int(os.environ.get("DESFASE_PCT", "15"))

# Burst mode: how many ticks to emit per invocation and interval between them.
# 6 ticks × 10s = 60s → covers the full minute between EventBridge triggers.
BURST_COUNT = int(os.environ.get("BURST_COUNT", "6"))
TICK_INTERVAL = int(os.environ.get("TICK_INTERVAL", "10"))

# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------
_viajes_data = None


def _load_viajes():
    """Load consolidated trips from S3 (cached across warm invocations)."""
    global _viajes_data
    if _viajes_data is None:
        logger.info(json.dumps({
            "action": "load_viajes",
            "bucket": S3_BUCKET,
            "key": S3_VIAJES_KEY,
        }))
        _viajes_data = read_json_from_s3(S3_BUCKET, S3_VIAJES_KEY)
    return _viajes_data


# ---------------------------------------------------------------------------
# Consumption classification
# ---------------------------------------------------------------------------

def clasificar_consumo(spn_valores: dict) -> str:
    """Classify fuel consumption state from SPN values.

    Priority: SPN 185 (Rendimiento km/L) > SPN 183 (Tasa combustible L/h).
    """
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


# ---------------------------------------------------------------------------
# Frame selection with offset
# ---------------------------------------------------------------------------

def _get_frame_for_bus(viaje: dict, bus_index: int, ahora: float) -> dict:
    """Select the current frame for a bus based on elapsed time + desfase.

    The bus loops through its trip frames. Each bus has a different
    starting offset so they don't overlap on the route.

    Args:
        viaje: Trip dict with "frames" and "duracion_segundos".
        bus_index: Index of this bus (0, 1, 2...) for desfase calculation.
        ahora: Current unix timestamp (may be offset for burst ticks).

    Returns:
        The frame dict for this bus at this moment.
    """
    frames = viaje["frames"]
    total_frames = len(frames)
    duracion = viaje["duracion_segundos"]

    if total_frames == 0 or duracion == 0:
        return frames[0] if frames else {}

    # Desfase: shift each bus by DESFASE_PCT% of the trip duration
    desfase_segundos = int(duracion * (DESFASE_PCT / 100.0) * bus_index)

    # Elapsed seconds in the simulation (with speedup via STEP_SECONDS)
    # We use wall clock time so the simulation is stateless.
    # ahora is divided by TICK_INTERVAL to normalize the tick rate.
    elapsed = (int(ahora) * STEP_SECONDS // TICK_INTERVAL) + desfase_segundos

    # Position in the trip (looping)
    posicion_en_viaje = elapsed % duracion

    # Find the frame closest to this position
    # Binary search since frames are sorted by segundos_desde_inicio
    lo, hi = 0, total_frames - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if frames[mid]["segundos_desde_inicio"] <= posicion_en_viaje:
            lo = mid
        else:
            hi = mid - 1

    return frames[lo]


# ---------------------------------------------------------------------------
# Build DynamoDB item from frame
# ---------------------------------------------------------------------------

# Map SPN IDs to short field names for flat DynamoDB attributes
_SPN_FLAT_NAMES = {
    "84": "velocidad_kmh",
    "190": "rpm",
    "91": "pct_acelerador",
    "521": "pct_freno",
    "183": "tasa_combustible_lh",
    "185": "rendimiento_kml",
    "184": "ahorro_instantaneo_kml",
    "96": "nivel_combustible_pct",
    "110": "temperatura_motor_c",
    "175": "temperatura_aceite_c",
    "100": "presion_aceite_kpa",
    "98": "nivel_aceite_pct",
    "111": "nivel_anticongelante_pct",
    "168": "voltaje_bateria_v",
    "513": "torque_pct",
    "917": "odometro_km",
    "247": "horas_motor_h",
    "1761": "nivel_urea_pct",
    "1099": "balata_del_izq_pct",
    "1100": "balata_del_der_pct",
    "1101": "balata_tras_izq1_pct",
    "1102": "balata_tras_der1_pct",
    "1103": "balata_tras_izq2_pct",
    "1104": "balata_tras_der2_pct",
}


def _build_dynamo_item(viaje: dict, frame: dict, catalogo_spn: dict, timestamp_iso: str, ttl: int) -> dict:
    """Build a DynamoDB item from a trip + frame.

    Includes:
      - Trip context (autobus, operador, ruta, GPS)
      - spn_valores map with fuera_de_rango flags
      - Flat SPN fields for direct queries
      - alertas_spn list
      - estado_consumo classification
      - TTL
    """
    spn_valores = {}
    alertas_spn = []
    campos_planos = {}

    for spn_key, spn_data in frame.get("spn_valores", {}).items():
        spn_id = int(spn_key)
        valor = spn_data.get("valor", 0)
        nombre = spn_data.get("name", f"SPN_{spn_id}")
        unidad = spn_data.get("unidad", "")

        # Check out of range using catalog
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

        # Flat field
        flat_name = _SPN_FLAT_NAMES.get(spn_key)
        if flat_name:
            campos_planos[flat_name] = valor

    estado_consumo = clasificar_consumo(spn_valores)

    item = {
        "autobus": str(viaje["autobus"]),
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
        "ttl_expiry": ttl,
        **campos_planos,
    }

    return item


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Simulate real-time telemetry for multiple buses (burst mode).

    Each invocation (triggered every 1 minute by EventBridge Scheduler):
      1. Loads consolidated trips from S3 (cached).
      2. Loads SPN catalog (cached).
      3. Generates BURST_COUNT ticks (default 6), each separated by
         TICK_INTERVAL seconds (default 10s), covering the full minute.
      4. For each tick × bus, selects the frame and builds a DynamoDB item
         with a distinct timestamp.
      5. Batch writes all items to DynamoDB in one go.

    Result: DynamoDB has records every ~10 seconds even though the Lambda
    only runs once per minute.
    """
    ahora = time.time()
    base_dt = datetime.now(timezone.utc)
    ttl = int(ahora) + 86400

    # --- 1. Load trips ---
    try:
        data = _load_viajes()
        viajes = data.get("viajes", [])
    except Exception as exc:
        logger.error(json.dumps({
            "action": "load_viajes",
            "error": str(exc),
        }))
        return {"statusCode": 200, "body": json.dumps({"status": "error", "reason": str(exc)})}

    if not viajes:
        return {"statusCode": 200, "body": json.dumps({"status": "skipped", "reason": "No trips"})}

    # --- 2. Load SPN catalog ---
    try:
        catalogo_spn = cargar_catalogo_spn(S3_BUCKET, S3_CATALOGO_KEY)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "load_catalogo",
            "error": str(exc),
        }))
        return {"statusCode": 200, "body": json.dumps({"status": "error", "reason": str(exc)})}

    # --- 3. Generate burst ticks ---
    all_items = []
    for tick in range(BURST_COUNT):
        # Simulate wall-clock time for this tick
        tick_time = ahora + (tick * TICK_INTERVAL)
        tick_dt = base_dt + timedelta(seconds=tick * TICK_INTERVAL)
        tick_ts = tick_dt.isoformat()

        for bus_index, viaje in enumerate(viajes):
            try:
                frame = _get_frame_for_bus(viaje, bus_index, tick_time)
                item = _build_dynamo_item(
                    viaje, frame, catalogo_spn, tick_ts, ttl,
                )
                all_items.append(item)
            except Exception as exc:
                logger.warning(json.dumps({
                    "action": "process_bus",
                    "bus": viaje.get("autobus", "?"),
                    "tick": tick,
                    "error": str(exc),
                }))

    # --- 4. Write all items to DynamoDB ---
    write_result = {}
    if all_items:
        try:
            write_result = batch_write_items(DYNAMODB_TABLE, all_items)
        except Exception as exc:
            logger.error(json.dumps({
                "action": "batch_write",
                "error": str(exc),
                "items_count": len(all_items),
            }))

    # --- 5. Log summary ---
    # Log only the last tick's state for brevity
    last_tick_items = all_items[-(len(viajes)):]  if all_items else []
    buses_info = []
    for item in last_tick_items:
        buses_info.append({
            "autobus": item["autobus"],
            "estado": item["estado_consumo"],
            "alertas": len(item.get("alertas_spn", [])),
            "lat": item.get("latitud"),
            "lon": item.get("longitud"),
        })

    resumen = {
        "action": "simulador_summary",
        "timestamp": base_dt.isoformat(),
        "burst_count": BURST_COUNT,
        "tick_interval_s": TICK_INTERVAL,
        "buses_por_tick": len(viajes),
        "total_items": len(all_items),
        "items_escritos": write_result.get("items_written", 0),
        "buses_ultimo_tick": buses_info,
    }
    logger.info(json.dumps(resumen, default=str))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "burst_count": BURST_COUNT,
            "buses_por_tick": len(viajes),
            "total_items": len(all_items),
            "items_escritos": write_result.get("items_written", 0),
        }),
    }
