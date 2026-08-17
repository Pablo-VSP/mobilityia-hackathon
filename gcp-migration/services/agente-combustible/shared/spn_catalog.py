"""
spn_catalog — Catálogo SPN con validación de rangos.

Mismo catálogo de 36 SPNs, adaptado para GCP (usa gcs_utils).
Cachea el catálogo en memoria tras la primera carga.
"""

import json
import logging
from functools import lru_cache
from typing import Optional

from .gcs_utils import read_json_from_gcs

logger = logging.getLogger(__name__)

_catalog_cache: Optional[dict] = None


def cargar_catalogo_spn(bucket: str, blob_path: str) -> dict:
    """
    Carga el catálogo SPN desde GCS. Cachea en memoria.

    Args:
        bucket: Bucket GCS.
        blob_path: Ruta al motor_spn.json.

    Returns:
        Dict con SPN ID (int) como clave y metadata como valor.
    """
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache

    raw_data = read_json_from_gcs(bucket, blob_path)

    catalog = {}
    items = raw_data if isinstance(raw_data, list) else raw_data.get("spns", [])
    for item in items:
        spn_id = int(item.get("id", 0))
        catalog[spn_id] = {
            "id": spn_id,
            "name": item.get("name", f"SPN_{spn_id}"),
            "unidad": item.get("unidad", ""),
            "minimo": float(item.get("minimo", 0)),
            "maximo": float(item.get("maximo", 9999)),
            "tipo": item.get("tipo", "FLOAT"),
            "delta": float(item.get("delta", 0)),
            "variable_tipo": item.get("variable_tipo", "EDA"),
        }

    _catalog_cache = catalog
    logger.info(f"Catálogo SPN cargado: {len(catalog)} variables")
    return catalog


def obtener_spn(catalogo: dict, spn_id: int) -> Optional[dict]:
    """Obtiene metadata de un SPN del catálogo."""
    return catalogo.get(spn_id)


def valor_fuera_de_rango(catalogo: dict, spn_id: int, valor: float) -> tuple[bool, str]:
    """
    Verifica si un valor está fuera del rango del catálogo.

    Returns:
        Tuple (fuera_de_rango: bool, mensaje: str)
    """
    spn_info = catalogo.get(spn_id)
    if spn_info is None:
        return False, ""

    minimo = spn_info["minimo"]
    maximo = spn_info["maximo"]
    nombre = spn_info["name"]

    if valor < minimo:
        return True, f"{nombre} ({valor} {spn_info['unidad']}) por debajo del mínimo ({minimo})"
    if valor > maximo:
        return True, f"{nombre} ({valor} {spn_info['unidad']}) por encima del máximo ({maximo})"

    return False, ""


def variacion_anomala(catalogo: dict, spn_id: int, valor_anterior: float, valor_actual: float) -> bool:
    """
    Detecta si la variación entre dos lecturas consecutivas es anómala
    (mayor a 2x delta del catálogo).
    """
    spn_info = catalogo.get(spn_id)
    if spn_info is None:
        return False

    delta = spn_info.get("delta", 0)
    if delta <= 0:
        return False

    variacion = abs(valor_actual - valor_anterior)
    return variacion > (2 * delta)
