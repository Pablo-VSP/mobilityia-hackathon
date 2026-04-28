"""
tool-consultar-alertas — Consulta alertas activas por autobús.

Maintenance Agent Tool invocado por Bedrock AgentCore. Consulta la tabla
ado-alertas para obtener las alertas activas de un autobús específico,
o todas las alertas activas si no se especifica autobús.

Permite al agente verificar si ya existen tickets antes de crear nuevos.
"""

import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Attr

from ado_common.response import build_agent_response, build_error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_ALERTAS = os.environ.get("DYNAMODB_TABLE_ALERTAS", "ado-alertas")

_dynamodb = boto3.resource("dynamodb")


def _get_param(event, name, default=None):
    """Extract a named parameter from a Bedrock AgentCore event."""
    params = event.get("parameters", [])
    for p in params:
        if p.get("name") == name:
            return p.get("value", default)
    return default


def lambda_handler(event, context):
    """Query active alerts, optionally filtered by bus number.

    Parameters:
        autobus (optional): Filter alerts for a specific bus.

    Returns:
        List of active alerts with full details.
    """
    logger.info(json.dumps({
        "action": "lambda_handler",
        "event_keys": list(event.keys()) if isinstance(event, dict) else "not_dict",
    }))

    autobus = _get_param(event, "autobus")

    table = _dynamodb.Table(TABLE_ALERTAS)

    # Build filter expression
    filter_expr = Attr("estado").eq("ACTIVA")
    if autobus:
        autobus = str(autobus).strip()
        filter_expr = filter_expr & Attr("autobus").eq(autobus)

    # Scan with filter
    items = []
    scan_kwargs = {"FilterExpression": filter_expr}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    # Sort by timestamp descending (newest first)
    items.sort(key=lambda a: a.get("timestamp", ""), reverse=True)

    alertas = []
    for item in items:
        alertas.append({
            "alerta_id": item.get("alerta_id", ""),
            "timestamp": item.get("timestamp", ""),
            "autobus": item.get("autobus", ""),
            "tipo_alerta": item.get("tipo_alerta", ""),
            "nivel_riesgo": item.get("nivel_riesgo", ""),
            "diagnostico": item.get("diagnostico", ""),
            "urgencia": item.get("urgencia", ""),
            "componentes": item.get("componentes", []),
            "numero_referencia": item.get("numero_referencia", ""),
            "estado": item.get("estado", ""),
            "agente_origen": item.get("agente_origen", ""),
            "viaje_ruta": item.get("viaje_ruta", ""),
            "operador_desc": item.get("operador_desc", ""),
        })

    if autobus:
        if alertas:
            mensaje = (
                f"El autobús {autobus} tiene {len(alertas)} alerta(s) activa(s). "
                f"Ya existe un ticket registrado. No es necesario generar uno nuevo."
            )
        else:
            mensaje = (
                f"El autobús {autobus} no tiene alertas activas registradas. "
                f"Si el análisis indica riesgo moderado o superior, se puede generar una nueva recomendación."
            )
    else:
        mensaje = f"Hay {len(alertas)} alerta(s) activa(s) en total."

    response_body = {
        "total_alertas": len(alertas),
        "alertas": alertas,
        "mensaje": mensaje,
        "autobus_consultado": autobus or "todos",
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "autobus": autobus or "todos",
        "alertas_count": len(alertas),
    }))

    return build_agent_response(response_body)
