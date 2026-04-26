"""
Unit tests for tool-listar-buses-activos Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - Timestamp limit computation (now - 5 minutes)
  - Route filtering via GSI query vs full scan
  - Deduplication: multiple records per bus → keep most recent
  - Bus summary extraction (autobus, viaje_ruta, operador, estado_consumo, alertas)
  - Sorting logic: ALERTA_SIGNIFICATIVA first, then by alertas_spn_count descending
  - Empty results response
  - Error handling for DynamoDB failures
  - Response format compliance with Bedrock AgentCore

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 11.4, 11.6
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
_mock_boto3.dynamodb = _mock_dynamodb
_mock_boto3.dynamodb.conditions = _mock_conditions
sys.modules["boto3"] = _mock_boto3
sys.modules["boto3.dynamodb"] = _mock_dynamodb
sys.modules["boto3.dynamodb.conditions"] = _mock_conditions

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lambda_function import (  # noqa: E402
    lambda_handler,
    _get_param,
    _compute_timestamp_limit,
    _deduplicate_buses,
    _extract_bus_summary,
    _sort_buses,
    ESTADO_CONSUMO_PRIORITY,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_record(
    autobus="1001",
    timestamp="2026-01-15T10:00:00Z",
    viaje_ruta="RUTA-MEX-PUE",
    operador_desc="Juan Pérez",
    estado_consumo="EFICIENTE",
    alertas_spn=None,
    spn_valores=None,
):
    """Build a sample DynamoDB record for bus listing."""
    if alertas_spn is None:
        alertas_spn = []
    if spn_valores is None:
        spn_valores = {}
    return {
        "autobus": autobus,
        "timestamp": timestamp,
        "viaje_ruta": viaje_ruta,
        "operador_desc": operador_desc,
        "estado_consumo": estado_consumo,
        "alertas_spn": alertas_spn,
        "spn_valores": spn_valores,
    }


def _make_event(viaje_ruta=None):
    """Build a Bedrock AgentCore event with optional viaje_ruta parameter."""
    params = []
    if viaje_ruta is not None:
        params.append({"name": "viaje_ruta", "value": viaje_ruta})
    return {"parameters": params}


def _parse_response_body(response):
    """Extract the parsed data dict from a build_agent_response result."""
    text_body = response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    payload = json.loads(text_body)
    return payload.get("data", payload)


def _make_alerta(spn_id=185, name="Rendimiento", mensaje="Valor fuera de rango"):
    """Build a sample alertas_spn entry."""
    return {
        "spn_id": spn_id,
        "name": name,
        "valor": 1.5,
        "unidad": "km/L",
        "mensaje": mensaje,
    }


# ---------------------------------------------------------------------------
# 1. _get_param helper
# ---------------------------------------------------------------------------

class TestGetParam:
    def test_extracts_existing_param(self):
        event = {"parameters": [{"name": "viaje_ruta", "value": "RUTA-MEX-PUE"}]}
        assert _get_param(event, "viaje_ruta") == "RUTA-MEX-PUE"

    def test_returns_default_for_missing_param(self):
        event = {"parameters": []}
        assert _get_param(event, "viaje_ruta") is None

    def test_returns_custom_default(self):
        event = {"parameters": []}
        assert _get_param(event, "viaje_ruta", "fallback") == "fallback"

    def test_handles_missing_parameters_key(self):
        event = {}
        assert _get_param(event, "viaje_ruta") is None


# ---------------------------------------------------------------------------
# 2. Timestamp limit computation (Req 5.1)
# ---------------------------------------------------------------------------

class TestComputeTimestampLimit:
    @patch("lambda_function.datetime")
    def test_returns_iso_format(self, mock_dt):
        from datetime import datetime as real_dt, timezone as real_tz
        fixed_now = real_dt(2026, 1, 15, 10, 30, 0, tzinfo=real_tz.utc)
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = lambda *a, **kw: real_dt(*a, **kw)

        # We need to also handle timedelta, so let's just test the real function
        # by checking the format is valid ISO 8601
        result = _compute_timestamp_limit()
        assert "T" in result
        assert result.endswith("Z")

    def test_timestamp_limit_is_in_the_past(self):
        from datetime import datetime as real_dt, timezone as real_tz
        now = real_dt.now(real_tz.utc)
        result = _compute_timestamp_limit()
        # The limit should be before now
        assert result < now.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# 3. Deduplication (keep most recent per bus)
# ---------------------------------------------------------------------------

class TestDeduplicateBuses:
    def test_keeps_most_recent_record(self):
        records = [
            _make_record(autobus="1001", timestamp="2026-01-15T10:00:00Z"),
            _make_record(autobus="1001", timestamp="2026-01-15T10:05:00Z"),
            _make_record(autobus="1001", timestamp="2026-01-15T10:02:00Z"),
        ]
        result = _deduplicate_buses(records)
        assert len(result) == 1
        assert result[0]["timestamp"] == "2026-01-15T10:05:00Z"

    def test_keeps_all_different_buses(self):
        records = [
            _make_record(autobus="1001", timestamp="2026-01-15T10:00:00Z"),
            _make_record(autobus="1002", timestamp="2026-01-15T10:01:00Z"),
            _make_record(autobus="1003", timestamp="2026-01-15T10:02:00Z"),
        ]
        result = _deduplicate_buses(records)
        assert len(result) == 3

    def test_handles_empty_list(self):
        assert _deduplicate_buses([]) == []

    def test_skips_records_without_autobus(self):
        records = [
            {"timestamp": "2026-01-15T10:00:00Z"},
            _make_record(autobus="1001"),
        ]
        result = _deduplicate_buses(records)
        assert len(result) == 1
        assert result[0]["autobus"] == "1001"

    def test_mixed_buses_deduplication(self):
        records = [
            _make_record(autobus="1001", timestamp="2026-01-15T10:00:00Z"),
            _make_record(autobus="1002", timestamp="2026-01-15T10:01:00Z"),
            _make_record(autobus="1001", timestamp="2026-01-15T10:03:00Z"),
            _make_record(autobus="1002", timestamp="2026-01-15T10:00:30Z"),
        ]
        result = _deduplicate_buses(records)
        assert len(result) == 2
        bus_map = {r["autobus"]: r for r in result}
        assert bus_map["1001"]["timestamp"] == "2026-01-15T10:03:00Z"
        assert bus_map["1002"]["timestamp"] == "2026-01-15T10:01:00Z"


# ---------------------------------------------------------------------------
# 4. Bus summary extraction (Req 5.4)
# ---------------------------------------------------------------------------

class TestExtractBusSummary:
    def test_extracts_basic_fields(self):
        record = _make_record(
            autobus="1001",
            viaje_ruta="RUTA-MEX-PUE",
            operador_desc="Juan Pérez",
            estado_consumo="EFICIENTE",
        )
        summary = _extract_bus_summary(record)
        assert summary["autobus"] == "1001"
        assert summary["viaje_ruta"] == "RUTA-MEX-PUE"
        assert summary["operador"] == "Juan Pérez"
        assert summary["estado_consumo"] == "EFICIENTE"

    def test_counts_alertas_spn(self):
        alertas = [_make_alerta(), _make_alerta(spn_id=190)]
        record = _make_record(alertas_spn=alertas)
        summary = _extract_bus_summary(record)
        assert summary["alertas_spn_count"] == 2

    def test_zero_alertas_when_empty(self):
        record = _make_record(alertas_spn=[])
        summary = _extract_bus_summary(record)
        assert summary["alertas_spn_count"] == 0

    def test_counts_spns_fuera_de_rango(self):
        spn_valores = {
            "185": {"valor": 1.5, "fuera_de_rango": True},
            "190": {"valor": 1800, "fuera_de_rango": False},
            "84": {"valor": 130, "fuera_de_rango": True},
        }
        record = _make_record(spn_valores=spn_valores)
        summary = _extract_bus_summary(record)
        assert summary["spns_fuera_de_rango"] == 2

    def test_includes_alertas_resumen(self):
        alertas = [_make_alerta(spn_id=185, name="Rendimiento", mensaje="Bajo")]
        record = _make_record(alertas_spn=alertas)
        summary = _extract_bus_summary(record)
        assert len(summary["alertas_resumen"]) == 1
        assert summary["alertas_resumen"][0]["spn_id"] == 185

    def test_defaults_estado_consumo_to_sin_datos(self):
        record = {"autobus": "1001", "timestamp": "2026-01-15T10:00:00Z"}
        summary = _extract_bus_summary(record)
        assert summary["estado_consumo"] == "SIN_DATOS"


# ---------------------------------------------------------------------------
# 5. Sorting logic (Req 5.5)
# ---------------------------------------------------------------------------

class TestSortBuses:
    def test_alerta_significativa_first(self):
        buses = [
            {"autobus": "1001", "estado_consumo": "EFICIENTE", "alertas_spn_count": 0},
            {"autobus": "1002", "estado_consumo": "ALERTA_SIGNIFICATIVA", "alertas_spn_count": 2},
            {"autobus": "1003", "estado_consumo": "ALERTA_MODERADA", "alertas_spn_count": 1},
        ]
        sorted_buses = _sort_buses(buses)
        assert sorted_buses[0]["autobus"] == "1002"
        assert sorted_buses[1]["autobus"] == "1003"
        assert sorted_buses[2]["autobus"] == "1001"

    def test_same_estado_sorted_by_alertas_count_desc(self):
        buses = [
            {"autobus": "1001", "estado_consumo": "ALERTA_SIGNIFICATIVA", "alertas_spn_count": 1},
            {"autobus": "1002", "estado_consumo": "ALERTA_SIGNIFICATIVA", "alertas_spn_count": 5},
            {"autobus": "1003", "estado_consumo": "ALERTA_SIGNIFICATIVA", "alertas_spn_count": 3},
        ]
        sorted_buses = _sort_buses(buses)
        assert sorted_buses[0]["autobus"] == "1002"
        assert sorted_buses[1]["autobus"] == "1003"
        assert sorted_buses[2]["autobus"] == "1001"

    def test_sin_datos_last(self):
        buses = [
            {"autobus": "1001", "estado_consumo": "SIN_DATOS", "alertas_spn_count": 0},
            {"autobus": "1002", "estado_consumo": "EFICIENTE", "alertas_spn_count": 0},
        ]
        sorted_buses = _sort_buses(buses)
        assert sorted_buses[0]["autobus"] == "1002"
        assert sorted_buses[1]["autobus"] == "1001"

    def test_empty_list(self):
        assert _sort_buses([]) == []

    def test_full_priority_order(self):
        buses = [
            {"autobus": "A", "estado_consumo": "SIN_DATOS", "alertas_spn_count": 0},
            {"autobus": "B", "estado_consumo": "EFICIENTE", "alertas_spn_count": 0},
            {"autobus": "C", "estado_consumo": "ALERTA_MODERADA", "alertas_spn_count": 0},
            {"autobus": "D", "estado_consumo": "ALERTA_SIGNIFICATIVA", "alertas_spn_count": 0},
        ]
        sorted_buses = _sort_buses(buses)
        order = [b["autobus"] for b in sorted_buses]
        assert order == ["D", "C", "B", "A"]


# ---------------------------------------------------------------------------
# 6. Priority map
# ---------------------------------------------------------------------------

class TestEstadoConsumoPriority:
    def test_priority_values(self):
        assert ESTADO_CONSUMO_PRIORITY["ALERTA_SIGNIFICATIVA"] == 0
        assert ESTADO_CONSUMO_PRIORITY["ALERTA_MODERADA"] == 1
        assert ESTADO_CONSUMO_PRIORITY["EFICIENTE"] == 2
        assert ESTADO_CONSUMO_PRIORITY["SIN_DATOS"] == 3


# ---------------------------------------------------------------------------
# 7. Full handler — no filter (scan) (Req 5.1, 5.3)
# ---------------------------------------------------------------------------

class TestHandlerNoFilter:
    @patch("lambda_function.scan_recent")
    def test_returns_all_active_buses(self, mock_scan):
        mock_scan.return_value = [
            _make_record(autobus="1001", estado_consumo="EFICIENTE"),
            _make_record(autobus="1002", estado_consumo="ALERTA_SIGNIFICATIVA",
                         alertas_spn=[_make_alerta()]),
        ]

        event = _make_event()
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_buses_activos"] == 2
        assert data["filtro_viaje_ruta"] == "ninguno"
        # ALERTA_SIGNIFICATIVA should be first
        assert data["buses"][0]["autobus"] == "1002"
        assert data["buses"][1]["autobus"] == "1001"

    @patch("lambda_function.scan_recent")
    def test_calls_scan_recent_with_timestamp(self, mock_scan):
        mock_scan.return_value = []

        event = _make_event()
        lambda_handler(event, None)

        mock_scan.assert_called_once()
        call_args = mock_scan.call_args
        assert call_args[0][0] == "ado-telemetria-live"
        # Second arg is the timestamp_limit
        assert "T" in call_args[0][1]

    @patch("lambda_function.scan_recent")
    def test_empty_scan_returns_message(self, mock_scan):
        mock_scan.return_value = []

        event = _make_event()
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_buses_activos"] == 0
        assert "mensaje" in data
        assert "5 minutos" in data["mensaje"]


# ---------------------------------------------------------------------------
# 8. Full handler — with viaje_ruta filter (Req 5.2)
# ---------------------------------------------------------------------------

class TestHandlerWithFilter:
    @patch("lambda_function.query_gsi")
    def test_queries_gsi_when_viaje_ruta_provided(self, mock_gsi):
        mock_gsi.return_value = [
            _make_record(autobus="1001", viaje_ruta="RUTA-MEX-PUE"),
        ]

        event = _make_event(viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        mock_gsi.assert_called_once()
        call_args = mock_gsi.call_args
        assert call_args[0][0] == "ado-telemetria-live"
        assert call_args[0][1] == "viaje_ruta-timestamp-index"
        assert call_args[0][2] == "RUTA-MEX-PUE"
        assert data["filtro_viaje_ruta"] == "RUTA-MEX-PUE"
        assert data["total_buses_activos"] == 1

    @patch("lambda_function.query_gsi")
    def test_empty_gsi_returns_route_specific_message(self, mock_gsi):
        mock_gsi.return_value = []

        event = _make_event(viaje_ruta="RUTA-MEX-GDL")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_buses_activos"] == 0
        assert "RUTA-MEX-GDL" in data["mensaje"]


# ---------------------------------------------------------------------------
# 9. Deduplication in handler
# ---------------------------------------------------------------------------

class TestHandlerDeduplication:
    @patch("lambda_function.scan_recent")
    def test_deduplicates_multiple_records_per_bus(self, mock_scan):
        mock_scan.return_value = [
            _make_record(autobus="1001", timestamp="2026-01-15T10:00:00Z",
                         estado_consumo="ALERTA_MODERADA"),
            _make_record(autobus="1001", timestamp="2026-01-15T10:05:00Z",
                         estado_consumo="EFICIENTE"),
            _make_record(autobus="1002", timestamp="2026-01-15T10:03:00Z"),
        ]

        event = _make_event()
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_buses_activos"] == 2
        bus_map = {b["autobus"]: b for b in data["buses"]}
        # Should keep the most recent record for bus 1001
        assert bus_map["1001"]["ultimo_timestamp"] == "2026-01-15T10:05:00Z"
        assert bus_map["1001"]["estado_consumo"] == "EFICIENTE"


# ---------------------------------------------------------------------------
# 10. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @patch("lambda_function.scan_recent")
    def test_dynamodb_scan_failure(self, mock_scan):
        mock_scan.side_effect = Exception("DynamoDB timeout")

        event = _make_event()
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)

        assert payload["status"] == "error"
        assert "autobuses activos" in payload["error"]["message"].lower()

    @patch("lambda_function.query_gsi")
    def test_dynamodb_gsi_failure(self, mock_gsi):
        mock_gsi.side_effect = Exception("GSI not found")

        event = _make_event(viaje_ruta="RUTA-MEX-PUE")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)

        assert payload["status"] == "error"


# ---------------------------------------------------------------------------
# 11. Response format (Req 11.4)
# ---------------------------------------------------------------------------

class TestResponseFormat:
    @patch("lambda_function.scan_recent")
    def test_response_follows_agent_format(self, mock_scan):
        mock_scan.return_value = [_make_record()]

        event = _make_event()
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

    @patch("lambda_function.scan_recent")
    def test_response_data_structure(self, mock_scan):
        mock_scan.return_value = [_make_record()]

        event = _make_event()
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert "total_buses_activos" in data
        assert "timestamp_limite" in data
        assert "filtro_viaje_ruta" in data
        assert "buses" in data
        assert isinstance(data["buses"], list)
