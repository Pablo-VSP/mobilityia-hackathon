"""
Unit tests for tool-consultar-obd Lambda function.

Covers:
  - Parameter parsing from Bedrock AgentCore event format
  - Trend calculation (estable, ascendente, descendente)
  - Anomalous variation detection
  - Brake pad status thresholds
  - Fault retrieval from S3
  - Health summary generation
  - Error handling for missing parameters and service failures
  - Response format compliance with Bedrock AgentCore

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 11.4, 11.6
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
    _calcular_tendencia,
    _detectar_variaciones_anomalas,
    _evaluar_balatas,
    _obtener_fallas_recientes,
    _construir_resumen_salud,
    BRAKE_PAD_THRESHOLD,
    TREND_THRESHOLD,
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


def _make_records_stable(count=20, **kwargs):
    """Build a list of N records with the same SPN values (stable trends)."""
    records = []
    for i in range(count):
        ts = f"2026-01-15T10:{i:02d}:00Z"
        records.append(_make_record(timestamp=ts, **kwargs))
    return records


def _make_records_ascending(count=20):
    """Build records where second half has higher temp_motor than first half (ascending trend)."""
    records = []
    for i in range(count):
        ts = f"2026-01-15T10:{i:02d}:00Z"
        # First half (indices 0-9): temp_motor = 90
        # Second half (indices 10-19): temp_motor = 110
        temp = 90.0 if i < count // 2 else 110.0
        records.append(_make_record(timestamp=ts, temp_motor=temp))
    return records


def _make_records_descending(count=20):
    """Build records where second half has lower temp_motor than first half (descending trend)."""
    records = []
    for i in range(count):
        ts = f"2026-01-15T10:{i:02d}:00Z"
        # First half (indices 0-9): temp_motor = 110
        # Second half (indices 10-19): temp_motor = 90
        temp = 110.0 if i < count // 2 else 90.0
        records.append(_make_record(timestamp=ts, temp_motor=temp))
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
# 3. Trend calculation (Req 6.2)
# ---------------------------------------------------------------------------

class TestCalcularTendencia:
    def test_estable_with_same_values(self):
        values = [100.0] * 20
        assert _calcular_tendencia(values) == "estable"

    def test_ascendente_when_second_half_higher(self):
        # First half avg = 90, second half avg = 110 -> diff > 5%
        values = [90.0] * 10 + [110.0] * 10
        result = _calcular_tendencia(values)
        assert result == "ascendente"

    def test_descendente_when_second_half_lower(self):
        # First half avg = 110, second half avg = 90 -> diff > 5%
        values = [110.0] * 10 + [90.0] * 10
        result = _calcular_tendencia(values)
        assert result == "descendente"

    def test_estable_with_small_difference(self):
        # First half avg = 100, second half avg = 101 -> diff ~1% < 5%
        values = [100.0] * 10 + [101.0] * 10
        result = _calcular_tendencia(values)
        assert result == "estable"

    def test_estable_with_single_value(self):
        assert _calcular_tendencia([100.0]) == "estable"

    def test_estable_with_empty_list(self):
        assert _calcular_tendencia([]) == "estable"

    def test_estable_with_two_equal_values(self):
        assert _calcular_tendencia([50.0, 50.0]) == "estable"

    def test_ascendente_boundary(self):
        # Exactly at 5% boundary: second half is ~5.3% higher
        values = [100.0] * 10 + [106.0] * 10
        result = _calcular_tendencia(values)
        assert result == "ascendente"


# ---------------------------------------------------------------------------
# 4. Brake pad evaluation (Req 6.4)
# ---------------------------------------------------------------------------

class TestEvaluarBalatas:
    def test_all_acceptable(self):
        records = _make_records_stable(
            1,
            balata_del_izq=55.0,
            balata_del_der=50.0,
            balata_tras_izq1=45.0,
            balata_tras_der1=40.0,
            balata_tras_izq2=35.0,
            balata_tras_der2=30.0,
        )
        balatas = _evaluar_balatas(records, SAMPLE_CATALOGO)
        assert len(balatas) == 6
        for b in balatas:
            assert b["estado"] == "aceptable"

    def test_some_require_attention(self):
        records = _make_records_stable(
            1,
            balata_del_izq=55.0,
            balata_del_der=25.0,  # < 30%
            balata_tras_izq1=10.0,  # < 30%
            balata_tras_der1=40.0,
            balata_tras_izq2=5.0,  # < 30%
            balata_tras_der2=30.0,  # exactly 30% -> aceptable
        )
        balatas = _evaluar_balatas(records, SAMPLE_CATALOGO)
        attention_count = sum(1 for b in balatas if b["estado"] == "REQUIERE_ATENCION")
        assert attention_count == 3

    def test_boundary_at_30_percent(self):
        """Exactly 30% should be aceptable."""
        records = _make_records_stable(
            1,
            balata_del_izq=30.0,
            balata_del_der=30.0,
            balata_tras_izq1=30.0,
            balata_tras_der1=30.0,
            balata_tras_izq2=30.0,
            balata_tras_der2=30.0,
        )
        balatas = _evaluar_balatas(records, SAMPLE_CATALOGO)
        for b in balatas:
            assert b["estado"] == "aceptable"

    def test_boundary_below_30_percent(self):
        """29.9% should be REQUIERE_ATENCION."""
        records = _make_records_stable(
            1,
            balata_del_izq=29.9,
            balata_del_der=29.9,
            balata_tras_izq1=29.9,
            balata_tras_der1=29.9,
            balata_tras_izq2=29.9,
            balata_tras_der2=29.9,
        )
        balatas = _evaluar_balatas(records, SAMPLE_CATALOGO)
        for b in balatas:
            assert b["estado"] == "REQUIERE_ATENCION"

    def test_empty_records(self):
        balatas = _evaluar_balatas([], SAMPLE_CATALOGO)
        assert balatas == []

    def test_balata_includes_position_name(self):
        records = _make_records_stable(1)
        balatas = _evaluar_balatas(records, SAMPLE_CATALOGO)
        posiciones = [b["posicion"] for b in balatas]
        assert "Delantero Izquierdo" in posiciones
        assert "Trasero Derecho 2" in posiciones


# ---------------------------------------------------------------------------
# 5. Fault retrieval (Req 6.5)
# ---------------------------------------------------------------------------

class TestObtenerFallasRecientes:
    @patch("lambda_function.read_json_from_s3")
    def test_filters_by_autobus(self, mock_read):
        mock_read.return_value = SAMPLE_FAULTS
        fallas = _obtener_fallas_recientes("1001", "bucket", "key")
        assert len(fallas) == 2
        for f in fallas:
            assert f["codigo"] in ("P0217", "P0520")

    @patch("lambda_function.read_json_from_s3")
    def test_returns_max_5_faults(self, mock_read):
        # Create 10 faults for the same bus
        many_faults = []
        for i in range(10):
            many_faults.append({
                "autobus": "1001",
                "fecha_hora": f"2026-01-{15-i:02d}T09:00:00Z",
                "codigo": f"P0{i:03d}",
                "severidad": i,
                "descripcion": f"Fault {i}",
                "modelo": "9700",
                "marca_comercial": "Volvo",
                "zona": "Zona A",
            })
        mock_read.return_value = many_faults
        fallas = _obtener_fallas_recientes("1001", "bucket", "key")
        assert len(fallas) == 5

    @patch("lambda_function.read_json_from_s3")
    def test_sorted_by_fecha_hora_descending(self, mock_read):
        mock_read.return_value = SAMPLE_FAULTS
        fallas = _obtener_fallas_recientes("1001", "bucket", "key")
        assert fallas[0]["fecha_hora"] >= fallas[1]["fecha_hora"]

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

    @patch("lambda_function.read_json_from_s3")
    def test_fault_includes_required_fields(self, mock_read):
        mock_read.return_value = SAMPLE_FAULTS
        fallas = _obtener_fallas_recientes("1001", "bucket", "key")
        required_fields = {"codigo", "severidad", "descripcion", "modelo", "marca_comercial", "zona"}
        for f in fallas:
            assert required_fields.issubset(set(f.keys()))


# ---------------------------------------------------------------------------
# 6. Health summary (Req 6.6)
# ---------------------------------------------------------------------------

class TestConstruirResumenSalud:
    def test_stable_summary(self):
        senales = [{"nombre": "Temp Motor", "tendencia": "estable"}]
        balatas = [{"posicion": "Del Izq", "estado": "aceptable"}]
        resumen = _construir_resumen_salud(senales, balatas, [], [])
        assert "estables" in resumen.lower() or "aceptable" in resumen.lower()

    def test_ascending_trend_mentioned(self):
        senales = [{"nombre": "Temperatura Motor", "tendencia": "ascendente"}]
        balatas = []
        resumen = _construir_resumen_salud(senales, balatas, [], [])
        assert "ascendente" in resumen.lower()
        assert "Temperatura Motor" in resumen

    def test_brake_attention_mentioned(self):
        senales = []
        balatas = [{"posicion": "Delantero Izquierdo", "estado": "REQUIERE_ATENCION"}]
        resumen = _construir_resumen_salud(senales, balatas, [], [])
        assert "Delantero Izquierdo" in resumen

    def test_anomalies_mentioned(self):
        anomalias = [{"spn_id": 110, "nombre": "Temp Motor"}]
        resumen = _construir_resumen_salud([], [], anomalias, [])
        assert "variaciones anómalas" in resumen.lower() or "anomal" in resumen.lower()

    def test_faults_mentioned(self):
        fallas = [{"codigo": "P0217", "severidad": 3}]
        resumen = _construir_resumen_salud([], [], [], fallas)
        assert "fallas" in resumen.lower()



# ---------------------------------------------------------------------------
# 7. Missing parameters
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
# 8. Full handler integration (Req 6.1-6.6)
# ---------------------------------------------------------------------------

class TestHandlerIntegration:
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_successful_obd_query(self, mock_catalog, mock_query, mock_s3):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records_stable(20)
        mock_s3.return_value = SAMPLE_FAULTS

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "1001"
        assert data["registros_analizados"] == 20
        assert len(data["senales_mantenimiento"]) > 0
        assert len(data["estado_balatas"]) == 6
        assert "resumen_salud" in data
        assert isinstance(data["resumen_salud"], str)

    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_no_records_returns_empty_response(self, mock_catalog, mock_query, mock_s3):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = []

        event = _make_event(autobus="9999")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["autobus"] == "9999"
        assert data["registros_analizados"] == 0
        assert data["senales_mantenimiento"] == []
        assert data["estado_balatas"] == []
        assert "No se encontraron" in data["mensaje"]

    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_trends_detected_in_response(self, mock_catalog, mock_query, mock_s3):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records_ascending(20)
        mock_s3.return_value = []

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        # Find the temp motor signal
        temp_signal = next(
            (s for s in data["senales_mantenimiento"] if s["spn_id"] == 110),
            None,
        )
        assert temp_signal is not None
        assert temp_signal["tendencia"] == "ascendente"

    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_brake_pad_status_in_response(self, mock_catalog, mock_query, mock_s3):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records_stable(
            20,
            balata_del_izq=20.0,  # REQUIERE_ATENCION
            balata_del_der=50.0,  # aceptable
        )
        mock_s3.return_value = []

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        balatas = data["estado_balatas"]
        del_izq = next(b for b in balatas if b["spn_id"] == 1099)
        del_der = next(b for b in balatas if b["spn_id"] == 1100)
        assert del_izq["estado"] == "REQUIERE_ATENCION"
        assert del_der["estado"] == "aceptable"

    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_faults_included_in_response(self, mock_catalog, mock_query, mock_s3):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records_stable(20)
        mock_s3.return_value = SAMPLE_FAULTS

        event = _make_event(autobus="1001")
        result = lambda_handler(event, None)
        data = _parse_response_body(result)

        assert data["total_fallas_recientes"] == 2
        assert len(data["fallas_recientes"]) == 2


# ---------------------------------------------------------------------------
# 9. Error handling
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
# 10. Response format (Req 11.4)
# ---------------------------------------------------------------------------

class TestResponseFormat:
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.query_latest_records")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_response_follows_agent_format(self, mock_catalog, mock_query, mock_s3):
        mock_catalog.return_value = SAMPLE_CATALOGO
        mock_query.return_value = _make_records_stable(20)
        mock_s3.return_value = []

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


# ---------------------------------------------------------------------------
# 11. Anomalous variation detection (Req 6.3)
# ---------------------------------------------------------------------------

class TestDetectarVariacionesAnomalas:
    def test_detects_anomalous_variation(self):
        """When consecutive readings differ by more than 2x delta, flag it."""
        # SPN 110 (Temp Motor) has delta=5.0, so threshold = 10.0
        records = [
            _make_record(timestamp="2026-01-15T10:01:00Z", temp_motor=120.0),
            _make_record(timestamp="2026-01-15T10:00:00Z", temp_motor=95.0),
        ]
        anomalias = _detectar_variaciones_anomalas(records, SAMPLE_CATALOGO)
        temp_anomalias = [a for a in anomalias if a["spn_id"] == 110]
        assert len(temp_anomalias) == 1
        assert temp_anomalias[0]["variacion"] == 25.0

    def test_no_anomaly_within_threshold(self):
        """When variation is within 2x delta, no anomaly."""
        # SPN 110 delta=5.0, threshold=10.0, variation=8.0 < 10.0
        records = [
            _make_record(timestamp="2026-01-15T10:01:00Z", temp_motor=103.0),
            _make_record(timestamp="2026-01-15T10:00:00Z", temp_motor=95.0),
        ]
        anomalias = _detectar_variaciones_anomalas(records, SAMPLE_CATALOGO)
        temp_anomalias = [a for a in anomalias if a["spn_id"] == 110]
        assert len(temp_anomalias) == 0

    def test_stable_records_no_anomalies(self):
        """Stable records should produce no anomalies."""
        records = _make_records_stable(20)
        anomalias = _detectar_variaciones_anomalas(records, SAMPLE_CATALOGO)
        assert len(anomalias) == 0
