import asyncio
import gzip
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest
from app.main import create_app
from app.providers.trade import parse_historical_html, parse_pdf
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, login

FIXTURES = Path(__file__).parent / "fixtures/providers/trade"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def body(name):
    return gzip.decompress((FIXTURES / f"{name}.gz").read_bytes())


def trade_response(request):
    url = unquote(str(request.url))
    mapping = {unquote(m["url"]): m["name"] for m in MANIFEST}
    mapping.update({unquote(m["final_url"]): m["name"] for m in MANIFEST})
    return httpx.Response(200, content=body(mapping[url]))


def test_real_trade_publications():
    for m in MANIFEST:
        raw = body(m["name"])
        assert hashlib.sha256(raw).hexdigest() == m["sha256"]
        if "reviewed_values" not in m:
            continue
        parsed = (
            parse_historical_html(raw, m["url"], m["checked_at"])
            if "pib" in m["name"]
            else parse_pdf(raw, m["url"], m["checked_at"])
        )
        assert {f"{r.series_id}:{r.period.key}": r.value for r in parsed} == m["reviewed_values"]
        for p in parsed:
            assert p.definition.unit == "usd_billion"
            assert p.definition.status == "unspecified"
            assert p.definition.published_at is not None


def test_trade_live_discovery_fixture_to_authenticated_api(settings, clock):
    app = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(trade_response)))
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        assert client.get("/api/v1/panels/trade").status_code == 401
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        assert asyncio.run(app.state.jobs["trade"].collect_once())
        data = client.get("/api/v1/panels/trade", headers=bearer).json()
        assert data["state"] == "ready"
        series = {s["id"]: s for s in data["series"]}
        lookup = {(s["id"], p["period"]["key"]): p for s in data["series"] for p in s["points"]}
        for p in series["trade_balance"]["points"]:
            assert Decimal(p["value"]) == Decimal(
                lookup["trade_exports", p["period"]["key"]]["value"]
            ) - Decimal(lookup["trade_imports", p["period"]["key"]]["value"])
            assert len(p["definition"]["inputs"]) == 2
        assert lookup["trade_balance", "FY2026-27:08"]["value"] == "-147.09"
        assert (
            len([p for p in series["trade_exports"]["points"] if p["period"]["kind"] == "fiscal_year"]) == 5
        )
        assert (
            lookup["trade_exports", "FY2022-23"]["value"] == "451.07"
        )  # newer 2024 vintage replaces 2023's 447.46
        monthly = next(s for s in data["summaries"] if s["current"]["series_id"] == "trade_exports")
        assert monthly["comparison"]["period_key"] == "2025-08"
        with localcontext() as ctx:
            ctx.prec = 80
            assert Decimal(monthly["value"]) == (Decimal("43.81") / Decimal("34.74") - 1) * 100
        assert asyncio.run(app.state.jobs["trade"].collect_once())
        with app.state.db.connect() as db:
            assert db.execute("SELECT count(*) FROM observations WHERE group_id='trade'").fetchone()[0] == 33
        app.state.jobs["trade"].client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(403))
        )
        assert not asyncio.run(app.state.jobs["trade"].collect_once())
        stale = client.get("/api/v1/panels/trade", headers=bearer).json()
        assert stale["state"] == "stale" and stale["series"] == data["series"]


def test_historical_period_mismatch_is_rejected():
    raw = body("commerce_pib2017942")
    with pytest.raises(ValueError):
        parse_historical_html(
            raw.replace(b"2022-23", b"2020-21"),
            "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2017942",
            "2026-10-15T12:00:00Z",
        )
