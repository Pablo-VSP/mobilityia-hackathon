"""
tool-buscar-patrones-historicos — Búsqueda de patrones en historial de fallas.

Maintenance Agent Tool invocado por Bedrock AgentCore. Lee el dataset
Data_Fault desde S3, filtra por código de falla (exacto o parcial),
prioriza coincidencias por modelo/marca_comercial sin excluir otros
resultados, y computa estadísticas de patrones históricos.

Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.4
"""

import json
import logging
import os
from collections import Counter
from datetime import datetime

from ado_common.s3_utils import read_json_from_s3, read_parquet_from_s3
from ado_common.response import build_agent_response, build_error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_FALLAS_KEY = os.environ.get("S3_FALLAS_KEY", "hackathon-data/fallas-simuladas/data_fault.json")

# Maximum events to return (Req 8.3)
MAX_EVENTS = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_param(event, name, default=None):
    """Extract a named parameter from a Bedrock AgentCore event."""
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


def _load_faults(bucket, fallas_key):
    """Load fault data from S3, trying JSON first, then Parquet.

    Args:
        bucket: S3 bucket name.
        fallas_key: S3 key for the faults file.

    Returns:
        List of fault dicts.

    Raises:
        Exception: If both JSON and Parquet reads fail.
    """
    if fallas_key.endswith(".parquet"):
        return read_parquet_from_s3(bucket, fallas_key)
    return read_json_from_s3(bucket, fallas_key)


def _filter_by_codigo(faults, codigo):
    """Filter faults by codigo using exact or partial match (in operator).

    Req 8.1: exact or partial match.

    Args:
        faults: List of fault dicts.
        codigo: Fault code to search for.

    Returns:
        List of matching fault dicts.
    """
    codigo_lower = str(codigo).strip().lower()
    return [
        f for f in faults
        if codigo_lower in str(f.get("codigo", "")).strip().lower()
    ]


def _prioritize_matches(faults, modelo=None, marca_comercial=None):
    """Sort faults so that matching modelo/marca_comercial appear first,
    without excluding non-matching results.

    Req 8.2: prioritize matches without excluding others.

    Args:
        faults: List of fault dicts already filtered by codigo.
        modelo: Optional bus model to prioritize.
        marca_comercial: Optional commercial brand to prioritize.

    Returns:
        Sorted list of fault dicts (prioritized first, then others).
    """
    if not modelo and not marca_comercial:
        return faults

    def _priority_score(fault):
        score = 0
        if modelo and str(fault.get("modelo", "")).strip().lower() == str(modelo).strip().lower():
            score += 1
        if marca_comercial and str(fault.get("marca_comercial", "")).strip().lower() == str(marca_comercial).strip().lower():
            score += 1
        return score

    # Sort by priority score descending (higher = better match)
    return sorted(faults, key=_priority_score, reverse=True)


def _parse_datetime(dt_str):
    """Parse a datetime string, returning None on failure."""
    if not dt_str:
        return None
    try:
        # Handle various ISO formats
        dt_str = str(dt_str).strip()
        if "T" in dt_str:
            # Remove trailing Z if present
            dt_str = dt_str.replace("Z", "+00:00")
            if "+" in dt_str[10:]:
                dt_str = dt_str[:dt_str.index("+", 10)]
            return datetime.fromisoformat(dt_str)
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def _compute_duration(fault):
    """Compute event duration in minutes from fecha_hora and fecha_hora_fin.

    Args:
        fault: Fault dict with fecha_hora and fecha_hora_fin fields.

    Returns:
        Duration in minutes as float, or None if computation fails.
    """
    start = _parse_datetime(fault.get("fecha_hora"))
    end = _parse_datetime(fault.get("fecha_hora_fin"))
    if start and end:
        delta = end - start
        total_minutes = delta.total_seconds() / 60.0
        return round(total_minutes, 2) if total_minutes >= 0 else None
    return None


def _compute_statistics(faults):
    """Compute pattern statistics from a list of matching faults.

    Req 8.4: average severity, most affected models, most affected
    zones/regions, average event duration, affected service types.

    Args:
        faults: List of fault dicts (all matching, not just top 10).

    Returns:
        Dict with computed statistics.
    """
    if not faults:
        return {
            "total_eventos": 0,
            "severidad_promedio": None,
            "modelos_mas_afectados": [],
            "zonas_mas_afectadas": [],
            "regiones_mas_afectadas": [],
            "duracion_promedio_minutos": None,
            "tipos_servicio_afectados": [],
        }

    # Average severity
    severidades = [
        _safe_float(f.get("severidad"))
        for f in faults
        if _safe_float(f.get("severidad")) is not None
    ]
    severidad_promedio = round(sum(severidades) / len(severidades), 2) if severidades else None

    # Most affected models
    modelos = [str(f.get("modelo", "")).strip() for f in faults if f.get("modelo")]
    modelos_counter = Counter(modelos)
    modelos_mas_afectados = [
        {"modelo": m, "cantidad": c}
        for m, c in modelos_counter.most_common(5)
        if m
    ]

    # Most affected zones
    zonas = [str(f.get("zona", "")).strip() for f in faults if f.get("zona")]
    zonas_counter = Counter(zonas)
    zonas_mas_afectadas = [
        {"zona": z, "cantidad": c}
        for z, c in zonas_counter.most_common(5)
        if z
    ]

    # Most affected regions
    regiones = [str(f.get("region", "")).strip() for f in faults if f.get("region")]
    regiones_counter = Counter(regiones)
    regiones_mas_afectadas = [
        {"region": r, "cantidad": c}
        for r, c in regiones_counter.most_common(5)
        if r
    ]

    # Average event duration
    duraciones = [
        _compute_duration(f)
        for f in faults
    ]
    duraciones_validas = [d for d in duraciones if d is not None]
    duracion_promedio = (
        round(sum(duraciones_validas) / len(duraciones_validas), 2)
        if duraciones_validas
        else None
    )

    # Affected service types
    servicios = [str(f.get("servicio", "")).strip() for f in faults if f.get("servicio")]
    servicios_counter = Counter(servicios)
    tipos_servicio = [
        {"servicio": s, "cantidad": c}
        for s, c in servicios_counter.most_common(5)
        if s
    ]

    return {
        "total_eventos": len(faults),
        "severidad_promedio": severidad_promedio,
        "modelos_mas_afectados": modelos_mas_afectados,
        "zonas_mas_afectadas": zonas_mas_afectadas,
        "regiones_mas_afectadas": regiones_mas_afectadas,
        "duracion_promedio_minutos": duracion_promedio,
        "tipos_servicio_afectados": tipos_servicio,
    }


def _format_event(fault):
    """Format a single fault event for the response.

    Req 8.5: return each event with id, autobus, fecha_hora, codigo,
    severidad, descripcion, modelo, marca_comercial, zona, region,
    servicio, duration.

    Args:
        fault: Fault dict from Data_Fault.

    Returns:
        Dict with selected and computed fields.
    """
    duration = _compute_duration(fault)
    return {
        "id": fault.get("id", ""),
        "autobus": fault.get("autobus", ""),
        "fecha_hora": fault.get("fecha_hora", ""),
        "codigo": fault.get("codigo", ""),
        "severidad": fault.get("severidad"),
        "descripcion": fault.get("descripcion", ""),
        "modelo": fault.get("modelo", ""),
        "marca_comercial": fault.get("marca_comercial", ""),
        "zona": fault.get("zona", ""),
        "region": fault.get("region", ""),
        "servicio": fault.get("servicio", ""),
        "duracion_minutos": duration,
    }


# ---------------------------------------------------------------------------
# Lambda handler (Req 8.1–8.6, 11.4)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the buscar-patrones-historicos tool.

    Invoked by Bedrock AgentCore as a Maintenance Agent Action Group tool.

    Flow:
      1. Parse ``codigo`` (required), optional ``modelo``, optional
         ``marca_comercial`` from event.
      2. Read Data_Fault from S3 (JSON or Parquet).
      3. Filter by ``codigo`` (exact or partial match) (Req 8.1).
      4. If ``modelo``/``marca_comercial`` provided: prioritize matches
         without excluding others (Req 8.2).
      5. Sort by ``fecha_hora`` descending, limit to top 10 (Req 8.3).
      6. Compute statistics from ALL matching faults (Req 8.4).
      7. Return each event with required fields (Req 8.5).
      8. Return no-patterns-found response if no matches (Req 8.6).
      9. Use ``build_agent_response()`` for response formatting (Req 11.4).

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

    # --- 1. Parse parameters (Req 8.1) ---
    codigo = _get_param(event, "codigo")
    if not codigo:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_codigo_parameter",
        }))
        return build_error_response("Parámetro 'codigo' es requerido.", 400)

    codigo = str(codigo).strip()
    modelo = _get_param(event, "modelo")
    marca_comercial = _get_param(event, "marca_comercial")

    if modelo:
        modelo = str(modelo).strip()
    if marca_comercial:
        marca_comercial = str(marca_comercial).strip()

    logger.info(json.dumps({
        "action": "parse_params",
        "codigo": codigo,
        "modelo": modelo,
        "marca_comercial": marca_comercial,
    }))

    # --- 2. Read Data_Fault from S3 (Req 8.1) ---
    try:
        all_faults = _load_faults(S3_BUCKET, S3_FALLAS_KEY)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "load_faults",
            "bucket": S3_BUCKET,
            "key": S3_FALLAS_KEY,
            "error": str(exc),
        }))
        return build_error_response(
            "Error al leer el historial de fallas desde S3.", 500
        )

    if not isinstance(all_faults, list):
        all_faults = []

    # --- 3. Filter by codigo (Req 8.1) ---
    matching_faults = _filter_by_codigo(all_faults, codigo)

    # --- 4. No patterns found (Req 8.6) ---
    if not matching_faults:
        logger.info(json.dumps({
            "action": "no_patterns_found",
            "codigo": codigo,
            "total_faults_in_dataset": len(all_faults),
        }))
        return build_agent_response({
            "codigo": codigo,
            "modelo": modelo,
            "marca_comercial": marca_comercial,
            "mensaje": (
                f"No se encontraron patrones históricos para el código "
                f"de falla '{codigo}'. No hay eventos registrados con "
                f"este código en el historial."
            ),
            "total_coincidencias": 0,
            "estadisticas": _compute_statistics([]),
            "eventos": [],
        })

    # --- 5. Compute statistics from ALL matching faults (Req 8.4) ---
    estadisticas = _compute_statistics(matching_faults)

    # --- 6. Prioritize by modelo/marca_comercial (Req 8.2) ---
    prioritized = _prioritize_matches(matching_faults, modelo, marca_comercial)

    # --- 7. Sort by fecha_hora descending within priority groups (Req 8.3) ---
    # First, stable-sort by fecha_hora descending so that within each
    # priority level, events are ordered by date.
    prioritized.sort(key=lambda f: f.get("fecha_hora", ""), reverse=True)

    # Re-apply priority sort (stable sort preserves fecha_hora order within
    # same priority level)
    if modelo or marca_comercial:
        prioritized = _prioritize_matches(prioritized, modelo, marca_comercial)

    # Limit to top 10 (Req 8.3)
    top_events = prioritized[:MAX_EVENTS]

    # --- 8. Format events (Req 8.5) ---
    eventos_formateados = [_format_event(f) for f in top_events]

    # --- 9. Build and return response (Req 11.4) ---
    response_body = {
        "codigo": codigo,
        "modelo": modelo,
        "marca_comercial": marca_comercial,
        "total_coincidencias": len(matching_faults),
        "eventos_retornados": len(eventos_formateados),
        "estadisticas": estadisticas,
        "eventos": eventos_formateados,
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "codigo": codigo,
        "total_matching": len(matching_faults),
        "events_returned": len(eventos_formateados),
    }))

    return build_agent_response(response_body)
