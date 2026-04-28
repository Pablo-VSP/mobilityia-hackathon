"""
tool-consultar-obd — Consulta de diagnóstico OBD por autobús.

Maintenance Agent Tool invocado por Bedrock AgentCore. Consulta los últimos
20 registros de telemetría de un autobús, extrae SPNs de mantenimiento,
calcula tendencias, detecta variaciones anómalas, evalúa estado de balatas,
lee fallas recientes de S3 y construye un resumen de salud mecánica.

Requisitos: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 11.4, 11.6
"""

import json
import logging
import os
from decimal import Decimal

from ado_common.spn_catalog import cargar_catalogo_spn, obtener_spn, variacion_anomala
from ado_common.dynamo_utils import query_latest_records
from ado_common.s3_utils import read_json_from_s3
from ado_common.response import build_agent_response, build_error_response
from ado_common.constants import (
    SPNS_MANTENIMIENTO,
    SPNS_BALATAS,
    SPN_BALATA_DEL_IZQ,
    SPN_BALATA_DEL_DER,
    SPN_BALATA_TRAS_IZQ1,
    SPN_BALATA_TRAS_DER1,
    SPN_BALATA_TRAS_IZQ2,
    SPN_BALATA_TRAS_DER2,
    SPN_TEMPERATURA_MOTOR,
    SPN_TEMPERATURA_ACEITE,
    SPN_PRESION_ACEITE,
    SPN_NIVEL_ACEITE,
    SPN_NIVEL_ANTICONGELANTE,
    SPN_VOLTAJE_BATERIA,
    SPN_NIVEL_UREA,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables (Req 11.6)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "hackathon-data/catalogo/motor_spn.json")
S3_FALLAS_KEY = os.environ.get("S3_FALLAS_KEY", "hackathon-data/fallas-simuladas/data_fault.json")

# Number of records to query for OBD analysis
RECORDS_LIMIT = 20

# Brake pad threshold (Req 6.4)
BRAKE_PAD_THRESHOLD = 30.0

# Trend threshold: 5% difference between halves
TREND_THRESHOLD = 0.05

# Maximum recent faults to return (Req 6.5)
MAX_FAULTS = 5

# Human-readable names for brake pad positions
BALATA_NOMBRES = {
    SPN_BALATA_DEL_IZQ: "Delantero Izquierdo",
    SPN_BALATA_DEL_DER: "Delantero Derecho",
    SPN_BALATA_TRAS_IZQ1: "Trasero Izquierdo 1",
    SPN_BALATA_TRAS_DER1: "Trasero Derecho 1",
    SPN_BALATA_TRAS_IZQ2: "Trasero Izquierdo 2",
    SPN_BALATA_TRAS_DER2: "Trasero Derecho 2",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_param(event, name, default=None):
    """Extract a named parameter from a Bedrock AgentCore event."""
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

    Returns list of float values in the same order as records (oldest to newest
    depends on caller's record order).
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


def _safe_avg(values):
    """Compute average of a list of floats, returning None if empty."""
    if not values:
        return None
    return sum(values) / len(values)


def _calcular_tendencia(values):
    """Calculate trend by comparing first-half vs second-half averages.

    Args:
        values: List of float values (ordered from most recent to oldest,
                or any consistent order — the split is positional).

    Returns:
        Trend string: 'estable', 'ascendente', or 'descendente'.
        Returns 'estable' if insufficient data.
    """
    if len(values) < 2:
        return "estable"

    mid = len(values) // 2
    first_half = values[:mid]
    second_half = values[mid:]

    avg_first = _safe_avg(first_half)
    avg_second = _safe_avg(second_half)

    if avg_first is None or avg_second is None:
        return "estable"

    # Avoid division by zero
    if avg_first == 0 and avg_second == 0:
        return "estable"

    # Use the larger of the two averages as the reference for percentage calc
    reference = max(abs(avg_first), abs(avg_second))
    if reference == 0:
        return "estable"

    diff_ratio = (avg_second - avg_first) / reference

    if diff_ratio > TREND_THRESHOLD:
        return "ascendente"
    elif diff_ratio < -TREND_THRESHOLD:
        return "descendente"
    else:
        return "estable"


def _detectar_variaciones_anomalas(records, catalogo_spn):
    """Detect anomalous variations between consecutive readings for maintenance SPNs.

    Uses variacion_anomala() from spn_catalog (2x delta threshold).

    Args:
        records: List of DynamoDB items (most recent first).
        catalogo_spn: The SPN catalog dict.

    Returns:
        List of dicts describing anomalous variations found.
    """
    anomalias = []

    for spn_id in SPNS_MANTENIMIENTO:
        spn_key = str(spn_id)
        valores_consecutivos = []

        for record in records:
            spn_valores = record.get("spn_valores", {})
            spn_data = spn_valores.get(spn_key)
            if spn_data:
                val = _safe_float(spn_data.get("valor"))
                if val is not None:
                    valores_consecutivos.append((record.get("timestamp", ""), val))

        # Check consecutive pairs for anomalous variation
        for i in range(len(valores_consecutivos) - 1):
            ts_actual, val_actual = valores_consecutivos[i]
            ts_anterior, val_anterior = valores_consecutivos[i + 1]

            if variacion_anomala(catalogo_spn, spn_id, val_anterior, val_actual):
                spn_info = obtener_spn(catalogo_spn, spn_id)
                nombre = spn_info["name"] if spn_info else f"SPN_{spn_id}"
                unidad = spn_info["unidad"] if spn_info else ""
                delta = spn_info["delta"] if spn_info else 0

                anomalias.append({
                    "spn_id": spn_id,
                    "nombre": nombre,
                    "valor_anterior": round(val_anterior, 2),
                    "valor_actual": round(val_actual, 2),
                    "variacion": round(abs(val_actual - val_anterior), 2),
                    "umbral_delta_2x": round(2.0 * delta, 2),
                    "unidad": unidad,
                    "timestamp": ts_actual,
                })

    return anomalias


def _evaluar_balatas(records, catalogo_spn):
    """Build brake pad status for all 6 positions.

    Uses the most recent record's values. ≥30% → aceptable, <30% → REQUIERE_ATENCION.

    Args:
        records: List of DynamoDB items (most recent first).
        catalogo_spn: The SPN catalog dict.

    Returns:
        List of dicts with brake pad status for each position.
    """
    balatas = []

    if not records:
        return balatas

    # Use the most recent record for current brake pad status
    latest = records[0]
    spn_valores = latest.get("spn_valores", {})

    for spn_id in sorted(SPNS_BALATAS):
        spn_key = str(spn_id)
        spn_data = spn_valores.get(spn_key)

        spn_info = obtener_spn(catalogo_spn, spn_id)
        nombre_posicion = BALATA_NOMBRES.get(spn_id, f"Posición SPN {spn_id}")

        if spn_data:
            valor = _safe_float(spn_data.get("valor"))
        else:
            valor = None

        if valor is not None:
            estado = "aceptable" if valor >= BRAKE_PAD_THRESHOLD else "REQUIERE_ATENCION"
        else:
            estado = "sin_datos"

        balatas.append({
            "spn_id": spn_id,
            "posicion": nombre_posicion,
            "porcentaje_restante": round(valor, 2) if valor is not None else None,
            "estado": estado,
        })

    return balatas


def _obtener_fallas_recientes(autobus, bucket, fallas_key):
    """Read Data_Fault from S3, filter by autobus, return 5 most recent.

    Args:
        autobus: Bus number to filter by.
        bucket: S3 bucket name.
        fallas_key: S3 key for the faults JSON file.

    Returns:
        List of up to 5 fault dicts with selected fields, sorted by
        fecha_hora descending. Returns empty list on error.
    """
    try:
        all_faults = read_json_from_s3(bucket, fallas_key)
    except Exception as exc:
        logger.warning(json.dumps({
            "action": "obtener_fallas_recientes",
            "error": str(exc),
            "message": "No se pudieron leer las fallas desde S3, continuando sin fallas",
        }))
        return []

    if not isinstance(all_faults, list):
        return []

    # Filter by autobus (string comparison)
    autobus_str = str(autobus).strip()
    bus_faults = [
        f for f in all_faults
        if str(f.get("autobus", "")).strip() == autobus_str
    ]

    # Sort by fecha_hora descending
    bus_faults.sort(key=lambda f: f.get("fecha_hora", ""), reverse=True)

    # Take top 5 and extract relevant fields
    result = []
    for fault in bus_faults[:MAX_FAULTS]:
        result.append({
            "codigo": fault.get("codigo", ""),
            "severidad": fault.get("severidad"),
            "descripcion": fault.get("descripcion", ""),
            "modelo": fault.get("modelo", ""),
            "marca_comercial": fault.get("marca_comercial", ""),
            "zona": fault.get("zona", ""),
            "fecha_hora": fault.get("fecha_hora", ""),
        })

    return result


def _construir_resumen_salud(senales_mantenimiento, balatas, anomalias, fallas_recientes):
    """Build a text summary of the bus's overall mechanical health.

    Args:
        senales_mantenimiento: List of maintenance signal dicts with trends.
        balatas: List of brake pad status dicts.
        anomalias: List of anomalous variation dicts.
        fallas_recientes: List of recent fault dicts.

    Returns:
        String with a human-readable health summary.
    """
    partes = []

    # Count trends
    ascendentes = [s for s in senales_mantenimiento if s.get("tendencia") == "ascendente"]
    descendentes = [s for s in senales_mantenimiento if s.get("tendencia") == "descendente"]

    if not ascendentes and not descendentes and not anomalias and not fallas_recientes:
        partes.append("Las señales de mantenimiento se encuentran estables.")
    else:
        if ascendentes:
            nombres = ", ".join(s["nombre"] for s in ascendentes[:3])
            partes.append(f"Tendencia ascendente detectada en: {nombres}.")
        if descendentes:
            nombres = ", ".join(s["nombre"] for s in descendentes[:3])
            partes.append(f"Tendencia descendente detectada en: {nombres}.")

    # Brake pad alerts
    balatas_atencion = [b for b in balatas if b.get("estado") == "REQUIERE_ATENCION"]
    if balatas_atencion:
        posiciones = ", ".join(b["posicion"] for b in balatas_atencion)
        partes.append(f"Balatas requieren atención en: {posiciones}.")
    else:
        balatas_con_datos = [b for b in balatas if b.get("estado") != "sin_datos"]
        if balatas_con_datos:
            partes.append("Estado de balatas aceptable en todas las posiciones.")

    # Anomalous variations
    if anomalias:
        partes.append(
            f"Se detectaron {len(anomalias)} variaciones anómalas en señales de mantenimiento."
        )

    # Recent faults
    if fallas_recientes:
        partes.append(
            f"Se encontraron {len(fallas_recientes)} fallas recientes registradas."
        )
    else:
        partes.append("No se encontraron fallas recientes registradas.")

    return " ".join(partes)


# ---------------------------------------------------------------------------
# Lambda handler (Req 6.1–6.6, 11.4, 11.6)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the consultar-obd tool.

    Invoked by Bedrock AgentCore as a Maintenance Agent Action Group tool.

    Flow:
      1. Parse ``autobus`` from event.
      2. Load SPN catalog from S3 (cached via lru_cache).
      3. Query DynamoDB for the last 20 records of the bus.
      4. If no records found, return empty-data response.
      5. Extract maintenance-relevant SPNs and calculate trends (Req 6.2).
      6. Detect anomalous variations (Req 6.3).
      7. Evaluate brake pad status for all 6 positions (Req 6.4).
      8. Read Data_Fault from S3 and filter by autobus (Req 6.5).
      9. Build resumen_salud text summary (Req 6.6).
      10. Return formatted response via ``build_agent_response()`` (Req 11.4).

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

    # --- 1. Parse parameters (Req 6.1) ---
    autobus = _get_param(event, "autobus")
    if not autobus:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_autobus_parameter",
        }))
        return build_error_response("Parámetro 'autobus' es requerido.", 400)

    autobus = str(autobus).strip()

    logger.info(json.dumps({
        "action": "parse_params",
        "autobus": autobus,
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

    # --- 3. Query DynamoDB for last 20 records (Req 6.1) ---
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

    # --- 4. Empty-data response ---
    if not records:
        logger.info(json.dumps({
            "action": "no_records_found",
            "autobus": autobus,
        }))
        return build_agent_response({
            "autobus": autobus,
            "mensaje": (
                f"No se encontraron registros de telemetría para el autobús "
                f"{autobus}. No es posible realizar el diagnóstico OBD."
            ),
            "registros_analizados": 0,
            "senales_mantenimiento": [],
            "variaciones_anomalas": [],
            "estado_balatas": [],
            "fallas_recientes": [],
            "resumen_salud": "Sin datos disponibles para evaluar la salud mecánica.",
        })

    # --- 5. Extract maintenance SPNs and calculate trends (Req 6.1, 6.2) ---
    senales_mantenimiento = []
    for spn_id in sorted(SPNS_MANTENIMIENTO):
        spn_info = obtener_spn(catalogo_spn, spn_id)
        if not spn_info:
            continue

        values = _extract_spn_values(records, spn_id)
        if not values:
            continue

        tendencia = _calcular_tendencia(values)
        valor_actual = values[0] if values else None
        promedio = _safe_avg(values)

        senales_mantenimiento.append({
            "spn_id": spn_id,
            "nombre": spn_info["name"],
            "unidad": spn_info["unidad"],
            "valor_actual": round(valor_actual, 2) if valor_actual is not None else None,
            "promedio": round(promedio, 2) if promedio is not None else None,
            "tendencia": tendencia,
            "rango_catalogo": f"{spn_info['minimo']}-{spn_info['maximo']}",
        })

    # --- 6. Detect anomalous variations (Req 6.3) ---
    variaciones_anomalas = _detectar_variaciones_anomalas(records, catalogo_spn)

    # --- 7. Evaluate brake pad status (Req 6.4) ---
    estado_balatas = _evaluar_balatas(records, catalogo_spn)

    # --- 8. Read faults from S3 (Req 6.5) ---
    fallas_recientes = _obtener_fallas_recientes(autobus, S3_BUCKET, S3_FALLAS_KEY)

    # --- 9. Build health summary (Req 6.6) ---
    resumen_salud = _construir_resumen_salud(
        senales_mantenimiento, estado_balatas, variaciones_anomalas, fallas_recientes
    )

    # --- 10. Build and return response (Req 11.4) ---
    latest_record = records[0]
    response_body = {
        "autobus": autobus,
        "ultimo_timestamp": latest_record.get("timestamp", ""),
        "registros_analizados": len(records),
        "senales_mantenimiento": senales_mantenimiento,
        "variaciones_anomalas": variaciones_anomalas,
        "total_variaciones_anomalas": len(variaciones_anomalas),
        "estado_balatas": estado_balatas,
        "fallas_recientes": fallas_recientes,
        "total_fallas_recientes": len(fallas_recientes),
        "resumen_salud": resumen_salud,
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "autobus": autobus,
        "records_analyzed": len(records),
        "senales_count": len(senales_mantenimiento),
        "anomalias_count": len(variaciones_anomalas),
        "fallas_count": len(fallas_recientes),
    }))

    return build_agent_response(response_body)
