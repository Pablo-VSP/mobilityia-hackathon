"""
Unit tests for tool-consultar-telemetria Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - Successful query with valid bus data and SPN translation
  - Empty results when no records found for a bus
  - variables_actuales construction with catalog range and out-of-range status
  - historial_reciente construction with consumption state and SPN counts
  - Trip context extraction
  - Error handling for missing parameters and DynamoDB/S3 failures

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 11.4, 11.6
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
    _build_variables_actuales,
    _build_historial_reciente,
    _extract_trip_context,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CATALOGO = {
    84: {
        "id": 84,
        "name": "Velocidad Km/h",
        "unidad": "km/h",
        "minimo": 0.0,
        "maximo": 120.0,
        "delta": 12.0,
        "tipo": "FLOAT",
        "variable_tipo": "EDA",
    },
    185: {
        "id": 185,
        "name": "Rendimiento",
        "unidad": "km/L",
        "minimo": 0.0,
        "maximo": 10.0,
        "delta": 1.0,
        "tipo": "FLOAT",
        "variable_tipo": "EDA",
    },
    110: {
        "id": 110,
        "name": "Temperatura Motor",
        "unidad": "°C",
        "minimo": 60.0,
        "maximo": 110.0,
        "delta": 5.0,
        "tipo": "FLOAT",
        "variable_tipo": "EDA",
    },
}


def _make_dynamo_record(
    autobus="1001",
    timestamp="2026-01-15T10:00:00Z",
    estado_consumo="EFICIENTE",
    rendimiento_kml=3.5,
    spn_valores=None,
    alertas_spn=None,
):
    """Build a sample DynamoDB record matching the ado-telemetria-live schema."""
    if spn_valores is None:
        spn_valores = {
            "84": {"valor": 85.0, "name": "Velocidad Km/h", "unidad": "km/h", "fuera_de_rango": False},
            "185": {"valor": 3.5, "name": "Rendimiento", "unidad": "km/L", "fuera_de_rango": False},
        }
    if alertas_spn is None:
        alertas_spn = []

    return {
        "autobus": autobus,
        "timestamp": timestamp,
        "viaje_ruta": "RUTA-MEX-PUE",
        "viaje_ruta_origen": "México",
        "viaje_ruta_destino": "Puebla",
        "operador_cve": "OP-042",
        "operador_desc": "Juan Pérez",
        "estado_consumo": estado_consumo,
        "rendimiento_kml": rendimiento_kml,
        "spn_valores": spn_valores,
        "alertas_spn": alertas_spn,
    }


def _make_event(autobus=None, ultimos_n_registros=None):
    """Build a Bedrock AgentCore event with parameters list."""
    params = []
    if autobus is not None:
        params.append({"name": "autobus", "value": autobus})
    if ultimos_n_registros is not None:
        params.append({"name": "ultimos_n_registros", "value": str(ultimos_n_registros)})
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
        event = {"parameters": [{"name": "autobus", "value": "1001"}]}
        assert _get_param(event, "missing", "default_val") == "default_val"

    def test_returns_none_for_missing_param_no_default(self):
        event = {"parameters": []}
        assert _get_param(event, "autobus") is None

    def test_handles_empty_parameters_list(self):
        event = {"parameters": []}
        assert _get_param(event, "autobus", "fallback") == "fallback"

    def test_handles_missing_parameters_key(self):
        event = {}
        assert _get_param(event, "autobus") is None


# ---------------------------------------------------------------------------
# 2. Missing autobus parameter (Req 3.1)
# ---------------------------------------------------------------------------

class TestMissingAutobus:
    def test_returns_error_when_autobus_missing(self):
        event = {"parameters": []}
        result = lambda_handler(event, None)

        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "autobus" in payload["error"]["message"].lower()

    def test_returns_400_status_code(self):
        event = {"parameters": []}
        result = lambda_handler(event, None)

        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["error"]["status_code"] == 400


# ---------------------------------------------------------------------------
# 3. Successful query with valid bus data (Req 3.1, 3.2, 3.3, 3.4, 3.5)
# ---------------------------------------------------------------------------

class TestSuccessfulQuery:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_returns_success_with_valid_data(self, mock_catalog, mock_query):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [
            _make_dynamo_record(timestamp="2026-01-15T10:00:00Z"),
            _make_dynamo_record(timestamp="2026-01-15T09:59:50Z"),
        ]

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "1001"
        assert data["registros_consultados"] == 2
        assert len(data["variables_actuales"]) > 0
        assert len(data["historial_reciente"]) == 2

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_includes_trip_context(self, mock_catalog, mock_query):
        """Req 3.4: Response includes trip context."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [_make_dynamo_record()]

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["viaje_ruta"] == "RUTA-MEX-PUE"
        assert data["viaje_ruta_origen"] == "México"
        assert data["viaje_ruta_destino"] == "Puebla"
        assert data["operador_cve"] == "OP-042"
        assert data["operador_desc"] == "Juan Pérez"

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_variables_actuales_has_catalog_info(self, mock_catalog, mock_query):
        """Req 3.2, 3.3: Each variable includes SPN ID, name, value, unit, range, out-of-range."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [_make_dynamo_record()]

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        variables = data["variables_actuales"]
        assert len(variables) >= 2

        # Find the velocity SPN
        vel_var = next((v for v in variables if v["spn_id"] == 84), None)
        assert vel_var is not None
        assert vel_var["nombre"] == "Velocidad Km/h"
        assert vel_var["unidad"] == "km/h"
        assert vel_var["valor"] == 85.0
        assert vel_var["fuera_de_rango"] is False
        assert "rango_catalogo" in vel_var
        assert vel_var["rango_catalogo"] == "0.0-120.0"

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_historial_reciente_structure(self, mock_catalog, mock_query):
        """Req 3.5: historial_reciente has timestamp, estado_consumo, rendimiento, spns count."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        records = [
            _make_dynamo_record(
                timestamp="2026-01-15T10:00:00Z",
                estado_consumo="EFICIENTE",
                rendimiento_kml=3.5,
            ),
            _make_dynamo_record(
                timestamp="2026-01-15T09:59:50Z",
                estado_consumo="ALERTA_MODERADA",
                rendimiento_kml=2.5,
            ),
        ]
        mock_query.return_value = records

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        historial = data["historial_reciente"]
        assert len(historial) == 2
        assert historial[0]["timestamp"] == "2026-01-15T10:00:00Z"
        assert historial[0]["estado_consumo"] == "EFICIENTE"
        assert historial[1]["estado_consumo"] == "ALERTA_MODERADA"
        assert "spns_fuera_de_rango" in historial[0]

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_respects_custom_limit(self, mock_catalog, mock_query):
        """Req 3.1: ultimos_n_registros parameter is respected."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [_make_dynamo_record()]

        event = _make_event(autobus="1001", ultimos_n_registros=5)
        lambda_handler(event, None)

        # Verify query was called with limit=5
        mock_query.assert_called_once_with("ado-telemetria-live", "1001", 5)

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_limit_capped_at_max_50(self, mock_catalog, mock_query):
        """Req 3.1: ultimos_n_registros is capped at 50."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [_make_dynamo_record()]

        event = _make_event(autobus="1001", ultimos_n_registros=100)
        lambda_handler(event, None)

        mock_query.assert_called_once_with("ado-telemetria-live", "1001", 50)

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_default_limit_is_10(self, mock_catalog, mock_query):
        """Req 3.1: Default limit is 10 when not specified."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [_make_dynamo_record()]

        event = _make_event(autobus="1001")
        lambda_handler(event, None)

        mock_query.assert_called_once_with("ado-telemetria-live", "1001", 10)


# ---------------------------------------------------------------------------
# 4. Empty results (Req 3.6)
# ---------------------------------------------------------------------------

class TestEmptyResults:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_returns_empty_data_response(self, mock_catalog, mock_query):
        """Req 3.6: Returns empty-data response when no records found."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = []

        event = _make_event(autobus="9999")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "9999"
        assert "No se encontraron" in data["mensaje"]
        assert data["variables_actuales"] == []
        assert data["alertas_activas"] == []
        assert data["historial_reciente"] == []


# ---------------------------------------------------------------------------
# 5. Alertas activas
# ---------------------------------------------------------------------------

class TestAlertasActivas:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_includes_alertas_from_record(self, mock_catalog, mock_query):
        """Alertas from alertas_spn are included in the response."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        record = _make_dynamo_record(
            alertas_spn=[
                {
                    "spn_id": 110,
                    "name": "Temperatura Motor",
                    "valor": 125.0,
                    "unidad": "°C",
                    "mensaje": "SPN 110: valor 125.0 por encima del máximo 110.0",
                },
            ],
            spn_valores={
                "110": {"valor": 125.0, "name": "Temperatura Motor", "unidad": "°C", "fuera_de_rango": True},
            },
        )
        mock_query.return_value = [record]

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert len(data["alertas_activas"]) == 1
        alerta = data["alertas_activas"][0]
        assert alerta["spn_id"] == 110
        assert alerta["nombre"] == "Temperatura Motor"
        assert alerta["valor"] == 125.0

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_out_of_range_counted_in_historial(self, mock_catalog, mock_query):
        """Out-of-range SPNs are counted in historial_reciente."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        record = _make_dynamo_record(
            spn_valores={
                "84": {"valor": 85.0, "name": "Velocidad", "unidad": "km/h", "fuera_de_rango": False},
                "110": {"valor": 125.0, "name": "Temp Motor", "unidad": "°C", "fuera_de_rango": True},
                "185": {"valor": 3.5, "name": "Rendimiento", "unidad": "km/L", "fuera_de_rango": False},
            },
        )
        mock_query.return_value = [record]

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["historial_reciente"][0]["spns_fuera_de_rango"] == 1


# ---------------------------------------------------------------------------
# 6. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @patch("lambda_function.cargar_catalogo_spn")
    def test_catalog_load_failure_returns_error(self, mock_catalog):
        """Returns error response when SPN catalog fails to load."""
        mock_catalog.side_effect = Exception("S3 access denied")

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)

        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "catálogo" in payload["error"]["message"].lower()

    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_dynamodb_query_failure_returns_error(self, mock_catalog, mock_query):
        """Returns error response when DynamoDB query fails."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.side_effect = Exception("DynamoDB timeout")

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)

        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "1001" in payload["error"]["message"]


# ---------------------------------------------------------------------------
# 7. Response format (Req 11.4)
# ---------------------------------------------------------------------------

class TestResponseFormat:
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_response_follows_agent_format(self, mock_catalog, mock_query):
        """Req 11.4: Response uses Bedrock AgentCore Action Group format."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = [_make_dynamo_record()]

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)

        assert result["messageVersion"] == "1.0"
        assert "response" in result
        assert "functionResponse" in result["response"]
        assert "responseBody" in result["response"]["functionResponse"]
        assert "TEXT" in result["response"]["functionResponse"]["responseBody"]
        assert "body" in result["response"]["functionResponse"]["responseBody"]["TEXT"]

        # Body should be valid JSON
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "success"
        assert "data" in payload
