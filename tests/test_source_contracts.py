"""Offline checks for the source/storage contract. No application server required."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import socket
import ssl
import sys
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from probe_sources import SOURCES, error_kind, parse_gdp, probe, workspace_path
from prove_gdp import connect, ingest, panel, record_failure, validate_india_metadata

FIXTURES = ROOT / "tests" / "fixtures"
AT = "2026-10-15T13:31:57Z"


def responses() -> dict:
    return {name: {"body": (FIXTURES / f"{name}.json").read_bytes(), "url": SOURCES[name]["url"], "retrieved_at": AT} for name in ("world_bank_india", "world_bank_world")}


def altered(data: dict, mutate) -> dict:
    data = deepcopy(data)
    payload = json.loads(data["world_bank_india"]["body"])
    mutate(payload)
    data["world_bank_india"]["body"] = json.dumps(payload).encode()
    return data


class SourceContracts(unittest.TestCase):
    def setUp(self):
        self.connection = connect(":memory:")
        self.addCleanup(self.connection.close)
        self.data = responses()

    def test_exact_decimal_and_reporting_metadata(self):
        metadata, points = parse_gdp(self.data["world_bank_india"]["body"], "IND")
        self.assertEqual(metadata["dataset_updated_on"], "2026-10-08")
        self.assertEqual(points[-1]["value"], "7.56666179284244")
        note = validate_india_metadata((FIXTURES / "world_bank_india_metadata.json").read_bytes())
        self.assertIn("March 31", note)

    def test_negative_growth_is_valid(self):
        _metadata, points = parse_gdp(self.data["world_bank_india"]["body"], "IND")
        self.assertLess(Decimal(points[0]["value"]), 0)

    def test_wrong_indicator_and_geography_are_rejected(self):
        for field in ("indicator", "countryiso3code"):
            with self.subTest(field=field):
                changed = altered(self.data, lambda p: p[1][0].update({field: {"id": "wrong"} if field == "indicator" else "USA"}))
                with self.assertRaises(ValueError):
                    ingest(self.connection, changed, AT)
                self.assertEqual(panel(self.connection)["state"], "unavailable")

    def test_nonfinite_boolean_and_text_values_are_rejected(self):
        for value in (float("nan"), float("inf"), True, "7.5"):
            with self.subTest(value=value):
                changed = altered(self.data, lambda p: p[1][0].update(value=value))
                with self.assertRaises(ValueError):
                    ingest(self.connection, changed, AT)

    def test_duplicate_period_and_incomplete_pagination_are_rejected(self):
        changes = [lambda p: p[1][0].update(date=p[1][1]["date"]), lambda p: p[0].update(pages=2), lambda p: p[1].__setitem__(0, None)]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    ingest(self.connection, altered(self.data, change), AT)

    def test_duplicate_ingestion_is_idempotent(self):
        ingest(self.connection, self.data, AT)
        ingest(self.connection, self.data, AT)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM observations").fetchone()[0], 12)

    def test_invalid_batch_is_atomic_and_marks_retained_data_stale(self):
        ingest(self.connection, self.data, AT)
        before = panel(self.connection)
        changed = altered(self.data, lambda p: p[1][1].update(value="bad"))
        with self.assertRaises(ValueError):
            ingest(self.connection, changed, "2026-10-16T06:30:00Z")
        after = panel(self.connection)
        self.assertEqual(after["state"], "stale")
        self.assertEqual(before["series"], after["series"])
        self.assertEqual(before["collection"]["last_success_at"], after["collection"]["last_success_at"])

    def test_missing_latest_observation_does_not_overwrite_valid_value(self):
        ingest(self.connection, self.data, AT)
        before = panel(self.connection)["series"]
        with self.assertRaises(ValueError):
            ingest(self.connection, altered(self.data, lambda p: p[1][0].update(value=None)), AT)
        self.assertEqual(panel(self.connection)["series"], before)

    def test_missing_historical_point_stays_null_and_is_not_zero(self):
        ingest(self.connection, altered(self.data, lambda p: p[1][4].update(value=None)), AT)
        result = panel(self.connection)
        self.assertIsNone(result["series"][0]["points"][0]["value"])

    def test_read_contract_does_not_call_upstream(self):
        ingest(self.connection, self.data, AT)
        with patch("urllib.request.urlopen", side_effect=AssertionError("Database reads must not fetch upstream")):
            result = panel(self.connection)
        self.assertEqual(result["state"], "ready")
        india = result["series"][0]["points"][-1]
        self.assertEqual((india["period_start"], india["period_end"]), ("2025-04-01", "2026-03-31"))
        self.assertEqual(result["summaries"][0]["change"]["value"], "0.46738286107726")
        self.assertIsNone(result["series"][0]["source"]["published_at"])

    def test_empty_and_failed_initial_collection_are_distinct(self):
        self.assertEqual(panel(self.connection)["state"], "empty")
        record_failure(self.connection, "timeout", AT)
        self.assertEqual(panel(self.connection)["state"], "unavailable")

    def test_runtime_errors_are_distinguished(self):
        self.assertEqual(error_kind(URLError(socket.gaierror(8, "DNS unavailable"))), "dns_error")
        self.assertEqual(error_kind(URLError(ssl.SSLCertVerificationError(1, "issuer unavailable"))), "tls_verification_error")
        self.assertEqual(error_kind(URLError(TimeoutError())), "timeout")

    def test_tls_failure_does_not_claim_an_http_request_was_sent(self):
        with patch("socket.getaddrinfo", return_value=[]), patch("urllib.request.urlopen", side_effect=URLError(ssl.SSLCertVerificationError(1, "issuer unavailable"))):
            result = probe("inflation_target", ROOT / ".verification", 12)
        self.assertEqual(result["error_kind"], "tls_verification_error")
        self.assertIs(result["request_sent"], False)
        self.assertNotIn("http_status", result)

    def test_outputs_cannot_escape_workspace(self):
        with self.assertRaises(ValueError):
            workspace_path(ROOT.parent / "another-project")


if __name__ == "__main__":
    unittest.main()
