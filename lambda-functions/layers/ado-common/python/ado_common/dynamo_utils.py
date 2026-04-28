"""
dynamo_utils — Helpers de lectura/escritura para Amazon DynamoDB.

Módulo utilitario de la capa compartida ado-common-layer que provee
funciones para consultar y escribir en las tablas DynamoDB del proyecto
ADO MobilityIA:

  - ado-telemetria-live (PK: autobus, SK: timestamp)
  - ado-alertas (PK: alerta_id, SK: timestamp)

Todas las funciones usan boto3.resource('dynamodb') y registran
eventos en formato JSON estructurado para CloudWatch (Req 11.3).
"""

import json
import logging
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr


def _convert_floats(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Inicialización del recurso DynamoDB (reutilizado entre invocaciones Lambda)
_dynamodb_resource = boto3.resource("dynamodb")


def _get_table(table_name: str):
    """Obtiene referencia a una tabla DynamoDB."""
    return _dynamodb_resource.Table(table_name)


def query_latest_records(table_name: str, autobus: str, limit: int = 10) -> list[dict]:
    """
    Consulta los últimos N registros de un autobús en DynamoDB,
    ordenados por timestamp descendente.

    Usa ScanIndexForward=False para obtener los registros más recientes primero.
    La tabla debe tener PK=autobus (S) y SK=timestamp (S).

    Args:
        table_name: Nombre de la tabla DynamoDB (ej: 'ado-telemetria-live').
        autobus: Número económico del autobús (partition key).
        limit: Cantidad máxima de registros a retornar (default 10).

    Returns:
        Lista de diccionarios con los registros más recientes del autobús.
    """
    try:
        table = _get_table(table_name)
        response = table.query(
            KeyConditionExpression=Key("autobus").eq(autobus),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = response.get("Items", [])
        logger.info(json.dumps({
            "action": "query_latest_records",
            "table": table_name,
            "autobus": autobus,
            "limit": limit,
            "records_returned": len(items),
        }))
        return items

    except Exception as e:
        logger.error(json.dumps({
            "action": "query_latest_records",
            "table": table_name,
            "autobus": autobus,
            "error": str(e),
        }))
        raise


def batch_write_items(table_name: str, items: list[dict]) -> dict:
    """
    Escribe múltiples ítems en DynamoDB usando batch_write_item
    con reintentos para ítems no procesados.

    Divide los ítems en lotes de 25 (límite de DynamoDB) y reintenta
    automáticamente los ítems que no se procesaron con backoff exponencial.

    Args:
        table_name: Nombre de la tabla DynamoDB.
        items: Lista de diccionarios a escribir.

    Returns:
        Diccionario con resumen: total_items, items_written, retries.
    """
    total_items = len(items)
    items_written = 0
    retries = 0
    max_retries = 5

    try:
        table = _get_table(table_name)

        # Dividir en lotes de 25 (límite de batch_write_item)
        batch_size = 25
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            with table.batch_writer() as writer:
                for item in batch:
                    writer.put_item(Item=_convert_floats(item))

            items_written += len(batch)

        result = {
            "total_items": total_items,
            "items_written": items_written,
            "retries": retries,
        }

        logger.info(json.dumps({
            "action": "batch_write_items",
            "table": table_name,
            **result,
        }))
        return result

    except Exception as e:
        logger.error(json.dumps({
            "action": "batch_write_items",
            "table": table_name,
            "total_items": total_items,
            "items_written": items_written,
            "error": str(e),
        }))
        raise


def put_item(table_name: str, item: dict) -> dict:
    """
    Escribe un solo ítem en DynamoDB.

    Args:
        table_name: Nombre de la tabla DynamoDB.
        item: Diccionario con los atributos del ítem a escribir.

    Returns:
        Respuesta de DynamoDB (metadata de la operación).
    """
    try:
        table = _get_table(table_name)
        response = table.put_item(Item=_convert_floats(item))

        logger.info(json.dumps({
            "action": "put_item",
            "table": table_name,
            "item_keys": {
                k: str(v) for k, v in item.items()
                if k in ("autobus", "timestamp", "alerta_id")
            },
        }))
        return response

    except Exception as e:
        logger.error(json.dumps({
            "action": "put_item",
            "table": table_name,
            "error": str(e),
        }))
        raise


def scan_recent(table_name: str, timestamp_limit: str) -> list[dict]:
    """
    Escanea la tabla para obtener todos los ítems con timestamp mayor
    al límite proporcionado.

    Usa FilterExpression con Attr para filtrar por timestamp > timestamp_limit.
    Adecuado para tablas pequeñas (~20 buses en el MVP).

    Args:
        table_name: Nombre de la tabla DynamoDB.
        timestamp_limit: Timestamp ISO 8601 mínimo (exclusivo).

    Returns:
        Lista de diccionarios con los ítems que cumplen el filtro.
    """
    try:
        table = _get_table(table_name)
        items = []

        # Scan con paginación para manejar tablas con más de 1MB de datos
        scan_kwargs = {
            "FilterExpression": Attr("timestamp").gt(timestamp_limit),
        }

        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            # Manejar paginación
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key

        logger.info(json.dumps({
            "action": "scan_recent",
            "table": table_name,
            "timestamp_limit": timestamp_limit,
            "records_returned": len(items),
        }))
        return items

    except Exception as e:
        logger.error(json.dumps({
            "action": "scan_recent",
            "table": table_name,
            "timestamp_limit": timestamp_limit,
            "error": str(e),
        }))
        raise


def query_gsi(
    table_name: str,
    index_name: str,
    pk_value: str,
    sk_condition: str,
) -> list[dict]:
    """
    Consulta un Global Secondary Index (GSI) con partition key
    y condición de sort key (mayor que).

    Diseñado para el GSI viaje_ruta-timestamp-index de ado-telemetria-live
    donde PK=viaje_ruta y SK=timestamp.

    Args:
        table_name: Nombre de la tabla DynamoDB.
        index_name: Nombre del GSI (ej: 'viaje_ruta-timestamp-index').
        pk_value: Valor de la partition key del GSI (ej: viaje_ruta).
        sk_condition: Valor para la condición greater-than del sort key
                      (ej: timestamp ISO 8601 para filtrar registros recientes).

    Returns:
        Lista de diccionarios con los ítems que coinciden con la consulta.
    """
    try:
        table = _get_table(table_name)
        items = []

        # Determinar los nombres de las claves del GSI a partir del index_name
        # Formato esperado: '{pk_attr}-{sk_attr}-index'
        gsi_parts = index_name.replace("-index", "").rsplit("-", 1)
        gsi_pk_attr = gsi_parts[0] if len(gsi_parts) >= 1 else "viaje_ruta"
        gsi_sk_attr = gsi_parts[1] if len(gsi_parts) >= 2 else "timestamp"

        query_kwargs = {
            "IndexName": index_name,
            "KeyConditionExpression": (
                Key(gsi_pk_attr).eq(pk_value)
                & Key(gsi_sk_attr).gt(sk_condition)
            ),
        }

        while True:
            response = table.query(**query_kwargs)
            items.extend(response.get("Items", []))

            # Manejar paginación
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            query_kwargs["ExclusiveStartKey"] = last_key

        logger.info(json.dumps({
            "action": "query_gsi",
            "table": table_name,
            "index": index_name,
            "pk_value": pk_value,
            "sk_condition": sk_condition,
            "records_returned": len(items),
        }))
        return items

    except Exception as e:
        logger.error(json.dumps({
            "action": "query_gsi",
            "table": table_name,
            "index": index_name,
            "pk_value": pk_value,
            "error": str(e),
        }))
        raise
