"""
Unit tests for tool-buscar-patrones-historicos Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - Fault code filtering (exact and partial match)
  - Prioritization by modelo/marca_comercial without excluding others
  - Sorting by fecha_hora descending and top-10 limit
  - Statistics computation (severity, models, zones, regions, duration, services)
  - Event formatting with duration computation
  - No-patterns-found response
  - Error handling for missing parameters and S3 failures
  - Response format compliance with Bedrock AgentCore

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.4
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
    _filter_by_codigo,
    _prioritize_matches,
    _compute_duration,
    _compute_statistics,
    _format_event,
    _parse_datetime,
    MAX_EVENTS,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_FAULTS = [
    {
        "type": "fault",
        "id": "F001",
        "fecha_hora": "2026-01-15T09:00:00Z",
        "fecha_hora_fin": "2026-01-15T10:30:00Z",
        "autobus": "1001",
        "region": "Centro",
        "marca_comercial": "Volvo",
        "zona": "Zona A",
        "modelo": "9700",
        "servicio": "Ejecutivo",
        "codigo": "P0217",
        "severidad": 3,
        "descripcion": "Temperatura motor elevada",
    },
    {
        "type": "fault",
        "id": "F002",
        "fecha_hora": "2026-01-14T08:00:00Z",
        "fecha_hora_fin": "2026-01-14T09:00:00Z",
        "autobus": "1002",
        "region": "Norte",
        "marca_comercial": "MAN",
        "zona": "Zona B",
        "modelo": "Lion",
        "servicio": "Economico",
        "codigo": "P0217",
        "severidad": 5,
        "descripcion": "Temperatura motor critica",
    },
    {
        "type": "fault",
        "id": "F003",
        "fecha_hora": "2026-01-13T07:00:00Z",
        "fecha_hora_fin": "2026-01-13T07:45:00Z",
        "autobus": "1003",
        "region": "Centro",
        "marca_comercial": "Volvo",
        "zona": "Zona A",
        "modelo": "9700",
        "servicio": "Ejecutivo",
        "codigo": "P0520",
        "severidad": 2,
        "descripcion": "Presion aceite baja",
    },
    {
        "type": "fault",
        "id": "F004",
        "fecha_hora": "2026-01-12T06:00:00Z",
        "fecha_hora_fin": "2026-01-12T08:00:00Z",
        "autobus": "1004",
        "region": "Sur",
        "marca_comercial": "Mercedes",
        "zona": "Zona C",
        "modelo": "Tourismo",
        "servicio": "Lujo",
        "codigo": "P0217",
        "severidad": 4,
        "descripcion": "Temperatura motor alta",
    },
    {
        "type": "fault",
        "id": "F005",
        "fecha_hora": "2026-01-11T05:00:00Z",
        "fecha_hora_fin": "2026-01-11T05:30:00Z",
        "autobus": "1005",
        "region": "Centro",
        "marca_comercial": "Volvo",
        "zona": "Zona A",
        "modelo": "9700",
        "servicio": "Ejecutivo",
        "codigo": "P0217-SUB",
        "severidad": 1,
        "descripcion": "Temperatura motor leve",
    },
]


def _make_event(codigo=None, modelo=None, marca_comercial=None):
    """Build a Bedrock AgentCore event with parameters list."""
    params = []
    if codigo is not None:
        params.append({"name": "codigo", "value": codigo})
    if modelo is not None:
        params.append({"name": "modelo", "value": modelo})
    if marca_comercial is not None:
        params.append({"name": "marca_comercial", "value": marca_comercial})
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
        event = {"parameters": [{"name": "codigo", "value": "P0217"}]}
        assert _get_param(event, "codigo") == "P0217"

    def test_returns_default_for_missing_param(self):
        event = {"parameters": []}
        assert _get_param(event, "codigo", "fallback") == "fallback"

    def test_handles_missing_parameters_key(self):
        event = {}
        assert _get_param(event, "codigo") is None

    def test_extracts_optional_params(self):
        event = {"parameters": [
            {"name": "codigo", "value": "P0217"},
            {"name": "modelo", "value": "9700"},
            {"name": "marca_comercial", "value": "Volvo"},
        ]}
        assert _get_param(event, "modelo") == "9700"
        assert _get_param(event, "marca_comercial") == "Volvo"


# ---------------------------------------------------------------------------
# 2. _filter_by_codigo (Req 8.1)
# ---------------------------------------------------------------------------

class TestFilterByCodigo:
    def test_exact_match(self):
        """Exact code match returns matching faults."""
        result = _filter_by_codigo(SAMPLE_FAULTS, "P0217")
        # F001, F002, F004 have exact "P0217"; F005 has "P0217-SUB" (partial)
        assert len(result) == 4
        codes = [f["codigo"] for f in result]
        assert "P0217" in codes
        assert "P0217-SUB" in codes

    def test_partial_match(self):
        """Partial code match using 'in' operator."""
        result = _filter_by_codigo(SAMPLE_FAULTS, "P02")
        # All P0217 and P0217-SUB contain "P02"
        assert len(result) == 4

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        result = _filter_by_codigo(SAMPLE_FAULTS, "p0217")
        assert len(result) == 4

    def test_no_match(self):
        """Non-matching code returns empty list."""
        result = _filter_by_codigo(SAMPLE_FAULTS, "ZZZZ")
        assert result == []

    def test_exact_only_match(self):
        """Code that only matches one fault."""
        result = _filter_by_codigo(SAMPLE_FAULTS, "P0520")
        assert len(result) == 1
        assert result[0]["id"] == "F003"


# ---------------------------------------------------------------------------
# 3. _prioritize_matches (Req 8.2)
# ---------------------------------------------------------------------------

class TestPrioritizeMatches:
    def test_no_filters_returns_same_order(self):
        """Without modelo/marca, order is unchanged."""
        faults = SAMPLE_FAULTS[:3]
        result = _prioritize_matches(faults)
        assert [f["id"] for f in result] == [f["id"] for f in faults]

    def test_modelo_prioritization(self):
        """Faults matching modelo appear first."""
        faults = [
            {"id": "A", "modelo": "Lion", "marca_comercial": "MAN"},
            {"id": "B", "modelo": "9700", "marca_comercial": "Volvo"},
            {"id": "C", "modelo": "Tourismo", "marca_comercial": "Mercedes"},
        ]
        result = _prioritize_matches(faults, modelo="9700")
        assert result[0]["id"] == "B"

    def test_marca_prioritization(self):
        """Faults matching marca_comercial appear first."""
        faults = [
            {"id": "A", "modelo": "Lion", "marca_comercial": "MAN"},
            {"id": "B", "modelo": "9700", "marca_comercial": "Volvo"},
        ]
        result = _prioritize_matches(faults, marca_comercial="Volvo")
        assert result[0]["id"] == "B"

    def test_both_filters_highest_priority(self):
        """Faults matching both modelo AND marca get highest priority."""
        faults = [
            {"id": "A", "modelo": "Lion", "marca_comercial": "MAN"},
            {"id": "B", "modelo": "9700", "marca_comercial": "Volvo"},
            {"id": "C", "modelo": "9700", "marca_comercial": "MAN"},
        ]
        result = _prioritize_matches(faults, modelo="9700", marca_comercial="Volvo")
        assert result[0]["id"] == "B"  # matches both

    def test_does_not_exclude_non_matching(self):
        """Non-matching faults are still included, just lower priority."""
        faults = [
            {"id": "A", "modelo": "Lion", "marca_comercial": "MAN"},
            {"id": "B", "modelo": "9700", "marca_comercial": "Volvo"},
        ]
        result = _prioritize_matches(faults, modelo="9700")
        assert len(result) == 2
        ids = [f["id"] for f in result]
        assert "A" in ids
        assert "B" in ids


# ---------------------------------------------------------------------------
# 4. _compute_duration
# ---------------------------------------------------------------------------

class TestComputeDuration:
    def test_valid_duration(self):
        fault = {
            "fecha_hora": "2026-01-15T09:00:00Z",
            "fecha_hora_fin": "2026-01-15T10:30:00Z",
        }
        duration = _compute_duration(fault)
        assert duration == 90.0

    def test_short_duration(self):
        fault = {
            "fecha_hora": "2026-01-15T09:00:00Z",
            "fecha_hora_fin": "2026-01-15T09:15:00Z",
        }
        duration = _compute_duration(fault)
        assert duration == 15.0

    def test_missing_end_returns_none(self):
        fault = {"fecha_hora": "2026-01-15T09:00:00Z"}
        assert _compute_duration(fault) is None

    def test_missing_start_returns_none(self):
        fault = {"fecha_hora_fin": "2026-01-15T10:00:00Z"}
        assert _compute_duration(fault) is None

    def test_empty_strings_return_none(self):
        fault = {"fecha_hora": "", "fecha_hora_fin": ""}
        assert _compute_duration(fault) is None


# ---------------------------------------------------------------------------
# 5. _compute_statistics (Req 8.4)
# ---------------------------------------------------------------------------

class TestComputeStatistics:
    def test_empty_faults(self):
        stats = _compute_statistics([])
        assert stats["total_eventos"] == 0
        assert stats["severidad_promedio"] is None
        assert stats["modelos_mas_afectados"] == []
        assert stats["duracion_promedio_minutos"] is None

    def test_average_severity(self):
        faults = [
            {"severidad": 3, "fecha_hora": "2026-01-15T09:00:00Z", "fecha_hora_fin": "2026-01-15T10:00:00Z"},
            {"severidad": 5, "fecha_hora": "2026-01-14T08:00:00Z", "fecha_hora_fin": "2026-01-14T09:00:00Z"},
        ]
        stats = _compute_statistics(faults)
        assert stats["severidad_promedio"] == 4.0

    def test_most_affected_models(self):
        faults = [
            {"modelo": "9700", "severidad": 1},
            {"modelo": "9700", "severidad": 1},
            {"modelo": "Lion", "severidad": 1},
        ]
        stats = _compute_statistics(faults)
        assert stats["modelos_mas_afectados"][0]["modelo"] == "9700"
        assert stats["modelos_mas_afectados"][0]["cantidad"] == 2

    def test_most_affected_zones(self):
        faults = [
            {"zona": "Zona A", "severidad": 1},
            {"zona": "Zona A", "severidad": 1},
            {"zona": "Zona B", "severidad": 1},
        ]
        stats = _compute_statistics(faults)
        assert stats["zonas_mas_afectadas"][0]["zona"] == "Zona A"
        assert stats["zonas_mas_afectadas"][0]["cantidad"] == 2

    def test_most_affected_regions(self):
        faults = [
            {"region": "Centro", "severidad": 1},
            {"region": "Centro", "severidad": 1},
            {"region": "Norte", "severidad": 1},
        ]
        stats = _compute_statistics(faults)
        assert stats["regiones_mas_afectadas"][0]["region"] == "Centro"

    def test_average_duration(self):
        faults = [
            {"fecha_hora": "2026-01-15T09:00:00Z", "fecha_hora_fin": "2026-01-15T10:00:00Z", "severidad": 1},
            {"fecha_hora": "2026-01-14T08:00:00Z", "fecha_hora_fin": "2026-01-14T10:00:00Z", "severidad": 1},
        ]
        stats = _compute_statistics(faults)
        # 60 min + 120 min = 180 / 2 = 90
        assert stats["duracion_promedio_minutos"] == 90.0

    def test_affected_service_types(self):
        faults = [
            {"servicio": "Ejecutivo", "severidad": 1},
            {"servicio": "Ejecutivo", "severidad": 1},
            {"servicio": "Lujo", "severidad": 1},
        ]
        stats = _compute_statistics(faults)
        assert stats["tipos_servicio_afectados"][0]["servicio"] == "Ejecutivo"

    def test_full_statistics_from_sample(self):
        """Compute statistics from the full sample dataset."""
        p0217_faults = [f for f in SAMPLE_FAULTS if "P0217" in f["codigo"]]
        stats = _compute_statistics(p0217_faults)
        assert stats["total_eventos"] == 4
        assert stats["severidad_promedio"] is not None
        assert len(stats["modelos_mas_afectados"]) > 0
        assert len(stats["zonas_mas_afectadas"]) > 0


# ---------------------------------------------------------------------------
# 6. _format_event (Req 8.5)
# ---------------------------------------------------------------------------

class TestFormatEvent:
    def test_includes_all_required_fields(self):
        event = _format_event(SAMPLE_FAULTS[0])
        required_fields = [
            "id", "autobus", "fecha_hora", "codigo", "severidad",
            "descripcion", "modelo", "marca_comercial", "zona",
            "region", "servicio", "duracion_minutos",
        ]
        for field in required_fields:
            assert field in event, f"Missing field: {field}"

    def test_computes_duration(self):
        event = _format_event(SAMPLE_FAULTS[0])
        # F001: 09:00 to 10:30 = 90 minutes
        assert event["duracion_minutos"] == 90.0

    def test_preserves_original_values(self):
        event = _format_event(SAMPLE_FAULTS[0])
        assert event["id"] == "F001"
        assert event["autobus"] == "1001"
        assert event["codigo"] == "P0217"
        assert event["severidad"] == 3
        assert event["modelo"] == "9700"
        assert event["marca_comercial"] == "Volvo"


# ---------------------------------------------------------------------------
# 7. Missing parameters
# ---------------------------------------------------------------------------

class TestMissingParameters:
    def test_returns_error_when_codigo_missing(self):
        event = _make_event()
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"
        assert "codigo" in payload["error"]["message"].lower()


# ---------------------------------------------------------------------------
# 8. Full handler integration (Req 8.1-8.6)
# ---------------------------------------------------------------------------

class TestHandlerIntegration:
    @patch("lambda_function._load_faults")
    def test_successful_pattern_search(self, mock_load):
        """Full flow: search by codigo, return matching events and stats."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="P0217")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["codigo"] == "P0217"
        assert data["total_coincidencias"] == 4  # F001, F002, F004, F005
        assert len(data["eventos"]) <= MAX_EVENTS
        assert "estadisticas" in data
        assert data["estadisticas"]["total_eventos"] == 4

    @patch("lambda_function._load_faults")
    def test_no_patterns_found(self, mock_load):
        """Req 8.6: no matching faults returns appropriate message."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="ZZZZ")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_coincidencias"] == 0
        assert "No se encontraron" in data["mensaje"]
        assert data["eventos"] == []

    @patch("lambda_function._load_faults")
    def test_prioritization_with_modelo(self, mock_load):
        """Req 8.2: modelo prioritization puts matching faults first."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="P0217", modelo="9700")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        # 9700 model faults should appear first
        eventos = data["eventos"]
        assert len(eventos) > 0
        # First events should be modelo=9700
        first_event = eventos[0]
        assert first_event["modelo"] == "9700"

    @patch("lambda_function._load_faults")
    def test_prioritization_with_marca(self, mock_load):
        """Req 8.2: marca_comercial prioritization."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="P0217", marca_comercial="Volvo")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        eventos = data["eventos"]
        assert len(eventos) > 0
        # First events should be Volvo
        assert eventos[0]["marca_comercial"] == "Volvo"

    @patch("lambda_function._load_faults")
    def test_events_sorted_by_fecha_hora_descending(self, mock_load):
        """Req 8.3: events sorted by fecha_hora descending."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="P0217")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        eventos = data["eventos"]
        fechas = [e["fecha_hora"] for e in eventos]
        assert fechas == sorted(fechas, reverse=True)

    @patch("lambda_function._load_faults")
    def test_max_10_events_returned(self, mock_load):
        """Req 8.3: limit to top 10 events."""
        # Create 15 faults with same code
        many_faults = []
        for i in range(15):
            many_faults.append({
                "id": f"F{i:03d}",
                "fecha_hora": f"2026-01-{15-i:02d}T09:00:00Z",
                "fecha_hora_fin": f"2026-01-{15-i:02d}T10:00:00Z",
                "autobus": f"100{i}",
                "region": "Centro",
                "marca_comercial": "Volvo",
                "zona": "Zona A",
                "modelo": "9700",
                "servicio": "Ejecutivo",
                "codigo": "P0300",
                "severidad": 3,
                "descripcion": f"Falla {i}",
            })
        mock_load.return_value = many_faults

        event = _make_event(codigo="P0300")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_coincidencias"] == 15
        assert data["eventos_retornados"] == 10
        assert len(data["eventos"]) == 10

    @patch("lambda_function._load_faults")
    def test_statistics_computed_from_all_matches(self, mock_load):
        """Req 8.4: statistics use ALL matching faults, not just top 10."""
        many_faults = []
        for i in range(15):
            many_faults.append({
                "id": f"F{i:03d}",
                "fecha_hora": f"2026-01-{15-i:02d}T09:00:00Z",
                "fecha_hora_fin": f"2026-01-{15-i:02d}T10:00:00Z",
                "autobus": f"100{i}",
                "region": "Centro",
                "marca_comercial": "Volvo",
                "zona": "Zona A",
                "modelo": "9700",
                "servicio": "Ejecutivo",
                "codigo": "P0300",
                "severidad": 3,
                "descripcion": f"Falla {i}",
            })
        mock_load.return_value = many_faults

        event = _make_event(codigo="P0300")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        # Statistics should reflect all 15, not just 10
        assert data["estadisticas"]["total_eventos"] == 15

    @patch("lambda_function._load_faults")
    def test_events_include_duration(self, mock_load):
        """Req 8.5: each event includes computed duration."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="P0217")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        for ev in data["eventos"]:
            assert "duracion_minutos" in ev

    @patch("lambda_function._load_faults")
    def test_s3_error_returns_error_response(self, mock_load):
        """S3 read failure returns error response."""
        mock_load.side_effect = Exception("S3 access denied")

        event = _make_event(codigo="P0217")
        result = lambda_handler(event, None)
        text_body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        payload = json.loads(text_body)
        assert payload["status"] == "error"

    @patch("lambda_function._load_faults")
    def test_response_format_bedrock_compatible(self, mock_load):
        """Req 11.4: response uses build_agent_response format."""
        mock_load.return_value = SAMPLE_FAULTS

        event = _make_event(codigo="P0217")
        result = lambda_handler(event, None)

        assert result["messageVersion"] == "1.0"
        assert "response" in result
        assert "functionResponse" in result["response"]
        assert "responseBody" in result["response"]["functionResponse"]
        assert "TEXT" in result["response"]["functionResponse"]["responseBody"]

    @patch("lambda_function._load_faults")
    def test_partial_code_match(self, mock_load):
        """Req 8.1: partial match finds faults containing the code."""
        mock_load.return_value = SAMPLE_FAULTS

        # "SUB" should match "P0217-SUB"
        event = _make_event(codigo="SUB")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_coincidencias"] == 1
        assert data["eventos"][0]["codigo"] == "P0217-SUB"
