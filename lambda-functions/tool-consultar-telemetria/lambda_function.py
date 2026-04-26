"""
tool-consultar-telemetria — Consulta de telemetría consolidada por autobús.

Fuel Agent Tool invocado por Bedrock AgentCore. Recupera los últimos N
registros de telemetría consolidada de un autobús desde DynamoDB, traduce
los SPNs a nombres legibles usando el catálogo, y construye un resumen
con variables actuales, alertas activas e historial reciente.

Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 11.4, 11.6
"""

import json
import logging
import os
from decimal import Decimal

from ado_common.spn_catalog import cargar_catalogo_spn, obtener_spn
from ado_common.dynamo_utils import query_latest_records
from ado_common.response import build_agent_response, build_error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables (Req 11.6)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-mobilityia-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "catalogo/motor_spn.json")

# Limits for ultimos_n_registros parameter
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


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
    """Convert a value to float, handling Decimal and None gracefully.

    Args:
        value: A numeric value (float, int, Decimal, str) or None.

    Returns:
        A Python float, or None if conversion fails.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _build_variables_actuales(record, catalogo_spn):
    """Build the variables_actuales array from a DynamoDB record's spn_valores.

    For each SPN entry in the record, looks up the catalog to provide
    human-readable name, unit, catalog range, and out-of-range status.

    Args:
        record: A single DynamoDB item with a ``spn_valores`` map.
        catalogo_spn: The SPN catalog dict from ``cargar_catalogo_spn()``.

    Returns:
        List of dicts, each with: spn_id, nombre, valor, unidad,
        rango_catalogo (minimo–maximo), and fuera_de_rango.
    """
    spn_valores = record.get("spn_valores", {})
    variables = []

    for spn_id_str, spn_data in spn_valores.items():
        try:
            spn_id = int(spn_id_str)
        except (ValueError, TypeError):
            continue

        valor = _safe_float(spn_data.get("valor"))
        if valor is None:
            continue

        # Look up catalog for human-readable info
        spn_info = obtener_spn(catalogo_spn, spn_id)
        if spn_info:
            nombre = spn_info["name"]
            unidad = spn_info["unidad"]
            minimo = spn_info["minimo"]
            maximo = spn_info["maximo"]
        else:
            nombre = spn_data.get("name", f"SPN_{spn_id}")
            unidad = spn_data.get("unidad", "")
            minimo = None
            maximo = None

        fuera_de_rango = bool(spn_data.get("fuera_de_rango", False))

        variable_entry = {
            "spn_id": spn_id,
            "nombre": nombre,
            "valor": valor,
            "unidad": unidad,
            "fuera_de_rango": fuera_de_rango,
        }

        if minimo is not None and maximo is not None:
            variable_entry["rango_catalogo"] = f"{minimo}-{maximo}"

        variables.append(variable_entry)

    # Sort by SPN ID for consistent output
    variables.sort(key=lambda v: v["spn_id"])
    return variables


def _build_historial_reciente(records):
    """Build the historial_reciente array from a list of DynamoDB records.

    Each entry summarises a record's timestamp, consumption state,
    fuel efficiency, and count of out-of-range SPNs.

    Args:
        records: List of DynamoDB items sorted by timestamp descending.

    Returns:
        List of dicts with: timestamp, estado_consumo, rendimiento_kml,
        and spns_fuera_de_rango (count).
    """
    historial = []

    for record in records:
        spn_valores = record.get("spn_valores", {})

        # Count out-of-range SPNs
        fuera_de_rango_count = sum(
            1 for spn_data in spn_valores.values()
            if spn_data.get("fuera_de_rango", False)
        )

        entry = {
            "timestamp": record.get("timestamp", ""),
            "estado_consumo": record.get("estado_consumo", "SIN_DATOS"),
            "rendimiento_kml": _safe_float(record.get("rendimiento_kml")),
            "spns_fuera_de_rango": fuera_de_rango_count,
        }
        historial.append(entry)

    return historial


def _extract_trip_context(record):
    """Extract trip context fields from a DynamoDB record.

    Args:
        record: A single DynamoDB item.

    Returns:
        Dict with trip context: viaje_ruta, viaje_ruta_origen,
        viaje_ruta_destino, operador_cve, operador_desc.
    """
    return {
        "viaje_ruta": record.get("viaje_ruta", ""),
        "viaje_ruta_origen": record.get("viaje_ruta_origen", ""),
        "viaje_ruta_destino": record.get("viaje_ruta_destino", ""),
        "operador_cve": record.get("operador_cve", ""),
        "operador_desc": record.get("operador_desc", ""),
    }


# ---------------------------------------------------------------------------
# Lambda handler (Req 3.1–3.6, 11.4, 11.6)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the consultar-telemetria tool.

    Invoked by Bedrock AgentCore as a Fuel Agent Action Group tool.

    Flow:
      1. Parse ``autobus`` and optional ``ultimos_n_registros`` from event.
      2. Load SPN catalog from S3 (cached via lru_cache).
      3. Query DynamoDB for the latest N records of the bus.
      4. If no records found, return an empty-data response.
      5. Build ``variables_actuales`` from the most recent record's spn_valores.
      6. Build ``alertas_activas`` from the most recent record's alertas_spn.
      7. Build ``historial_reciente`` summarising all N records.
      8. Include trip context from the most recent record.
      9. Return formatted response via ``build_agent_response()``.

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

    # --- 1. Parse parameters (Req 3.1) ---
    autobus = _get_param(event, "autobus")
    if not autobus:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_autobus_parameter",
        }))
        return build_error_response("Parámetro 'autobus' es requerido.", 400)

    autobus = str(autobus).strip()

    # Parse optional limit with bounds
    ultimos_n_raw = _get_param(event, "ultimos_n_registros")
    if ultimos_n_raw is not None:
        try:
            limit = int(ultimos_n_raw)
            limit = max(1, min(limit, MAX_LIMIT))
        except (ValueError, TypeError):
            limit = DEFAULT_LIMIT
    else:
        limit = DEFAULT_LIMIT

    logger.info(json.dumps({
        "action": "parse_params",
        "autobus": autobus,
        "limit": limit,
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

    # --- 3. Query DynamoDB (Req 3.1) ---
    try:
        records = query_latest_records(DYNAMODB_TABLE, autobus, limit)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "query_dynamodb",
            "autobus": autobus,
            "error": str(exc),
        }))
        return build_error_response(
            f"Error al consultar telemetría del autobús {autobus}.", 500
        )

    # --- 4. Empty-data response (Req 3.6) ---
    if not records:
        logger.info(json.dumps({
            "action": "no_records_found",
            "autobus": autobus,
        }))
        return build_agent_response({
            "autobus": autobus,
            "mensaje": f"No se encontraron registros de telemetría para el autobús {autobus}.",
            "variables_actuales": [],
            "alertas_activas": [],
            "historial_reciente": [],
        })

    # --- 5. Build variables_actuales from most recent record (Req 3.2, 3.3) ---
    latest_record = records[0]
    variables_actuales = _build_variables_actuales(latest_record, catalogo_spn)

    # --- 6. Build alertas_activas from most recent record ---
    alertas_spn_raw = latest_record.get("alertas_spn", [])
    alertas_activas = []
    for alerta in alertas_spn_raw:
        alertas_activas.append({
            "spn_id": alerta.get("spn_id"),
            "nombre": alerta.get("name", ""),
            "valor": _safe_float(alerta.get("valor")),
            "unidad": alerta.get("unidad", ""),
            "mensaje": alerta.get("mensaje", ""),
        })

    # --- 7. Build historial_reciente (Req 3.5) ---
    historial_reciente = _build_historial_reciente(records)

    # --- 8. Build trip context (Req 3.4) ---
    trip_context = _extract_trip_context(latest_record)

    # --- 9. Assemble and return response (Req 11.4) ---
    response_body = {
        "autobus": autobus,
        "ultimo_timestamp": latest_record.get("timestamp", ""),
        "registros_consultados": len(records),
        **trip_context,
        "variables_actuales": variables_actuales,
        "alertas_activas": alertas_activas,
        "historial_reciente": historial_reciente,
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "autobus": autobus,
        "records_returned": len(records),
        "variables_count": len(variables_actuales),
        "alertas_count": len(alertas_activas),
    }))

    return build_agent_response(response_body)
