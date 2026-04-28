"""
ado-dashboard-api — API del dashboard ejecutivo ADO MobilityIA.

Lambda con enrutamiento basado en path que sirve datos consolidados
de la flota para consumo por QuickSight o Streamlit:

  /dashboard/flota-status      Estado actual de todos los autobuses
  /dashboard/alertas-activas   Alertas activas ordenadas por urgencia
  /dashboard/resumen-consumo   Resúmenes de eficiencia por ruta
  /dashboard/co2-estimado      Estimaciones cualitativas de reducción CO₂

Usa build_api_response() con headers CORS para API Gateway.

Requisitos: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.6, 11.7
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Attr

from ado_common.dynamo_utils import scan_recent, query_gsi
from ado_common.spn_catalog import cargar_catalogo_spn, obtener_spn
from ado_common.response import build_api_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
TABLE_TELEMETRIA = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
TABLE_ALERTAS = os.environ.get("DYNAMODB_TABLE_ALERTAS", "ado-alertas")
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "hackathon-data/catalogo/motor_spn.json")

# DynamoDB resource for alertas scan (not covered by dynamo_utils helpers)
_dynamodb = boto3.resource("dynamodb")

# Urgency sort order for alertas-activas
_URGENCY_ORDER = {
    "INMEDIATA": 0,
    "ESTA_SEMANA": 1,
    "PROXIMO_SERVICIO": 2,
}


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_flota_status() -> dict:
    """
    /dashboard/flota-status — Req 10.1, 10.5

    Scans DynamoDB_Telemetria for the latest record per bus,
    aggregates by estado_consumo, translates SPNs to readable names.

    Returns dict with:
      - total_buses, buses_activos
      - resumen_por_estado: count per Consumption_State
      - buses: list with per-bus details
    """
    # Scan for records from the last 10 minutes
    timestamp_limit = (
        datetime.now(timezone.utc) - timedelta(minutes=10)
    ).isoformat()

    records = scan_recent(TABLE_TELEMETRIA, timestamp_limit)

    # Load SPN catalog for name translation
    catalogo = cargar_catalogo_spn(S3_BUCKET, S3_CATALOGO_KEY)

    # Keep only the latest record per bus
    latest_by_bus: dict[str, dict] = {}
    for record in records:
        autobus = record.get("autobus", "")
        ts = record.get("timestamp", "")
        if autobus not in latest_by_bus or ts > latest_by_bus[autobus].get("timestamp", ""):
            latest_by_bus[autobus] = record

    # Aggregate by estado_consumo
    resumen_por_estado: dict[str, int] = defaultdict(int)
    buses_list = []

    for autobus, record in latest_by_bus.items():
        estado = record.get("estado_consumo", "SIN_DATOS")
        resumen_por_estado[estado] += 1

        # Count out-of-range SPNs
        alertas_spn = record.get("alertas_spn", [])
        spn_fuera_rango = len(alertas_spn) if isinstance(alertas_spn, list) else 0

        # Translate SPN names in alertas if present
        alertas_traducidas = []
        for alerta in (alertas_spn if isinstance(alertas_spn, list) else []):
            spn_id = alerta.get("spn_id")
            spn_info = obtener_spn(catalogo, int(spn_id)) if spn_id is not None else None
            alertas_traducidas.append({
                "spn_id": spn_id,
                "nombre": spn_info["name"] if spn_info else alerta.get("name", f"SPN_{spn_id}"),
                "valor": alerta.get("valor"),
                "unidad": spn_info["unidad"] if spn_info else alerta.get("unidad", ""),
                "mensaje": alerta.get("mensaje", ""),
            })

        buses_list.append({
            "autobus": autobus,
            "viaje_ruta": record.get("viaje_ruta", ""),
            "viaje_ruta_origen": record.get("viaje_ruta_origen", ""),
            "viaje_ruta_destino": record.get("viaje_ruta_destino", ""),
            "operador_desc": record.get("operador_desc", ""),
            "estado_consumo": estado,
            "spns_fuera_de_rango": spn_fuera_rango,
            "ultimo_timestamp": record.get("timestamp", ""),
            "alertas_spn": alertas_traducidas,
            "latitud": float(record.get("latitud", 0) or 0),
            "longitud": float(record.get("longitud", 0) or 0),
            "velocidad_kmh": float(record.get("velocidad_kmh", 0) or 0),
            "rpm": float(record.get("rpm", 0) or 0),
            "temperatura_motor_c": float(record.get("temperatura_motor_c", 0) or 0),
            "presion_aceite_kpa": float(record.get("presion_aceite_kpa", 0) or 0),
            "tasa_combustible_lh": float(record.get("tasa_combustible_lh", 0) or 0),
            "nivel_combustible_pct": float(record.get("nivel_combustible_pct", 0) or 0),
        })

    # Sort buses: ALERTA_SIGNIFICATIVA first, then by spns_fuera_de_rango desc
    estado_order = {
        "ALERTA_SIGNIFICATIVA": 0,
        "ALERTA_MODERADA": 1,
        "EFICIENTE": 2,
        "SIN_DATOS": 3,
    }
    buses_list.sort(
        key=lambda b: (
            estado_order.get(b["estado_consumo"], 9),
            -b["spns_fuera_de_rango"],
        )
    )

    return {
        "total_buses": len(latest_by_bus),
        "buses_activos": len(latest_by_bus),
        "resumen_por_estado": dict(resumen_por_estado),
        "buses": buses_list,
    }


def handle_alertas_activas() -> dict:
    """
    /dashboard/alertas-activas — Req 10.2, 11.7

    Queries DynamoDB_Alertas for records with estado=ACTIVA,
    sorted by urgency: INMEDIATA first, then ESTA_SEMANA, then PROXIMO_SERVICIO.
    """
    table = _dynamodb.Table(TABLE_ALERTAS)

    # Scan with filter for estado=ACTIVA
    items = []
    scan_kwargs = {
        "FilterExpression": Attr("estado").eq("ACTIVA"),
    }

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    # Sort by urgency
    items.sort(
        key=lambda a: (
            _URGENCY_ORDER.get(a.get("urgencia", "PROXIMO_SERVICIO"), 99),
            a.get("timestamp", ""),
        )
    )

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

    return {
        "total_alertas": len(alertas),
        "alertas": alertas,
    }


def handle_resumen_consumo() -> dict:
    """
    /dashboard/resumen-consumo — Req 10.3, 11.6

    Queries DynamoDB_Telemetria via GSI viaje_ruta-timestamp-index
    to aggregate consumption data by route.
    Computes average rendimiento per route and efficiency summaries.
    """
    # Scan for recent records (last 10 minutes)
    timestamp_limit = (
        datetime.now(timezone.utc) - timedelta(minutes=10)
    ).isoformat()

    records = scan_recent(TABLE_TELEMETRIA, timestamp_limit)

    # Group by viaje_ruta
    rutas: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        ruta = record.get("viaje_ruta", "SIN_RUTA")
        rutas[ruta].append(record)

    resumen_rutas = []
    for ruta, ruta_records in rutas.items():
        # Compute average rendimiento
        rendimientos = []
        for r in ruta_records:
            rend = r.get("rendimiento_kml")
            if rend is not None:
                try:
                    rendimientos.append(float(rend))
                except (ValueError, TypeError):
                    pass

        avg_rendimiento = (
            round(sum(rendimientos) / len(rendimientos), 2)
            if rendimientos
            else None
        )

        # Count by estado_consumo
        estados_count: dict[str, int] = defaultdict(int)
        for r in ruta_records:
            estado = r.get("estado_consumo", "SIN_DATOS")
            estados_count[estado] += 1

        # Unique buses on this route
        buses_en_ruta = list({r.get("autobus", "") for r in ruta_records})

        # Determine overall route efficiency
        total = len(ruta_records)
        eficientes = estados_count.get("EFICIENTE", 0)
        if total > 0 and eficientes / total >= 0.7:
            eficiencia_ruta = "EFICIENTE"
        elif total > 0 and estados_count.get("ALERTA_SIGNIFICATIVA", 0) / total >= 0.3:
            eficiencia_ruta = "REQUIERE_ATENCION"
        else:
            eficiencia_ruta = "MODERADA"

        resumen_rutas.append({
            "viaje_ruta": ruta,
            "total_registros": total,
            "total_buses": len(buses_en_ruta),
            "buses": buses_en_ruta,
            "rendimiento_promedio_kml": avg_rendimiento,
            "resumen_estados": dict(estados_count),
            "eficiencia_ruta": eficiencia_ruta,
        })

    # Sort by rendimiento ascending (worst routes first)
    resumen_rutas.sort(
        key=lambda r: r["rendimiento_promedio_kml"] if r["rendimiento_promedio_kml"] is not None else 999
    )

    return {
        "total_rutas": len(resumen_rutas),
        "rutas": resumen_rutas,
    }


def handle_co2_estimado() -> dict:
    """
    /dashboard/co2-estimado — Req 10.4

    Calcula métricas ambientales en tiempo real basadas en:
    1. Rendimiento actual de los buses en ruta (DynamoDB)
    2. Factor de emisión: 2.68 kg CO₂ por litro de diésel (IPCC)
    3. Rendimiento de referencia: 3.7 km/L (ruta CDMX-Acapulco, manual ambiental)
    4. Distancia de referencia: 380 km por viaje

    Genera indicadores de CO₂ por bus, por ruta y de flota,
    comparando contra el rendimiento de referencia.
    C-003: Los valores se presentan pero las mejoras usan lenguaje difuso.
    """
    FACTOR_CO2_KG_POR_LITRO = 2.68
    RENDIMIENTO_REFERENCIA = 3.7  # km/L (manual ambiental, ruta pivote)
    DISTANCIA_RUTA_KM = 380

    # CO₂ de referencia por viaje (el "ideal")
    consumo_ref = DISTANCIA_RUTA_KM / RENDIMIENTO_REFERENCIA
    co2_ref_por_viaje = consumo_ref * FACTOR_CO2_KG_POR_LITRO

    # Consultar buses activos (últimos 10 min)
    timestamp_limit = (
        datetime.now(timezone.utc) - timedelta(minutes=10)
    ).isoformat()
    records = scan_recent(TABLE_TELEMETRIA, timestamp_limit)

    if not records:
        return {
            "titulo": "Impacto Ambiental — ADO MobilityIA",
            "estado": "sin_datos",
            "mensaje": "No hay buses activos en este momento para calcular métricas ambientales.",
            "factor_co2": f"{FACTOR_CO2_KG_POR_LITRO} kg CO₂/L diésel (IPCC)",
            "rendimiento_referencia_kml": RENDIMIENTO_REFERENCIA,
        }

    # Calcular métricas por bus
    buses_data = {}
    for record in records:
        bus = record.get("autobus", "?")
        rend = None
        try:
            rend = float(record.get("rendimiento_kml", 0))
        except (ValueError, TypeError):
            pass

        tasa = None
        try:
            tasa = float(record.get("tasa_combustible_lh", 0))
        except (ValueError, TypeError):
            pass

        vel = None
        try:
            vel = float(record.get("velocidad_kmh", 0))
        except (ValueError, TypeError):
            pass

        if bus not in buses_data:
            buses_data[bus] = {
                "rendimientos": [],
                "tasas": [],
                "velocidades": [],
                "ruta": record.get("viaje_ruta", ""),
                "operador": record.get("operador_desc", ""),
            }

        if rend and rend > 0:
            buses_data[bus]["rendimientos"].append(rend)
        if tasa and tasa > 0:
            buses_data[bus]["tasas"].append(tasa)
        if vel and vel > 0:
            buses_data[bus]["velocidades"].append(vel)

    # Calcular indicadores por bus
    indicadores_buses = []
    total_co2_estimado = 0
    total_co2_referencia = 0
    rendimientos_flota = []

    for bus, data in buses_data.items():
        if not data["rendimientos"]:
            continue

        rend_avg = sum(data["rendimientos"]) / len(data["rendimientos"])
        rendimientos_flota.append(rend_avg)

        # CO₂ estimado para este bus (proyectado al viaje completo)
        consumo_bus = DISTANCIA_RUTA_KM / max(rend_avg, 0.5)
        co2_bus = consumo_bus * FACTOR_CO2_KG_POR_LITRO

        # Diferencia vs referencia
        co2_diferencia = co2_bus - co2_ref_por_viaje

        total_co2_estimado += co2_bus
        total_co2_referencia += co2_ref_por_viaje

        # Clasificación ambiental (del manual de emisiones)
        co2_por_km = FACTOR_CO2_KG_POR_LITRO / max(rend_avg, 0.5)
        if co2_por_km < 0.670:
            clasificacion = "ECO_EFICIENTE"
        elif co2_por_km <= 0.724:
            clasificacion = "EFICIENTE"
        elif co2_por_km <= 0.838:
            clasificacion = "ESTANDAR"
        elif co2_por_km <= 0.967:
            clasificacion = "INEFICIENTE"
        else:
            clasificacion = "CRITICO"

        # Descripción cualitativa (C-003)
        if co2_diferencia <= 0:
            tendencia = "El autobús opera por debajo del estándar de emisiones de la ruta."
        elif co2_diferencia < 20:
            tendencia = "Emisiones ligeramente superiores al estándar. Oportunidad de mejora menor."
        elif co2_diferencia < 50:
            tendencia = "Emisiones moderadamente superiores al estándar. Se recomienda revisar patrones de conducción."
        else:
            tendencia = "Emisiones significativamente superiores al estándar. Intervención recomendada."

        indicadores_buses.append({
            "autobus": bus,
            "operador": data["operador"],
            "ruta": data["ruta"],
            "rendimiento_promedio_kml": round(rend_avg, 2),
            "co2_estimado_por_viaje_kg": round(co2_bus, 1),
            "co2_referencia_por_viaje_kg": round(co2_ref_por_viaje, 1),
            "co2_por_km_kg": round(co2_por_km, 3),
            "clasificacion_ambiental": clasificacion,
            "tendencia": tendencia,
        })

    # Ordenar: peores primero
    indicadores_buses.sort(key=lambda x: x["co2_estimado_por_viaje_kg"], reverse=True)

    # Métricas de flota
    rend_flota = sum(rendimientos_flota) / len(rendimientos_flota) if rendimientos_flota else 0
    co2_flota_por_km = FACTOR_CO2_KG_POR_LITRO / max(rend_flota, 0.5) if rend_flota > 0 else 0

    # Distribución ambiental
    dist = defaultdict(int)
    for b in indicadores_buses:
        dist[b["clasificacion_ambiental"]] += 1

    # Potencial de ahorro si todos alcanzan referencia
    ahorro_potencial_co2 = max(total_co2_estimado - total_co2_referencia, 0)

    return {
        "titulo": "Impacto Ambiental en Tiempo Real — ADO MobilityIA",
        "factor_co2": f"{FACTOR_CO2_KG_POR_LITRO} kg CO₂/L diésel (IPCC)",
        "rendimiento_referencia_kml": RENDIMIENTO_REFERENCIA,
        "distancia_ruta_km": DISTANCIA_RUTA_KM,
        "co2_referencia_por_viaje_kg": round(co2_ref_por_viaje, 1),
        "flota": {
            "buses_activos": len(indicadores_buses),
            "rendimiento_promedio_kml": round(rend_flota, 2),
            "co2_promedio_por_km_kg": round(co2_flota_por_km, 3),
            "co2_total_estimado_kg": round(total_co2_estimado, 1),
            "co2_total_referencia_kg": round(total_co2_referencia, 1),
            "ahorro_potencial_co2_kg": round(ahorro_potencial_co2, 1),
            "distribucion_ambiental": dict(dist),
            "descripcion": (
                "La flota activa muestra una oportunidad de reducción de emisiones "
                "al optimizar los patrones de conducción de las unidades clasificadas "
                "como ineficientes o críticas."
                if ahorro_potencial_co2 > 0
                else "La flota activa opera dentro de los parámetros ambientales esperados."
            ),
        },
        "buses": indicadores_buses,
        "cumplimiento_normativo": {
            "nom_044": "El monitoreo continuo de rendimiento y emisiones estimadas contribuye al cumplimiento de NOM-044-SEMARNAT.",
            "acuerdo_paris": "Las métricas de CO₂ por kilómetro permiten evidenciar el compromiso de reducción de emisiones de la flota.",
        },
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_ROUTE_MAP = {
    "/dashboard/flota-status": handle_flota_status,
    "/dashboard/alertas-activas": handle_alertas_activas,
    "/dashboard/resumen-consumo": handle_resumen_consumo,
    "/dashboard/co2-estimado": handle_co2_estimado,
}


def lambda_handler(event, context):
    """
    Main Lambda handler with path-based routing.

    Extracts the path from the API Gateway event and dispatches
    to the appropriate handler function.
    """
    # Support both API Gateway v1 (path) and v2 (rawPath) event formats
    path = event.get("rawPath") or event.get("path") or event.get("resource", "")

    logger.info(json.dumps({
        "action": "dashboard_api_request",
        "path": path,
        "method": event.get("httpMethod", "GET"),
    }))

    handler = _ROUTE_MAP.get(path)

    if handler is None:
        return build_api_response(
            {"error": f"Ruta no encontrada: {path}", "rutas_disponibles": list(_ROUTE_MAP.keys())},
            status_code=404,
        )

    try:
        result = handler()
        return build_api_response(result)
    except Exception as e:
        logger.error(json.dumps({
            "action": "dashboard_api_error",
            "path": path,
            "error": str(e),
        }))
        return build_api_response(
            {"error": f"Error procesando {path}: {str(e)}"},
            status_code=500,
        )
