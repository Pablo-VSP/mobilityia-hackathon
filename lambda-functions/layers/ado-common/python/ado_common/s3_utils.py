"""
s3_utils — Helpers de lectura para Amazon S3.

Módulo utilitario de la capa compartida ado-common-layer que provee
funciones para leer archivos JSON y Parquet desde S3, y listar objetos
bajo un prefijo.

Todas las funciones usan boto3.client('s3') y registran eventos en
formato JSON estructurado para CloudWatch (Req 11.3).
"""

import json
import logging

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_s3_client = boto3.client("s3")


def read_json_from_s3(bucket: str, key: str) -> dict | list:
    """
    Lee y parsea un archivo JSON desde S3.

    Args:
        bucket: Nombre del bucket S3.
        key: Clave del objeto en S3 (ej: 'hackathon-data/fallas-simuladas/data_fault.json').

    Returns:
        Contenido parseado del JSON (dict o list).

    Raises:
        Exception: Si la lectura o el parseo fallan.
    """
    try:
        response = _s3_client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        data = json.loads(body)

        logger.info(json.dumps({
            "action": "read_json_from_s3",
            "bucket": bucket,
            "key": key,
            "type": type(data).__name__,
            "size": len(data) if isinstance(data, (list, dict)) else 0,
        }))
        return data

    except Exception as e:
        logger.error(json.dumps({
            "action": "read_json_from_s3",
            "bucket": bucket,
            "key": key,
            "error": str(e),
        }))
        raise


def read_parquet_from_s3(bucket: str, key: str) -> list[dict]:
    """
    Lee un archivo Parquet desde S3 y lo retorna como lista de dicts.

    Intenta usar pandas para leer Parquet. Si pandas no está disponible
    en el entorno Lambda, hace fallback a leer un archivo JSON con la
    misma ruta pero extensión .json.

    Args:
        bucket: Nombre del bucket S3.
        key: Clave del objeto Parquet en S3.

    Returns:
        Lista de diccionarios con los registros del archivo.

    Raises:
        Exception: Si tanto la lectura Parquet como el fallback JSON fallan.
    """
    try:
        import pandas as pd
        import io

        response = _s3_client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()
        df = pd.read_parquet(io.BytesIO(body))
        data = df.to_dict(orient="records")

        logger.info(json.dumps({
            "action": "read_parquet_from_s3",
            "bucket": bucket,
            "key": key,
            "method": "pandas",
            "records": len(data),
        }))
        return data

    except ImportError:
        # pandas no disponible — fallback a JSON
        logger.info(json.dumps({
            "action": "read_parquet_from_s3",
            "bucket": bucket,
            "key": key,
            "method": "fallback_json",
            "reason": "pandas not available",
        }))
        # Intentar con extensión .json
        json_key = key.rsplit(".", 1)[0] + ".json" if "." in key else key + ".json"
        return read_json_from_s3(bucket, json_key)

    except Exception as e:
        logger.error(json.dumps({
            "action": "read_parquet_from_s3",
            "bucket": bucket,
            "key": key,
            "error": str(e),
        }))
        raise


def list_objects(bucket: str, prefix: str) -> list[str]:
    """
    Lista las claves de objetos bajo un prefijo en S3.

    Maneja paginación automáticamente para prefijos con más de 1000 objetos.

    Args:
        bucket: Nombre del bucket S3.
        prefix: Prefijo para filtrar objetos (ej: 'hackathon-data/telemetria-simulada/2026-04/').

    Returns:
        Lista de strings con las claves de los objetos encontrados.
    """
    try:
        keys: list[str] = []
        continuation_token = None

        while True:
            kwargs = {
                "Bucket": bucket,
                "Prefix": prefix,
            }
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = _s3_client.list_objects_v2(**kwargs)

            for obj in response.get("Contents", []):
                keys.append(obj["Key"])

            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        logger.info(json.dumps({
            "action": "list_objects",
            "bucket": bucket,
            "prefix": prefix,
            "objects_found": len(keys),
        }))
        return keys

    except Exception as e:
        logger.error(json.dumps({
            "action": "list_objects",
            "bucket": bucket,
            "prefix": prefix,
            "error": str(e),
        }))
        raise
