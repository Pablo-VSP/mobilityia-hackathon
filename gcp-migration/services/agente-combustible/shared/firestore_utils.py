"""
firestore_utils — Helpers de lectura/escritura para Google Cloud Firestore.

Equivalente a dynamo_utils.py del proyecto AWS. Provee funciones para
consultar y escribir en las colecciones Firestore del proyecto:

  - telemetria-live (doc_id: {autobus}_{timestamp})
  - alertas (doc_id: UUID)

Usa google-cloud-firestore y registra eventos en formato JSON
para Cloud Logging.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Firestore client (reutilizado entre requests en Cloud Run)
_db: Optional[firestore.Client] = None


def get_db() -> firestore.Client:
    """Obtiene o crea el cliente Firestore (singleton)."""
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


def query_latest_records(
    collection: str,
    autobus: str,
    limit: int = 10,
) -> list[dict]:
    """
    Consulta los últimos N registros de un autobús en Firestore,
    ordenados por timestamp descendente.

    Args:
        collection: Nombre de la colección (ej: 'telemetria-live').
        autobus: Número económico del autobús.
        limit: Cantidad máxima de registros a retornar.

    Returns:
        Lista de diccionarios con los registros más recientes.
    """
    try:
        db = get_db()
        query = (
            db.collection(collection)
            .where("autobus", "==", autobus)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = query.stream()
        items = [doc.to_dict() for doc in docs]

        logger.info(json.dumps({
            "action": "query_latest_records",
            "collection": collection,
            "autobus": autobus,
            "limit": limit,
            "records_returned": len(items),
        }))
        return items

    except Exception as e:
        logger.error(json.dumps({
            "action": "query_latest_records",
            "collection": collection,
            "autobus": autobus,
            "error": str(e),
        }))
        raise


def batch_write_items(collection: str, items: list[dict]) -> dict:
    """
    Escribe múltiples documentos en Firestore usando batch writes.

    Divide los ítems en lotes de 500 (límite de Firestore batch).

    Args:
        collection: Nombre de la colección.
        items: Lista de diccionarios a escribir.

    Returns:
        Diccionario con resumen: total_items, items_written.
    """
    total_items = len(items)
    items_written = 0

    try:
        db = get_db()
        col_ref = db.collection(collection)

        # Firestore batch limit is 500 operations
        batch_size = 500
        for i in range(0, len(items), batch_size):
            batch = db.batch()
            chunk = items[i : i + batch_size]

            for item in chunk:
                # Use autobus_timestamp as document ID for telemetria
                doc_id = item.get("doc_id") or f"{item.get('autobus', 'unknown')}_{item.get('timestamp', '')}"
                doc_ref = col_ref.document(doc_id)
                batch.set(doc_ref, item)

            batch.commit()
            items_written += len(chunk)

        result = {
            "total_items": total_items,
            "items_written": items_written,
        }

        logger.info(json.dumps({
            "action": "batch_write_items",
            "collection": collection,
            **result,
        }))
        return result

    except Exception as e:
        logger.error(json.dumps({
            "action": "batch_write_items",
            "collection": collection,
            "total_items": total_items,
            "items_written": items_written,
            "error": str(e),
        }))
        raise


def put_item(collection: str, item: dict, doc_id: Optional[str] = None) -> None:
    """
    Escribe un solo documento en Firestore.

    Args:
        collection: Nombre de la colección.
        item: Diccionario con los datos del documento.
        doc_id: ID del documento (opcional, auto-generado si no se provee).
    """
    try:
        db = get_db()
        col_ref = db.collection(collection)

        if doc_id:
            col_ref.document(doc_id).set(item)
        else:
            col_ref.add(item)

        logger.info(json.dumps({
            "action": "put_item",
            "collection": collection,
            "doc_id": doc_id or "auto",
        }))

    except Exception as e:
        logger.error(json.dumps({
            "action": "put_item",
            "collection": collection,
            "error": str(e),
        }))
        raise


def scan_recent(collection: str, timestamp_limit: str) -> list[dict]:
    """
    Consulta documentos con timestamp mayor al límite proporcionado.

    Args:
        collection: Nombre de la colección.
        timestamp_limit: Timestamp ISO 8601 mínimo (exclusivo).

    Returns:
        Lista de diccionarios con los documentos que cumplen el filtro.
    """
    try:
        db = get_db()
        query = (
            db.collection(collection)
            .where("timestamp", ">", timestamp_limit)
        )
        docs = query.stream()
        items = [doc.to_dict() for doc in docs]

        logger.info(json.dumps({
            "action": "scan_recent",
            "collection": collection,
            "timestamp_limit": timestamp_limit,
            "records_returned": len(items),
        }))
        return items

    except Exception as e:
        logger.error(json.dumps({
            "action": "scan_recent",
            "collection": collection,
            "timestamp_limit": timestamp_limit,
            "error": str(e),
        }))
        raise


def query_by_field(
    collection: str,
    field: str,
    value: str,
    order_by: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Consulta documentos por un campo específico.

    Args:
        collection: Nombre de la colección.
        field: Campo a filtrar.
        value: Valor del campo.
        order_by: Campo para ordenar (opcional).
        limit: Máximo de documentos a retornar.

    Returns:
        Lista de diccionarios con los documentos encontrados.
    """
    try:
        db = get_db()
        query = db.collection(collection).where(field, "==", value)

        if order_by:
            query = query.order_by(order_by, direction=firestore.Query.DESCENDING)

        query = query.limit(limit)
        docs = query.stream()
        items = [doc.to_dict() for doc in docs]

        logger.info(json.dumps({
            "action": "query_by_field",
            "collection": collection,
            "field": field,
            "value": value,
            "records_returned": len(items),
        }))
        return items

    except Exception as e:
        logger.error(json.dumps({
            "action": "query_by_field",
            "collection": collection,
            "error": str(e),
        }))
        raise
