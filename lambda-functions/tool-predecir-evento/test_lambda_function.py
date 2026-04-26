"""
Unit tests for tool-predecir-evento Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - Feature vector construction from maintenance SPNs
  - Heuristic scoring algorithm with various SPN combinations
  - Risk level classification thresholds (BAJO, MODERADO, ELEVADO, CRITICO)
  - Urgency mapping
  - At-risk component determination
  - SageMaker invocation and fallback behavior
  - Error handling for missing parameters and service failures
  - Response format compliance with Bedrock AgentCore

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 11.4, 11.6
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Bootstrap: add layer path and mock boto3 before any ado_common import.
# ---------------------------------------------------------------------------

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "layers", "ado-common", "python"),
)

_mock_boto3 = MagicMock()
_mock_dynamodb = MagicMock()
_mock_conditions = MagicMock()
_mock_conditions.Key = MagicMock()
_mock_conditions.Attr = MagicMock()
_mock_dynamodb.conditions = _mock_conditions
_mock_boto3.dynamodb = _mock_dynamodb
sys.modules["boto3"] = _mock_boto3
sys.modules["boto3.dynamodb"] = _mock_dynamodb
sys.modules["boto3.dynamodb.conditions"] = _mock_conditions

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lambda_function import (  # noqa: E402
    lambda_handler,
    _get_param,
    _safe_float,
    _extract_spn_values,
    _safe_avg,
    _build_feature_vector,
    _heuristic_score,
    _classify_risk,
    _get_at_risk_components,
    _obtener_fallas_recientes,
    RISK_THRESHOLDS,
    URGENCY_MAP,
    RISK_DESCRIPTIONS,
    SPN_COMPONENT_MAP,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CATALOGO = {
    84: {"id": 84, "name": "Velocidad Km/h", "unidad": "km/h", "minimo": 0.0, "maximo": 120.0, "delta": 12.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    98: {"id": 98, "name": "Nivel de aceite", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    100: {"id": 100, "name": "Presion Aceite Motor", "unidad": "kPa", "minimo": 100.0, "maximo": 600.0, "delta": 50.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    110: {"id": 110, "name": "Temperatura Motor", "unidad": "C", "minimo": -40.0, "maximo": 210.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    111: {"id": 111, "name": "Nivel de anticongelante", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    168: {"id": 168, "name": "Voltaje Bateria", "unidad": "V", "minimo": 0.0, "maximo": 32.0, "delta": 2.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    171: {"id": 171, "name": "Temperatura ambiente", "unidad": "C", "minimo": -40.0, "maximo": 85.0, "delta": 3.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    175: {"id": 175, "name": "Temperatura Aceite Motor", "unidad": "C", "minimo": -40.0, "maximo": 210.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    190: {"id": 190, "name": "RPM", "unidad": "rpm", "minimo": 0.0, "maximo": 3000.0, "delta": 360.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    247: {"id": 247, "name": "Horas Motor", "unidad": "h", "minimo": 0.0, "maximo": 100000.0, "delta": 0.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    520: {"id": 520, "name": "Retarder Percent Torque", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 75.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    521: {"id": 521, "name": "Posicion Pedal Freno", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 30.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    917: {"id": 917, "name": "Odometro", "unidad": "km", "minimo": 0.0, "maximo": 1000000.0, "delta": 0.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1099: {"id": 1099, "name": "Balata Del Izq", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1100: {"id": 1100, "name": "Balata Del Der", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1101: {"id": 1101, "name": "Balata Tras Izq 1", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1102: {"id": 1102, "name": "Balata Tras Der 1", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1103: {"id": 1103, "name": "Balata Tras Izq 2", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1104: {"id": 1104, "name": "Balata Tras Der 2", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "inicio_fin"},
    1761: {"id": 1761, "name": "Nivel Urea", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 5.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
}


def _make_record(
    autobus="1001",
    timestamp="2026-01-15T10:00:00Z",
    temp_motor=95.0,
    temp_aceite=90.0,
    presion_aceite=350.0,
    nivel_aceite=75.0,
    nivel_anticongelante=80.0,
    voltaje_bateria=26.0,
    nivel_urea=60.0,
    rpm=1800,
    freno=10.0,
    retarder=20.0,
    odometro=150000.0,
    horas_motor=5000.0,
    temp_ambiente=25.0,
    balata_del_izq=55.0,
    balata_del_der=50.0,
    balata_tras_izq1=45.0,
    balata_tras_der1=40.0,
    balata_tras_izq2=35.0,
    balata_tras_der2=30.0,
):
    """Build a sample DynamoDB record with maintenance SPNs."""
    spn_valores = {
        "110": {"valor": temp_motor, "name": "Temperatura Motor", "unidad": "C", "fuera_de_rango": False},
        "175": {"valor": temp_aceite, "name": "Temperatura Aceite Motor", "unidad": "C", "fuera_de_rango": False},
        "100": {"valor": presion_aceite, "name": "Presion Aceite Motor", "unidad": "kPa", "fuera_de_rango": False},
        "98": {"valor": nivel_aceite, "name": "Nivel de aceite", "unidad": "%", "fuera_de_rango": False},
        "111": {"valor": nivel_anticongelante, "name": "Nivel de anticongelante", "unidad": "%", "fuera_de_rango": False},
        "168": {"valor": voltaje_bateria, "name": "Voltaje Bateria", "unidad": "V", "fuera_de_rango": False},
        "1761": {"valor": nivel_urea, "name": "Nivel Urea", "unidad": "%", "fuera_de_rango": False},
        "190": {"valor": rpm, "name": "RPM", "unidad": "rpm", "fuera_de_rango": False},
        "521": {"valor": freno, "name": "Posicion Pedal Freno", "unidad": "%", "fuera_de_rango": False},
        "520": {"valor": retarder, "name": "Retarder Percent Torque", "unidad": "%", "fuera_de_rango": False},
        "917": {"valor": odometro, "name": "Odometro", "unidad": "km", "fuera_de_rango": False},
        "247": {"valor": horas_motor, "name": "Horas Motor", "unidad": "h", "fuera_de_rango": False},
        "171": {"valor": temp_ambiente, "name": "Temperatura ambiente", "unidad": "C", "fuera_de_rango": False},
        "1099": {"valor": balata_del_izq, "name": "Balata Del Izq", "unidad": "%", "fuera_de_rango": False},
        "1100": {"valor": balata_del_der, "name": "Balata Del Der", "unidad": "%", "fuera_de_rango": False},
        "1101": {"valor": balata_tras_izq1, "name": "Balata Tras Izq 1", "unidad": "%", "fuera_de_rango": False},
        "1102": {"valor": balata_tras_der1, "name": "Balata Tras Der 1", "unidad": "%", "fuera_de_rango": False},
        "1103": {"valor": balata_tras_izq2, "name": "Balata Tras Izq 2", "unidad": "%", "fuera_de_rango": False},
        "1104": {"valor": balata_tras_der2, "name": "Balata Tras Der 2", "unidad": "%", "fuera_de_rango": False},
    }
    return {
        "autobus": autobus,
        "timestamp": timestamp,
        "viaje_ruta": "RUTA-MEX-PUE",
        "spn_valores": spn_valores,
    }


def _make_records(count=20, **kwargs):
    """Build a list of N records with the same SPN values."""
    records = []
    for i in range(count):
        ts = f"2026-01-15T10:{i:02d}:00Z"
        records.append(_make_record(timestamp=ts, **kwargs))
    return records


def _make_event(autobus=None):
    """Build a Bedrock AgentCore event with parameters list."""
    params = []
    if autobus is not None:
        params.append({"name": "autobus", "value": autobus})
    return {"parameters": params}


def _parse_response_body(response):
    """Extract the parsed data dict from a build_agent_response result."""
    text_body = response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    payload = json.loads(text_body)
    return payload.get("data", payload)


SAMPLE_FAULTS = [
    {
        "type": "fault",
        "id": "F001",
        "fecha_hora": "2026-01-15T09:00:00Z",
        "autobus": "1001",
        "region": "Centro",
        "marca_comercial": "Volvo",
        "zona": "Zona A",
        "modelo": "9700",
        "codigo": "P0217",
        "severidad": 3,
        "descripcion": "Temperatura motor elevada",
    },
    {
        "type": "fault",
        "id": "F002",
        "fecha_hora": "2026-01-14T08:00:00Z",
        "autobus": "1001",
        "region": "Centro",
        "marca_comercial": "Volvo",
        "zona": "Zona A",
        "modelo": "9700",
        "codigo": "P0520",
        "severidad": 2,
        "descripcion": "Presion aceite baja",
    },
    {
        "type": "fault",
        "id": "F003",
        "fecha_hora": "2026-01-13T07:00:00Z",
        "autobus": "2002",
        "region": "Norte",
        "marca_comercial": "MAN",
        "zona": "Zona B",
        "modelo": "Lion",
        "codigo": "P0300",
        "severidad": 4,
        "descripcion": "Falla multiple cilindros",
    },
]



# ---------------------------------------------------------------------------
# 1. _get_param helper
# ---------------------------------------------------------------------------

class TestGetParam:
    def test_extracts_existing_param(self):
        event = {"parameters": [{"name": "autobus", "value": "1001"}]}
        assert _get_param(event, "autobus") == "1001"

    def test_returns_default_for_missing_param(self):
        event = {"parameters": []}
        assert _get_param(event, "autobus", "fallback") == "fallback"

    def test_handles_missing_parameters_key(self):
        event = {}
        assert _get_param(event, "autobus") is None


# ---------------------------------------------------------------------------
# 2. _safe_float helper
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_converts_int(self):
        assert _safe_float(42) == 42.0

    def test_converts_string(self):
        assert _safe_float("3.14") == 3.14

    def test_returns_none_for_none(self):
        assert _safe_float(None) is None

    def test_returns_none_for_invalid(self):
        assert _safe_float("abc") is None


# ---------------------------------------------------------------------------
# 3. Feature vector construction (Req 7.1)
# ---------------------------------------------------------------------------

class TestBuildFeatureVector:
    def test_builds_features_from_records(self):
        records = _make_records(5, temp_motor=100.0, presion_aceite=300.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)

        assert 110 in features  # temp motor
        assert features[110]["avg"] == 100.0
        assert features[110]["max"] == 100.0
        assert features[110]["min"] == 100.0
        assert features[110]["count"] == 5

    def test_computes_correct_stats_with_varying_values(self):
        records = [
            _make_record(timestamp=f"2026-01-15T10:0{i}:00Z", temp_motor=90.0 + i * 5)
            for i in range(4)
        ]
        # temp_motor values: 90, 95, 100, 105
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        f110 = features[110]
        assert f110["min"] == 90.0
        assert f110["max"] == 105.0
        assert f110["avg"] == 97.5
        assert f110["count"] == 4

    def test_counts_out_of_range_values(self):
        # SPN 100 (Presion Aceite) range: 100-600 kPa
        records = _make_records(4, presion_aceite=80.0)  # below minimo
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        assert features[100]["out_of_range_count"] == 4

    def test_empty_records_returns_empty_features(self):
        features = _build_feature_vector([], SAMPLE_CATALOGO)
        assert features == {}

    def test_includes_brake_pad_spns(self):
        records = _make_records(3, balata_del_izq=25.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        assert 1099 in features
        assert features[1099]["avg"] == 25.0


# ---------------------------------------------------------------------------
# 4. Heuristic scoring algorithm (Req 7.3, 7.4)
# ---------------------------------------------------------------------------

class TestHeuristicScore:
    def test_all_normal_values_score_zero(self):
        """Normal SPN values should produce score 0."""
        records = _make_records(20)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        assert score == 0
        assert factors == []
        assert len(spns) == 0

    def test_high_temp_motor_avg(self):
        """SPN 110 avg > 120°C → +3 points."""
        records = _make_records(20, temp_motor=125.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        temp_factors = [f for f in factors if f["spn_id"] == 110 and f["puntos"] == 3]
        assert len(temp_factors) == 1
        assert 110 in spns

    def test_high_temp_motor_max(self):
        """SPN 110 max > 140°C → +2 points."""
        # Most records at 100, one at 145
        records = _make_records(19, temp_motor=100.0)
        records.append(_make_record(timestamp="2026-01-15T10:19:00Z", temp_motor=145.0))
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        max_factors = [f for f in factors if f["spn_id"] == 110 and f["puntos"] == 2]
        assert len(max_factors) == 1

    def test_high_temp_motor_both_conditions(self):
        """SPN 110 avg > 120 AND max > 140 → +3 + +2 = 5 points from temp alone."""
        records = _make_records(20, temp_motor=145.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        temp_points = sum(f["puntos"] for f in factors if f["spn_id"] == 110)
        assert temp_points == 5

    def test_high_oil_temp(self):
        """SPN 175 avg > 130°C → +2 points."""
        records = _make_records(20, temp_aceite=135.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        oil_factors = [f for f in factors if f["spn_id"] == 175]
        assert len(oil_factors) == 1
        assert oil_factors[0]["puntos"] == 2
        assert 175 in spns

    def test_low_oil_pressure_min(self):
        """SPN 100 min < 150 kPa → +3 points."""
        records = _make_records(19, presion_aceite=300.0)
        records.append(_make_record(timestamp="2026-01-15T10:19:00Z", presion_aceite=140.0))
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        pressure_min_factors = [f for f in factors if f["spn_id"] == 100 and f["puntos"] == 3]
        assert len(pressure_min_factors) == 1

    def test_low_oil_pressure_avg(self):
        """SPN 100 avg < 250 kPa → +1 point."""
        records = _make_records(20, presion_aceite=200.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        pressure_avg_factors = [f for f in factors if f["spn_id"] == 100 and f["puntos"] == 1]
        assert len(pressure_avg_factors) == 1

    def test_low_oil_level(self):
        """SPN 98 avg < 30% → +2 points."""
        records = _make_records(20, nivel_aceite=25.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        oil_factors = [f for f in factors if f["spn_id"] == 98]
        assert len(oil_factors) == 1
        assert oil_factors[0]["puntos"] == 2
        assert 98 in spns

    def test_low_coolant(self):
        """SPN 111 avg < 40% → +2 points."""
        records = _make_records(20, nivel_anticongelante=35.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        coolant_factors = [f for f in factors if f["spn_id"] == 111]
        assert len(coolant_factors) == 1
        assert coolant_factors[0]["puntos"] == 2
        assert 111 in spns

    def test_low_battery(self):
        """SPN 168 min < 22V → +1 point."""
        records = _make_records(19, voltaje_bateria=26.0)
        records.append(_make_record(timestamp="2026-01-15T10:19:00Z", voltaje_bateria=20.0))
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        battery_factors = [f for f in factors if f["spn_id"] == 168]
        assert len(battery_factors) == 1
        assert battery_factors[0]["puntos"] == 1
        assert 168 in spns

    def test_low_urea(self):
        """SPN 1761 avg < 15% → +1 point."""
        records = _make_records(20, nivel_urea=10.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        urea_factors = [f for f in factors if f["spn_id"] == 1761]
        assert len(urea_factors) == 1
        assert urea_factors[0]["puntos"] == 1
        assert 1761 in spns

    def test_brake_pads_very_low(self):
        """Brake pad avg < 15% → +2 points per pad."""
        records = _make_records(20, balata_del_izq=10.0, balata_del_der=10.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        brake_factors = [f for f in factors if f["spn_id"] in (1099, 1100) and f["puntos"] == 2]
        assert len(brake_factors) == 2

    def test_brake_pads_moderate(self):
        """Brake pad avg < 30% but >= 15% → +1 point per pad."""
        records = _make_records(20, balata_del_izq=20.0)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        brake_factors = [f for f in factors if f["spn_id"] == 1099 and f["puntos"] == 1]
        assert len(brake_factors) == 1

    def test_fault_severity_added_to_score(self):
        """Recent fault severity is added directly to score."""
        records = _make_records(20)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        faults = [{"codigo": "P0217", "severidad": 3}]
        score, factors, spns = _heuristic_score(features, faults)
        assert score == 3
        fault_factors = [f for f in factors if f["nombre"] == "Falla reciente"]
        assert len(fault_factors) == 1
        assert fault_factors[0]["puntos"] == 3

    def test_multiple_faults_cumulative(self):
        """Multiple faults add their severities cumulatively."""
        records = _make_records(20)
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        faults = [
            {"codigo": "P0217", "severidad": 3},
            {"codigo": "P0520", "severidad": 2},
        ]
        score, factors, spns = _heuristic_score(features, faults)
        assert score == 5

    def test_combined_high_score(self):
        """Multiple bad signals produce a high cumulative score."""
        records = _make_records(
            20,
            temp_motor=130.0,       # avg>120 → +3
            temp_aceite=135.0,      # avg>130 → +2
            nivel_aceite=25.0,      # avg<30 → +2
            nivel_anticongelante=35.0,  # avg<40 → +2
        )
        features = _build_feature_vector(records, SAMPLE_CATALOGO)
        score, factors, spns = _heuristic_score(features, [])
        # At minimum: 3 + 2 + 2 + 2 = 9 (could be more if max>140 etc.)
        assert score >= 9


# ---------------------------------------------------------------------------
# 5. Risk classification (Req 7.5)
# ---------------------------------------------------------------------------

class TestClassifyRisk:
    def test_bajo_at_zero(self):
        level, urgency, desc = _classify_risk(0)
        assert level == "BAJO"
        assert urgency == "PROXIMO_SERVICIO"

    def test_bajo_at_two(self):
        level, urgency, desc = _classify_risk(2)
        assert level == "BAJO"
        assert urgency == "PROXIMO_SERVICIO"

    def test_moderado_at_three(self):
        level, urgency, desc = _classify_risk(3)
        assert level == "MODERADO"
        assert urgency == "PROXIMO_SERVICIO"

    def test_moderado_at_five(self):
        level, urgency, desc = _classify_risk(5)
        assert level == "MODERADO"
        assert urgency == "PROXIMO_SERVICIO"

    def test_elevado_at_six(self):
        level, urgency, desc = _classify_risk(6)
        assert level == "ELEVADO"
        assert urgency == "ESTA_SEMANA"

    def test_elevado_at_eight(self):
        level, urgency, desc = _classify_risk(8)
        assert level == "ELEVADO"
        assert urgency == "ESTA_SEMANA"

    def test_critico_at_nine(self):
        level, urgency, desc = _classify_risk(9)
        assert level == "CRITICO"
        assert urgency == "INMEDIATA"

    def test_critico_at_high_score(self):
        level, urgency, desc = _classify_risk(20)
        assert level == "CRITICO"
        assert urgency == "INMEDIATA"

    def test_description_is_nonempty(self):
        for score in [0, 3, 6, 9]:
            _, _, desc = _classify_risk(score)
            assert len(desc) > 0


# ---------------------------------------------------------------------------
# 6. At-risk components (Req 7.6)
# ---------------------------------------------------------------------------

class TestGetAtRiskComponents:
    def test_temp_motor_maps_to_refrigeracion(self):
        components = _get_at_risk_components({110})
        assert "sistema_refrigeracion" in components
        assert "bomba_agua" in components

    def test_coolant_maps_to_refrigeracion(self):
        components = _get_at_risk_components({111})
        assert "sistema_refrigeracion" in components
        assert "bomba_agua" in components

    def test_oil_spns_map_to_circuito_aceite(self):
        components = _get_at_risk_components({175})
        assert "circuito_aceite" in components
        components = _get_at_risk_components({100})
        assert "circuito_aceite" in components
        components = _get_at_risk_components({98})
        assert "circuito_aceite" in components

    def test_battery_maps_to_electrico(self):
        components = _get_at_risk_components({168})
        assert "sistema_electrico" in components

    def test_urea_maps_to_escape(self):
        components = _get_at_risk_components({1761})
        assert "sistema_escape" in components

    def test_brake_spns_map_to_frenos(self):
        components = _get_at_risk_components({1099})
        assert "sistema_frenos" in components
        components = _get_at_risk_components({1104})
        assert "sistema_frenos" in components

    def test_empty_spns_returns_empty(self):
        components = _get_at_risk_components(set())
        assert components == []

    def test_multiple_spns_deduplicated(self):
        components = _get_at_risk_components({110, 111})
        # Both map to sistema_refrigeracion and bomba_agua
        assert components.count("sistema_refrigeracion") == 1
        assert components.count("bomba_agua") == 1

    def test_components_are_sorted(self):
        components = _get_at_risk_components({110, 168, 1099, 1761})
        assert components == sorted(components)



# ---------------------------------------------------------------------------
# 7. Fault retrieval
# ---------------------------------------------------------------------------

class TestObtenerFallasRecientes:
    @patch("lambda_function.read_json_from_s3")
    def test_filters_by_autobus(self, mock_read):
        mock_read.return_value = SAMPLE_FAULTS
        fallas = _obtener_fallas_recientes("1001", "bucket", "key")
        assert len(fallas) == 2
        for f in fallas:
            assert str(f.get("autobus", "")).strip() == "1001"

    @patch("lambda_function.read_json_from_s3")
    def test_returns_empty_on_s3_error(self, mock_read):
        mock_read.side_effect = Exception("S3 access denied")
        fallas = _obtener_fallas_recientes("1001", "bucket", "key")
        assert fallas == []

    @patch("lambda_function.read_json_from_s3")
    def test_returns_empty_when_no_matching_bus(self, mock_read):
        mock_read.return_value = SAMPLE_FAULTS
        fallas = _obtener_fallas_recientes("9999", "bucket", "key")
        assert fallas == []


# ---------------------------------------------------------------------------
# 8. Missing parameters
# ---------------------------------------------------------------------------

class TestMissingParameters:
    def test_returns_error_when_autobus_missing(self):
        event = _make_event()
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "autobus" in payload["error"]["message"].lower()


# ---------------------------------------------------------------------------
# 9. Full handler integration (Req 7.1-7.7)
# ---------------------------------------------------------------------------

class TestHandlerIntegration:
    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_successful_prediction_heuristic(self, mock_catalog, mock_query, mock_s3, mock_sm):
        """Full flow with heuristic fallback (SageMaker unavailable)."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(20)
        mock_s3.return_value = []
        mock_sm.return_value = None  # SageMaker fails

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "1001"
        assert data["registros_analizados"] == 20
        assert data["metodo_prediccion"] == "heuristica"
        assert data["nivel_riesgo"] in ("BAJO", "MODERADO", "ELEVADO", "CRITICO")
        assert data["urgencia"] in ("PROXIMO_SERVICIO", "ESTA_SEMANA", "INMEDIATA")
        assert isinstance(data["factores_contribuyentes"], list)
        assert isinstance(data["componentes_en_riesgo"], list)
        assert "descripcion" in data

    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_successful_prediction_ml(self, mock_catalog, mock_query, mock_s3, mock_sm):
        """Full flow with ML model response."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(20)
        mock_s3.return_value = []
        mock_sm.return_value = {
            "nivel_riesgo": "ELEVADO",
            "descripcion": "ML prediction: high risk",
            "factores_contribuyentes": [{"nombre": "ML factor"}],
            "componentes_en_riesgo": ["sistema_refrigeracion"],
            "score": 7,
        }

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["metodo_prediccion"] == "modelo_ml"
        assert data["nivel_riesgo"] == "ELEVADO"
        assert data["urgencia"] == "ESTA_SEMANA"

    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_no_records_returns_empty_response(self, mock_catalog, mock_query, mock_s3, mock_sm):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = []

        event = _make_event(autobus="9999")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "9999"
        assert data["registros_analizados"] == 0
        assert data["nivel_riesgo"] is None
        assert "No se encontraron" in data["mensaje"]
        assert data["metodo_prediccion"] is None

    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_high_risk_scenario(self, mock_catalog, mock_query, mock_s3, mock_sm):
        """Bus with multiple bad signals should produce CRITICO risk."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(
            20,
            temp_motor=145.0,           # avg>120 → +3, max>140 → +2
            temp_aceite=135.0,          # avg>130 → +2
            nivel_aceite=25.0,          # avg<30 → +2
            nivel_anticongelante=35.0,  # avg<40 → +2
        )
        mock_s3.return_value = []
        mock_sm.return_value = None

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["metodo_prediccion"] == "heuristica"
        assert data["nivel_riesgo"] == "CRITICO"
        assert data["urgencia"] == "INMEDIATA"
        assert len(data["factores_contribuyentes"]) > 0
        assert len(data["componentes_en_riesgo"]) > 0
        assert "sistema_refrigeracion" in data["componentes_en_riesgo"]
        assert "circuito_aceite" in data["componentes_en_riesgo"]

    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_faults_increase_risk(self, mock_catalog, mock_query, mock_s3, mock_sm):
        """Recent faults should increase the risk score."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(20)  # normal values → score 0
        mock_s3.return_value = SAMPLE_FAULTS  # bus 1001 has sev 3 + sev 2 = 5
        mock_sm.return_value = None

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["puntuacion_riesgo"] == 5
        assert data["nivel_riesgo"] == "MODERADO"

    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_bajo_risk_normal_bus(self, mock_catalog, mock_query, mock_s3, mock_sm):
        """Bus with all normal values and no faults → BAJO."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(20)
        mock_s3.return_value = []
        mock_sm.return_value = None

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["nivel_riesgo"] == "BAJO"
        assert data["urgencia"] == "PROXIMO_SERVICIO"
        assert data["puntuacion_riesgo"] == 0


# ---------------------------------------------------------------------------
# 10. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @patch("lambda_function.cargar_catalogo_spn")
    def test_catalog_load_failure(self, mock_catalog):
        mock_catalog.side_effect = Exception("S3 access denied")
        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_dynamodb_query_failure(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.side_effect = Exception("DynamoDB timeout")
        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"


# ---------------------------------------------------------------------------
# 11. Response format (Req 11.4)
# ---------------------------------------------------------------------------

class TestResponseFormat:
    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_response_follows_agent_format(self, mock_catalog, mock_query, mock_s3, mock_sm):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(20)
        mock_s3.return_value = []
        mock_sm.return_value = None

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)

        assert result["messageVersion"] == "1.0"
        assert "response" in result
        assert "functionResponse" in result["response"]
        assert "responseBody" in result["response"]["functionResponse"]
        assert "TEXT" in result["response"]["functionResponse"]["responseBody"]

        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "success"
        assert "data" in payload

    @patch("lambda_function._invoke_sagemaker")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_response_includes_metodo_prediccion(self, mock_catalog, mock_query, mock_s3, mock_sm):
        """Req 7.7: Response must include metodo_prediccion field."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(20)
        mock_s3.return_value = []
        mock_sm.return_value = None

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert "metodo_prediccion" in data
        assert data["metodo_prediccion"] in ("heuristica", "modelo_ml")
