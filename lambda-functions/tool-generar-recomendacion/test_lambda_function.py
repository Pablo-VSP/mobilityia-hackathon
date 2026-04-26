"""
Unit tests for tool-generar-recomendacion Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - componentes parsing (comma-separated and JSON array)
  - UUID v4 generation for alerta_id
  - numero_referencia format OT-{YYYY}-{MMDD}-{autobus}
  - Enrichment from DynamoDB_Telemetria (viaje_ruta, operador_desc)
  - Alert item construction (tipo_alerta, estado, agente_origen)
  - DynamoDB write success and failure handling
  - Response format compliance with Bedrock AgentCore
  - Error handling for missing parameters

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 11.4, 11.7
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

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
    _parse_componentes,
    _generate_numero_referencia,
    _enrich_from_telemetria,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_event(autobus=None, diagnostico=None, nivel_riesgo=None,
                urgencia=None, componentes=None):
    """Build a Bedrock AgentCore event with parameters list."""
    params = []
    if autobus is not None:
        params.append({"name": "autobus", "value": autobus})
    if diagnostico is not None:
        params.append({"name": "diagnostico", "value": diagnostico})
    if nivel_riesgo is not None:
        params.append({"name": "nivel_riesgo", "value": nivel_riesgo})
    if urgencia is not None:
        params.append({"name": "urgencia", "value": urgencia})
    if componentes is not None:
        params.append({"name": "componentes", "value": componentes})
    return {"parameters": params}


def _parse_response_body(response):
    """Extract the parsed data dict from a build_agent_response result."""
    text_body = response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    payload = json.loads(text_body)
    return payload.get("data", payload)


def _parse_error_body(response):
    """Extract the parsed error dict from a build_error_response result."""
    text_body = response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    return json.loads(text_body)


SAMPLE_TELEMETRIA_RECORD = {
    "autobus": "1001",
    "timestamp": "2026-01-15T10:00:00Z",
    "viaje_ruta": "RUTA-MEX-PUE",
    "operador_desc": "Juan Pérez",
    "estado_consumo": "EFICIENTE",
}


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

    def test_extracts_multiple_params(self):
        event = {"parameters": [
            {"name": "autobus", "value": "1001"},
            {"name": "diagnostico", "value": "Temperatura elevada"},
        ]}
        assert _get_param(event, "autobus") == "1001"
        assert _get_param(event, "diagnostico") == "Temperatura elevada"


# ---------------------------------------------------------------------------
# 2. _parse_componentes
# ---------------------------------------------------------------------------

class TestParseComponentes:
    def test_comma_separated_string(self):
        result = _parse_componentes("sistema_refrigeracion,bomba_agua,circuito_aceite")
        assert result == ["sistema_refrigeracion", "bomba_agua", "circuito_aceite"]

    def test_json_array_string(self):
        result = _parse_componentes('["sistema_refrigeracion","bomba_agua"]')
        assert result == ["sistema_refrigeracion", "bomba_agua"]

    def test_none_returns_empty(self):
        assert _parse_componentes(None) == []

    def test_empty_string_returns_empty(self):
        assert _parse_componentes("") == []

    def test_whitespace_string_returns_empty(self):
        assert _parse_componentes("   ") == []

    def test_comma_separated_with_spaces(self):
        result = _parse_componentes("sistema_refrigeracion, bomba_agua , circuito_aceite")
        assert result == ["sistema_refrigeracion", "bomba_agua", "circuito_aceite"]

    def test_single_component(self):
        result = _parse_componentes("sistema_frenos")
        assert result == ["sistema_frenos"]

    def test_json_array_with_spaces(self):
        result = _parse_componentes('[ "sistema_refrigeracion" , "bomba_agua" ]')
        assert result == ["sistema_refrigeracion", "bomba_agua"]

    def test_invalid_json_falls_back_to_comma(self):
        result = _parse_componentes("[invalid json")
        assert result == ["[invalid json"]


# ---------------------------------------------------------------------------
# 3. _generate_numero_referencia (Req 9.2)
# ---------------------------------------------------------------------------

class TestGenerateNumeroReferencia:
    @patch("lambda_function.datetime")
    def test_format_matches_spec(self, mock_dt):
        mock_now = MagicMock()
        mock_now.year = 2026
        mock_now.month = 4
        mock_now.day = 23
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = _generate_numero_referencia("1001")
        assert result == "OT-2026-0423-1001"

    @patch("lambda_function.datetime")
    def test_single_digit_month_padded(self, mock_dt):
        mock_now = MagicMock()
        mock_now.year = 2026
        mock_now.month = 1
        mock_now.day = 5
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        result = _generate_numero_referencia("247")
        assert result == "OT-2026-0105-247"


# ---------------------------------------------------------------------------
# 4. _enrich_from_telemetria (Req 9.4)
# ---------------------------------------------------------------------------

class TestEnrichFromTelemetria:
    @patch("lambda_function.query_latest_records")
    def test_returns_viaje_ruta_and_operador(self, mock_query):
        mock_query.return_value = [SAMPLE_TELEMETRIA_RECORD]
        viaje_ruta, operador_desc = _enrich_from_telemetria("1001")
        assert viaje_ruta == "RUTA-MEX-PUE"
        assert operador_desc == "Juan Pérez"
        mock_query.assert_called_once_with("ado-telemetria-live", "1001", limit=1)

    @patch("lambda_function.query_latest_records")
    def test_returns_empty_on_no_records(self, mock_query):
        mock_query.return_value = []
        viaje_ruta, operador_desc = _enrich_from_telemetria("9999")
        assert viaje_ruta == ""
        assert operador_desc == ""

    @patch("lambda_function.query_latest_records")
    def test_returns_empty_on_exception(self, mock_query):
        mock_query.side_effect = Exception("DynamoDB timeout")
        viaje_ruta, operador_desc = _enrich_from_telemetria("1001")
        assert viaje_ruta == ""
        assert operador_desc == ""


# ---------------------------------------------------------------------------
# 5. Missing parameters
# ---------------------------------------------------------------------------

class TestMissingParameters:
    def test_returns_error_when_autobus_missing(self):
        event = _make_event(diagnostico="Test")
        result = lambda_handler(event, None)
        payload = _parse_error_body(result)
        assert payload["status"] == "error"
        assert "autobus" in payload["error"]["message"].lower()

    def test_returns_error_when_diagnostico_missing(self):
        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        payload = _parse_error_body(result)
        assert payload["status"] == "error"
        assert "diagnostico" in payload["error"]["message"].lower()


# ---------------------------------------------------------------------------
# 6. Successful alert creation (Req 9.1, 9.2, 9.3, 9.5)
# ---------------------------------------------------------------------------

class TestSuccessfulAlertCreation:
    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_creates_alert_and_returns_confirmation(self, mock_query, mock_put):
        mock_query.return_value = [SAMPLE_TELEMETRIA_RECORD]
        mock_put.return_value = {}

        event = _make_event(
            autobus="1001",
            diagnostico="Temperatura motor elevada con tendencia ascendente",
            nivel_riesgo="ELEVADO",
            urgencia="ESTA_SEMANA",
            componentes="sistema_refrigeracion,bomba_agua",
        )
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        # Req 9.5 — confirmation fields
        assert data["autobus"] == "1001"
        assert data["nivel_riesgo"] == "ELEVADO"
        assert data["urgencia"] == "ESTA_SEMANA"
        assert "alerta_id" in data
        assert "numero_referencia" in data
        assert "mensaje" in data
        assert data["numero_referencia"].startswith("OT-")
        assert "1001" in data["numero_referencia"]

    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_put_item_called_with_correct_alert_structure(self, mock_query, mock_put):
        mock_query.return_value = [SAMPLE_TELEMETRIA_RECORD]
        mock_put.return_value = {}

        event = _make_event(
            autobus="1001",
            diagnostico="Presión de aceite baja",
            nivel_riesgo="CRITICO",
            urgencia="INMEDIATA",
            componentes='["circuito_aceite","sistema_frenos"]',
        )
        lambda_handler(event, None)

        # Verify put_item was called
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        table_name = call_args[0][0]
        item = call_args[0][1]

        # Req 11.7 — correct table
        assert table_name == "ado-alertas"

        # Req 9.2 — alerta_id is UUID v4 format
        assert len(item["alerta_id"]) == 36  # UUID format
        assert "-" in item["alerta_id"]

        # Req 9.2 — numero_referencia format
        assert item["numero_referencia"].startswith("OT-")
        assert "1001" in item["numero_referencia"]

        # Req 9.3 — fixed fields
        assert item["tipo_alerta"] == "MANTENIMIENTO"
        assert item["estado"] == "ACTIVA"
        assert item["agente_origen"] == "ado-agente-mantenimiento"

        # Req 9.1 — input fields
        assert item["autobus"] == "1001"
        assert item["diagnostico"] == "Presión de aceite baja"
        assert item["nivel_riesgo"] == "CRITICO"
        assert item["urgencia"] == "INMEDIATA"
        assert item["componentes"] == ["circuito_aceite", "sistema_frenos"]

        # Req 9.4 — enriched fields
        assert item["viaje_ruta"] == "RUTA-MEX-PUE"
        assert item["operador_desc"] == "Juan Pérez"

        # timestamp present
        assert "timestamp" in item

    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_defaults_nivel_riesgo_and_urgencia(self, mock_query, mock_put):
        """When nivel_riesgo and urgencia are not provided, defaults are used."""
        mock_query.return_value = []
        mock_put.return_value = {}

        event = _make_event(
            autobus="1001",
            diagnostico="Revisión general",
        )
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["nivel_riesgo"] == "MODERADO"
        assert data["urgencia"] == "PROXIMO_SERVICIO"

    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_enrichment_failure_still_creates_alert(self, mock_query, mock_put):
        """If telemetria enrichment fails, alert is still created with empty fields."""
        mock_query.side_effect = Exception("DynamoDB timeout")
        mock_put.return_value = {}

        event = _make_event(
            autobus="1001",
            diagnostico="Test diagnóstico",
            nivel_riesgo="BAJO",
            urgencia="PROXIMO_SERVICIO",
            componentes="sistema_electrico",
        )
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        # Alert should still be created successfully
        assert data["autobus"] == "1001"
        assert "alerta_id" in data

        # put_item should have been called with empty enrichment fields
        mock_put.assert_called_once()
        item = mock_put.call_args[0][1]
        assert item["viaje_ruta"] == ""
        assert item["operador_desc"] == ""


# ---------------------------------------------------------------------------
# 7. DynamoDB write failure (Req 9.6)
# ---------------------------------------------------------------------------

class TestDynamoDBWriteFailure:
    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_returns_error_on_put_item_failure(self, mock_query, mock_put):
        mock_query.return_value = [SAMPLE_TELEMETRIA_RECORD]
        mock_put.side_effect = Exception("ConditionalCheckFailedException")

        event = _make_event(
            autobus="1001",
            diagnostico="Test diagnóstico",
            nivel_riesgo="MODERADO",
            urgencia="ESTA_SEMANA",
            componentes="sistema_frenos",
        )
        result = lambda_handler(event, None)
        payload = _parse_error_body(result)

        assert payload["status"] == "error"
        assert "1001" in payload["error"]["message"]
        assert payload["error"]["status_code"] == 500


# ---------------------------------------------------------------------------
# 8. Response format compliance (Req 11.4)
# ---------------------------------------------------------------------------

class TestResponseFormat:
    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_response_has_bedrock_agentcore_structure(self, mock_query, mock_put):
        mock_query.return_value = [SAMPLE_TELEMETRIA_RECORD]
        mock_put.return_value = {}

        event = _make_event(
            autobus="1001",
            diagnostico="Test",
            nivel_riesgo="BAJO",
            urgencia="PROXIMO_SERVICIO",
        )
        result = lambda_handler(event, None)

        # Bedrock AgentCore Action Group format
        assert result["messageVersion"] == "1.0"
        assert "response" in result
        assert "functionResponse" in result["response"]
        assert "responseBody" in result["response"]["functionResponse"]
        assert "TEXT" in result["response"]["functionResponse"]["responseBody"]
        assert "body" in result["response"]["functionResponse"]["responseBody"]["TEXT"]

    @patch("lambda_function.put_item")
    @patch("lambda_function.query_latest_records")
    def test_success_message_is_human_readable(self, mock_query, mock_put):
        mock_query.return_value = [SAMPLE_TELEMETRIA_RECORD]
        mock_put.return_value = {}

        event = _make_event(
            autobus="1001",
            diagnostico="Test",
            nivel_riesgo="ELEVADO",
            urgencia="ESTA_SEMANA",
        )
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        mensaje = data["mensaje"]
        assert "1001" in mensaje
        assert "ELEVADO" in mensaje
        assert "ESTA_SEMANA" in mensaje
        assert "OT-" in mensaje
