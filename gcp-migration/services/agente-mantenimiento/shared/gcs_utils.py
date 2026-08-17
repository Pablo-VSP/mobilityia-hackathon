"""
gcs_utils — Helpers de lectura para Google Cloud Storage.

Equivalente a s3_utils.py del proyecto AWS. Provee funciones para
leer archivos JSON y listar objetos en GCS.
"""

import json
import logging
from typing import Optional

from google.cloud import storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# GCS client (reutilizado entre requests)
_gcs_client: Optional[storage.Client] = None


def get_gcs_client() -> storage.Client:
    """Obtiene o crea el cliente GCS (singleton)."""
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


def read_json_from_gcs(bucket: str, blob_path: str) -> dict | list:
    """
    Lee y parsea un archivo JSON desde Cloud Storage.

    Args:
        bucket: Nombre del bucket GCS.
        blob_path: Ruta del objeto (ej: 'hackathon-data/catalogo/motor_spn.json').

    Returns:
        Contenido parseado del JSON.
    """
    try:
        client = get_gcs_client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(blob_path)
        content = blob.download_as_text()
        data = json.loads(content)

        logger.info(json.dumps({
            "action": "read_json_from_gcs",
            "bucket": bucket,
            "blob_path": blob_path,
            "type": type(data).__name__,
            "size": len(data) if isinstance(data, (list, dict)) else 0,
        }))
        return data

    except Exception as e:
        logger.error(json.dumps({
            "action": "read_json_from_gcs",
            "bucket": bucket,
            "blob_path": blob_path,
            "error": str(e),
        }))
        raise


def read_bytes_from_gcs(bucket: str, blob_path: str) -> bytes:
    """
    Lee bytes de un archivo en Cloud Storage.

    Args:
        bucket: Nombre del bucket GCS.
        blob_path: Ruta del objeto.

    Returns:
        Contenido en bytes.
    """
    try:
        client = get_gcs_client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(blob_path)
        data = blob.download_as_bytes()

        logger.info(json.dumps({
            "action": "read_bytes_from_gcs",
            "bucket": bucket,
            "blob_path": blob_path,
            "size_bytes": len(data),
        }))
        return data

    except Exception as e:
        logger.error(json.dumps({
            "action": "read_bytes_from_gcs",
            "bucket": bucket,
            "blob_path": blob_path,
            "error": str(e),
        }))
        raise


def list_blobs(bucket: str, prefix: str) -> list[str]:
    """
    Lista objetos bajo un prefijo en GCS.

    Args:
        bucket: Nombre del bucket GCS.
        prefix: Prefijo para filtrar objetos.

    Returns:
        Lista de nombres de blob.
    """
    try:
        client = get_gcs_client()
        bucket_obj = client.bucket(bucket)
        blobs = bucket_obj.list_blobs(prefix=prefix)
        names = [blob.name for blob in blobs]

        logger.info(json.dumps({
            "action": "list_blobs",
            "bucket": bucket,
            "prefix": prefix,
            "blobs_found": len(names),
        }))
        return names

    except Exception as e:
        logger.error(json.dumps({
            "action": "list_blobs",
            "bucket": bucket,
            "prefix": prefix,
            "error": str(e),
        }))
        raise


def upload_json_to_gcs(bucket: str, blob_path: str, data: dict | list) -> None:
    """
    Sube un JSON a Cloud Storage.

    Args:
        bucket: Nombre del bucket GCS.
        blob_path: Ruta destino del objeto.
        data: Datos a serializar como JSON.
    """
    try:
        client = get_gcs_client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(blob_path)
        content = json.dumps(data, ensure_ascii=False, default=str)
        blob.upload_from_string(content, content_type="application/json")

        logger.info(json.dumps({
            "action": "upload_json_to_gcs",
            "bucket": bucket,
            "blob_path": blob_path,
        }))

    except Exception as e:
        logger.error(json.dumps({
            "action": "upload_json_to_gcs",
            "bucket": bucket,
            "blob_path": blob_path,
            "error": str(e),
        }))
        raise
