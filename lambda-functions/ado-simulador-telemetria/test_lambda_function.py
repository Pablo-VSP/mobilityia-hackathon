"""
Unit tests for ado-simulador-telemetria Lambda function.

Covers:
  - clasificar_consumo: all classification thresholds and SIN_DATOS fallback
  - Stateless offset calculation cycling behavior
  - Error handling when SPN catalog fails to load
  - Error handling when S3 telemetry is unavailable for a bus

Requirements: 2.5, 2.6, 2.9, 2.10
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Bootstrap: add layer path and mock boto3 before any ado_common import.
# Several layer modules create boto3 clients/resources at module level,
# and dynamo_utils imports from boto3.dynamodb.conditions.
# ---------------------------------------------------------------------------

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "layers", "ado-common", "python"),
)

# Build a mock boto3 hierarchy that satisfies all module-level usages:
#   boto3.client("s3")
#   boto3.resource("dynamodb")
#   from boto3.dynamodb.conditions import Key, Attr
_mock_boto3 = MagicMock()
_mock_dynamodb = MagicMock()
_mock_conditions = MagicMock()

# Provide Key and Attr as callable mocks
_mock_conditions.Key = MagicMock()
_mock_conditions.Attr = MagicMock()

# Wire up the hierarchy
_mock_dynamodb.conditions = _mock_conditions
_mock_boto3.dynamodb = _mock_dynamodb

# Inject into sys.modules so `import boto3` and `from boto3.dynamodb.conditions`
# both resolve to our mocks.
sys.modules["boto3"] = _mock_boto3
sys.modules["boto3.dynamodb"] = _mock_dynamodb
sys.modules["boto3.dynamodb.conditions"] = _mock_conditions

# Also add the Lambda directory to sys.path so `lambda_function` can be imported
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__)),
)

# Now safe to import the module under test
from lambda_function import clasificar_consumo, lambda_handler  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spn_entry(valor):
    """Build a minimal spn_valores entry."""
    return {"valor": valor}


# ---------------------------------------------------------------------------
# 1. clasificar_consumo — SPN 185 thresholds (Req 2.5)
# ---------------------------------------------------------------------------

class TestClasificarConsumoSPN185:
    """SPN 185 (Rendimiento km/L) is the primary metric."""

    def test_eficiente_at_boundary(self):
        """SPN 185 == 3.0 → EFICIENTE (boundary)."""
        spn_valores = {"185": _spn_entry(3.0)}
        assert clasificar_consumo(spn_valores) == "EFICIENTE"

    def test_eficiente_above_boundary(self):
        """SPN 185 > 3.0 → EFICIENTE."""
        spn_valores = {"185": _spn_entry(4.5)}
        assert clasificar_consumo(spn_valores) == "EFICIENTE"

    def test_alerta_moderada_at_lower_boundary(self):
        """SPN 185 == 2.0 → ALERTA_MODERADA (boundary)."""
        spn_valores = {"185": _spn_entry(2.0)}
        assert clasificar_consumo(spn_valores) == "ALERTA_MODERADA"

    def test_alerta_moderada_mid_range(self):
        """SPN 185 == 2.5 → ALERTA_MODERADA."""
        spn_valores = {"185": _spn_entry(2.5)}
        assert clasificar_consumo(spn_valores) == "ALERTA_MODERADA"

    def test_alerta_significativa_below_2(self):
        """SPN 185 < 2.0 → ALERTA_SIGNIFICATIVA."""
        spn_valores = {"185": _spn_entry(1.9)}
        assert clasificar_consumo(spn_valores) == "ALERTA_SIGNIFICATIVA"

    def test_alerta_significativa_zero(self):
        """SPN 185 == 0 → ALERTA_SIGNIFICATIVA."""
        spn_valores = {"185": _spn_entry(0.0)}
        assert clasificar_consumo(spn_valores) == "ALERTA_SIGNIFICATIVA"


# ---------------------------------------------------------------------------
# 2. clasificar_consumo — SPN 183 fallback thresholds (Req 2.5)
# ---------------------------------------------------------------------------

class TestClasificarConsumoSPN183Fallback:
    """SPN 183 (Tasa combustible L/h) is used when SPN 185 is absent."""

    def test_eficiente_at_boundary(self):
        """SPN 183 == 30 → EFICIENTE (boundary)."""
        spn_valores = {"183": _spn_entry(30.0)}
        assert clasificar_consumo(spn_valores) == "EFICIENTE"

    def test_eficiente_below_boundary(self):
        """SPN 183 < 30 → EFICIENTE."""
        spn_valores = {"183": _spn_entry(20.0)}
        assert clasificar_consumo(spn_valores) == "EFICIENTE"

    def test_alerta_moderada_above_30(self):
        """SPN 183 between 30 and 50 → ALERTA_MODERADA."""
        spn_valores = {"183": _spn_entry(40.0)}
        assert clasificar_consumo(spn_valores) == "ALERTA_MODERADA"

    def test_alerta_moderada_at_upper_boundary(self):
        """SPN 183 == 50 → ALERTA_MODERADA (boundary)."""
        spn_valores = {"183": _spn_entry(50.0)}
        assert clasificar_consumo(spn_valores) == "ALERTA_MODERADA"

    def test_alerta_significativa_above_50(self):
        """SPN 183 > 50 → ALERTA_SIGNIFICATIVA."""
        spn_valores = {"183": _spn_entry(55.0)}
        assert clasificar_consumo(spn_valores) == "ALERTA_SIGNIFICATIVA"


# ---------------------------------------------------------------------------
# 3. clasificar_consumo — SIN_DATOS and priority (Req 2.5)
# ---------------------------------------------------------------------------

class TestClasificarConsumoEdgeCases:
    """Edge cases: neither SPN present, and SPN 185 priority over 183."""

    def test_sin_datos_empty_dict(self):
        """Empty spn_valores → SIN_DATOS."""
        assert clasificar_consumo({}) == "SIN_DATOS"

    def test_sin_datos_unrelated_spns(self):
        """Only unrelated SPNs present → SIN_DATOS."""
        spn_valores = {"84": _spn_entry(80.0), "190": _spn_entry(1500)}
        assert clasificar_consumo(spn_valores) == "SIN_DATOS"

    def test_spn_185_takes_priority_over_183(self):
        """When both SPN 185 and 183 are present, SPN 185 wins."""
        # SPN 185 = 3.5 → EFICIENTE, SPN 183 = 55 → would be ALERTA_SIGNIFICATIVA
        spn_valores = {
            "185": _spn_entry(3.5),
            "183": _spn_entry(55.0),
        }
        assert clasificar_consumo(spn_valores) == "EFICIENTE"

    def test_spn_185_priority_alerta(self):
        """SPN 185 classifies as ALERTA even when SPN 183 would be EFICIENTE."""
        # SPN 185 = 1.5 → ALERTA_SIGNIFICATIVA, SPN 183 = 20 → would be EFICIENTE
        spn_valores = {
            "185": _spn_entry(1.5),
            "183": _spn_entry(20.0),
        }
        assert clasificar_consumo(spn_valores) == "ALERTA_SIGNIFICATIVA"

    def test_spn_185_none_valor_falls_through_to_183(self):
        """SPN 185 entry with None valor falls through to SPN 183."""
        spn_valores = {
            "185": {"valor": None},
            "183": _spn_entry(25.0),
        }
        assert clasificar_consumo(spn_valores) == "EFICIENTE"


# ---------------------------------------------------------------------------
# 4. Stateless offset calculation (Req 2.6)
# ---------------------------------------------------------------------------

class TestStatelessOffset:
    """The offset formula (int(time.time()) // 10 + bus_index) % total_records
    should produce deterministic cycling behavior."""

    def test_offset_cycles_through_records(self):
        """Different bus_index values produce different offsets."""
        total_records = 100
        t = 1700000000  # fixed timestamp
        offsets = set()
        for bus_index in range(20):
            offset = (t // 10 + bus_index) % total_records
            offsets.add(offset)
        # All 20 buses should get distinct offsets (since 20 < 100)
        assert len(offsets) == 20

    def test_offset_wraps_around(self):
        """Offset wraps around when it exceeds total_records."""
        total_records = 10
        t = 1700000000
        offset = (t // 10 + 15) % total_records
        assert 0 <= offset < total_records

    def test_offset_advances_with_time(self):
        """Offset advances by 1 every 10 seconds for the same bus."""
        total_records = 100
        bus_index = 0
        t1 = 1700000000
        t2 = t1 + 10  # 10 seconds later
        offset1 = (t1 // 10 + bus_index) % total_records
        offset2 = (t2 // 10 + bus_index) % total_records
        assert (offset2 - offset1) % total_records == 1

    def test_offset_deterministic(self):
        """Same time and bus_index always produce the same offset."""
        total_records = 50
        t = 1700000000
        bus_index = 5
        offset_a = (t // 10 + bus_index) % total_records
        offset_b = (t // 10 + bus_index) % total_records
        assert offset_a == offset_b


# ---------------------------------------------------------------------------
# 5. Error handling — catalog fails to load (Req 2.9)
# ---------------------------------------------------------------------------

class TestCatalogLoadFailure:
    """When the SPN catalog fails to load, the handler should skip the
    invocation without crashing."""

    @patch("lambda_function.cargar_catalogo_spn")
    def test_catalog_failure_returns_skipped(self, mock_catalog):
        """Handler returns skipped status when catalog load raises."""
        mock_catalog.side_effect = Exception("S3 access denied")

        result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert "catalog" in body["reason"].lower() or "SPN" in body["reason"]

    @patch("lambda_function.cargar_catalogo_spn")
    def test_catalog_failure_does_not_crash(self, mock_catalog):
        """Handler does not raise an exception when catalog fails."""
        mock_catalog.side_effect = RuntimeError("Network timeout")

        # Should not raise
        result = lambda_handler({}, None)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 6. Error handling — S3 telemetry unavailable for a bus (Req 2.10)
# ---------------------------------------------------------------------------

class TestS3TelemetryUnavailable:
    """When S3 telemetry is unavailable for a specific bus, the handler
    should skip that bus and continue processing the remaining buses."""

    @patch("lambda_function.batch_write_items")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.list_objects")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_skips_bus_on_s3_error_continues_others(
        self, mock_catalog, mock_list, mock_read_json, mock_batch_write
    ):
        """If reading telemetry for one bus fails, others still get processed."""
        # Setup catalog with SPNs needed for pivot
        mock_catalog.return_value = {
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
        }

        # Two telemetry files available
        mock_list.return_value = [
            "telemetria-simulada/file1.json",
            "telemetria-simulada/file2.json",
        ]

        sample_record = {
            "autobus": "1001",
            "viaje_id": 100,
            "operador_cve": "OP1",
            "operador_desc": "Operador 1",
            "viaje_ruta": "RUTA-MEX-PUE",
            "viaje_ruta_origen": "México",
            "viaje_ruta_destino": "Puebla",
            "evento_latitud": 19.43,
            "evento_longitud": -99.13,
            "evento_spn": 84,
            "evento_valor": 80.0,
            "evento_fecha_hora": "2026-01-01T12:00:00Z",
        }

        call_count = [0]

        def side_effect_read(bucket, key):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (for bus 0) — raise error
                raise Exception("S3 GetObject failed")
            # Subsequent calls return valid data
            return [sample_record] * 10

        mock_read_json.side_effect = side_effect_read
        mock_batch_write.return_value = {"items_written": 0}

        # Run with NUM_BUSES=2
        with patch("lambda_function.NUM_BUSES", 2):
            result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        # At least one bus should have been skipped
        assert body["buses_omitidos"] >= 1
        # The handler should still succeed
        assert body["status"] == "success"

    @patch("lambda_function.batch_write_items")
    @patch("lambda_function.read_json_from_s3")
    @patch("lambda_function.list_objects")
    @patch("lambda_function.cargar_catalogo_spn")
    def test_all_buses_fail_gracefully(
        self, mock_catalog, mock_list, mock_read_json, mock_batch_write
    ):
        """If all buses fail, handler still returns success with 0 processed."""
        mock_catalog.return_value = {
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
        }
        mock_list.return_value = ["telemetria-simulada/file1.json"]
        mock_read_json.side_effect = Exception("S3 bucket not found")
        mock_batch_write.return_value = {"items_written": 0}

        with patch("lambda_function.NUM_BUSES", 3):
            result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["buses_procesados"] == 0
        assert body["buses_omitidos"] == 3
