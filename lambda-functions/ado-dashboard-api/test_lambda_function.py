"""
Unit tests for ado-dashboard-api Lambda function.

Covers:
  - Path-based routing dispatches to correct handler
  - /flota-status aggregation logic and SPN translation
  - /alertas-activas urgency sorting
  - /resumen-consumo route aggregation
  - /co2-estimado fuzzy language response
  - Error handling returns proper HTTP status codes
  - 404 for unknown routes

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.6, 11.7
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock, PropertyMock
from collections import defaultdict

# ---------------------------------------------------------------------------
# Bootstrap: add layer path and mock boto3 before any ado_common import.
# ---------------------------------------------------------------------------

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "layers", "ado-common", "python"),
)

_mock_boto3 = MagicMock()
_mock_dynamodb_resource = MagicMock()
_mock_boto3.resource.return_value = _mock_dynamodb_resource
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
    handle_flota_status,
    handle_alertas_activas,
    handle_resumen_consumo,
    handle_co2_estimado,
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


def _make_telemetria_record(
    autobus="1001",
    timestamp="2026-01-15T10:00:00Z",
    estado_consumo="EFICIENTE",
    rendimiento_kml=3.5,
    viaje_ruta="RUTA-MEX-PUE",
    alertas_spn=None,
):
    """Build a sample DynamoDB telemetria record."""
    if alertas_spn is None:
        alertas_spn = []
    return {
        "autobus": autobus,
        "timestamp": timestamp,
        "viaje_ruta": viaje_ruta,
        "viaje_ruta_origen": "México",
        "viaje_ruta_destino": "Puebla",
        "operador_desc": "Juan Pérez",
        "estado_consumo": estado_consumo,
        "rendimiento_kml": rendimiento_kml,
        "alertas_spn": alertas_spn,
    }


def _make_alerta_record(
    alerta_id="alert-001",
    timestamp="2026-01-15T10:00:00Z",
    autobus="1001",
    urgencia="ESTA_SEMANA",
    nivel_riesgo="MODERADO",
    estado="ACTIVA",
):
    """Build a sample DynamoDB alertas record."""
    return {
        "alerta_id": alerta_id,
        "timestamp": timestamp,
        "autobus": autobus,
        "tipo_alerta": "MANTENIMIENTO",
        "nivel_riesgo": nivel_riesgo,
        "diagnostico": "Señales de desgaste en sistema de frenos",
        "urgencia": urgencia,
        "componentes": ["sistema_frenos"],
        "numero_referencia": f"OT-2026-0115-{autobus}",
        "estado": estado,
        "agente_origen": "ado-agente-mantenimiento",
        "viaje_ruta": "RUTA-MEX-PUE",
        "operador_desc": "Juan Pérez",
    }


def _make_event(path):
    """Build an API Gateway event with the given path."""
    return {"path": path, "httpMethod": "GET"}


def _parse_api_body(response):
    """Parse the JSON body from an API Gateway response."""
    return json.loads(response["body"])


# ---------------------------------------------------------------------------
# 1. Path-based routing (Req 10.1)
# ---------------------------------------------------------------------------

class TestRouting:
    def test_unknown_path_returns_404(self):
        event = _make_event("/dashboard/unknown")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 404
        body = _parse_api_body(result)
        assert "error" in body

    def test_empty_path_returns_404(self):
        event = {"path": "", "httpMethod": "GET"}
        result = lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_routes_to_flota_status(self):
        mock_handler = MagicMock(return_value={"total_buses": 0, "buses": []})
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/flota-status": mock_handler}):
            event = _make_event("/dashboard/flota-status")
            result = lambda_handler(event, None)
            assert result["statusCode"] == 200
            mock_handler.assert_called_once()

    def test_routes_to_alertas_activas(self):
        mock_handler = MagicMock(return_value={"total_alertas": 0, "alertas": []})
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/alertas-activas": mock_handler}):
            event = _make_event("/dashboard/alertas-activas")
            result = lambda_handler(event, None)
            assert result["statusCode"] == 200
            mock_handler.assert_called_once()

    def test_routes_to_resumen_consumo(self):
        mock_handler = MagicMock(return_value={"total_rutas": 0, "rutas": []})
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/resumen-consumo": mock_handler}):
            event = _make_event("/dashboard/resumen-consumo")
            result = lambda_handler(event, None)
            assert result["statusCode"] == 200
            mock_handler.assert_called_once()

    def test_routes_to_co2_estimado(self):
        mock_handler = MagicMock(return_value={"titulo": "CO2"})
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/co2-estimado": mock_handler}):
            event = _make_event("/dashboard/co2-estimado")
            result = lambda_handler(event, None)
            assert result["statusCode"] == 200
            mock_handler.assert_called_once()

    def test_uses_resource_field_as_fallback(self):
        """When path is empty, falls back to resource field."""
        event = {"path": "", "resource": "/dashboard/co2-estimado", "httpMethod": "GET"}
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_404_includes_available_routes(self):
        event = _make_event("/dashboard/invalid")
        result = lambda_handler(event, None)
        body = _parse_api_body(result)
        assert "rutas_disponibles" in body


# ---------------------------------------------------------------------------
# 2. CORS headers (Req 10.1)
# ---------------------------------------------------------------------------

class TestCORSHeaders:
    def test_response_includes_cors_headers(self):
        mock_handler = MagicMock(return_value={"titulo": "CO2"})
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/co2-estimado": mock_handler}):
            event = _make_event("/dashboard/co2-estimado")
            result = lambda_handler(event, None)

            assert result["headers"]["Access-Control-Allow-Origin"] == "*"
            assert "Content-Type" in result["headers"]
            assert result["headers"]["Content-Type"] == "application/json"

    def test_404_also_has_cors_headers(self):
        event = _make_event("/dashboard/unknown")
        result = lambda_handler(event, None)
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"


# ---------------------------------------------------------------------------
# 3. /dashboard/flota-status (Req 10.1, 10.5)
# ---------------------------------------------------------------------------

class TestFlotaStatus:
    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_returns_total_buses_and_list(self, mock_scan, mock_catalog):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", estado_consumo="EFICIENTE"),
            _make_telemetria_record(autobus="1002", estado_consumo="ALERTA_MODERADA"),
        ]

        result = handle_flota_status()

        assert result["total_buses"] == 2
        assert result["buses_activos"] == 2
        assert len(result["buses"]) == 2

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_aggregates_by_estado_consumo(self, mock_scan, mock_catalog):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", estado_consumo="EFICIENTE"),
            _make_telemetria_record(autobus="1002", estado_consumo="EFICIENTE"),
            _make_telemetria_record(autobus="1003", estado_consumo="ALERTA_MODERADA"),
        ]

        result = handle_flota_status()

        assert result["resumen_por_estado"]["EFICIENTE"] == 2
        assert result["resumen_por_estado"]["ALERTA_MODERADA"] == 1

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_keeps_latest_record_per_bus(self, mock_scan, mock_catalog):
        """When multiple records exist for a bus, only the latest is used."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", timestamp="2026-01-15T10:00:00Z", estado_consumo="EFICIENTE"),
            _make_telemetria_record(autobus="1001", timestamp="2026-01-15T10:01:00Z", estado_consumo="ALERTA_MODERADA"),
        ]

        result = handle_flota_status()

        assert result["total_buses"] == 1
        assert result["buses"][0]["estado_consumo"] == "ALERTA_MODERADA"

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_sorts_by_severity(self, mock_scan, mock_catalog):
        """ALERTA_SIGNIFICATIVA buses appear first."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", estado_consumo="EFICIENTE"),
            _make_telemetria_record(autobus="1002", estado_consumo="ALERTA_SIGNIFICATIVA"),
            _make_telemetria_record(autobus="1003", estado_consumo="ALERTA_MODERADA"),
        ]

        result = handle_flota_status()

        assert result["buses"][0]["autobus"] == "1002"
        assert result["buses"][0]["estado_consumo"] == "ALERTA_SIGNIFICATIVA"

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_bus_includes_required_fields(self, mock_scan, mock_catalog):
        """Each bus entry has all required fields per Req 10.1."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001"),
        ]

        result = handle_flota_status()
        bus = result["buses"][0]

        assert "autobus" in bus
        assert "viaje_ruta" in bus
        assert "viaje_ruta_origen" in bus
        assert "viaje_ruta_destino" in bus
        assert "operador_desc" in bus
        assert "estado_consumo" in bus
        assert "spns_fuera_de_rango" in bus
        assert "ultimo_timestamp" in bus

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_counts_out_of_range_spns(self, mock_scan, mock_catalog):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(
                autobus="1001",
                alertas_spn=[
                    {"spn_id": 110, "name": "Temperatura Motor", "valor": 125.0, "unidad": "°C", "mensaje": "fuera de rango"},
                    {"spn_id": 100, "name": "Presión Aceite", "valor": 50.0, "unidad": "kPa", "mensaje": "fuera de rango"},
                ],
            ),
        ]

        result = handle_flota_status()
        assert result["buses"][0]["spns_fuera_de_rango"] == 2

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_translates_spn_names_in_alertas(self, mock_scan, mock_catalog):
        """Req 10.5: SPN IDs are translated to human-readable names."""
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = [
            _make_telemetria_record(
                autobus="1001",
                alertas_spn=[
                    {"spn_id": 110, "name": "Temp", "valor": 125.0, "unidad": "°C", "mensaje": "alto"},
                ],
            ),
        ]

        result = handle_flota_status()
        alerta = result["buses"][0]["alertas_spn"][0]
        assert alerta["nombre"] == "Temperatura Motor"

    @patch("lambda_function.cargar_catalogo_spn")
    @patch("lambda_function.scan_recent")
    def test_empty_fleet_returns_zero(self, mock_scan, mock_catalog):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_scan.return_value = []

        result = handle_flota_status()
        assert result["total_buses"] == 0
        assert result["buses"] == []


# ---------------------------------------------------------------------------
# 4. /dashboard/alertas-activas (Req 10.2, 11.7)
# ---------------------------------------------------------------------------

class TestAlertasActivas:
    @patch("lambda_function._dynamodb")
    def test_returns_active_alerts(self, mock_ddb):
        mock_table = MagicMock()
        mock_ddb.Table.return_value = mock_table
        mock_table.scan.return_value = {
            "Items": [
                _make_alerta_record(alerta_id="a1", urgencia="ESTA_SEMANA"),
            ],
        }

        result = handle_alertas_activas()
        assert result["total_alertas"] == 1
        assert result["alertas"][0]["alerta_id"] == "a1"

    @patch("lambda_function._dynamodb")
    def test_sorts_by_urgency_inmediata_first(self, mock_ddb):
        """Req 10.2: INMEDIATA alerts appear before ESTA_SEMANA and PROXIMO_SERVICIO."""
        mock_table = MagicMock()
        mock_ddb.Table.return_value = mock_table
        mock_table.scan.return_value = {
            "Items": [
                _make_alerta_record(alerta_id="a1", urgencia="PROXIMO_SERVICIO"),
                _make_alerta_record(alerta_id="a2", urgencia="INMEDIATA"),
                _make_alerta_record(alerta_id="a3", urgencia="ESTA_SEMANA"),
            ],
        }

        result = handle_alertas_activas()
        urgencias = [a["urgencia"] for a in result["alertas"]]
        assert urgencias == ["INMEDIATA", "ESTA_SEMANA", "PROXIMO_SERVICIO"]

    @patch("lambda_function._dynamodb")
    def test_empty_alertas(self, mock_ddb):
        mock_table = MagicMock()
        mock_ddb.Table.return_value = mock_table
        mock_table.scan.return_value = {"Items": []}

        result = handle_alertas_activas()
        assert result["total_alertas"] == 0
        assert result["alertas"] == []

    @patch("lambda_function._dynamodb")
    def test_alert_includes_required_fields(self, mock_ddb):
        mock_table = MagicMock()
        mock_ddb.Table.return_value = mock_table
        mock_table.scan.return_value = {
            "Items": [_make_alerta_record()],
        }

        result = handle_alertas_activas()
        alerta = result["alertas"][0]

        required_fields = [
            "alerta_id", "timestamp", "autobus", "tipo_alerta",
            "nivel_riesgo", "diagnostico", "urgencia", "componentes",
            "numero_referencia", "estado", "agente_origen",
        ]
        for field in required_fields:
            assert field in alerta, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# 5. /dashboard/resumen-consumo (Req 10.3)
# ---------------------------------------------------------------------------

class TestResumenConsumo:
    @patch("lambda_function.scan_recent")
    def test_aggregates_by_route(self, mock_scan):
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", viaje_ruta="RUTA-MEX-PUE", rendimiento_kml=3.5),
            _make_telemetria_record(autobus="1002", viaje_ruta="RUTA-MEX-PUE", rendimiento_kml=2.5),
            _make_telemetria_record(autobus="1003", viaje_ruta="RUTA-MEX-GDL", rendimiento_kml=4.0),
        ]

        result = handle_resumen_consumo()
        assert result["total_rutas"] == 2

    @patch("lambda_function.scan_recent")
    def test_computes_average_rendimiento(self, mock_scan):
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", viaje_ruta="RUTA-MEX-PUE", rendimiento_kml=3.0),
            _make_telemetria_record(autobus="1002", viaje_ruta="RUTA-MEX-PUE", rendimiento_kml=4.0),
        ]

        result = handle_resumen_consumo()
        ruta = next(r for r in result["rutas"] if r["viaje_ruta"] == "RUTA-MEX-PUE")
        assert ruta["rendimiento_promedio_kml"] == 3.5

    @patch("lambda_function.scan_recent")
    def test_counts_estados_per_route(self, mock_scan):
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", viaje_ruta="RUTA-MEX-PUE", estado_consumo="EFICIENTE"),
            _make_telemetria_record(autobus="1002", viaje_ruta="RUTA-MEX-PUE", estado_consumo="ALERTA_MODERADA"),
        ]

        result = handle_resumen_consumo()
        ruta = next(r for r in result["rutas"] if r["viaje_ruta"] == "RUTA-MEX-PUE")
        assert ruta["resumen_estados"]["EFICIENTE"] == 1
        assert ruta["resumen_estados"]["ALERTA_MODERADA"] == 1

    @patch("lambda_function.scan_recent")
    def test_sorts_worst_routes_first(self, mock_scan):
        mock_scan.return_value = [
            _make_telemetria_record(autobus="1001", viaje_ruta="RUTA-GOOD", rendimiento_kml=5.0),
            _make_telemetria_record(autobus="1002", viaje_ruta="RUTA-BAD", rendimiento_kml=1.5),
        ]

        result = handle_resumen_consumo()
        assert result["rutas"][0]["viaje_ruta"] == "RUTA-BAD"

    @patch("lambda_function.scan_recent")
    def test_empty_records(self, mock_scan):
        mock_scan.return_value = []

        result = handle_resumen_consumo()
        assert result["total_rutas"] == 0
        assert result["rutas"] == []

    @patch("lambda_function.scan_recent")
    def test_handles_missing_rendimiento(self, mock_scan):
        record = _make_telemetria_record(autobus="1001", viaje_ruta="RUTA-MEX-PUE")
        del record["rendimiento_kml"]
        mock_scan.return_value = [record]

        result = handle_resumen_consumo()
        ruta = result["rutas"][0]
        assert ruta["rendimiento_promedio_kml"] is None


# ---------------------------------------------------------------------------
# 6. /dashboard/co2-estimado (Req 10.4, C-003)
# ---------------------------------------------------------------------------

class TestCO2Estimado:
    def test_returns_qualitative_descriptions(self):
        result = handle_co2_estimado()

        assert "titulo" in result
        assert "descripcion_general" in result
        assert "areas_de_impacto" in result
        assert len(result["areas_de_impacto"]) > 0

    def test_no_numeric_values_in_response(self):
        """C-003: No specific numeric values in CO2 response."""
        result = handle_co2_estimado()
        result_str = json.dumps(result)

        # Should not contain percentage patterns or currency
        import re
        # Check no patterns like "15%", "$2.8M", "2,400 toneladas"
        assert not re.search(r'\d+%', result_str), "Found numeric percentage in CO2 response"
        assert "$" not in result_str, "Found currency symbol in CO2 response"

    def test_uses_fuzzy_language(self):
        """C-003: Uses fuzzy language like 'reducción notable', 'mejora significativa'."""
        result = handle_co2_estimado()
        result_str = json.dumps(result, ensure_ascii=False)

        fuzzy_terms = ["reducción", "mejora", "optimización", "contribución"]
        found = any(term in result_str.lower() for term in fuzzy_terms)
        assert found, "CO2 response should use fuzzy language terms"

    def test_includes_compliance_note(self):
        result = handle_co2_estimado()
        assert "cumplimiento_normativo" in result
        assert "nota" in result


# ---------------------------------------------------------------------------
# 7. Error handling (Req 10.6)
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_handler_error_returns_500(self):
        mock_handler = MagicMock(side_effect=Exception("DynamoDB timeout"))
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/flota-status": mock_handler}):
            event = _make_event("/dashboard/flota-status")
            result = lambda_handler(event, None)

            assert result["statusCode"] == 500
            body = _parse_api_body(result)
            assert "error" in body
            assert "DynamoDB timeout" in body["error"]

    def test_alertas_error_returns_500(self):
        mock_handler = MagicMock(side_effect=Exception("Connection refused"))
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/alertas-activas": mock_handler}):
            event = _make_event("/dashboard/alertas-activas")
            result = lambda_handler(event, None)

            assert result["statusCode"] == 500
            body = _parse_api_body(result)
            assert "error" in body

    def test_resumen_error_returns_500(self):
        mock_handler = MagicMock(side_effect=Exception("Scan failed"))
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/resumen-consumo": mock_handler}):
            event = _make_event("/dashboard/resumen-consumo")
            result = lambda_handler(event, None)

            assert result["statusCode"] == 500

    def test_error_response_has_cors_headers(self):
        """Error responses should also include CORS headers."""
        event = _make_event("/dashboard/unknown")
        result = lambda_handler(event, None)
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_500_error_has_cors_headers(self):
        mock_handler = MagicMock(side_effect=Exception("fail"))
        with patch.dict("lambda_function._ROUTE_MAP", {"/dashboard/flota-status": mock_handler}):
            event = _make_event("/dashboard/flota-status")
            result = lambda_handler(event, None)
            assert result["headers"]["Access-Control-Allow-Origin"] == "*"
