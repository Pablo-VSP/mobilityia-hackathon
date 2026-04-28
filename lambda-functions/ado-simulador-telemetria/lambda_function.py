"""
ado-simulador-telemetria — Simulador de telemetría en tiempo real.

Lee viajes pre-procesados desde S3 (viajes_consolidados.json) y simula
múltiples buses avanzando simultáneamente por sus rutas.

Datos de entrada:
  - 10 viajes de 5 minutos (300 frames cada uno, 1 frame/segundo)
  - 22 SPNs por frame, GPS real de la ruta México–Acapulco
  - 2-3 anomalías inyectadas por viaje (conducción agresiva, riesgo
    mecánico, velocidad excesiva, frenado brusco, balatas desgastadas)
  - Cada bus tiene un fragmento GPS diferente (sin solapamiento)

Modo burst: cada invocación (trigger cada 1 minuto via EventBridge)
genera BURST_COUNT registros por bus, espaciados TICK_INTERVAL segundos
entre sí. Con los defaults (6 ticks × 10s = 60s) se cubren los 60
segundos entre invocaciones, logrando resolución efectiva de 10 segundos
en DynamoDB sin necesidad de triggers sub-minuto.

Con STEP_SECONDS=10 y frames cada 1s, cada tick avanza 10 frames →
el bus se mueve fluidamente en el mapa. Los viajes de 5 min se
reproducen en loop infinito (reinician al terminar).

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
from ado_common.dynamo_utils import batch_write_items, put_item
from ado_common.s3_utils import read_json_from_s3
from ado_common.constants import (
    SPN_RENDIMIENTO, SPN_TASA_COMBUSTIBLE,
    SPN_TEMPERATURA_MOTOR, SPN_PRESION_ACEITE, SPN_NIVEL_ACEITE,
    SPN_NIVEL_ANTICONGELANTE, SPN_VOLTAJE_BATERIA,
)

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
# With frames every 1s and TICK_INTERVAL=10, STEP_SECONDS=10 means
# each tick advances 10 frames → 1x real-time, fluid movement.
STEP_SECONDS = int(os.environ.get("STEP_SECONDS", "10"))

# Desfase entre buses: bus 0 starts at 0%, bus 1 at DESFASE%, etc.
# Set to 0 when trips already have non-overlapping GPS fragments.
DESFASE_PCT = int(os.environ.get("DESFASE_PCT", "0"))

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
# Auto-ticket generation
# ---------------------------------------------------------------------------

TABLE_ALERTAS = os.environ.get("DYNAMODB_TABLE_ALERTAS", "ado-alertas")
_dynamodb_resource = boto3.resource("dynamodb")
_alertas_cache: dict[str, str] = {}  # bus -> last ticket timestamp (in-memory per warm invocation)

# Minimum interval between auto-tickets for the same bus (seconds)
AUTO_TICKET_COOLDOWN = 300  # 5 minutes

# SPN thresholds that trigger auto-tickets
_AUTO_TICKET_RULES = [
    {
        "spn_id": str(SPN_TEMPERATURA_MOTOR),
        "field": "temperatura_motor_c",
        "condition": "gt",
        "threshold": 125,
        "componente": "sistema_refrigeracion",
        "diagnostico": "Temperatura del motor por encima del umbral operativo seguro",
    },
    {
        "spn_id": str(SPN_PRESION_ACEITE),
        "field": "presion_aceite_kpa",
        "condition": "lt",
        "threshold": 120,
        "componente": "circuito_aceite",
        "diagnostico": "Presión de aceite del motor por debajo del umbral mínimo seguro",
    },
    {
        "spn_id": str(SPN_VOLTAJE_BATERIA),
        "field": "voltaje_bateria_v",
        "condition": "lt",
        "threshold": 22,
        "componente": "sistema_electrico",
        "diagnostico": "Voltaje de batería por debajo del umbral operativo",
    },
    {
        "spn_id": str(SPN_NIVEL_ANTICONGELANTE),
        "field": "nivel_anticongelante_pct",
        "condition": "lt",
        "threshold": 25,
        "componente": "sistema_refrigeracion",
        "diagnostico": "Nivel de anticongelante críticamente bajo",
    },
]


def _check_existing_alerts(autobus: str) -> bool:
    """Check if bus already has active alerts in DynamoDB. Returns True if alerts exist."""
    try:
        from boto3.dynamodb.conditions import Attr
        table = _dynamodb_resource.Table(TABLE_ALERTAS)
        resp = table.scan(
            FilterExpression=Attr("estado").eq("ACTIVA") & Attr("autobus").eq(autobus),
            Select="COUNT",
        )
        return resp.get("Count", 0) > 0
    except Exception:
        return False  # On error, assume no alerts (allow creation)


def _generate_auto_tickets(last_tick_items: list[dict], timestamp_iso: str) -> int:
    """Evaluate last tick items and auto-generate tickets for buses with critical conditions.

    Only generates a ticket if:
    - The bus has ALERTA_SIGNIFICATIVA status
    - At least one critical SPN threshold is breached
    - No active ticket exists for this bus
    - Cooldown period has passed since last auto-ticket

    Returns count of tickets created.
    """
    import uuid

    tickets_created = 0
    now_ts = time.time()

    for item in last_tick_items:
        autobus = item.get("autobus", "")
        estado = item.get("estado_consumo", "")

        # Only auto-ticket for significant alerts
        if estado != "ALERTA_SIGNIFICATIVA":
            continue

        # Check cooldown
        last_ticket_ts = _alertas_cache.get(autobus, "")
        if last_ticket_ts:
            try:
                last_ts = datetime.fromisoformat(last_ticket_ts).timestamp()
                if now_ts - last_ts < AUTO_TICKET_COOLDOWN:
                    continue
            except Exception:
                pass

        # Check which rules are triggered
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

        # Also check alertas_spn count
        alertas_spn = item.get("alertas_spn", [])
        if not triggered_rules and len(alertas_spn) < 3:
            continue  # Not critical enough for auto-ticket

        # Check if bus already has active alerts
        if _check_existing_alerts(autobus):
            _alertas_cache[autobus] = timestamp_iso  # Update cooldown
            continue

        # Build ticket
        componentes = list({r["componente"] for r in triggered_rules})
        if not componentes:
            componentes = ["revision_general"]

        diagnostico_parts = [r["diagnostico"] for r in triggered_rules[:3]]
        if alertas_spn:
            spn_msgs = [a.get("mensaje", "") for a in alertas_spn[:3] if a.get("mensaje")]
            if spn_msgs:
                diagnostico_parts.append("Señales fuera de rango: " + "; ".join(spn_msgs))

        diagnostico = ". ".join(diagnostico_parts) if diagnostico_parts else (
            f"El autobús {autobus} presenta múltiples señales fuera de rango que requieren atención."
        )

        # Determine severity
        if len(triggered_rules) >= 2 or len(alertas_spn) >= 5:
            nivel_riesgo = "ELEVADO"
            urgencia = "ESTA_SEMANA"
        else:
            nivel_riesgo = "MODERADO"
            urgencia = "PROXIMO_SERVICIO"

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
            put_item(TABLE_ALERTAS, alert_item)
            _alertas_cache[autobus] = timestamp_iso
            tickets_created += 1
            logger.info(json.dumps({
                "action": "auto_ticket_created",
                "autobus": autobus,
                "nivel_riesgo": nivel_riesgo,
                "componentes": componentes,
            }))
        except Exception as exc:
            logger.warning(json.dumps({
                "action": "auto_ticket_error",
                "autobus": autobus,
                "error": str(exc),
            }))

    return tickets_created


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

    # --- 5. Auto-generate tickets for buses with critical conditions ---
    auto_tickets = 0
    last_tick_items = all_items[-(len(viajes)):] if all_items else []
    if last_tick_items:
        try:
            auto_tickets = _generate_auto_tickets(last_tick_items, base_dt.isoformat())
        except Exception as exc:
            logger.warning(json.dumps({
                "action": "auto_ticket_generation_error",
                "error": str(exc),
            }))

    # --- 6. Log summary ---
    # Log only the last tick's state for brevity
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
        "auto_tickets_creados": auto_tickets,
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
            "auto_tickets_creados": auto_tickets,
        }),
    }
