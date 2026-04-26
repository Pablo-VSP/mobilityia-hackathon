"""
tool-calcular-desviacion — Cálculo de desviación de consumo de combustible.

Fuel Agent Tool invocado por Bedrock AgentCore. Consulta los últimos 10
registros de telemetría de un autobús, calcula promedios de SPNs de
eficiencia, clasifica la desviación y analiza SPNs correlacionados
para identificar causas probables de ineficiencia.

Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5, 11.4, 11.6
"""

import json
import logging
import os
import statistics
from decimal import Decimal

from ado_common.spn_catalog import cargar_catalogo_spn, obtener_spn
from ado_common.dynamo_utils import query_latest_records
from ado_common.response import build_agent_response, build_error_response
from ado_common.constants import (
    SPN_RENDIMIENTO,          # 185 — Rendimiento km/L
    SPN_TASA_COMBUSTIBLE,     # 183 — Tasa combustible L/h
    SPN_AHORRO_INSTANTANEO,   # 184 — Ahorro instantáneo km/L
    SPN_RPM,                  # 190 — RPM
    SPN_ACELERADOR,           # 91  — Posición Pedal Acelerador %
    SPN_VELOCIDAD,            # 84  — Velocidad km/h
    SPN_FRENO,                # 521 — Posición Pedal Freno %
    SPN_TORQUE,               # 513 — Porcentaje Torque %
    SPN_MARCHA,               # 523 — Marchas
    SPN_CRUISE_CONTROL_STATES,  # 527 — Cruise Control States
    SPN_CRUISE_CONTROL_ENABLE,  # 596 — Cruise Control Enable Switch
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables (Req 11.6)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-mobilityia-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "catalogo/motor_spn.json")

# Number of records to query for deviation analysis
RECORDS_LIMIT = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_param(event, name, default=None):
    """Extract a named parameter from a Bedrock AgentCore event.

    AgentCore sends parameters as a list of {name, value} dicts
    inside event["parameters"].
    """
    params = event.get("parameters", [])
    for p in params:
        if p.get("name") == name:
            return p.get("value", default)
    return default


def _safe_float(value):
    """Convert a value to float, handling Decimal and None gracefully."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _extract_spn_values(records, spn_id):
    """Extract numeric values for a given SPN from spn_valores across records.

    Args:
        records: List of DynamoDB items.
        spn_id: The SPN ID to extract.

    Returns:
        List of float values found for that SPN across all records.
    """
    values = []
    spn_key = str(spn_id)
    for record in records:
        spn_valores = record.get("spn_valores", {})
        spn_data = spn_valores.get(spn_key)
        if spn_data:
            val = _safe_float(spn_data.get("valor"))
            if val is not None:
                values.append(val)
    return values


def _extract_flat_field_values(records, field_name):
    """Extract numeric values for a flat field across records.

    Falls back to flat fields when spn_valores might not contain the SPN.

    Args:
        records: List of DynamoDB items.
        field_name: The flat field name (e.g., 'rendimiento_kml').

    Returns:
        List of float values found for that field across all records.
    """
    values = []
    for record in records:
        val = _safe_float(record.get(field_name))
        if val is not None:
            values.append(val)
    return values


def _safe_avg(values):
    """Compute average of a list of floats, returning None if empty."""
    if not values:
        return None
    return sum(values) / len(values)


def _clasificar_desviacion(rendimiento_avg):
    """Classify fuel deviation based on average rendimiento km/L.

    Args:
        rendimiento_avg: Average fuel efficiency in km/L, or None.

    Returns:
        Tuple of (category_str, description_str).
    """
    if rendimiento_avg is None:
        return "SIN_DATOS", "No hay datos suficientes de rendimiento para clasificar"

    if rendimiento_avg >= 3.0:
        return (
            "DENTRO_DE_RANGO",
            "El rendimiento promedio se encuentra dentro del rango esperado",
        )
    elif rendimiento_avg >= 2.5:
        return (
            "DESVIACION_LEVE",
            "Se detecta una desviación leve en el rendimiento de combustible",
        )
    elif rendimiento_avg >= 2.0:
        return (
            "DESVIACION_MODERADA",
            "Se detecta una desviación moderada en el rendimiento de combustible",
        )
    else:
        return (
            "DESVIACION_SIGNIFICATIVA",
            "Se detecta una desviación significativa en el rendimiento de combustible",
        )


def _analizar_causas_probables(records, catalogo_spn):
    """Analyze correlated SPNs to identify probable causes of deviation.

    Checks the following conditions (Req 4.3):
      - SPN 190 avg > 2200 rpm → RPM above optimal cruise range
      - SPN 91  avg > 65%     → Frequent harsh acceleration
      - SPN 84  avg > 100 km/h → Excessive speed
      - SPN 521 avg > 25%     → Frequent late braking
      - SPN 513 avg > 75%     → Sustained high engine load
      - SPN 523 frequent gear changes → Inefficient gear pattern
      - SPN 527/596 inactive  → Cruise control not used

    Args:
        records: List of DynamoDB items (last 10 records).
        catalogo_spn: The SPN catalog dict.

    Returns:
        List of dicts, each describing a probable cause with:
        spn_id, nombre, hallazgo, valor_promedio, unidad, rango_catalogo.
    """
    causas = []

    def _build_causa(spn_id, hallazgo, avg_value):
        """Build a probable cause entry with catalog info."""
        spn_info = obtener_spn(catalogo_spn, spn_id)
        nombre = spn_info["name"] if spn_info else f"SPN_{spn_id}"
        unidad = spn_info["unidad"] if spn_info else ""
        rango = ""
        if spn_info:
            rango = f"{spn_info['minimo']}-{spn_info['maximo']}"
        return {
            "spn_id": spn_id,
            "nombre": nombre,
            "hallazgo": hallazgo,
            "valor_promedio": round(avg_value, 2) if avg_value is not None else None,
            "unidad": unidad,
            "rango_catalogo": rango,
        }

    # --- SPN 190: RPM avg > 2200 ---
    rpm_values = _extract_spn_values(records, SPN_RPM)
    if not rpm_values:
        rpm_values = _extract_flat_field_values(records, "rpm")
    rpm_avg = _safe_avg(rpm_values)
    if rpm_avg is not None and rpm_avg > 2200:
        causas.append(_build_causa(
            SPN_RPM,
            "RPM por encima del rango óptimo de crucero",
            rpm_avg,
        ))

    # --- SPN 91: Acelerador avg > 65% ---
    accel_values = _extract_spn_values(records, SPN_ACELERADOR)
    if not accel_values:
        accel_values = _extract_flat_field_values(records, "pct_acelerador")
    accel_avg = _safe_avg(accel_values)
    if accel_avg is not None and accel_avg > 65:
        causas.append(_build_causa(
            SPN_ACELERADOR,
            "Aceleración brusca frecuente",
            accel_avg,
        ))

    # --- SPN 84: Velocidad avg > 100 km/h ---
    speed_values = _extract_spn_values(records, SPN_VELOCIDAD)
    if not speed_values:
        speed_values = _extract_flat_field_values(records, "velocidad_kmh")
    speed_avg = _safe_avg(speed_values)
    if speed_avg is not None and speed_avg > 100:
        causas.append(_build_causa(
            SPN_VELOCIDAD,
            "Velocidad excesiva",
            speed_avg,
        ))

    # --- SPN 521: Freno avg > 25% ---
    brake_values = _extract_spn_values(records, SPN_FRENO)
    if not brake_values:
        brake_values = _extract_flat_field_values(records, "pct_freno")
    brake_avg = _safe_avg(brake_values)
    if brake_avg is not None and brake_avg > 25:
        causas.append(_build_causa(
            SPN_FRENO,
            "Frenado tardío frecuente",
            brake_avg,
        ))

    # --- SPN 513: Torque avg > 75% ---
    torque_values = _extract_spn_values(records, SPN_TORQUE)
    if not torque_values:
        torque_values = _extract_flat_field_values(records, "torque_pct")
    torque_avg = _safe_avg(torque_values)
    if torque_avg is not None and torque_avg > 75:
        causas.append(_build_causa(
            SPN_TORQUE,
            "Carga de motor sostenida alta",
            torque_avg,
        ))

    # --- SPN 523: Frequent gear changes ---
    gear_values = _extract_spn_values(records, SPN_MARCHA)
    if not gear_values:
        gear_values = _extract_flat_field_values(records, "marcha")
    if len(gear_values) >= 3:
        distinct_gears = len(set(gear_values))
        try:
            gear_stdev = statistics.stdev(gear_values)
        except statistics.StatisticsError:
            gear_stdev = 0.0
        # Detect frequent changes: high standard deviation or many distinct values
        # relative to the number of records
        if gear_stdev > 2.0 or distinct_gears >= 5:
            causas.append(_build_causa(
                SPN_MARCHA,
                "Patrón de cambio de marchas ineficiente",
                _safe_avg(gear_values),
            ))

    # --- SPN 527/596: Cruise control inactive ---
    cc_states_values = _extract_spn_values(records, SPN_CRUISE_CONTROL_STATES)
    cc_enable_values = _extract_spn_values(records, SPN_CRUISE_CONTROL_ENABLE)
    cc_states_avg = _safe_avg(cc_states_values)
    cc_enable_avg = _safe_avg(cc_enable_values)
    # Cruise control is considered inactive if average is 0 or very low
    cc_inactive = False
    if cc_states_values and cc_states_avg is not None and cc_states_avg <= 0.5:
        cc_inactive = True
    elif cc_enable_values and cc_enable_avg is not None and cc_enable_avg <= 0.5:
        cc_inactive = True
    if cc_inactive:
        # Report using SPN 527 as the primary reference
        avg_val = cc_states_avg if cc_states_avg is not None else cc_enable_avg
        causas.append(_build_causa(
            SPN_CRUISE_CONTROL_STATES,
            "Cruise control no utilizado",
            avg_val if avg_val is not None else 0.0,
        ))

    return causas


# ---------------------------------------------------------------------------
# Lambda handler (Req 4.1–4.5, 11.4, 11.6)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the calcular-desviacion tool.

    Invoked by Bedrock AgentCore as a Fuel Agent Action Group tool.

    Flow:
      1. Parse ``autobus`` and ``viaje_ruta`` from event.
      2. Load SPN catalog from S3 (cached via lru_cache).
      3. Query DynamoDB for the last 10 records of the bus.
      4. If no records found, return insufficient-data response.
      5. Compute averages for fuel efficiency SPNs (185, 183, 184).
      6. Classify deviation based on rendimiento average.
      7. Analyze correlated SPNs for probable causes.
      8. Return formatted response via ``build_agent_response()``.

    Args:
        event: Bedrock AgentCore event with parameters list.
        context: Lambda context (unused).

    Returns:
        Dict in Bedrock AgentCore Action Group response format.
    """
    logger.info(json.dumps({
        "action": "lambda_handler",
        "event_keys": list(event.keys()) if isinstance(event, dict) else "not_dict",
    }))

    # --- 1. Parse parameters (Req 4.1) ---
    autobus = _get_param(event, "autobus")
    if not autobus:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_autobus_parameter",
        }))
        return build_error_response("Parámetro 'autobus' es requerido.", 400)

    autobus = str(autobus).strip()

    viaje_ruta = _get_param(event, "viaje_ruta")
    if not viaje_ruta:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_viaje_ruta_parameter",
        }))
        return build_error_response("Parámetro 'viaje_ruta' es requerido.", 400)

    viaje_ruta = str(viaje_ruta).strip()

    logger.info(json.dumps({
        "action": "parse_params",
        "autobus": autobus,
        "viaje_ruta": viaje_ruta,
    }))

    # --- 2. Load SPN catalog ---
    try:
        catalogo_spn = cargar_catalogo_spn(S3_BUCKET, S3_CATALOGO_KEY)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "cargar_catalogo",
            "error": str(exc),
        }))
        return build_error_response(
            "Error al cargar el catálogo SPN desde S3.", 500
        )

    # --- 3. Query DynamoDB for last 10 records (Req 4.1) ---
    try:
        records = query_latest_records(DYNAMODB_TABLE, autobus, RECORDS_LIMIT)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "query_dynamodb",
            "autobus": autobus,
            "error": str(exc),
        }))
        return build_error_response(
            f"Error al consultar telemetría del autobús {autobus}.", 500
        )

    # --- 4. Insufficient-data response (Req 4.5) ---
    if not records:
        logger.info(json.dumps({
            "action": "no_records_found",
            "autobus": autobus,
        }))
        return build_agent_response({
            "autobus": autobus,
            "viaje_ruta": viaje_ruta,
            "mensaje": (
                f"No se encontraron registros de telemetría para el autobús "
                f"{autobus}. No es posible calcular la desviación de consumo."
            ),
            "registros_analizados": 0,
            "metricas_eficiencia": {},
            "clasificacion_desviacion": "SIN_DATOS",
            "causas_probables": [],
        })

    # --- 5. Compute averages for fuel efficiency SPNs (Req 4.1) ---
    # SPN 185 — Rendimiento km/L
    rendimiento_values = _extract_spn_values(records, SPN_RENDIMIENTO)
    if not rendimiento_values:
        rendimiento_values = _extract_flat_field_values(records, "rendimiento_kml")
    rendimiento_avg = _safe_avg(rendimiento_values)

    # SPN 183 — Tasa combustible L/h
    tasa_values = _extract_spn_values(records, SPN_TASA_COMBUSTIBLE)
    if not tasa_values:
        tasa_values = _extract_flat_field_values(records, "tasa_combustible_lh")
    tasa_avg = _safe_avg(tasa_values)

    # SPN 184 — Ahorro instantáneo km/L
    ahorro_values = _extract_spn_values(records, SPN_AHORRO_INSTANTANEO)
    if not ahorro_values:
        ahorro_values = _extract_flat_field_values(records, "ahorro_instantaneo_kml")
    ahorro_avg = _safe_avg(ahorro_values)

    metricas_eficiencia = {}
    if rendimiento_avg is not None:
        metricas_eficiencia["rendimiento_promedio_kml"] = round(rendimiento_avg, 2)
    if tasa_avg is not None:
        metricas_eficiencia["tasa_combustible_promedio_lh"] = round(tasa_avg, 2)
    if ahorro_avg is not None:
        metricas_eficiencia["ahorro_instantaneo_promedio_kml"] = round(ahorro_avg, 2)

    # --- 6. Classify deviation (Req 4.2) ---
    clasificacion, descripcion = _clasificar_desviacion(rendimiento_avg)

    # --- 7. Analyze correlated SPNs for probable causes (Req 4.3, 4.4) ---
    causas_probables = _analizar_causas_probables(records, catalogo_spn)

    # --- 8. Build and return response (Req 11.4) ---
    latest_record = records[0]
    response_body = {
        "autobus": autobus,
        "viaje_ruta": viaje_ruta,
        "ultimo_timestamp": latest_record.get("timestamp", ""),
        "registros_analizados": len(records),
        "metricas_eficiencia": metricas_eficiencia,
        "clasificacion_desviacion": clasificacion,
        "descripcion_desviacion": descripcion,
        "causas_probables": causas_probables,
        "total_causas_identificadas": len(causas_probables),
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "autobus": autobus,
        "viaje_ruta": viaje_ruta,
        "records_analyzed": len(records),
        "clasificacion": clasificacion,
        "causas_count": len(causas_probables),
    }))

    return build_agent_response(response_body)
