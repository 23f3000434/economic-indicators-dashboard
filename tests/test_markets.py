import asyncio
import gzip
import json
import socket
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from app.gdp import timestamp
from app.main import create_app
from app.markets import (
    BSE_URL,
    NSE_URL,
    MarketBSE,
    QuoteBatch,
    parse_bse,
    parse_nse,
    read_markets,
    store_quotes,
)
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, login

FIXTURES = Path(__file__).parent / "fixtures/providers/markets"


def body(name):
    return gzip.decompress((FIXTURES / (name + ".gz")).read_bytes())


def market_response(request):
    if str(request.url) == NSE_URL:
        assert "authorization" not in request.headers
        name = "nse_quotes"
    else:
        assert request.url.host == "api.upstox.com"
        assert request.headers.get("authorization") == "Bearer test-only-market-token"
        name = (
            "upstox_sensex"
            if str(request.url) == BSE_URL
            else "upstox_timings"
            if "/market/timings/" in request.url.path
            else "upstox_status_" + request.url.path.rsplit("/", 1)[-1].lower()
        )
    return httpx.Response(200, content=body(name))


def market_settings(settings):
    return replace(settings, upstox_analytics_token="test-only-market-token")


def test_actual_quote_definitions_time_and_previous_close(clock):
    nse = parse_nse(body("nse_quotes"), timestamp(clock()))
    sensex = parse_bse(body("upstox_sensex"), timestamp(clock()))[0]
    assert [q.value for q in nse] == ["55810.5", "30719.8"]
    assert [q.previous_close for q in nse] == ["55316", "30171"]
    assert nse[0].exchange_timestamp == "2026-10-15T10:00:00Z"
    assert nse[0].exchange_timestamp_precision == "minute"
    assert sensex.value == "74315.61" and sensex.previous_close == "72781.89"
    assert sensex.previous_close_basis == "last_price_minus_net_change"
    assert sensex.exchange_timestamp == "2026-10-15T10:29:59.981000Z"
    assert sensex.provider_timestamp != sensex.exchange_timestamp


@pytest.mark.parametrize(
    "field,value", [("last", -1), ("previousClose", 0), ("variation", 999), ("percentChange", 50)]
)
def test_invalid_nse_values_do_not_pass(field, value, clock):
    raw = json.loads(body("nse_quotes"))
    row = next(r for r in raw["data"] if r["index"] == "NIFTY BANK")
    row[field] = value
    with pytest.raises(ValueError):
        parse_nse(json.dumps(raw).encode(), timestamp(clock()))


def test_quote_identity_future_time_and_credential_destination(settings, clock):
    raw = json.loads(body("upstox_sensex"))
    raw["data"]["BSE_INDEX:SENSEX"]["instrument_token"] = "BSE_INDEX|SENSEX50"
    with pytest.raises(ValueError, match="instrument"):
        parse_bse(json.dumps(raw).encode(), timestamp(clock()))
    with pytest.raises(ValueError, match="Future"):
        parse_bse(body("upstox_sensex"), "2026-10-01T00:00:00Z")
    adapter = MarketBSE(market_settings(settings))
    for url in [
        NSE_URL,
        "https://api.upstox.com.evil.example/",
        "http://api.upstox.com/",
        "https://api.upstox.com:444/",
    ]:
        with pytest.raises(ValueError, match="destination"):
            adapter.request_headers(url)
    assert "test-only-market-token" not in repr(adapter.settings)


def test_sources_store_protected_reads_arithmetic_failures_restart_and_recovery(settings, clock, monkeypatch):
    config = market_settings(settings)
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(market_response))
    app = create_app(config, clock, upstream)
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        assert client.get("/api/v1/ticker").status_code == 401
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        for g in ("market_nse", "market_bse", "market_status"):
            assert asyncio.run(app.state.jobs[g].collect_once())
        original = client.get("/api/v1/ticker", headers=bearer).json()
        assert all(q["state"] == "closed" for q in original["ticker"])
        for q in original["ticker"]:
            assert Decimal(q["change_points"]) == Decimal(q["value"]) - Decimal(q["previous_close"])
            assert abs(
                Decimal(q["change_percent"]) - (Decimal(q["value"]) / Decimal(q["previous_close"]) - 1) * 100
            ) < Decimal("1e-20")
        assert "test-only-market-token" not in json.dumps(original)
        job = app.state.jobs["market_nse"]
        job.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
        clock.advance(1)
        assert not asyncio.run(job.collect_once())
        failed = client.get("/api/v1/ticker", headers=bearer).json()
        assert failed["ticker"][0] == original["ticker"][0]  # BSE quote/status unaffected.
        for q, prior in zip(failed["ticker"][1:], original["ticker"][1:]):
            assert q["state"] == "stale" and q["retained"]
            assert all(
                q[f] == prior[f]
                for f in ["value", "exchange_timestamp", "retrieved_at", "source_url", "response_sha256"]
            )
        job.client = upstream
        assert asyncio.run(job.collect_once())
        assert all(
            q["state"] == "closed" for q in client.get("/api/v1/ticker", headers=bearer).json()["ticker"]
        )
        assert asyncio.run(job.collect_once())
        with app.state.db.connect() as db:
            assert db.execute("SELECT count(*) FROM market_quotes").fetchone()[0] == 3

        async def disabled(*args, **kwargs):
            raise AssertionError("DB-only read attempted HTTP")

        monkeypatch.setattr(httpx.AsyncClient, "send", disabled)
        monkeypatch.setattr(
            socket, "create_connection", lambda *a, **k: pytest.fail("DB-only read attempted socket")
        )
        good = client.get("/api/v1/ticker", headers=bearer).json()
        assert client.get("/api/v1/dashboard", headers=bearer).json()["ticker"] == good["ticker"]
        restarted = create_app(config, clock)
        with TestClient(restarted) as again:
            assert again.get("/api/v1/ticker", headers=bearer).json() == good


def test_omission_retention_and_regressing_timestamps(settings, clock):
    app = create_app(market_settings(settings), clock)
    app.state.db.migrate()
    job = app.state.jobs["market_nse"]
    points = parse_nse(body("nse_quotes"), timestamp(clock()))
    run = job.state.begin(timestamp(clock()), 2026, 2026)
    store_quotes(app.state.db, job.state, run, points)
    run = job.state.begin(timestamp(clock()), 2026, 2026)
    store_quotes(app.state.db, job.state, run, QuoteBatch(points[:1], points.expected))
    with app.state.db.connect() as db:
        old = db.execute(
            "SELECT payload_json,retained FROM market_quotes WHERE instrument_id='nifty_it'"
        ).fetchone()
        assert old[1] == 1 and json.loads(old[0])["response_sha256"] == points[1].response_sha256
    older = points[0].model_copy(update={"exchange_timestamp": "2026-10-14T10:00:00Z"})
    run = job.state.begin(timestamp(clock()), 2026, 2026)
    with pytest.raises(ValueError, match="Regressing"):
        store_quotes(app.state.db, job.state, run, QuoteBatch([older], {"nifty_bank"}))


def test_live_delayed_closed_and_status_expiry_are_distinct(settings, clock):
    config = market_settings(settings)
    app = create_app(config, clock, httpx.AsyncClient(transport=httpx.MockTransport(market_response)))
    app.state.db.migrate()
    for group in ("market_nse", "market_bse", "market_status"):
        assert asyncio.run(app.state.jobs[group].collect_once())
    closed, _ = read_markets(app.state.db, app.state.jobs, clock())
    assert all(q.state == "closed" for q in closed)  # Quote is hours old; verified market is closed.
    clock.advance(61)
    expired, _ = read_markets(app.state.db, app.state.jobs, clock())
    assert all(q.state == "stale" for q in expired)
    assert all(q.error_kind in {"market_status_unverified", "collection_overdue"} for q in expired)
    # Synthetic open-session clock/updates are test-only; original fixture bodies stay unchanged.
    clock.value = 1792054800.0  # 15 October 2026, 09:00 UTC, within the verified NSE/BSE session.
    with app.state.db.connect(write=True) as db:
        for row in db.execute("SELECT exchange,payload_json FROM market_sessions").fetchall():
            item = json.loads(row[1])
            item.update(
                status="NORMAL_OPEN", transition_at=timestamp(clock() - 3600), checked_at=timestamp(clock())
            )
            db.execute(
                "UPDATE market_sessions SET payload_json=? WHERE exchange=?", (json.dumps(item), row[0])
            )
        for row in db.execute("SELECT instrument_id,payload_json FROM market_quotes").fetchall():
            item = json.loads(row[1])
            item.update(
                exchange_timestamp=timestamp(clock() - 10),
                provider_timestamp=timestamp(clock()),
                retrieved_at=timestamp(clock()),
            )
            db.execute(
                "UPDATE market_quotes SET payload_json=?,retained=0 WHERE instrument_id=?",
                (json.dumps(item), row[0]),
            )
        db.execute(
            "UPDATE collection_runs SET attempted_at=?,completed_at=? WHERE group_id IN ('market_nse','market_bse','market_status')",
            (timestamp(clock()), timestamp(clock())),
        )
    fresh, _ = read_markets(app.state.db, app.state.jobs, clock())
    assert [q.state for q in fresh] == ["live", "snapshot", "snapshot"]
    # Keep status checks fresh while exchange quotes stop advancing.
    clock.advance(100)
    with app.state.db.connect(write=True) as db:
        for row in db.execute("SELECT exchange,payload_json FROM market_sessions").fetchall():
            item = json.loads(row[1])
            item["checked_at"] = timestamp(clock())
            db.execute(
                "UPDATE market_sessions SET payload_json=? WHERE exchange=?", (json.dumps(item), row[0])
            )
            db.execute(
                "UPDATE collection_runs SET attempted_at=?,completed_at=? WHERE group_id IN ('market_nse','market_bse','market_status')",
                (timestamp(clock()), timestamp(clock())),
            )
    delayed, _ = read_markets(app.state.db, app.state.jobs, clock())
    assert all(q.state == "delayed" for q in delayed)
