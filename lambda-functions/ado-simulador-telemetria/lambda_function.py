"""
ado-simulador-telemetria — Simulador de telemetría en tiempo real.

Lee registros de telemetría simulada desde S3, los pivotea en estado
consolidado por autobús usando el catálogo SPN, clasifica el consumo
de combustible y escribe el estado en DynamoDB.

Requisitos: 2.1–2.10, 11.3, 11.5
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

from ado_common.constants import SPN_RENDIMIENTO, SPN_TASA_COMBUSTIBLE
from ado_common.spn_catalog import cargar_catalogo_spn
from ado_common.telemetry_pivot import pivotar_telemetria
from ado_common.dynamo_utils import batch_write_items
from ado_common.s3_utils import read_json_from_s3, list_objects

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Clasificación de consumo de combustible (Req 2.5)
# ---------------------------------------------------------------------------

def clasificar_consumo(spn_valores: dict) -> str:
    """Clasifica el estado de consumo de combustible a partir de los SPNs disponibles.

    Lógica de clasificación:
      - **Primario** — SPN 185 (Rendimiento km/L):
            ≥ 3.0  → EFICIENTE
            2.0–3.0 → ALERTA_MODERADA
            < 2.0  → ALERTA_SIGNIFICATIVA
      - **Fallback** — SPN 183 (Tasa de combustible L/h):
            ≤ 30   → EFICIENTE
            30–50  → ALERTA_MODERADA
            > 50   → ALERTA_SIGNIFICATIVA
      - Si ninguno de los dos SPNs está disponible → SIN_DATOS

    Args:
        spn_valores: Diccionario con claves string de SPN IDs.
                     Cada valor es un dict con al menos ``{"valor": float}``.

    Returns:
        Una de: ``EFICIENTE``, ``ALERTA_MODERADA``,
        ``ALERTA_SIGNIFICATIVA`` o ``SIN_DATOS``.
    """
    # --- Intento primario: SPN 185 (Rendimiento km/L) ---
    spn_rendimiento = spn_valores.get(str(SPN_RENDIMIENTO))
    if spn_rendimiento is not None:
        rendimiento = spn_rendimiento.get("valor")
        if rendimiento is not None:
            rendimiento = float(rendimiento)
            if rendimiento >= 3.0:
                return "EFICIENTE"
            if rendimiento >= 2.0:
                return "ALERTA_MODERADA"
            return "ALERTA_SIGNIFICATIVA"

    # --- Fallback: SPN 183 (Tasa de combustible L/h) ---
    spn_tasa = spn_valores.get(str(SPN_TASA_COMBUSTIBLE))
    if spn_tasa is not None:
        tasa = spn_tasa.get("valor")
        if tasa is not None:
            tasa = float(tasa)
            if tasa <= 30.0:
                return "EFICIENTE"
            if tasa <= 50.0:
                return "ALERTA_MODERADA"
            return "ALERTA_SIGNIFICATIVA"

    # --- Ningún SPN disponible ---
    return "SIN_DATOS"


# ---------------------------------------------------------------------------
# Helpers (Req 2.1, 2.6)
# ---------------------------------------------------------------------------

# Environment variables (Req 11.5)
NUM_BUSES = int(os.environ.get("NUM_BUSES", "20"))
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_TELEMETRIA_PREFIX = os.environ.get("S3_TELEMETRIA_PREFIX", "hackathon-data/telemetria-simulada/")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "hackathon-data/catalogo/motor_spn.json")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "ado-telemetria-live")

# Temporal window size in seconds for grouping records (~30s)
VENTANA_TEMPORAL_SEGUNDOS = 30


def _listar_archivos_telemetria(bucket: str, prefix: str) -> list[str]:
    """Lista los archivos JSON de telemetría disponibles en S3.

    Args:
        bucket: Nombre del bucket S3.
        prefix: Prefijo bajo el cual buscar archivos.

    Returns:
        Lista de claves S3 filtradas a archivos JSON.
    """
    keys = list_objects(bucket, prefix)
    # Filtrar solo archivos JSON (excluir directorios/prefijos vacíos)
    return [k for k in keys if k.endswith(".json") or k.endswith(".JSON")]


def _leer_bloque_telemetria(
    bucket: str,
    key: str,
    offset: int,
    block_size: int = 50,
) -> list[dict]:
    """Lee un bloque de registros de telemetría desde un archivo S3.

    Carga el archivo completo y extrae un bloque circular de registros
    a partir del offset dado.

    Args:
        bucket: Nombre del bucket S3.
        key: Clave del archivo JSON en S3.
        offset: Índice de inicio dentro del archivo.
        block_size: Cantidad de registros a extraer.

    Returns:
        Lista de registros de telemetría (dicts).
    """
    data = read_json_from_s3(bucket, key)
    if not isinstance(data, list) or len(data) == 0:
        return []

    total = len(data)
    # Extracción circular
    registros = []
    for i in range(block_size):
        idx = (offset + i) % total
        registros.append(data[idx])
    return registros


def _agrupar_por_ventana_temporal(
    registros: list[dict],
    ventana_segundos: int = VENTANA_TEMPORAL_SEGUNDOS,
) -> list[list[dict]]:
    """Agrupa registros de telemetría por ventana temporal.

    Ordena los registros por evento_fecha_hora y los agrupa en ventanas
    de aproximadamente `ventana_segundos` segundos.

    Args:
        registros: Lista de registros con campo evento_fecha_hora.
        ventana_segundos: Tamaño de la ventana en segundos.

    Returns:
        Lista de grupos, donde cada grupo es una lista de registros.
    """
    if not registros:
        return []

    # Intentar ordenar por evento_fecha_hora
    def _parse_ts(r):
        ts = r.get("evento_fecha_hora", "")
        if isinstance(ts, str) and ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except (ValueError, TypeError):
                pass
        return 0.0

    sorted_records = sorted(registros, key=_parse_ts)

    grupos: list[list[dict]] = []
    grupo_actual: list[dict] = []
    ts_inicio: float | None = None

    for registro in sorted_records:
        ts = _parse_ts(registro)
        if ts_inicio is None:
            ts_inicio = ts

        if ts - ts_inicio > ventana_segundos and grupo_actual:
            grupos.append(grupo_actual)
            grupo_actual = [registro]
            ts_inicio = ts
        else:
            grupo_actual.append(registro)

    if grupo_actual:
        grupos.append(grupo_actual)

    return grupos


# ---------------------------------------------------------------------------
# Lambda handler (Req 2.1–2.10, 11.3, 11.5)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Punto de entrada del simulador de telemetría.

    Flujo de ejecución:
      1. Carga el catálogo SPN desde S3 (cacheado via lru_cache).
      2. Lista los archivos de telemetría disponibles en S3.
      3. Para cada uno de los NUM_BUSES autobuses:
         a. Calcula un offset estacionario para ciclar por los registros.
         b. Lee un bloque de registros de telemetría desde S3.
         c. Agrupa los registros por ventana temporal (~30s).
         d. Pivotea los registros en estado consolidado.
         e. Clasifica el consumo de combustible.
         f. Establece TTL de 24 horas.
      4. Escribe todos los estados en DynamoDB via batch_write_items.
      5. Registra un resumen en formato JSON estructurado.

    Args:
        event: Evento de EventBridge Scheduler (no se usa).
        context: Contexto Lambda (no se usa).

    Returns:
        Diccionario con resumen de la ejecución.
    """
    ahora = time.time()
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    # --- 1. Cargar catálogo SPN (Req 2.2, 2.9) ---
    try:
        catalogo_spn = cargar_catalogo_spn(S3_BUCKET, S3_CATALOGO_KEY)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "lambda_handler",
            "error": "catalogo_spn_load_failed",
            "detail": str(exc),
            "bucket": S3_BUCKET,
            "key": S3_CATALOGO_KEY,
        }))
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "skipped",
                "reason": "SPN catalog load failure",
            }),
        }

    # --- 2. Listar archivos de telemetría en S3 ---
    try:
        archivos_telemetria = _listar_archivos_telemetria(S3_BUCKET, S3_TELEMETRIA_PREFIX)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "lambda_handler",
            "error": "list_telemetry_files_failed",
            "detail": str(exc),
        }))
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "skipped",
                "reason": "Cannot list telemetry files from S3",
            }),
        }

    if not archivos_telemetria:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "warning": "no_telemetry_files",
            "prefix": S3_TELEMETRIA_PREFIX,
        }))
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "skipped",
                "reason": "No telemetry files found in S3",
            }),
        }

    total_archivos = len(archivos_telemetria)

    # --- 3. Procesar cada autobús (Req 2.1, 2.6) ---
    items_para_dynamo: list[dict] = []
    buses_procesados = 0
    buses_omitidos = 0

    for bus_index in range(NUM_BUSES):
        try:
            # 3a. Offset estacionario (Req 2.6)
            archivo_index = bus_index % total_archivos
            archivo_key = archivos_telemetria[archivo_index]

            # Leer el archivo para obtener total_records y calcular offset
            registros_raw = read_json_from_s3(S3_BUCKET, archivo_key)
            if not isinstance(registros_raw, list) or len(registros_raw) == 0:
                buses_omitidos += 1
                continue

            total_records = len(registros_raw)
            offset = (int(ahora) // 10 + bus_index) % total_records

            # 3b. Extraer bloque de registros desde el offset
            block_size = min(50, total_records)
            registros_bloque = []
            for i in range(block_size):
                idx = (offset + i) % total_records
                registros_bloque.append(registros_raw[idx])

            if not registros_bloque:
                buses_omitidos += 1
                continue

            # 3c. Agrupar por ventana temporal (~30s)
            grupos = _agrupar_por_ventana_temporal(registros_bloque)

            # Usar el último grupo (más reciente) para el estado actual
            registros_ventana = grupos[-1] if grupos else registros_bloque

            # 3d. Pivotar telemetría (Req 2.2, 2.3)
            estado = pivotar_telemetria(registros_ventana, catalogo_spn, solo_prioritarios=True)

            if not estado:
                buses_omitidos += 1
                continue

            # 3e. Clasificar consumo (Req 2.5)
            spn_valores = estado.get("spn_valores", {})
            estado["estado_consumo"] = clasificar_consumo(spn_valores)

            # 3f. Establecer timestamp y TTL (Req 2.7)
            estado["timestamp"] = timestamp_iso
            estado["ttl_expiry"] = int(ahora) + 86400

            items_para_dynamo.append(estado)
            buses_procesados += 1

        except Exception as exc:
            # Req 2.10: Si falla la telemetría de un bus, saltar y continuar
            logger.warning(json.dumps({
                "action": "process_bus",
                "bus_index": bus_index,
                "error": str(exc),
                "status": "skipped",
            }))
            buses_omitidos += 1
            continue

    # --- 4. Escribir en DynamoDB (Req 2.4, 2.7) ---
    write_result = {}
    if items_para_dynamo:
        try:
            write_result = batch_write_items(DYNAMODB_TABLE, items_para_dynamo)
        except Exception as exc:
            logger.error(json.dumps({
                "action": "batch_write_dynamo",
                "error": str(exc),
                "items_count": len(items_para_dynamo),
            }))

    # --- 5. Log resumen en formato JSON estructurado (Req 11.3) ---
    resumen = {
        "action": "lambda_handler_summary",
        "timestamp": timestamp_iso,
        "buses_procesados": buses_procesados,
        "buses_omitidos": buses_omitidos,
        "items_escritos": write_result.get("items_written", 0),
        "archivos_telemetria": total_archivos,
    }
    logger.info(json.dumps(resumen))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "success",
            "buses_procesados": buses_procesados,
            "buses_omitidos": buses_omitidos,
            "items_escritos": write_result.get("items_written", 0),
        }),
    }
