"""
api-dashboard — API del dashboard ADO MobilityIA (GCP Cloud Run).

Equivalente a ado-dashboard-api Lambda. Usa FastAPI con path routing
para servir datos de la flota desde Firestore.

Endpoints:
  GET /dashboard/flota-status
  GET /dashboard/alertas-activas
  GET /dashboard/resumen-consumo
  GET /dashboard/co2-estimado
"""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add shared to path

from shared.firestore_utils import scan_recent, query_by_field, get_db
from shared.spn_catalog import cargar_catalogo_spn, obtener_spn
from shared.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADO MobilityIA — Dashboard API (GCP)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Urgency sort order
_URGENCY_ORDER = {"INMEDIATA": 0, "ESTA_SEMANA": 1, "PROXIMO_SERVICIO": 2}


@app.get("/dashboard/flota-status")
async def flota_status():
    """Estado actual de todos los autobuses activos."""
    timestamp_limit = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    records = scan_recent(config.FIRESTORE_COLLECTION_TELEMETRIA, timestamp_limit)

    # Load SPN catalog
    catalogo = cargar_catalogo_spn(config.GCS_BUCKET, config.GCS_CATALOGO_KEY)

    # Keep only latest record per bus (skip future ticks)
    now_iso = datetime.now(timezone.utc).isoformat()
    latest_by_bus: dict[str, dict] = {}
    for record in records:
        autobus = record.get("autobus", "")
        ts = record.get("timestamp", "")
        if ts > now_iso:
            continue
        if autobus not in latest_by_bus or ts > latest_by_bus[autobus].get("timestamp", ""):
            latest_by_bus[autobus] = record

    # Aggregate by estado_consumo
    resumen_por_estado: dict[str, int] = defaultdict(int)
    buses_list = []

    for autobus, record in latest_by_bus.items():
        estado = record.get("estado_consumo", "SIN_DATOS")
        resumen_por_estado[estado] += 1

        alertas_spn = record.get("alertas_spn", [])
        spn_fuera_rango = len(alertas_spn) if isinstance(alertas_spn, list) else 0

        # Translate SPN names
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

    # Sort: alerts first
    estado_order = {"ALERTA_SIGNIFICATIVA": 0, "ALERTA_MODERADA": 1, "EFICIENTE": 2, "SIN_DATOS": 3}
    buses_list.sort(key=lambda b: (estado_order.get(b["estado_consumo"], 9), -b["spns_fuera_de_rango"]))

    return {
        "total_buses": len(latest_by_bus),
        "buses_activos": len(latest_by_bus),
        "resumen_por_estado": dict(resumen_por_estado),
        "buses": buses_list,
    }


@app.get("/dashboard/alertas-activas")
async def alertas_activas():
    """Alertas activas ordenadas por urgencia."""
    items = query_by_field(
        config.FIRESTORE_COLLECTION_ALERTAS,
        field="estado",
        value="ACTIVA",
        limit=100,
    )

    # Sort by urgency
    items.sort(key=lambda a: (
        _URGENCY_ORDER.get(a.get("urgencia", "PROXIMO_SERVICIO"), 99),
        a.get("timestamp", ""),
    ))

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

    return {"total_alertas": len(alertas), "alertas": alertas}


@app.get("/dashboard/resumen-consumo")
async def resumen_consumo():
    """Resúmenes de eficiencia por ruta."""
    timestamp_limit = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    records = scan_recent(config.FIRESTORE_COLLECTION_TELEMETRIA, timestamp_limit)

    # Group by viaje_ruta, keep latest per bus
    rutas: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        ruta = record.get("viaje_ruta", "SIN_RUTA")
        rutas[ruta].append(record)

    resumen_rutas = []
    for ruta, ruta_records in rutas.items():
        latest_per_bus: dict[str, dict] = {}
        for r in ruta_records:
            bus = r.get("autobus", "")
            ts = r.get("timestamp", "")
            if bus not in latest_per_bus or ts > latest_per_bus[bus].get("timestamp", ""):
                latest_per_bus[bus] = r

        bus_records = list(latest_per_bus.values())

        rendimientos = []
        for r in bus_records:
            rend = r.get("rendimiento_kml")
            if rend is not None:
                try:
                    rendimientos.append(float(rend))
                except (ValueError, TypeError):
                    pass

        avg_rendimiento = round(sum(rendimientos) / len(rendimientos), 2) if rendimientos else None

        estados_count: dict[str, int] = defaultdict(int)
        for r in bus_records:
            estados_count[r.get("estado_consumo", "SIN_DATOS")] += 1

        total = len(bus_records)
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
            "total_buses": len(latest_per_bus),
            "buses": list(latest_per_bus.keys()),
            "rendimiento_promedio_kml": avg_rendimiento,
            "resumen_estados": dict(estados_count),
            "eficiencia_ruta": eficiencia_ruta,
        })

    resumen_rutas.sort(key=lambda r: r["rendimiento_promedio_kml"] if r["rendimiento_promedio_kml"] is not None else 999)

    return {"total_rutas": len(resumen_rutas), "rutas": resumen_rutas}


@app.get("/dashboard/co2-estimado")
async def co2_estimado():
    """Métricas ambientales en tiempo real."""
    FACTOR_CO2 = 2.68
    RENDIMIENTO_REF = 3.7
    DISTANCIA_RUTA = 380

    consumo_ref = DISTANCIA_RUTA / RENDIMIENTO_REF
    co2_ref_por_viaje = consumo_ref * FACTOR_CO2

    timestamp_limit = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    records = scan_recent(config.FIRESTORE_COLLECTION_TELEMETRIA, timestamp_limit)

    if not records:
        return {
            "titulo": "Impacto Ambiental — ADO MobilityIA",
            "estado": "sin_datos",
            "mensaje": "No hay buses activos en este momento.",
            "factor_co2": f"{FACTOR_CO2} kg CO2/L diesel (IPCC)",
            "rendimiento_referencia_kml": RENDIMIENTO_REF,
            "distancia_ruta_km": DISTANCIA_RUTA,
            "co2_referencia_por_viaje_kg": round(co2_ref_por_viaje, 1),
            "flota": {"buses_activos": 0},
            "buses": [],
        }

    # Aggregate per bus
    buses_data: dict[str, dict] = {}
    for record in records:
        bus = record.get("autobus", "?")
        rend = None
        try:
            rend = float(record.get("rendimiento_kml", 0))
        except (ValueError, TypeError):
            pass

        if bus not in buses_data:
            buses_data[bus] = {
                "rendimientos": [],
                "ruta": record.get("viaje_ruta", ""),
                "operador": record.get("operador_desc", ""),
            }
        if rend and rend > 0:
            buses_data[bus]["rendimientos"].append(rend)

    indicadores_buses = []
    total_co2_estimado = 0
    total_co2_referencia = 0
    rendimientos_flota = []

    for bus, data in buses_data.items():
        if not data["rendimientos"]:
            continue

        rend_avg = sum(data["rendimientos"]) / len(data["rendimientos"])
        rendimientos_flota.append(rend_avg)

        consumo_bus = DISTANCIA_RUTA / max(rend_avg, 0.5)
        co2_bus = consumo_bus * FACTOR_CO2
        total_co2_estimado += co2_bus
        total_co2_referencia += co2_ref_por_viaje

        co2_por_km = FACTOR_CO2 / max(rend_avg, 0.5)
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

        co2_diferencia = co2_bus - co2_ref_por_viaje
        if co2_diferencia <= 0:
            tendencia = "Opera por debajo del estándar de emisiones."
        elif co2_diferencia < 20:
            tendencia = "Emisiones ligeramente superiores al estándar."
        elif co2_diferencia < 50:
            tendencia = "Emisiones moderadamente superiores."
        else:
            tendencia = "Emisiones significativamente superiores."

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

    rend_flota_avg = sum(rendimientos_flota) / len(rendimientos_flota) if rendimientos_flota else 0
    co2_flota_por_km = FACTOR_CO2 / max(rend_flota_avg, 0.5) if rend_flota_avg else 0

    # Distribution
    dist = defaultdict(int)
    for b in indicadores_buses:
        dist[b["clasificacion_ambiental"]] += 1

    return {
        "titulo": "Impacto Ambiental — ADO MobilityIA",
        "factor_co2": f"{FACTOR_CO2} kg CO2/L diesel (IPCC)",
        "rendimiento_referencia_kml": RENDIMIENTO_REF,
        "distancia_ruta_km": DISTANCIA_RUTA,
        "co2_referencia_por_viaje_kg": round(co2_ref_por_viaje, 1),
        "flota": {
            "buses_activos": len(indicadores_buses),
            "rendimiento_promedio_kml": round(rend_flota_avg, 2),
            "co2_promedio_por_km_kg": round(co2_flota_por_km, 3),
            "co2_total_estimado_kg": round(total_co2_estimado, 1),
            "co2_total_referencia_kg": round(total_co2_referencia, 1),
            "ahorro_potencial_co2_kg": round(total_co2_referencia - total_co2_estimado, 1),
            "distribucion_ambiental": dict(dist),
            "descripcion": "Métricas calculadas en tiempo real basadas en rendimiento actual de la flota.",
        },
        "buses": indicadores_buses,
        "cumplimiento_normativo": {
            "nom_044": "Estimación basada en factor IPCC y rendimiento actual.",
            "acuerdo_paris": "Contribución a reducción de emisiones vehiculares.",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-dashboard"}
