"""
Unit tests for tool-calcular-desviacion Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - Deviation classification thresholds (DENTRO_DE_RANGO, LEVE, MODERADA, SIGNIFICATIVA)
  - Probable cause detection for correlated SPNs
  - Insufficient-data response when no records found
  - Error handling for missing parameters and DynamoDB/S3 failures
  - Response format compliance with Bedrock AgentCore

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 11.4, 11.6
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
    _extract_flat_field_values,
    _safe_avg,
    _clasificar_desviacion,
    _analizar_causas_probables,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CATALOGO = {
    84: {"id": 84, "name": "Velocidad Km/h", "unidad": "km/h", "minimo": 0.0, "maximo": 120.0, "delta": 12.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    91: {"id": 91, "name": "Posicion Pedal Acelerador", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 80.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    183: {"id": 183, "name": "Tasa de combustible", "unidad": "L/h", "minimo": 0.0, "maximo": 100.0, "delta": 45.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    184: {"id": 184, "name": "Ahorro de combustible instantáneo", "unidad": "km/L", "minimo": 0.0, "maximo": 50.0, "delta": 31.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    185: {"id": 185, "name": "Rendimiento", "unidad": "km/L", "minimo": 0.0, "maximo": 50.0, "delta": 0.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    190: {"id": 190, "name": "RPM", "unidad": "rpm", "minimo": 0.0, "maximo": 3000.0, "delta": 360.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    513: {"id": 513, "name": "Porcentaje Torque", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 75.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    521: {"id": 521, "name": "Posicion Pedal Freno", "unidad": "%", "minimo": 0.0, "maximo": 100.0, "delta": 30.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    523: {"id": 523, "name": "Marchas", "unidad": "Marcha", "minimo": -3.0, "maximo": 16.0, "delta": 5.0, "tipo": "INTEGER", "variable_tipo": "EDA"},
    527: {"id": 527, "name": "Cruise Control States", "unidad": "bit", "minimo": 0.0, "maximo": 6.0, "delta": 6.0, "tipo": "FLOAT", "variable_tipo": "EDA"},
    596: {"id": 596, "name": "Cruise Control Enable Switch", "unidad": "bit", "minimo": 0.0, "maximo": 1.0, "delta": 1.0, "tipo": "INTEGER", "variable_tipo": "EDA"},
}


def _make_record(
    autobus="1001",
    timestamp="2026-01-15T10:00:00Z",
    rendimiento_kml=3.5,
    tasa_combustible_lh=25.0,
    ahorro_instantaneo_kml=3.2,
    rpm=1800,
    pct_acelerador=40.0,
    velocidad_kmh=85.0,
    pct_freno=10.0,
    torque_pct=50.0,
    marcha=6,
    cruise_control_states=3.0,
    cruise_control_enable=1.0,
):
    """Build a sample DynamoDB record with spn_valores for deviation analysis."""
    spn_valores = {
        "185": {"valor": rendimiento_kml, "name": "Rendimiento", "unidad": "km/L", "fuera_de_rango": False},
        "183": {"valor": tasa_combustible_lh, "name": "Tasa de combustible", "unidad": "L/h", "fuera_de_rango": False},
        "184": {"valor": ahorro_instantaneo_kml, "name": "Ahorro instantáneo", "unidad": "km/L", "fuera_de_rango": False},
        "190": {"valor": rpm, "name": "RPM", "unidad": "rpm", "fuera_de_rango": False},
        "91": {"valor": pct_acelerador, "name": "Acelerador", "unidad": "%", "fuera_de_rango": False},
        "84": {"valor": velocidad_kmh, "name": "Velocidad", "unidad": "km/h", "fuera_de_rango": False},
        "521": {"valor": pct_freno, "name": "Freno", "unidad": "%", "fuera_de_rango": False},
        "513": {"valor": torque_pct, "name": "Torque", "unidad": "%", "fuera_de_rango": False},
        "523": {"valor": marcha, "name": "Marchas", "unidad": "Marcha", "fuera_de_rango": False},
        "527": {"valor": cruise_control_states, "name": "Cruise Control States", "unidad": "bit", "fuera_de_rango": False},
        "596": {"valor": cruise_control_enable, "name": "Cruise Control Enable", "unidad": "bit", "fuera_de_rango": False},
    }
    return {
        "autobus": autobus,
        "timestamp": timestamp,
        "viaje_ruta": "RUTA-MEX-PUE",
        "rendimiento_kml": rendimiento_kml,
        "tasa_combustible_lh": tasa_combustible_lh,
        "spn_valores": spn_valores,
    }


def _make_records(count=10, **kwargs):
    """Build a list of N records with the same SPN values."""
    records = []
    for i in range(count):
        ts = f"2026-01-15T10:{i:02d}:00Z"
        records.append(_make_record(timestamp=ts, **kwargs))
    return records


def _make_event(autobus=None, viaje_ruta=None):
    """Build a Bedrock AgentCore event with parameters list."""
    params = []
    if autobus is not None:
        params.append({"name": "autobus", "value": autobus})
    if viaje_ruta is not None:
        params.append({"name": "viaje_ruta", "value": viaje_ruta})
    return {"parameters": params}


def _parse_response_body(response):
    """Extract the parsed data dict from a build_agent_response result."""
    text_body = response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    payload = json.loads(text_body)
    return payload.get("data", payload)


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
# 2. Missing parameters (Req 4.1)
# ---------------------------------------------------------------------------

class TestMissingParameters:
    def test_returns_error_when_autobus_missing(self):
        event = _make_event(viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "autobus" in payload["error"]["message"].lower()

    def test_returns_error_when_viaje_ruta_missing(self):
        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "viaje_ruta" in payload["error"]["message"].lower()


# ---------------------------------------------------------------------------
# 3. Deviation classification thresholds (Req 4.2)
# ---------------------------------------------------------------------------

class TestClasificarDesviacion:
    def test_dentro_de_rango_at_3_0(self):
        cat, _ = _clasificar_desviacion(3.0)
        assert cat == "DENTRO_DE_RANGO"

    def test_dentro_de_rango_above_3_0(self):
        cat, _ = _clasificar_desviacion(4.5)
        assert cat == "DENTRO_DE_RANGO"

    def test_desviacion_leve_at_2_5(self):
        cat, _ = _clasificar_desviacion(2.5)
        assert cat == "DESVIACION_LEVE"

    def test_desviacion_leve_at_2_9(self):
        cat, _ = _clasificar_desviacion(2.9)
        assert cat == "DESVIACION_LEVE"

    def test_desviacion_moderada_at_2_0(self):
        cat, _ = _clasificar_desviacion(2.0)
        assert cat == "DESVIACION_MODERADA"

    def test_desviacion_moderada_at_2_4(self):
        cat, _ = _clasificar_desviacion(2.4)
        assert cat == "DESVIACION_MODERADA"

    def test_desviacion_significativa_below_2_0(self):
        cat, _ = _clasificar_desviacion(1.5)
        assert cat == "DESVIACION_SIGNIFICATIVA"

    def test_sin_datos_when_none(self):
        cat, _ = _clasificar_desviacion(None)
        assert cat == "SIN_DATOS"


# ---------------------------------------------------------------------------
# 4. Probable cause detection (Req 4.3, 4.4)
# ---------------------------------------------------------------------------

class TestAnalizarCausasProbables:
    def test_detects_high_rpm(self):
        records = _make_records(10, rpm=2500)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        rpm_causas = [c for c in causas if c["spn_id"] == 190]
        assert len(rpm_causas) == 1
        assert "RPM" in rpm_causas[0]["hallazgo"]

    def test_no_rpm_cause_when_normal(self):
        records = _make_records(10, rpm=1800)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        rpm_causas = [c for c in causas if c["spn_id"] == 190]
        assert len(rpm_causas) == 0

    def test_detects_harsh_acceleration(self):
        records = _make_records(10, pct_acelerador=75.0)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        accel_causas = [c for c in causas if c["spn_id"] == 91]
        assert len(accel_causas) == 1
        assert "Aceleración" in accel_causas[0]["hallazgo"]

    def test_detects_excessive_speed(self):
        records = _make_records(10, velocidad_kmh=110.0)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        speed_causas = [c for c in causas if c["spn_id"] == 84]
        assert len(speed_causas) == 1
        assert "Velocidad" in speed_causas[0]["hallazgo"]

    def test_detects_late_braking(self):
        records = _make_records(10, pct_freno=35.0)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        brake_causas = [c for c in causas if c["spn_id"] == 521]
        assert len(brake_causas) == 1
        assert "Frenado" in brake_causas[0]["hallazgo"]

    def test_detects_high_engine_load(self):
        records = _make_records(10, torque_pct=85.0)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        torque_causas = [c for c in causas if c["spn_id"] == 513]
        assert len(torque_causas) == 1
        assert "motor" in torque_causas[0]["hallazgo"].lower()

    def test_detects_frequent_gear_changes(self):
        """SPN 523: Detect frequent gear changes via high stdev or many distinct values."""
        records = []
        gears = [3, 5, 2, 6, 4, 3, 5, 2, 6, 4]
        for i, gear in enumerate(gears):
            records.append(_make_record(
                timestamp=f"2026-01-15T10:{i:02d}:00Z",
                marcha=gear,
            ))
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        gear_causas = [c for c in causas if c["spn_id"] == 523]
        assert len(gear_causas) == 1
        assert "marchas" in gear_causas[0]["hallazgo"].lower()

    def test_no_gear_cause_when_stable(self):
        """SPN 523: No cause when gear is stable."""
        records = _make_records(10, marcha=6)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        gear_causas = [c for c in causas if c["spn_id"] == 523]
        assert len(gear_causas) == 0

    def test_detects_cruise_control_inactive(self):
        """SPN 527/596: Detect when cruise control is not used."""
        records = _make_records(10, cruise_control_states=0.0, cruise_control_enable=0.0)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        cc_causas = [c for c in causas if c["spn_id"] == 527]
        assert len(cc_causas) == 1
        assert "Cruise control" in cc_causas[0]["hallazgo"]

    def test_no_cruise_control_cause_when_active(self):
        """SPN 527/596: No cause when cruise control is active."""
        records = _make_records(10, cruise_control_states=3.0, cruise_control_enable=1.0)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        cc_causas = [c for c in causas if c["spn_id"] == 527]
        assert len(cc_causas) == 0

    def test_causa_includes_catalog_info(self):
        """Req 4.4: Each cause includes SPN ID, name, finding, avg, unit, range."""
        records = _make_records(10, rpm=2500)
        causas = _analizar_causas_probables(records, SAMPLE_CATALOGO)
        rpm_causa = next(c for c in causas if c["spn_id"] == 190)
        assert rpm_causa["nombre"] == "RPM"
        assert rpm_causa["unidad"] == "rpm"
        assert rpm_causa["valor_promedio"] == 2500.0
        assert rpm_causa["rango_catalogo"] == "0.0-3000.0"
        assert "hallazgo" in rpm_causa


# ---------------------------------------------------------------------------
# 5. Full handler integration (Req 4.1–4.5)
# ---------------------------------------------------------------------------

class TestHandlerIntegration:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_successful_deviation_calculation(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(10, rendimiento_kml=2.7)

        event = _make_event(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "1001"
        assert data["viaje_ruta"] == "RUTA-MEX-PUE"
        assert data["registros_analizados"] == 10
        assert data["clasificacion_desviacion"] == "DESVIACION_LEVE"
        assert "metricas_eficiencia" in data
        assert data["metricas_eficiencia"]["rendimiento_promedio_kml"] == 2.7

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_dentro_de_rango_response(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(10, rendimiento_kml=3.5)

        event = _make_event(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["clasificacion_desviacion"] == "DENTRO_DE_RANGO"

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_significativa_with_causes(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(
            10,
            rendimiento_kml=1.5,
            rpm=2500,
            pct_acelerador=70.0,
            velocidad_kmh=110.0,
        )

        event = _make_event(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["clasificacion_desviacion"] == "DESVIACION_SIGNIFICATIVA"
        assert data["total_causas_identificadas"] >= 3
        causa_ids = [c["spn_id"] for c in data["causas_probables"]]
        assert 190 in causa_ids  # RPM
        assert 91 in causa_ids   # Acelerador
        assert 84 in causa_ids   # Velocidad


# ---------------------------------------------------------------------------
# 6. Insufficient data (Req 4.5)
# ---------------------------------------------------------------------------

class TestInsufficientData:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_returns_insufficient_data_response(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = []

        event = _make_event(autobus="9999", viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "9999"
        assert data["registros_analizados"] == 0
        assert data["clasificacion_desviacion"] == "SIN_DATOS"
        assert data["causas_probables"] == []
        assert "No se encontraron" in data["mensaje"]


# ---------------------------------------------------------------------------
# 7. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @patch("lambda_function.cargar_catalogo_spn")
    def test_catalog_load_failure(self, mock_catalog):
        mock_catalog.side_effect = Exception("S3 access denied")
        event = _make_event(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_dynamodb_query_failure(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.side_effect = Exception("DynamoDB timeout")
        event = _make_event(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"


# ---------------------------------------------------------------------------
# 8. Response format (Req 11.4)
# ---------------------------------------------------------------------------

class TestResponseFormat:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_response_follows_agent_format(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records(10)

        event = _make_event(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
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
