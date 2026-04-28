"""
tool-listar-buses-activos — Listado de autobuses con telemetría reciente.

Fuel Agent Tool invocado por Bedrock AgentCore. Retorna todos los autobuses
con registros de telemetría en los últimos 5 minutos, con opción de filtrar
por viaje_ruta. Los resultados se ordenan por severidad: ALERTA_SIGNIFICATIVA
primero, luego por cantidad de SPNs fuera de rango descendente.

Para deduplicación: cuando existen múltiples registros para el mismo autobús,
se usa únicamente el más reciente (timestamp más alto).

Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5, 11.4, 11.6
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from ado_common.dynamo_utils import scan_recent, query_gsi
from ado_common.response import build_agent_response, build_error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables (Req 11.6)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "hackathon-data/catalogo/motor_spn.json")

# GSI name for viaje_ruta queries
GSI_VIAJE_RUTA = "viaje_ruta-timestamp-index"

# Time window for "active" buses (5 minutes)
ACTIVE_WINDOW_MINUTES = 5

# Priority map for sorting by estado_consumo (lower = higher priority)
ESTADO_CONSUMO_PRIORITY = {
    "ALERTA_SIGNIFICATIVA": 0,
    "ALERTA_MODERADA": 1,
    "EFICIENTE": 2,
    "SIN_DATOS": 3,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_param(event, name, default=None):
    """Extract a named parameter from a Bedrock AgentCore event.

    AgentCore sends parameters as a list of {name, value} dicts
    inside event["parameters"].

    Args:
        event: The Lambda event from Bedrock AgentCore.
        name: Parameter name to look up.
        default: Value to return if the parameter is not found.

    Returns:
        The parameter value as a string, or *default* if not present.
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


def _compute_timestamp_limit():
    """Compute the ISO 8601 timestamp for now - 5 minutes.

    Returns:
        ISO 8601 string representing the cutoff time.
    """
    now = datetime.now(timezone.utc)
    limit = now - timedelta(minutes=ACTIVE_WINDOW_MINUTES)
    return limit.strftime("%Y-%m-%dT%H:%M:%SZ")


def _deduplicate_buses(records):
    """Deduplicate records by autobus, keeping only the most recent one.

    When multiple records exist for the same bus, the one with the
    latest (lexicographically highest) timestamp is kept.

    Args:
        records: List of DynamoDB items.

    Returns:
        List of DynamoDB items with one entry per unique autobus.
    """
    bus_map = {}
    for record in records:
        autobus = record.get("autobus", "")
        if not autobus:
            continue
        existing = bus_map.get(autobus)
        if existing is None:
            bus_map[autobus] = record
        else:
            # Keep the record with the latest timestamp
            if record.get("timestamp", "") > existing.get("timestamp", ""):
                bus_map[autobus] = record
    return list(bus_map.values())


def _extract_bus_summary(record):
    """Extract a summary dict for a single bus from its DynamoDB record.

    Args:
        record: A single DynamoDB item.

    Returns:
        Dict with: autobus, viaje_ruta, operador, ultimo_timestamp,
        estado_consumo, alertas_spn_count, and alertas_resumen.
    """
    alertas_spn = record.get("alertas_spn", [])
    alertas_count = len(alertas_spn) if isinstance(alertas_spn, list) else 0

    # Count out-of-range SPNs from spn_valores as a secondary metric
    spn_valores = record.get("spn_valores", {})
    spns_fuera_de_rango = sum(
        1 for spn_data in spn_valores.values()
        if isinstance(spn_data, dict) and spn_data.get("fuera_de_rango", False)
    )

    # Build a brief summary of active alerts
    alertas_resumen = []
    for alerta in (alertas_spn if isinstance(alertas_spn, list) else []):
        alertas_resumen.append({
            "spn_id": alerta.get("spn_id"),
            "nombre": alerta.get("name", ""),
            "mensaje": alerta.get("mensaje", ""),
        })

    return {
        "autobus": record.get("autobus", ""),
        "viaje_ruta": record.get("viaje_ruta", ""),
        "operador": record.get("operador_desc", ""),
        "ultimo_timestamp": record.get("timestamp", ""),
        "estado_consumo": record.get("estado_consumo", "SIN_DATOS"),
        "alertas_spn_count": alertas_count,
        "spns_fuera_de_rango": spns_fuera_de_rango,
        "alertas_resumen": alertas_resumen,
    }


def _sort_buses(bus_summaries):
    """Sort bus summaries by severity.

    Sorting criteria (Req 5.5):
      1. ALERTA_SIGNIFICATIVA first (by estado_consumo priority map)
      2. Then by count of out-of-range SPNs descending

    Args:
        bus_summaries: List of bus summary dicts.

    Returns:
        Sorted list of bus summary dicts.
    """
    return sorted(
        bus_summaries,
        key=lambda b: (
            ESTADO_CONSUMO_PRIORITY.get(b.get("estado_consumo", "SIN_DATOS"), 3),
            -b.get("alertas_spn_count", 0),
        ),
    )


# ---------------------------------------------------------------------------
# Lambda handler (Req 5.1–5.5, 11.4, 11.6)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the listar-buses-activos tool.

    Invoked by Bedrock AgentCore as a Fuel Agent Action Group tool.

    Flow:
      1. Parse optional ``viaje_ruta`` from event.
      2. Compute timestamp_limit = now - 5 minutes.
      3. If viaje_ruta provided: query GSI ``viaje_ruta-timestamp-index``.
         If no filter: scan with FilterExpression on timestamp.
      4. Deduplicate records by autobus (keep most recent).
      5. Extract summary for each bus.
      6. Sort by severity: ALERTA_SIGNIFICATIVA first, then by alertas count.
      7. Return formatted response via ``build_agent_response()``.

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

    # --- 1. Parse optional viaje_ruta parameter ---
    viaje_ruta = _get_param(event, "viaje_ruta")
    if viaje_ruta:
        viaje_ruta = str(viaje_ruta).strip()

    logger.info(json.dumps({
        "action": "parse_params",
        "viaje_ruta": viaje_ruta or "sin_filtro",
    }))

    # --- 2. Compute timestamp limit (Req 5.1) ---
    timestamp_limit = _compute_timestamp_limit()

    logger.info(json.dumps({
        "action": "compute_timestamp_limit",
        "timestamp_limit": timestamp_limit,
    }))

    # --- 3. Query DynamoDB (Req 5.2, 5.3) ---
    try:
        if viaje_ruta:
            # Query GSI viaje_ruta-timestamp-index (Req 5.2)
            records = query_gsi(
                DYNAMODB_TABLE,
                GSI_VIAJE_RUTA,
                viaje_ruta,
                timestamp_limit,
            )
        else:
            # Scan with FilterExpression on timestamp (Req 5.3)
            records = scan_recent(DYNAMODB_TABLE, timestamp_limit)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "query_dynamodb",
            "viaje_ruta": viaje_ruta or "sin_filtro",
            "error": str(exc),
        }))
        return build_error_response(
            "Error al consultar autobuses activos en DynamoDB.", 500
        )

    # --- 4. Deduplicate by autobus (keep most recent) ---
    unique_records = _deduplicate_buses(records)

    # --- 5. Extract summary for each bus (Req 5.4) ---
    bus_summaries = [_extract_bus_summary(record) for record in unique_records]

    # --- 6. Sort by severity (Req 5.5) ---
    sorted_buses = _sort_buses(bus_summaries)

    # --- 7. Build and return response (Req 11.4) ---
    response_body = {
        "total_buses_activos": len(sorted_buses),
        "timestamp_limite": timestamp_limit,
        "filtro_viaje_ruta": viaje_ruta or "ninguno",
        "buses": sorted_buses,
    }

    if not sorted_buses:
        response_body["mensaje"] = (
            "No se encontraron autobuses con telemetría activa en los últimos 5 minutos."
        )
        if viaje_ruta:
            response_body["mensaje"] = (
                f"No se encontraron autobuses activos en la ruta {viaje_ruta} "
                f"en los últimos 5 minutos."
            )

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "total_buses": len(sorted_buses),
        "viaje_ruta_filter": viaje_ruta or "none",
    }))

    return build_agent_response(response_body)
