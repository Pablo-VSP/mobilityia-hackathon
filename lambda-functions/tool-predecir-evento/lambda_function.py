"""
tool-predecir-evento — Predicción de eventos mecánicos por autobús.

Maintenance Agent Tool invocado por Bedrock AgentCore. Consulta los últimos
20 registros de telemetría de un autobús, construye un vector de features
a partir de SPNs de mantenimiento, intenta invocar el endpoint de SageMaker
para predicción ML, y en caso de fallo usa un algoritmo heurístico de
puntuación basado en umbrales de SPNs y fallas recientes.

Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 11.4, 11.6
"""

import json
import logging
import os
from decimal import Decimal

import boto3
import statistics

from ado_common.spn_catalog import cargar_catalogo_spn, obtener_spn, variacion_anomala
from ado_common.dynamo_utils import query_latest_records
from ado_common.s3_utils import read_json_from_s3
from ado_common.response import build_agent_response, build_error_response
from ado_common.constants import (
    SPNS_MANTENIMIENTO,
    SPNS_BALATAS,
    SPN_TEMPERATURA_MOTOR,
    SPN_TEMPERATURA_ACEITE,
    SPN_PRESION_ACEITE,
    SPN_NIVEL_ACEITE,
    SPN_NIVEL_ANTICONGELANTE,
    SPN_VOLTAJE_BATERIA,
    SPN_NIVEL_UREA,
    SPN_ODOMETRO,
    SPN_HORAS_MOTOR,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables (Req 11.6)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE_TELEMETRIA", "ado-telemetria-live")
S3_BUCKET = os.environ.get("S3_BUCKET", "ado-telemetry-mvp")
S3_CATALOGO_KEY = os.environ.get("S3_CATALOGO_KEY", "hackathon-data/catalogo/motor_spn.json")
S3_FALLAS_KEY = os.environ.get("S3_FALLAS_KEY", "hackathon-data/fallas-simuladas/data_fault.json")
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT", "ado-prediccion-eventos")
S3_FEATURE_NAMES_KEY = os.environ.get(
    "S3_FEATURE_NAMES_KEY",
    "hackathon-data/modelos/sagemaker-v2/training-data/feature_names.json",
)

# Number of records to query for prediction analysis
RECORDS_LIMIT = 20

# Risk level classification thresholds (Req 7.5)
RISK_THRESHOLDS = {
    "BAJO": (0, 2),
    "MODERADO": (3, 5),
    "ELEVADO": (6, 8),
    # CRITICO: score > 8
}

# ML model risk thresholds (from model_summary.json)
ML_RISK_THRESHOLDS = {
    "BAJO": (0.0, 0.25),
    "MODERADO": (0.25, 0.50),
    "ELEVADO": (0.50, 0.75),
    "CRITICO": (0.75, 1.0),
}

# Códigos de falla críticos (severidad_inferencia = 3)
CODIGOS_CRITICOS = {"86", "100", "158"}
# Códigos de escalamiento (severidad_inferencia = 2)
CODIGOS_ESCALAMIENTO = {"32", "131", "111", "37"}

# Urgency mapping (Req 7.5)
URGENCY_MAP = {
    "BAJO": "PROXIMO_SERVICIO",
    "MODERADO": "PROXIMO_SERVICIO",
    "ELEVADO": "ESTA_SEMANA",
    "CRITICO": "INMEDIATA",
}

# Risk level descriptions (Req 7.6)
RISK_DESCRIPTIONS = {
    "BAJO": "Las señales del autobús se encuentran dentro de parámetros normales. No se detectan indicios significativos de evento mecánico próximo.",
    "MODERADO": "Se detectan algunas señales con desviación leve respecto a los parámetros esperados. Se recomienda programar revisión en el próximo servicio.",
    "ELEVADO": "Se detectan señales consistentes con patrones previos a eventos mecánicos. Se recomienda intervención preventiva esta semana.",
    "CRITICO": "Se detectan múltiples señales de alerta que indican alta probabilidad de evento mecánico inminente. Se recomienda intervención inmediata.",
}

# At-risk component mapping based on contributing SPNs (Req 7.6)
SPN_COMPONENT_MAP = {
    SPN_TEMPERATURA_MOTOR: ["sistema_refrigeracion", "bomba_agua"],
    SPN_NIVEL_ANTICONGELANTE: ["sistema_refrigeracion", "bomba_agua"],
    SPN_TEMPERATURA_ACEITE: ["circuito_aceite"],
    SPN_PRESION_ACEITE: ["circuito_aceite"],
    SPN_NIVEL_ACEITE: ["circuito_aceite"],
    SPN_VOLTAJE_BATERIA: ["sistema_electrico"],
    SPN_NIVEL_UREA: ["sistema_escape"],
}

# SageMaker client (lazy init)
_sagemaker_client = None
# Feature names cache
_feature_names = None


def _get_sagemaker_client():
    """Lazy-initialize the SageMaker runtime client."""
    global _sagemaker_client
    if _sagemaker_client is None:
        _sagemaker_client = boto3.client("sagemaker-runtime")
    return _sagemaker_client


def _load_feature_names():
    """Load the ordered feature names list from S3 (cached across invocations)."""
    global _feature_names
    if _feature_names is None:
        try:
            _feature_names = read_json_from_s3(S3_BUCKET, S3_FEATURE_NAMES_KEY)
            logger.info(json.dumps({
                "action": "load_feature_names",
                "count": len(_feature_names),
            }))
        except Exception as exc:
            logger.warning(json.dumps({
                "action": "load_feature_names",
                "error": str(exc),
                "message": "No se pudo cargar feature_names.json, SageMaker no disponible",
            }))
            _feature_names = []
    return _feature_names


# ---------------------------------------------------------------------------
# Helpers (reused patterns from tool-consultar-obd)
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


def _extract_spn_values(records, spn_id):
    """Extract numeric values for a given SPN from spn_valores across records.

    Returns list of float values in the same order as records.
    """
    values = []
    spn_key = str(spn_id)
    for record in records:
        spn_valores = record.get("spn_valores", {})
        spn_data = spn_valores.get(spn_key)
        if spn_data:
            val = _safe_float(spn_data.get("valor"))
            if val is not None:
                values.append(val)
    return values


def _safe_avg(values):
    """Compute average of a list of floats, returning None if empty."""
    if not values:
        return None
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Feature vector construction (Req 7.1)
# ---------------------------------------------------------------------------

def _build_feature_vector(records, catalogo_spn):
    """Build a feature vector from maintenance SPNs across records.

    For each maintenance SPN, computes 6 statistics matching the trained
    model: avg, max, min, std, out-of-range count, and anomaly count.

    Args:
        records: List of DynamoDB items (most recent first).
        catalogo_spn: The SPN catalog dict.

    Returns:
        Dict mapping spn_id -> {avg, max, min, std, count,
        out_of_range_count, anomaly_count}.
    """
    features = {}

    for spn_id in sorted(SPNS_MANTENIMIENTO):
        values = _extract_spn_values(records, spn_id)
        if not values:
            features[spn_id] = {
                "avg": 0.0, "max": 0.0, "min": 0.0, "std": 0.0,
                "count": 0, "out_of_range_count": 0, "anomaly_count": 0,
            }
            continue

        spn_info = obtener_spn(catalogo_spn, spn_id)
        out_of_range_count = 0
        anomaly_count = 0

        if spn_info:
            minimo = spn_info["minimo"]
            maximo = spn_info["maximo"]
            for v in values:
                if v < minimo or v > maximo:
                    out_of_range_count += 1
            for i in range(1, len(values)):
                if variacion_anomala(catalogo_spn, spn_id, values[i - 1], values[i]):
                    anomaly_count += 1

        std_val = statistics.stdev(values) if len(values) >= 2 else 0.0

        features[spn_id] = {
            "avg": sum(values) / len(values),
            "max": max(values),
            "min": min(values),
            "std": std_val,
            "count": len(values),
            "out_of_range_count": out_of_range_count,
            "anomaly_count": anomaly_count,
        }

    return features


# ---------------------------------------------------------------------------
# SageMaker invocation (Req 7.2)
# ---------------------------------------------------------------------------

def _build_fault_features(fallas_recientes):
    """Build fault-related features matching the trained model schema.

    Features:
        fallas_criticas_30d, fallas_criticas_90d, fallas_sev2_30d,
        fallas_sev2_recurrentes_30d, severidad_max_30d,
        dias_desde_ultima_falla_critica, tiene_falla_activa,
        codigos_criticos_unicos_90d, fallas_correlacionadas

    Args:
        fallas_recientes: List of fault dicts sorted by fecha_hora desc.

    Returns:
        Dict with the 9 fault features.
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)

    criticas_30 = 0
    criticas_90 = 0
    sev2_30 = 0
    sev_max_30 = 0
    dias_ultima_critica = 999
    tiene_activa = 0
    codigos_criticos_set = set()
    codigos_30d = []

    for f in fallas_recientes:
        codigo = str(f.get("codigo", "")).strip()
        sev = _safe_float(f.get("severidad"))
        fecha_str = f.get("fecha_hora", "")
        try:
            fecha = datetime.fromisoformat(fecha_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            continue

        es_critico = codigo in CODIGOS_CRITICOS
        es_sev2 = codigo in CODIGOS_ESCALAMIENTO

        if fecha >= d90:
            if es_critico:
                criticas_90 += 1
                codigos_criticos_set.add(codigo)
            if fecha >= d30:
                if es_critico:
                    criticas_30 += 1
                if es_sev2:
                    sev2_30 += 1
                if sev is not None and sev > sev_max_30:
                    sev_max_30 = int(sev)
                codigos_30d.append(codigo)

        if es_critico:
            dias = (now - fecha).days
            if dias < dias_ultima_critica:
                dias_ultima_critica = dias

        # Active fault = within last 24h
        if (now - fecha).total_seconds() < 86400:
            tiene_activa = 1

    # Recurrentes: códigos sev2 que aparecen más de una vez en 30d
    sev2_recurrentes = 0
    for c in CODIGOS_ESCALAMIENTO:
        if codigos_30d.count(c) > 1:
            sev2_recurrentes += 1

    # Fallas correlacionadas: si hay tanto críticas como sev2 en 30d
    fallas_correlacionadas = 1 if (criticas_30 > 0 and sev2_30 > 0) else 0

    if dias_ultima_critica == 999:
        dias_ultima_critica = 365  # No critical faults found

    return {
        "fallas_criticas_30d": criticas_30,
        "fallas_criticas_90d": criticas_90,
        "fallas_sev2_30d": sev2_30,
        "fallas_sev2_recurrentes_30d": sev2_recurrentes,
        "severidad_max_30d": sev_max_30,
        "dias_desde_ultima_falla_critica": dias_ultima_critica,
        "tiene_falla_activa": tiene_activa,
        "codigos_criticos_unicos_90d": len(codigos_criticos_set),
        "fallas_correlacionadas": fallas_correlacionadas,
    }


def _build_contextual_features(features, records):
    """Build contextual features matching the trained model schema.

    Features: balata_min_pct, odometro_km, horas_motor_h,
              total_spns_fuera_rango, total_anomalias

    Args:
        features: SPN feature dict from _build_feature_vector().
        records: DynamoDB records.

    Returns:
        Dict with the 5 contextual features.
    """
    # Minimum brake pad percentage across all 6 positions
    balata_vals = []
    for spn_id in sorted(SPNS_BALATAS):
        f = features.get(spn_id)
        if f and f["count"] > 0:
            balata_vals.append(f["min"])
    balata_min = min(balata_vals) if balata_vals else 100.0

    # Odometer and engine hours from latest record
    odometro = 0.0
    horas_motor = 0.0
    if records:
        latest = records[0]
        spn_vals = latest.get("spn_valores", {})
        od = spn_vals.get(str(SPN_ODOMETRO))
        if od:
            odometro = _safe_float(od.get("valor")) or 0.0
        hm = spn_vals.get(str(SPN_HORAS_MOTOR))
        if hm:
            horas_motor = _safe_float(hm.get("valor")) or 0.0

    # Total SPNs out of range and total anomalies
    total_oor = sum(f["out_of_range_count"] for f in features.values() if f["count"] > 0)
    total_anomalias = sum(f["anomaly_count"] for f in features.values() if f["count"] > 0)

    return {
        "balata_min_pct": balata_min,
        "odometro_km": odometro,
        "horas_motor_h": horas_motor,
        "total_spns_fuera_rango": total_oor,
        "total_anomalias": total_anomalias,
    }


def _build_csv_payload(features, fault_features, contextual_features, feature_names):
    """Build a CSV row matching the exact feature order expected by the model.

    Supports both v1 format (spn_{id}_{stat}_7d) and v2 format ({nombre}_{stat}).

    V2 feature name format:
      - {nombre}_{stat}  where nombre maps to a SPN ID and stat is avg/max/min/oor
      - pct_{condition}  threshold percentage features
      - total_oor, n_registros_ventana  contextual features
      - fallas_*, dias_*, tiene_*  fault features

    Args:
        features: SPN feature dict from _build_feature_vector().
        fault_features: Dict from _build_fault_features().
        contextual_features: Dict from _build_contextual_features().
        feature_names: Ordered list of feature names (54 for v2, 128 for v1).

    Returns:
        CSV string with comma-separated values.
    """
    # V2 nombre → SPN ID mapping
    NOMBRE_TO_SPN = {
        "presion_aceite": SPN_PRESION_ACEITE,    # 100
        "nivel_aceite": SPN_NIVEL_ACEITE,        # 98
        "temp_aceite": SPN_TEMPERATURA_ACEITE,   # 175
        "temp_motor": SPN_TEMPERATURA_MOTOR,     # 110
        "rpm": 190,
        "voltaje_bat": SPN_VOLTAJE_BATERIA,      # 168
        "freno": 521,
        "velocidad": 84,
        "retarder": 520,
        "horas_motor": SPN_HORAS_MOTOR,          # 247
    }

    # V2 stat mapping
    V2_STAT_MAP = {
        "avg": "avg",
        "max": "max",
        "min": "min",
        "oor": "out_of_range_count",
    }

    # V1 stat mapping (legacy)
    V1_STAT_MAP = {
        "avg": "avg",
        "max": "max",
        "min": "min",
        "std": "std",
        "oor_count": "out_of_range_count",
        "anomaly_count": "anomaly_count",
    }

    # V2 threshold features computed from raw SPN values
    def _compute_threshold_features(features):
        """Compute percentage-based threshold features for v2."""
        result = {}
        # Presión aceite
        f100 = features.get(SPN_PRESION_ACEITE)
        if f100 and f100["count"] > 0:
            values = _extract_spn_values_from_features(features, SPN_PRESION_ACEITE)
            result["pct_presion_bajo_150"] = sum(1 for v in values if v < 150) / max(len(values), 1) if values else 0
            result["pct_presion_bajo_50"] = sum(1 for v in values if v < 50) / max(len(values), 1) if values else 0
        else:
            result["pct_presion_bajo_150"] = 0
            result["pct_presion_bajo_50"] = 0

        # Temperatura motor
        f110 = features.get(SPN_TEMPERATURA_MOTOR)
        if f110 and f110["count"] > 0:
            # Use avg/max as proxy since we don't have raw values here
            result["pct_temp_motor_sobre_115"] = 1.0 if f110["avg"] > 115 else 0.0
            result["pct_temp_motor_sobre_140"] = 1.0 if f110["max"] > 140 else 0.0
        else:
            result["pct_temp_motor_sobre_115"] = 0
            result["pct_temp_motor_sobre_140"] = 0

        # Voltaje batería
        f168 = features.get(SPN_VOLTAJE_BATERIA)
        if f168 and f168["count"] > 0:
            result["pct_voltaje_bajo_12"] = 1.0 if f168["min"] < 12 else 0.0
            result["pct_voltaje_sobre_15_5"] = 1.0 if f168["max"] > 15.5 else 0.0
        else:
            result["pct_voltaje_bajo_12"] = 0
            result["pct_voltaje_sobre_15_5"] = 0

        # Contextual
        result["total_oor"] = sum(f["out_of_range_count"] for f in features.values() if f.get("count", 0) > 0)
        result["n_registros_ventana"] = sum(f["count"] for f in features.values())

        return result

    threshold_features = _compute_threshold_features(features)

    values = []
    for name in feature_names:
        # Check if it's a v1 format (spn_{id}_{stat}_7d)
        if name.startswith("spn_"):
            parts = name.split("_")
            spn_id = int(parts[1])
            stat_suffix = "_".join(parts[2:]).replace("_7d", "")
            internal_key = V1_STAT_MAP.get(stat_suffix, stat_suffix)
            spn_feat = features.get(spn_id)
            if spn_feat and internal_key in spn_feat:
                values.append(str(round(float(spn_feat[internal_key]), 6)))
            else:
                values.append("0")

        # Check if it's a v2 SPN feature ({nombre}_{stat})
        elif any(name.startswith(n + "_") for n in NOMBRE_TO_SPN.keys()):
            # Find which nombre matches
            matched = False
            for nombre, spn_id in NOMBRE_TO_SPN.items():
                if name.startswith(nombre + "_"):
                    stat = name[len(nombre) + 1:]  # e.g. "avg", "max", "min", "oor"
                    internal_key = V2_STAT_MAP.get(stat, stat)
                    spn_feat = features.get(spn_id)
                    if spn_feat and internal_key in spn_feat:
                        values.append(str(round(float(spn_feat[internal_key]), 6)))
                    else:
                        values.append("0")
                    matched = True
                    break
            if not matched:
                values.append("0")

        # Threshold features (pct_*)
        elif name.startswith("pct_") or name in ("total_oor", "n_registros_ventana"):
            val = threshold_features.get(name, 0)
            values.append(str(round(float(val), 6)))

        # Fault features
        elif name in fault_features:
            values.append(str(fault_features[name]))

        # Contextual features (v1)
        elif name in contextual_features:
            values.append(str(round(float(contextual_features[name]), 6)))

        else:
            values.append("0")

    return ",".join(values)


def _classify_ml_risk(probability):
    """Classify risk level from ML model probability output.

    Args:
        probability: Float between 0 and 1.

    Returns:
        Tuple of (risk_level, urgency, description, score).
    """
    if probability >= 0.75:
        level = "CRITICO"
    elif probability >= 0.50:
        level = "ELEVADO"
    elif probability >= 0.25:
        level = "MODERADO"
    else:
        level = "BAJO"

    return level, URGENCY_MAP[level], RISK_DESCRIPTIONS[level], round(probability, 4)


def _invoke_sagemaker(features, fault_features, contextual_features, autobus):
    """Invoke the SageMaker XGBoost endpoint with a properly formatted CSV payload.

    Builds the 128-feature CSV row in the exact order defined by
    feature_names.json, sends it as text/csv, and parses the probability
    output.

    Args:
        features: SPN feature dict from _build_feature_vector().
        fault_features: Dict from _build_fault_features().
        contextual_features: Dict from _build_contextual_features().
        autobus: Bus identifier for logging.

    Returns:
        Dict with ML prediction result, or None if invocation fails.
    """
    try:
        feature_names = _load_feature_names()
        if not feature_names:
            logger.warning(json.dumps({
                "action": "invoke_sagemaker",
                "error": "feature_names not available",
            }))
            return None

        client = _get_sagemaker_client()

        csv_payload = _build_csv_payload(
            features, fault_features, contextual_features, feature_names,
        )

        logger.info(json.dumps({
            "action": "invoke_sagemaker_request",
            "endpoint": SAGEMAKER_ENDPOINT,
            "autobus": autobus,
            "feature_count": len(feature_names),
            "payload_length": len(csv_payload),
        }))

        response = client.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType="text/csv",
            Body=csv_payload,
        )

        result_body = response["Body"].read().decode("utf-8").strip()
        probability = float(result_body)

        nivel_riesgo, urgencia, descripcion, score = _classify_ml_risk(probability)

        logger.info(json.dumps({
            "action": "invoke_sagemaker",
            "endpoint": SAGEMAKER_ENDPOINT,
            "autobus": autobus,
            "result": "success",
            "probability": probability,
            "nivel_riesgo": nivel_riesgo,
        }))

        return {
            "nivel_riesgo": nivel_riesgo,
            "urgencia": urgencia,
            "descripcion": descripcion,
            "score": score,
            "probabilidad_ml": probability,
        }

    except Exception as exc:
        logger.warning(json.dumps({
            "action": "invoke_sagemaker",
            "endpoint": SAGEMAKER_ENDPOINT,
            "autobus": autobus,
            "error": str(exc),
            "message": "SageMaker no disponible, usando heurística de fallback",
        }))
        return None


# ---------------------------------------------------------------------------
# Fault retrieval (reused from tool-consultar-obd)
# ---------------------------------------------------------------------------

def _obtener_fallas_recientes(autobus, bucket, fallas_key):
    """Read Data_Fault from S3, filter by autobus, return recent faults.

    Args:
        autobus: Bus number to filter by.
        bucket: S3 bucket name.
        fallas_key: S3 key for the faults JSON file.

    Returns:
        List of fault dicts sorted by fecha_hora descending.
        Returns empty list on error.
    """
    try:
        all_faults = read_json_from_s3(bucket, fallas_key)
    except Exception as exc:
        logger.warning(json.dumps({
            "action": "obtener_fallas_recientes",
            "error": str(exc),
            "message": "No se pudieron leer las fallas desde S3, continuando sin fallas",
        }))
        return []

    if not isinstance(all_faults, list):
        return []

    autobus_str = str(autobus).strip()
    bus_faults = [
        f for f in all_faults
        if str(f.get("autobus", "")).strip() == autobus_str
    ]

    bus_faults.sort(key=lambda f: f.get("fecha_hora", ""), reverse=True)
    return bus_faults


# ---------------------------------------------------------------------------
# Heuristic scoring algorithm (Req 7.3, 7.4)
# ---------------------------------------------------------------------------

def _heuristic_score(features, fallas_recientes):
    """Compute a heuristic risk score based on maintenance SPN thresholds
    and recent fault severity.

    Scoring rules (Req 7.4):
      - SPN 110 temp motor: +3 if avg>120°C, +2 if max>140°C
      - SPN 175 oil temp: +2 if avg>130°C
      - SPN 100 oil pressure: +3 if min<150 kPa, +1 if avg<250 kPa
      - SPN 98 oil level: +2 if avg<30%
      - SPN 111 coolant: +2 if avg<40%
      - SPN 168 battery: +1 if min<22V
      - SPN 1761 urea: +1 if avg<15%
      - Brake pads (SPNs 1099-1104): +2 if avg<15%, +1 if avg<30%
      - Recent fault severity added directly to score

    Args:
        features: Feature vector dict from _build_feature_vector().
        fallas_recientes: List of recent fault dicts.

    Returns:
        Tuple of (score: int, factors: list[dict], contributing_spns: set[int]).
    """
    score = 0
    factors = []
    contributing_spns = set()

    # SPN 110 — Temperatura Motor (Req 7.4)
    f110 = features.get(SPN_TEMPERATURA_MOTOR)
    if f110:
        if f110["avg"] > 120:
            score += 3
            factors.append({
                "spn_id": SPN_TEMPERATURA_MOTOR,
                "nombre": "Temperatura Motor",
                "condicion": f"Promedio ({f110['avg']:.1f}°C) superior a 120°C",
                "puntos": 3,
            })
            contributing_spns.add(SPN_TEMPERATURA_MOTOR)
        if f110["max"] > 140:
            score += 2
            factors.append({
                "spn_id": SPN_TEMPERATURA_MOTOR,
                "nombre": "Temperatura Motor",
                "condicion": f"Máximo ({f110['max']:.1f}°C) superior a 140°C",
                "puntos": 2,
            })
            contributing_spns.add(SPN_TEMPERATURA_MOTOR)

    # SPN 175 — Temperatura Aceite Motor (Req 7.4)
    f175 = features.get(SPN_TEMPERATURA_ACEITE)
    if f175:
        if f175["avg"] > 130:
            score += 2
            factors.append({
                "spn_id": SPN_TEMPERATURA_ACEITE,
                "nombre": "Temperatura Aceite Motor",
                "condicion": f"Promedio ({f175['avg']:.1f}°C) superior a 130°C",
                "puntos": 2,
            })
            contributing_spns.add(SPN_TEMPERATURA_ACEITE)

    # SPN 100 — Presión Aceite Motor (Req 7.4)
    f100 = features.get(SPN_PRESION_ACEITE)
    if f100:
        if f100["min"] < 150:
            score += 3
            factors.append({
                "spn_id": SPN_PRESION_ACEITE,
                "nombre": "Presión Aceite Motor",
                "condicion": f"Mínimo ({f100['min']:.1f} kPa) inferior a 150 kPa",
                "puntos": 3,
            })
            contributing_spns.add(SPN_PRESION_ACEITE)
        if f100["avg"] < 250:
            score += 1
            factors.append({
                "spn_id": SPN_PRESION_ACEITE,
                "nombre": "Presión Aceite Motor",
                "condicion": f"Promedio ({f100['avg']:.1f} kPa) inferior a 250 kPa",
                "puntos": 1,
            })
            contributing_spns.add(SPN_PRESION_ACEITE)

    # SPN 98 — Nivel de Aceite (Req 7.4)
    f98 = features.get(SPN_NIVEL_ACEITE)
    if f98:
        if f98["avg"] < 30:
            score += 2
            factors.append({
                "spn_id": SPN_NIVEL_ACEITE,
                "nombre": "Nivel de Aceite",
                "condicion": f"Promedio ({f98['avg']:.1f}%) inferior a 30%",
                "puntos": 2,
            })
            contributing_spns.add(SPN_NIVEL_ACEITE)

    # SPN 111 — Nivel de Anticongelante (Req 7.4)
    f111 = features.get(SPN_NIVEL_ANTICONGELANTE)
    if f111:
        if f111["avg"] < 40:
            score += 2
            factors.append({
                "spn_id": SPN_NIVEL_ANTICONGELANTE,
                "nombre": "Nivel de Anticongelante",
                "condicion": f"Promedio ({f111['avg']:.1f}%) inferior a 40%",
                "puntos": 2,
            })
            contributing_spns.add(SPN_NIVEL_ANTICONGELANTE)

    # SPN 168 — Voltaje Batería (Req 7.4)
    f168 = features.get(SPN_VOLTAJE_BATERIA)
    if f168:
        if f168["min"] < 22:
            score += 1
            factors.append({
                "spn_id": SPN_VOLTAJE_BATERIA,
                "nombre": "Voltaje Batería",
                "condicion": f"Mínimo ({f168['min']:.1f}V) inferior a 22V",
                "puntos": 1,
            })
            contributing_spns.add(SPN_VOLTAJE_BATERIA)

    # SPN 1761 — Nivel Urea (Req 7.4)
    f1761 = features.get(SPN_NIVEL_UREA)
    if f1761:
        if f1761["avg"] < 15:
            score += 1
            factors.append({
                "spn_id": SPN_NIVEL_UREA,
                "nombre": "Nivel Urea",
                "condicion": f"Promedio ({f1761['avg']:.1f}%) inferior a 15%",
                "puntos": 1,
            })
            contributing_spns.add(SPN_NIVEL_UREA)

    # Brake pads — SPNs 1099-1104 (Req 7.4)
    brake_spn_ids = sorted(SPNS_BALATAS)
    for spn_id in brake_spn_ids:
        f_brake = features.get(spn_id)
        if f_brake:
            if f_brake["avg"] < 15:
                score += 2
                factors.append({
                    "spn_id": spn_id,
                    "nombre": f"Balata SPN {spn_id}",
                    "condicion": f"Promedio ({f_brake['avg']:.1f}%) inferior a 15%",
                    "puntos": 2,
                })
                contributing_spns.add(spn_id)
            elif f_brake["avg"] < 30:
                score += 1
                factors.append({
                    "spn_id": spn_id,
                    "nombre": f"Balata SPN {spn_id}",
                    "condicion": f"Promedio ({f_brake['avg']:.1f}%) inferior a 30%",
                    "puntos": 1,
                })
                contributing_spns.add(spn_id)

    # Recent fault severity added directly to score (Req 7.4)
    for fault in fallas_recientes:
        severidad = fault.get("severidad")
        if severidad is not None:
            sev_val = _safe_float(severidad)
            if sev_val is not None and sev_val > 0:
                score += int(sev_val)
                factors.append({
                    "spn_id": None,
                    "nombre": "Falla reciente",
                    "condicion": f"Código {fault.get('codigo', 'N/A')} con severidad {int(sev_val)}",
                    "puntos": int(sev_val),
                })

    return score, factors, contributing_spns


# ---------------------------------------------------------------------------
# Risk classification (Req 7.5)
# ---------------------------------------------------------------------------

def _classify_risk(score):
    """Classify risk level based on heuristic score.

    Args:
        score: Integer risk score.

    Returns:
        Tuple of (risk_level: str, urgency: str, description: str).
    """
    if score <= 2:
        level = "BAJO"
    elif score <= 5:
        level = "MODERADO"
    elif score <= 8:
        level = "ELEVADO"
    else:
        level = "CRITICO"

    urgency = URGENCY_MAP[level]
    description = RISK_DESCRIPTIONS[level]

    return level, urgency, description


# ---------------------------------------------------------------------------
# At-risk components (Req 7.6)
# ---------------------------------------------------------------------------

def _get_at_risk_components(contributing_spns):
    """Determine at-risk components based on which SPNs contributed to the score.

    Mapping:
      - SPN 110, 111 → sistema_refrigeracion, bomba_agua
      - SPN 175, 100, 98 → circuito_aceite
      - SPN 168 → sistema_electrico
      - SPN 1761 → sistema_escape
      - Brake SPNs (1099-1104) → sistema_frenos

    Args:
        contributing_spns: Set of SPN IDs that contributed to the risk score.

    Returns:
        Sorted list of unique component names.
    """
    components = set()

    for spn_id in contributing_spns:
        # Check direct mapping
        if spn_id in SPN_COMPONENT_MAP:
            components.update(SPN_COMPONENT_MAP[spn_id])
        # Check brake SPNs
        elif spn_id in SPNS_BALATAS:
            components.add("sistema_frenos")

    return sorted(components)


# ---------------------------------------------------------------------------
# Lambda handler (Req 7.1–7.7, 11.4, 11.6)
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """Entry point for the predecir-evento tool.

    Invoked by Bedrock AgentCore as a Maintenance Agent Action Group tool.

    Flow:
      1. Parse ``autobus`` from event.
      2. Load SPN catalog from S3 (cached via lru_cache).
      3. Query DynamoDB for the last 20 records of the bus.
      4. If no records found, return empty-data response.
      5. Build feature vector from maintenance SPNs (Req 7.1).
      6. Attempt SageMaker endpoint invocation (Req 7.2).
      7. On SageMaker failure: use heuristic scoring (Req 7.3, 7.4).
      8. Classify risk level and urgency (Req 7.5).
      9. Determine at-risk components (Req 7.6).
      10. Return formatted response with metodo_prediccion (Req 7.7, 11.4).

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

    # --- 1. Parse parameters (Req 7.1) ---
    autobus = _get_param(event, "autobus")
    if not autobus:
        logger.warning(json.dumps({
            "action": "lambda_handler",
            "error": "missing_autobus_parameter",
        }))
        return build_error_response("Parámetro 'autobus' es requerido.", 400)

    autobus = str(autobus).strip()

    logger.info(json.dumps({
        "action": "parse_params",
        "autobus": autobus,
    }))

    # --- 2. Load SPN catalog ---
    try:
        catalogo_spn = cargar_catalogo_spn(S3_BUCKET, S3_CATALOGO_KEY)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "cargar_catalogo",
            "error": str(exc),
        }))
        return build_error_response(
            "Error al cargar el catálogo SPN desde S3.", 500
        )

    # --- 3. Query DynamoDB for last 20 records (Req 7.1) ---
    try:
        records = query_latest_records(DYNAMODB_TABLE, autobus, RECORDS_LIMIT)
    except Exception as exc:
        logger.error(json.dumps({
            "action": "query_dynamodb",
            "autobus": autobus,
            "error": str(exc),
        }))
        return build_error_response(
            f"Error al consultar telemetría del autobús {autobus}.", 500
        )

    # --- 4. Empty-data response ---
    if not records:
        logger.info(json.dumps({
            "action": "no_records_found",
            "autobus": autobus,
        }))
        return build_agent_response({
            "autobus": autobus,
            "mensaje": (
                f"No se encontraron registros de telemetría para el autobús "
                f"{autobus}. No es posible realizar la predicción de eventos."
            ),
            "registros_analizados": 0,
            "nivel_riesgo": None,
            "descripcion": "Sin datos disponibles para evaluar riesgo.",
            "urgencia": None,
            "factores_contribuyentes": [],
            "componentes_en_riesgo": [],
            "metodo_prediccion": None,
        })

    # --- 5. Build feature vector (Req 7.1) ---
    features = _build_feature_vector(records, catalogo_spn)

    # --- 6. Read recent faults from S3 ---
    fallas_recientes = _obtener_fallas_recientes(autobus, S3_BUCKET, S3_FALLAS_KEY)

    # --- 6b. Build fault and contextual features for ML model ---
    fault_features = _build_fault_features(fallas_recientes)
    contextual_features = _build_contextual_features(features, records)

    # --- 7. Attempt SageMaker invocation (Req 7.2) ---
    ml_result = _invoke_sagemaker(features, fault_features, contextual_features, autobus)

    if ml_result is not None:
        # ML prediction succeeded (Req 7.7)
        metodo_prediccion = "modelo_ml"
        nivel_riesgo = ml_result["nivel_riesgo"]
        urgencia = ml_result["urgencia"]
        descripcion = ml_result["descripcion"]
        score = ml_result["score"]

        # Still run heuristic to get contributing factors and components
        _, factores, contributing_spns = _heuristic_score(features, fallas_recientes)
        componentes = _get_at_risk_components(contributing_spns)
    else:
        # --- 8. Heuristic fallback (Req 7.3, 7.4) ---
        metodo_prediccion = "heuristica"
        score, factores, contributing_spns = _heuristic_score(features, fallas_recientes)

        # --- 9. Classify risk (Req 7.5) ---
        nivel_riesgo, urgencia, descripcion = _classify_risk(score)

        # --- 10. Determine at-risk components (Req 7.6) ---
        componentes = _get_at_risk_components(contributing_spns)

    # --- 11. Build and return response (Req 7.7, 11.4) ---
    latest_record = records[0]
    response_body = {
        "autobus": autobus,
        "ultimo_timestamp": latest_record.get("timestamp", ""),
        "registros_analizados": len(records),
        "nivel_riesgo": nivel_riesgo,
        "descripcion": descripcion,
        "urgencia": urgencia,
        "puntuacion_riesgo": score,
        "factores_contribuyentes": factores,
        "componentes_en_riesgo": componentes,
        "metodo_prediccion": metodo_prediccion,
    }

    logger.info(json.dumps({
        "action": "lambda_handler_success",
        "autobus": autobus,
        "records_analyzed": len(records),
        "metodo_prediccion": metodo_prediccion,
        "nivel_riesgo": nivel_riesgo,
        "score": score,
        "factores_count": len(factores),
        "componentes_count": len(componentes),
    }))

    return build_agent_response(response_body)
