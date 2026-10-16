import asyncio
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal, localcontext

import httpx
from app.collection import GroupState
from app.dashboard import Dashboard
from app.gdp import timestamp
from app.indicators import store_batch, summaries
from app.main import create_app
from app.providers.cga import parse, release_url
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, fixture_response, login
from tests.test_cga import body as cga_body
from tests.test_cga import cga_response
from tests.test_debt import debt_response
from tests.test_gst import gst_response
from tests.test_inflation import inflation_response
from tests.test_markets import market_response
from tests.test_trade import trade_response


def provider_response(request):
    host = request.url.host
    if host in {"www.nseindia.com", "api.upstox.com"}:
        return market_response(request)
    if host == "api.worldbank.org":
        return fixture_response(request)
    if host in {"data360files.worldbank.org", "data.imf.org"}:
        return debt_response(request)
    if host in {"cga.gov.in", "cga.nic.in"}:
        return cga_response(request)
    if host in {"www.gst.gov.in", "tutorial.gst.gov.in"}:
        return gst_response(request)
    if host in {"www.commerce.gov.in", "www.pib.gov.in"}:
        return trade_response(request)
    return inflation_response(request)


def test_all_paths_dashboard_offline_reads_and_independent_failure(settings, clock, monkeypatch):
    settings = replace(settings, upstox_analytics_token="test-only-market-token")
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider_response))
    app = create_app(settings, clock, upstream)
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        assert client.get("/api/v1/dashboard").status_code == 401
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        assert asyncio.run(app.state.collector.collect_once())
        for job in app.state.jobs.values():
            assert asyncio.run(job.collect_once())
        data = client.get("/api/v1/dashboard", headers=bearer)
        assert data.status_code == 200 and data.headers["cache-control"] == "no-store"
        payload = data.json()
        Dashboard.model_validate(payload)
        panels = {p["id"]: p for p in payload["panels"]}
        assert set(panels) == {"gdp", "debt", "trade", "gst", "inflation", "expenditure"}
        assert all(p["state"] == "ready" for p in panels.values())
        assert panels["debt"]["availability"] == "implemented"
        assert len(panels["debt"]["series"]) == 2 and len(panels["debt"]["collection"]) == 1
        assert len(payload["ticker"]) == 3 and all(
            t["value"] is not None and t["exchange_timestamp"] is not None and t["state"] == "closed"
            for t in payload["ticker"]
        )
        assert {g["group_id"] for g in payload["collection_groups"]} == {
            "gdp",
            "expenditure",
            "gst",
            "trade",
            "inflation",
            "inflation_policy",
            "debt",
            "market_nse",
            "market_bse",
            "market_status",
        }
        # Every card/derived/table input reference resolves inside its canonical panel.
        for k, p in panels.items():
            if k in {"gdp", "debt"}:
                continue
            lookup = {(s["id"], q["period"]["key"]): q for s in p["series"] for q in s["points"]}
            for summary in p["summaries"]:
                assert (summary["current"]["series_id"], summary["current"]["period_key"]) in lookup
                prior = summary["comparison"]
                if prior:
                    current = lookup[summary["current"]["series_id"], summary["current"]["period_key"]]
                    previous = lookup[prior["series_id"], prior["period_key"]]
                    assert current["period"]["kind"] == previous["period"]["kind"]
                    assert current["definition"]["methodology"] == previous["definition"]["methodology"]
            for point in lookup.values():
                for ref in point["definition"]["inputs"]:
                    assert (ref["series_id"], ref["period_key"]) in lookup
        trade = {
            s["current"]["period_key"]: s
            for s in panels["trade"]["summaries"]
            if s["current"]["series_id"] == "trade_exports"
        }
        assert trade["FY2026-27:09"]["comparison"]["period_key"] == "FY2025-26:09"
        with localcontext() as ctx:
            ctx.prec = 80
            assert (
                Decimal(trade["FY2026-27:09"]["value"]) == (Decimal("259.89") / Decimal("219.30") - 1) * 100
            )
        # A rejected independent provider retains data, other group timestamps/values stay intact.
        app.state.jobs["gst"].client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(403))
        )
        clock.advance(10)
        assert not asyncio.run(app.state.jobs["gst"].collect_once())
        failed = client.get("/api/v1/dashboard", headers=bearer).json()
        updated = {p["id"]: p for p in failed["panels"]}
        assert updated["gst"]["state"] == "stale" and updated["gst"]["series"] == panels["gst"]["series"]
        assert all(updated[k] == panels[k] for k in ("gdp", "trade", "inflation", "expenditure"))

        async def no_http(*args, **kwargs):
            raise AssertionError("API read attempted upstream HTTP")

        def no_socket(*args, **kwargs):
            raise AssertionError("API read attempted networking")

        monkeypatch.setattr(httpx.AsyncClient, "send", no_http)
        monkeypatch.setattr(socket, "create_connection", no_socket)
        assert client.get("/api/v1/dashboard", headers=bearer).json() == failed
        assert client.get("/api/v1/panels/gdp", headers=bearer).json() == panels["gdp"]
        assert client.get("/healthz").status_code == 200
        restart = create_app(settings, clock)
        with TestClient(restart) as again:
            assert again.get("/api/v1/dashboard", headers=bearer).json() == failed


def test_retained_missing_point_preserves_original_provenance_and_recovers(settings, clock):
    app = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(cga_response)))
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        job = app.state.jobs["expenditure"]
        assert asyncio.run(job.collect_once())
        before = client.get("/api/v1/panels/expenditure", headers=bearer).json()
        prior = next(
            p
            for s in before["series"]
            if s["id"] == "expenditure_revenue"
            for p in s["points"]
            if p["period"]["key"] == "FY2026-27:08"
        )
        clock.advance(10)
        run = job.state.begin(timestamp(clock()), 2020, 2026)
        missing = parse(cga_body("cga_aug2026"), release_url(2026, 8), timestamp(clock()), 2026, 8)[
            0
        ].model_copy(update={"value": None})
        store_batch(app.state.db, job.state, run, [missing])
        after = client.get("/api/v1/panels/expenditure", headers=bearer).json()
        retained = next(
            p
            for s in after["series"]
            if s["id"] == "expenditure_revenue"
            for p in s["points"]
            if p["period"]["key"] == "FY2026-27:08"
        )
        assert retained == {**prior, "retained": True}
        assert (
            after["state"] == "stale"
            and after["collection"][0]["last_error_kind"] == "provider_missing_retained"
        )
        assert asyncio.run(job.collect_once())
        assert client.get("/api/v1/panels/expenditure", headers=bearer).json()["state"] == "ready"


def test_frequent_group_retention_does_not_erase_gdp_api_last_success(settings, clock):
    app = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(fixture_response)))
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        assert asyncio.run(app.state.collector.collect_once())
        before = client.get("/api/v1/panels/gdp", headers=bearer).json()
        market = GroupState(app.state.db, clock, "market", "unaccepted_test_provider", interval=1)
        running = GroupState(app.state.db, clock, "other_running", "test_provider").begin(
            timestamp(clock()), 2026, 2026
        )
        for _ in range(205):
            run = market.begin(timestamp(clock()), 2026, 2026)
            market.finish(run, timestamp(clock()), "injected")
        after = client.get("/api/v1/dashboard", headers=bearer).json()
        assert next(p for p in after["panels"] if p["id"] == "gdp") == before
        assert (
            next(g for g in after["collection_groups"] if g["group_id"] == "gdp")["last_success_at"]
            == before["collection"]["last_success_at"]
        )
        with app.state.db.connect() as db:
            assert (
                db.execute("SELECT count(*) FROM collection_runs WHERE group_id='market'").fetchone()[0]
                == 200
            )
            assert (
                db.execute("SELECT outcome FROM collection_runs WHERE id=?", (running,)).fetchone()[0]
                == "running"
            )


def test_slow_provider_does_not_hold_dashboard_or_other_supervisors(settings, clock):
    started = threading.Event()
    release = threading.Event()

    async def upstream(request):
        if request.url.host == "cga.gov.in":
            started.set()
            while not release.is_set():
                await asyncio.sleep(0.01)
        return provider_response(request)

    app = create_app(
        replace(settings, collector_enabled=True, macro_groups=("expenditure",)),
        clock,
        httpx.AsyncClient(transport=httpx.MockTransport(upstream)),
    )
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        assert started.wait(2)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                try:
                    response = pool.submit(client.get, "/api/v1/dashboard", headers=bearer).result(timeout=2)
                finally:
                    release.set()
            assert response.status_code == 200
            cga = next(p for p in response.json()["panels"] if p["id"] == "expenditure")
            assert cga["collection"][0]["in_progress"]
            assert client.get("/healthz").status_code == 200
        finally:
            release.set()


def test_zero_comparison_and_no_cross_window_arithmetic():
    parsed = parse(cga_body("cga_aug2026"), release_url(2026, 8), "2026-10-15T12:00:00Z", 2026, 8)
    prior = parse(cga_body("cga_aug2025"), release_url(2025, 8), "2026-10-15T12:00:00Z", 2025, 8)[0]
    result = next(
        s
        for s in summaries([parsed[0], prior.model_copy(update={"value": "0"})])
        if s.current.series_id == "expenditure_revenue"
    )
    assert result.value is None
