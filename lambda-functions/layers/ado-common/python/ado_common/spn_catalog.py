"""
spn_catalog — Carga y validación del catálogo SPN desde S3.

Provee funciones para cargar el catálogo de 36 SPNs confirmados,
buscar entradas individuales y validar valores contra los rangos
definidos (minimo/maximo) y variaciones anómalas (delta).

El catálogo se cachea en memoria con lru_cache para reutilización
entre invocaciones Lambda en caliente (Req 1.2).

Funciones públicas:
    cargar_catalogo_spn   Carga catálogo desde S3, cacheado con lru_cache.
    obtener_spn           Busca una entrada SPN por ID.
    valor_fuera_de_rango  Verifica si un valor está fuera del rango [minimo, maximo].
    variacion_anomala     Detecta variación anómala entre lecturas consecutivas (2x delta).
"""

import json
import logging
from functools import lru_cache

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_s3_client = boto3.client("s3")


@lru_cache(maxsize=4)
def cargar_catalogo_spn(
    bucket: str,
    key: str = "catalogo/motor_spn.json",
) -> dict[int, dict]:
    """
    Carga el catálogo SPN desde un archivo JSON en S3 y lo retorna
    como diccionario indexado por SPN ID.

    El resultado se cachea con lru_cache para que invocaciones
    posteriores en la misma instancia Lambda no repitan la lectura.

    Args:
        bucket: Nombre del bucket S3 (ej: 'ado-mobilityia-mvp').
        key: Clave del objeto JSON en S3 (default: 'catalogo/motor_spn.json').

    Returns:
        Diccionario {spn_id (int): {id, name, unidad, minimo, maximo, delta,
        tipo, variable_tipo}} con todas las entradas del catálogo.

    Raises:
        Exception: Si la lectura de S3 falla (el caller debe manejar el error).
    """
    try:
        response = _s3_client.get_object(Bucket=bucket, Key=key)
        raw = json.loads(response["Body"].read().decode("utf-8"))

        catalogo: dict[int, dict] = {}
        for entry in raw:
            spn_id = int(entry["id"])
            catalogo[spn_id] = {
                "id": spn_id,
                "name": entry.get("name", "").strip(),
                "unidad": entry.get("unidad", "").strip(),
                "minimo": float(entry.get("minimo", 0)),
                "maximo": float(entry.get("maximo", 0)),
                "delta": float(entry.get("delta", 0)),
                "tipo": entry.get("tipo", "FLOAT").strip(),
                "variable_tipo": entry.get("variable_tipo", "EDA").strip(),
            }

        logger.info(json.dumps({
            "action": "cargar_catalogo_spn",
            "bucket": bucket,
            "key": key,
            "spn_count": len(catalogo),
        }))
        return catalogo

    except Exception as e:
        logger.error(json.dumps({
            "action": "cargar_catalogo_spn",
            "bucket": bucket,
            "key": key,
            "error": str(e),
        }))
        raise


def obtener_spn(catalogo: dict[int, dict], spn_id: int) -> dict | None:
    """
    Busca una entrada SPN por ID en el catálogo cargado.

    Args:
        catalogo: Diccionario retornado por cargar_catalogo_spn().
        spn_id: Identificador numérico del SPN a buscar.

    Returns:
        Diccionario con {id, name, unidad, minimo, maximo, delta, variable_tipo}
        o None si el SPN no existe en el catálogo.
    """
    return catalogo.get(spn_id)


def valor_fuera_de_rango(
    catalogo: dict[int, dict],
    spn_id: int,
    valor: float,
) -> tuple[bool, str]:
    """
    Verifica si un valor SPN está fuera del rango [minimo, maximo]
    definido en el catálogo.

    Args:
        catalogo: Diccionario retornado por cargar_catalogo_spn().
        spn_id: Identificador numérico del SPN.
        valor: Valor actual de la lectura del sensor.

    Returns:
        Tupla (fuera_de_rango: bool, mensaje: str).
        Si el SPN no existe en el catálogo, retorna (False, "SPN no encontrado").
    """
    spn = catalogo.get(spn_id)
    if spn is None:
        return False, f"SPN {spn_id} no encontrado en catálogo"

    minimo = spn["minimo"]
    maximo = spn["maximo"]

    if valor < minimo:
        return True, (
            f"SPN {spn_id} ({spn['name']}): valor {valor} {spn['unidad']} "
            f"por debajo del mínimo {minimo} {spn['unidad']}"
        )
    if valor > maximo:
        return True, (
            f"SPN {spn_id} ({spn['name']}): valor {valor} {spn['unidad']} "
            f"por encima del máximo {maximo} {spn['unidad']}"
        )

    return False, ""


def variacion_anomala(
    catalogo: dict[int, dict],
    spn_id: int,
    valor_anterior: float,
    valor_actual: float,
) -> bool:
    """
    Detecta si la variación entre dos lecturas consecutivas de un SPN
    excede 2 veces el delta esperado definido en el catálogo.

    Umbral = 2 × delta del catálogo (Req 1.4).

    Args:
        catalogo: Diccionario retornado por cargar_catalogo_spn().
        spn_id: Identificador numérico del SPN.
        valor_anterior: Valor de la lectura previa.
        valor_actual: Valor de la lectura actual.

    Returns:
        True si la variación es anómala (|actual - anterior| > 2 * delta),
        False si es normal o si el SPN no existe en el catálogo.
    """
    spn = catalogo.get(spn_id)
    if spn is None:
        return False

    delta = spn["delta"]
    if delta <= 0:
        # Si delta es 0 o negativo, no se puede evaluar variación
        return False

    variacion = abs(valor_actual - valor_anterior)
    umbral = 2.0 * delta

    return variacion > umbral
