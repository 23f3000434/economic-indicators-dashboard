import asyncio
import json
import os
import socket
import time
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest
from app.db import Database
from app.gdp import read_panel, validate_series
from app.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import FIXTURES, fixture_response, login


def collect(app, handler=fixture_response):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            collector = app.state.collector
            collector.client = client
            return await collector.collect_once()

    return asyncio.run(run())


def test_pipeline_decimal_canonical_points_idempotency_restart(client, app, settings, clock):
    assert collect(app)
    panel = read_panel(app.state.db, settings, clock())
    assert panel.state == "ready"
    india, world = panel.series
    assert india.points[-1].period_label == "FY 2025–26"
    assert india.points[-1].period_end == "2026-03-31"
    assert world.points[-1].period_label == "CY 2025"
    assert world.points[-1].period_end == "2025-12-31"
    assert panel.summaries[0].change.value == str(
        Decimal(india.points[-1].value) - Decimal(india.points[-2].value)
    )
    assert india.source.published_at is None
    assert collect(app)
    with app.state.db.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 12
    reopened = Database(settings.database)
    reopened.migrate()
    assert read_panel(reopened, settings, clock()).series == panel.series
    assert os.stat(settings.database).st_mode & 0o777 == 0o600
    assert os.stat(settings.database.parent).st_mode & 0o777 == 0o700


@pytest.mark.parametrize(
    "kind", ["timeout", "rejection", "bad_identity", "bad_metadata", "bad_number", "duplicate", "pagination"]
)
def test_invalid_data_and_provider_failure_retain_then_recover(client, app, settings, clock, kind):
    assert collect(app)
    before = read_panel(app.state.db, settings, clock())
    clock.advance(100)

    def broken(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("injected test timeout", request=request)
        if kind == "rejection":
            return httpx.Response(403)
        response = fixture_response(request)
        data = response.json()
        if "/WLD/" in request.url.path:
            if kind == "bad_identity":
                data[1][0]["countryiso3code"] = "USA"
            if kind == "bad_number":
                data[1][0]["value"] = True
            if kind == "duplicate":
                data[1][1]["date"] = data[1][0]["date"]
            if kind == "pagination":
                data[0]["pages"] = 2
        if kind == "bad_metadata" and "/metadata" in request.url.path:
            data = {}
        return httpx.Response(200, json=data)

    assert not collect(app, broken)
    stale = read_panel(app.state.db, settings, clock())
    assert stale.state == "stale"
    assert stale.series == before.series
    assert stale.collection.last_success_at == before.collection.last_success_at
    assert stale.collection.last_attempt_at != before.collection.last_attempt_at
    clock.advance(100)
    assert collect(app)
    recovered = read_panel(app.state.db, settings, clock())
    assert recovered.state == "ready" and recovered.collection.last_error_kind is None
    assert recovered.collection.last_success_at != before.collection.last_success_at


def test_missing_periods_zero_and_retained_provenance(client, app, settings, clock):
    def gaps(request):
        response = fixture_response(request)
        data = response.json()
        if "/country/" in request.url.path and "/metadata" not in request.url.path:
            for row in data[1]:
                if row["date"] in {"2023", "2025"}:
                    row["value"] = None
                if row["date"] == "2024":
                    row["value"] = 0
        return httpx.Response(200, json=data)

    assert collect(app, gaps)
    panel = read_panel(app.state.db, settings, clock())
    assert panel.state == "ready"
    assert panel.series[0].points[-1].value is None
    assert panel.series[0].points[-2].value == "0"
    assert panel.series[0].points[2].value is None
    assert panel.summaries[0].change.value is None
    assert collect(app)
    before = read_panel(app.state.db, settings, clock())
    clock.advance(100)
    assert collect(app, gaps)
    retained = read_panel(app.state.db, settings, clock())
    assert retained.state == "stale"
    assert retained.series[0].points[-1].retained
    assert retained.series[0].points[-1].retrieved_at == before.series[0].points[-1].retrieved_at
    assert retained.series[0].points[-1].value == before.series[0].points[-1].value


def test_empty_unavailable_and_interrupted_recovery(client, app, settings, clock):
    assert read_panel(app.state.db, settings, clock()).state == "empty"

    def fail(request):
        return httpx.Response(503)

    assert not collect(app, fail)
    assert read_panel(app.state.db, settings, clock()).state == "unavailable"
    assert collect(app)
    app.state.collector.begin(2020, 2025)
    assert read_panel(app.state.db, settings, clock()).collection.in_progress
    app.state.collector.recover()
    panel = read_panel(app.state.db, settings, clock())
    assert panel.state == "stale" and panel.collection.last_error_kind == "interrupted"
    assert app.state.collector.begin(2020, 2025) is not None
    assert app.state.collector.begin(2020, 2025) is None  # no overlapping group


def test_database_only_routes_with_outbound_network_disabled(client, app, monkeypatch):
    assert collect(app)
    tokens = login(client).json()

    def blocked(*args, **kwargs):
        raise AssertionError("Outbound networking is disabled for this API read")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)
    h = {"Authorization": "Bearer " + tokens["access_token"]}
    for _ in range(3):
        response = client.get("/api/v1/panels/gdp", headers=h)
        assert response.status_code == 200 and response.json()["state"] == "ready"
    assert client.get("/healthz").status_code == 200


def test_configurable_windows_not_frozen_to_proof(settings):
    rolling = replace(settings, start_year=None, end_year=None, collection_years=12)
    assert rolling.window(2030) == (2018, 2029)
    assert rolling.window(2031) == (2019, 2030)
    with pytest.raises(ValueError):
        replace(settings, start_year=2025, end_year=2025).window(2026)
    body = json.loads((FIXTURES / "world_bank_india.json").read_text())
    for row in body[1]:
        row["date"] = str(int(row["date"]) + 5)
    _, points = validate_series(json.dumps(body).encode(), "IND", 2025, 2030)
    assert "2030" in points


def test_slow_scheduled_upstream_does_not_delay_reads(settings, clock):
    started = __import__("threading").Event()

    async def slow(request):
        started.set()
        await asyncio.sleep(1)
        return fixture_response(request)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(slow))
    app = create_app(replace(settings, collector_enabled=True), clock, upstream)
    with TestClient(app, base_url="http://localhost:8000") as client:
        assert started.wait(timeout=2)
        begin = time.monotonic()
        assert client.get("/healthz").status_code == 200
        app.state.auth.create_user("analyst", "Test-only password 93!")
        tokens = login(client).json()
        response = client.get(
            "/api/v1/panels/gdp", headers={"Authorization": "Bearer " + tokens["access_token"]}
        )
        assert response.status_code == 200
        assert time.monotonic() - begin < 0.8
        assert response.json()["collection"]["in_progress"]
    # Cancellation on shutdown persists an interrupted run, preserving any valid data.
    with app.state.db.connect() as db:
        assert db.execute("SELECT outcome FROM collection_runs").fetchone()[0] == "error"
    asyncio.run(upstream.aclose())


def test_health_storage_failure_and_no_static_database_route(client, app):
    assert client.get("/data/dashboard.sqlite3").status_code == 404
    app.state.db.path.unlink()
    assert client.get("/healthz").status_code == 503


def test_scheduler_collects_without_browser_and_api_restart_keeps_sessions(settings, clock):
    calls = []

    def source(request):
        calls.append(str(request.url))
        return fixture_response(request)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(source))
    scheduled = create_app(replace(settings, collector_enabled=True), clock, upstream)
    with TestClient(scheduled, base_url="http://localhost:8000") as first:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if read_panel(scheduled.state.db, settings, clock()).state == "ready":
                break
            time.sleep(0.02)
        assert read_panel(scheduled.state.db, settings, clock()).state == "ready"
        assert len(calls) == 4
        scheduled.state.auth.create_user("analyst", "Test-only password 93!")
        tokens = login(first).json()
    with TestClient(create_app(settings, clock), base_url="http://localhost:8000") as second:
        response = second.get(
            "/api/v1/panels/gdp", headers={"Authorization": "Bearer " + tokens["access_token"]}
        )
        assert response.status_code == 200 and response.json()["state"] == "ready"
        assert (
            second.get(
                "/api/v1/me", headers={"Authorization": "Bearer " + tokens["access_token"]}
            ).status_code
            == 200
        )
        assert len(calls) == 4
    asyncio.run(upstream.aclose())
