#!/usr/bin/env python3
"""Read-only, bounded public-source probes. Python 3.11+; no dependencies.

No retries, browser impersonation, authentication, or market-access bypasses.
HTTP success alone never marks observation coverage as proven.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
INDICATOR = "NY.GDP.MKTP.KD.ZG"
USER_AGENT = "EconomicIndicatorsAssignmentSourceVerification/0.1"
MAX_BYTES = 4 * 1024 * 1024
WB_BASE = "https://api.worldbank.org/v2"
SOURCES = {
    "control": {"url": "https://example.com/", "kind": "control"},
    "world_bank_india": {
        "url": f"{WB_BASE}/country/IND/indicator/{INDICATOR}?format=json&date=2020:2025&per_page=100&footnote=y",
        "kind": "gdp", "country": "IND",
    },
    "world_bank_world": {
        "url": f"{WB_BASE}/country/WLD/indicator/{INDICATOR}?format=json&date=2020:2025&per_page=100&footnote=y",
        "kind": "gdp", "country": "WLD",
    },
    "world_bank_indicator": {"url": f"{WB_BASE}/indicator/{INDICATOR}?format=json", "kind": "metadata"},
    "world_bank_india_metadata": {"url": f"{WB_BASE}/sources/2/country/IND/metadata?format=json", "kind": "metadata"},
    "imf_debt": {
        "url": "https://www.imf.org/external/datamapper/api/v2/GGXWDG_NGDP/IND/USA?periods=2020,2021,2022,2023,2024,2025",
        "kind": "candidate",
    },
    "mospi_cpi": {"url": "https://esankhyiki.mospi.gov.in/", "kind": "candidate"},
    "gst": {
        "url": "https://tutorial.gst.gov.in/downloads/news/final_gst_revenue_report_for_publishing_monthly_sep_2026.pdf",
        "kind": "candidate",
    },
    "trade": {"url": "https://www.commerce.gov.in/ministryofcommerce/node/5158", "kind": "candidate"},
    "cga": {"url": "https://cga.gov.in/writereaddata/MonthAccount/82025/DATA2526.htm", "kind": "candidate"},
    "inflation_target": {"url": "https://egazette.gov.in/WriteReadData/2026/271285.pdf", "kind": "candidate"},
    "nse_indices": {
        "url": "https://www.nseindia.com/api/allIndices", "kind": "gated",
        "reason": "Market collection/display access unresolved with the panel; no quote request sent.",
    },
    "bse_sensex": {
        "url": "https://www.bseindices.com/indices-details/code/16", "kind": "gated",
        "reason": "SENSEX needs an accepted BSE source/access arrangement; no quote request sent.",
    },
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def workspace_path(value: str | Path) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Output must be inside this repository")
    return path


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def parse_gdp(body: bytes, country: str) -> tuple[dict, list[dict]]:
    """Validate the exact WDI series and preserve decimal strings/null gaps."""
    payload = json.loads(body, parse_float=Decimal)
    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError("Expected WDI [pagination, observations], not an error/document")
    metadata, rows = payload
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        raise ValueError("Invalid WDI envelope")
    if metadata.get("page") != 1 or metadata.get("pages") != 1 or metadata.get("total") != len(rows):
        raise ValueError("Incomplete or inconsistent pagination")
    if str(metadata.get("sourceid")) != "2":
        raise ValueError("Expected World Development Indicators source 2")
    updated = metadata.get("lastupdated")
    if not isinstance(updated, str):
        raise ValueError("Missing dataset update date")
    datetime.strptime(updated, "%Y-%m-%d")
    points, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Observation must be an object")
        if row.get("indicator", {}).get("id") != INDICATOR or row.get("countryiso3code") != country:
            raise ValueError("Wrong indicator or geography")
        year = row.get("date")
        if not isinstance(year, str) or not year.isdigit() or not 2020 <= int(year) <= 2025 or year in seen:
            raise ValueError("Invalid, duplicate, or out-of-window annual period")
        seen.add(year)
        value = row.get("value")
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                raise ValueError("Observation must be a JSON number or null")
            value = Decimal(value)
            if not value.is_finite():
                raise ValueError("Non-finite observation")
            value = format(value, "f")
        points.append({"period_key": year, "value": value, "provider_status": row.get("obs_status", ""), "footnote": row.get("footnote", "")})
    if not any(p["value"] is not None for p in points):
        raise ValueError("No usable observations in requested window")
    return {"dataset_updated_on": updated, "indicator_id": INDICATOR, "country": country}, sorted(points, key=lambda p: p["period_key"])


def error_kind(error: Exception) -> str:
    reason = getattr(error, "reason", error)
    if isinstance(reason, socket.gaierror):
        return "dns_error"
    if isinstance(reason, ssl.SSLCertVerificationError):
        return "tls_verification_error"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    return "network_error"


def probe(name: str, output: Path, timeout: float) -> dict:
    definition = SOURCES[name]
    result = {"source": name, "url": definition["url"], "attempted_at": now(), "status": "unverified"}
    if definition["kind"] == "gated":
        return {**result, "status": "blocked", "stage": "access_gate", "detail": definition["reason"], "request_sent": False}
    host = urllib.parse.urlsplit(definition["url"]).hostname
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        result["dns"] = "resolved"
    except socket.gaierror as exc:
        return {**result, "status": "blocked", "stage": "dns", "error_kind": "dns_error", "detail": str(exc), "request_sent": False}
    request = urllib.request.Request(definition["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,application/pdf;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_BYTES + 1)
            result.update({"http_status": response.status, "final_url": response.url, "content_type": response.headers.get("Content-Type", ""), "request_sent": True})
            if len(body) > MAX_BYTES:
                raise ValueError("Response exceeds 4 MiB probe limit")
            result.update({"retrieved_at": now(), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "stage": "http"})
            (output / f"{name}.body").write_bytes(body)
            if definition["kind"] == "gdp":
                metadata, points = parse_gdp(body, definition["country"])
                write_json(output / f"{name}.normalized.json", {**metadata, "points": points})
                result.update({"stage": "observations_validated", "valid_points": sum(p["value"] is not None for p in points), **metadata})
            else:
                result["detail"] = "HTTP response only; collector observation coverage not validated."
    except urllib.error.HTTPError as exc:
        snippet = exc.read(400).decode("utf-8", errors="replace")
        result.update({"status": "blocked", "stage": "http", "http_status": exc.code, "error_kind": "http_rejection", "detail": snippet, "request_sent": True})
    except (urllib.error.URLError, OSError) as exc:
        kind = error_kind(exc)
        result.update({"status": "blocked", "stage": "transport", "error_kind": kind, "detail": str(exc), "request_sent": False if kind in ("dns_error", "tls_verification_error") else None})
    except (ValueError, TypeError, AttributeError) as exc:
        result.update({"stage": "coverage", "error_kind": "payload_or_coverage_error", "detail": str(exc)})
    result["finished_at"] = now()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCES), default=list(SOURCES))
    parser.add_argument("--output-dir", default=".verification/network")
    parser.add_argument("--environment", required=True, help="Caller-supplied execution label, e.g. sandbox or network-enabled")
    parser.add_argument("--timeout", type=float, default=12)
    args = parser.parse_args()
    if args.timeout <= 0 or args.timeout > 30:
        parser.error("timeout must be > 0 and <= 30 seconds")
    output = workspace_path(args.output_dir)
    if output.exists():
        parser.error("Use a new output directory to preserve earlier evidence")
    output.mkdir(parents=True, mode=0o700)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda name: probe(name, output, args.timeout), args.sources))
    report = {"recorded_at": now(), "environment": args.environment, "python": sys.version.split()[0], "scope": "local source probe; not a cloud deployment test", "results": results}
    write_json(output / "report.json", report)
    for result in results:
        print(json.dumps({k: result[k] for k in ("source", "status", "stage", "http_status", "error_kind", "valid_points") if k in result}), flush=True)
    print(f"Report: {output.relative_to(ROOT) / 'report.json'}")


if __name__ == "__main__":
    main()
