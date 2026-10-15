#!/usr/bin/env python3
"""Verify cached live probes -> validated observations -> SQLite -> panel contract.

This is a disposable source/contract experiment, not an application server.
It makes no network requests; run probe_sources.py first.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from probe_sources import SOURCES, now, parse_gdp, workspace_path, write_json

SERIES = {"world_bank_india": ("gdp_india", "India", "IND"), "world_bank_world": ("gdp_world", "World", "WLD")}
SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
  series_id TEXT NOT NULL,
  period_key TEXT NOT NULL,
  value_decimal TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  dataset_updated_on TEXT,
  source_url TEXT NOT NULL,
  response_sha256 TEXT NOT NULL,
  provider_status TEXT NOT NULL,
  footnote TEXT NOT NULL,
  PRIMARY KEY (series_id, period_key)
);
CREATE TABLE IF NOT EXISTS collection_runs (
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL,
  attempted_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('ok', 'error')),
  error_kind TEXT
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def validate_india_metadata(body: bytes) -> str:
    payload = json.loads(body)
    for source in payload.get("source", []):
        if source.get("id") != "2":
            continue
        for concept in source.get("concept", []):
            for variable in concept.get("variable", []):
                if variable.get("id") == "IND":
                    for item in variable.get("metatype", []):
                        if item.get("id") == "SpecialNotes" and "fiscal year-end: March 31" in item.get("value", ""):
                            return item["value"]
    raise ValueError("India reporting-period metadata missing or changed; do not guess FY labels")


def record_failure(connection: sqlite3.Connection, error: str, at: str) -> None:
    with connection:
        connection.execute("INSERT INTO collection_runs(scope, attempted_at, finished_at, outcome, error_kind) VALUES (?, ?, ?, ?, ?)", ("gdp", at, at, "error", error))


def ingest(connection: sqlite3.Connection, responses: dict[str, dict], at: str, finished_at: str | None = None) -> int:
    """Validate both responses completely before a short atomic write.

    Null points never overwrite valid stored values. A missing latest/previous
    point fails this proof's paired-card coverage check and retains the batch.
    """
    prepared = []
    try:
        countries = {}
        for source, (series_id, _label, country) in SERIES.items():
            response = responses[source]
            metadata, points = parse_gdp(response["body"], country)
            countries[country] = {p["period_key"]: p["value"] for p in points}
            for point in points:
                if point["value"] is not None:
                    prepared.append((series_id, point["period_key"], point["value"], response["retrieved_at"], metadata["dataset_updated_on"], response["url"], hashlib.sha256(response["body"]).hexdigest(), point["provider_status"], point["footnote"]))
        latest = max(set(countries["IND"]) | set(countries["WLD"]))
        previous = str(int(latest) - 1)
        if any(countries[country].get(year) is None for country in countries for year in (latest, previous)):
            raise ValueError("Latest paired GDP observations and annual comparisons must be present")
        with connection:
            connection.executemany("""INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(series_id, period_key) DO UPDATE SET
                value_decimal=excluded.value_decimal, retrieved_at=excluded.retrieved_at,
                dataset_updated_on=excluded.dataset_updated_on, source_url=excluded.source_url,
                response_sha256=excluded.response_sha256, provider_status=excluded.provider_status,
                footnote=excluded.footnote""", prepared)
            connection.execute("INSERT INTO collection_runs(scope, attempted_at, finished_at, outcome) VALUES (?, ?, ?, ?)", ("gdp", at, finished_at or at, "ok"))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        record_failure(connection, "invalid_payload_or_coverage", at)
        raise ValueError(str(exc)) from exc
    return len(prepared)


def panel(connection: sqlite3.Connection) -> dict:
    """Read stored observations only; all visualisations share these points."""
    records = [dict(r) for r in connection.execute("SELECT * FROM observations ORDER BY period_key, series_id")]
    runs = [dict(r) for r in connection.execute("SELECT * FROM collection_runs WHERE scope = ? ORDER BY id", ("gdp",))]
    latest = runs[-1] if runs else None
    success = next((r for r in reversed(runs) if r["outcome"] == "ok"), None)
    state = ("stale" if latest and latest["outcome"] == "error" else "ready") if records else ("unavailable" if latest and latest["outcome"] == "error" else "empty")
    maximum = max((int(r["period_key"]) for r in records), default=None)
    years = [str(y) for y in range(maximum - 4, maximum + 1)] if maximum else []
    series, summaries = [], []
    for source, (series_id, label, country) in SERIES.items():
        lookup = {r["period_key"]: r for r in records if r["series_id"] == series_id}
        points = []
        for year in years:
            fiscal = country == "IND"
            points.append({
                "period_key": year,
                "period_label": f"FY {year}–{str(int(year) + 1)[-2:]}" if fiscal else f"CY {year}",
                "period_start": f"{year}-04-01" if fiscal else f"{year}-01-01",
                "period_end": f"{int(year) + 1}-03-31" if fiscal else f"{year}-12-31",
                "value": lookup[year]["value_decimal"] if year in lookup else None,
                "estimate_status": "unspecified",
                "provider_status": lookup[year]["provider_status"] if year in lookup else "",
                "footnote": lookup[year]["footnote"] if year in lookup else "",
            })
        current = str(maximum) if maximum else None
        previous = str(maximum - 1) if maximum else None
        left, right = lookup.get(current), lookup.get(previous)
        delta = format(Decimal(left["value_decimal"]) - Decimal(right["value_decimal"]), "f") if left and right else None
        latest_record = lookup[max(lookup)] if lookup else None
        series.append({
            "id": series_id, "label": label, "unit": "percent",
            "reporting_basis": "fiscal_year_apr_mar" if country == "IND" else "calendar_year_aggregate",
            "points": points,
            "source": {"id": "world_bank_wdi", "url": SOURCES[source]["url"], "published_at": None, "dataset_updated_on": latest_record["dataset_updated_on"] if latest_record else None, "retrieved_at": latest_record["retrieved_at"] if latest_record else None},
        })
        summaries.append({"series_id": series_id, "current_period_key": current, "comparison_period_key": previous, "change": {"kind": "percentage_points", "value": delta}})
    return {
        "schema_version": "1", "id": "gdp", "state": state,
        "collection": {"last_attempt_at": latest["attempted_at"] if latest else None, "last_success_at": success["finished_at"] if success else None, "last_error_kind": latest["error_kind"] if latest else None},
        "series": series, "summaries": summaries,
        "notes": ["India uses April–March fiscal years; World is the published annual aggregate. They are not identical reporting windows.", "WDI lastupdated is dataset metadata, not an observation publication date. Blank provider status does not establish finality."],
    }


def load_responses(directory: Path) -> tuple[dict, dict]:
    report = json.loads((directory / "report.json").read_text())
    results = {r["source"]: r for r in report["results"]}
    responses = {}
    for name in (*SERIES, "world_bank_india_metadata", "world_bank_indicator"):
        record = results[name]
        if record.get("http_status") != 200 or "sha256" not in record:
            raise ValueError(f"No successful live HTTP response recorded for {name}")
        body = (directory / f"{name}.body").read_bytes()
        if hashlib.sha256(body).hexdigest() != record["sha256"]:
            raise ValueError(f"Probe/body digest mismatch for {name}")
        responses[name] = {"body": body, "attempted_at": record["attempted_at"], "retrieved_at": record["retrieved_at"], "url": record["url"]}
    validate_india_metadata(responses["world_bank_india_metadata"]["body"])
    indicator = json.loads(responses["world_bank_indicator"]["body"])[1][0]
    if indicator.get("id") != "NY.GDP.MKTP.KD.ZG" or indicator.get("name") != "GDP growth (annual %)":
        raise ValueError("Indicator metadata changed")
    return responses, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=".verification/network")
    parser.add_argument("--output-dir", default=".verification/gdp-proof")
    args = parser.parse_args()
    input_dir, output = workspace_path(args.input_dir), workspace_path(args.output_dir)
    if output.exists():
        parser.error("Use a new output directory to preserve earlier evidence")
    responses, report = load_responses(input_dir)
    output.mkdir(parents=True, mode=0o700)
    database = output / "proof.sqlite3"
    connection = connect(database)
    os.chmod(database, 0o600)
    attempted_at = min(responses[name]["attempted_at"] for name in SERIES)
    inserted = ingest(connection, responses, attempted_at, finished_at=now())
    before = panel(connection)
    ingest(connection, responses, attempted_at, finished_at=now())
    count = connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    assert count == inserted, "Duplicate ingestion must not duplicate observations"
    connection.close()
    connection = connect(database)
    assert panel(connection)["series"] == before["series"], "Readback after reopen must match"
    ready = panel(connection)
    record_failure(connection, "simulated_timeout", now())
    stale = panel(connection)
    assert stale["state"] == "stale" and stale["series"] == ready["series"]
    assert stale["collection"]["last_success_at"] == ready["collection"]["last_success_at"]
    connection.close()
    write_json(output / "panel.ready.json", ready)
    write_json(output / "panel.stale.json", stale)
    evidence = {
        "recorded_at": now(),
        "status": "proven",
        "scope": "public HTTP responses -> validation -> private local SQLite -> stored-data panel contract; no API server/UI/cloud deployment yet",
        "probe_environment": report["environment"],
        "observations_stored": count,
        "idempotent_reingestion": True,
        "replayed_same_http_batch_not_refetched": True,
        "reopen_readback_matches": True,
        "injected_failure_preserves_observations": True,
        "injected_failure_is_not_a_provider_incident": True,
        "sources": {
            name: {
                "url": responses[name]["url"],
                "sha256": hashlib.sha256(responses[name]["body"]).hexdigest(),
                "retrieved_at": responses[name]["retrieved_at"],
            }
            for name in responses
        },
    }
    write_json(output / "proof.json", evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
