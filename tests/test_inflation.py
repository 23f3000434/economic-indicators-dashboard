import asyncio
import gzip
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest
from app.indicators import read_indicator, summaries
from app.main import create_app
from app.providers import cpi
from app.providers.policy import parse as parse_policy
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, login

FIXTURES = Path(__file__).parent / "fixtures/providers/inflation"


def manifest():
    return json.loads((FIXTURES / "manifest.json").read_text())


def body(name):
    return gzip.decompress((FIXTURES / f"{name}.gz").read_bytes())


def inflation_response(request):
    entries = manifest()
    if str(request.url) == cpi.LIST:
        assert request.method == "POST"
        data = json.loads(request.content)
        assert data["search_term"] == "CPI" and data["page_size"] == 100 and data["page_no"] == 1
    mapping = {unquote(m["url"]): m["name"] for m in entries}
    return httpx.Response(200, content=body(mapping[unquote(str(request.url))]))


def test_original_cpi_and_policy_observations():
    for m in manifest():
        assert hashlib.sha256(body(m["name"])).hexdigest() == m["sha256"]
    for name, fn, pub, args in [
        ("cpi_2026-10-12", cpi.parse_current, date(2026, 10, 12), ()),
        ("cpi_2026-01-12", cpi.parse_old, date(2026, 1, 12), (2020,)),
    ]:
        m = next(m for m in manifest() if m["name"] == name)
        points = fn(body(name), m["url"], m["checked_at"], pub, *args)
        lookup = {p.period.key: p for p in points}
        for key, value in m["reviewed_values"].items():
            assert lookup[key].value == value
        assert lookup[max(lookup)].definition.status == "provisional"
    m = manifest()[-1]
    policy = parse_policy(body("policy_native"), m["url"], m["checked_at"])
    assert {p.series_id: p.value for p in policy} == m["reviewed_values"]
    assert [policy[0].period.start.isoformat(), policy[0].period.end.isoformat()] == m["validity"]
    assert policy[0].definition.published_at == date(2026, 3, 25)


def test_cpi_and_policy_independent_authenticated_paths(settings, clock):
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(inflation_response))
    app = create_app(settings, clock, upstream)
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        assert client.get("/api/v1/panels/inflation").status_code == 401
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        assert asyncio.run(app.state.jobs["inflation"].collect_once())
        assert asyncio.run(app.state.jobs["inflation_policy"].collect_once())
        data = client.get("/api/v1/panels/inflation", headers=bearer).json()
        assert data["state"] == "ready" and len(data["collection"]) == 2
        series = {s["id"]: s for s in data["series"]}
        assert len(series["cpi_yoy_2012"]["points"]) == 72
        assert len(series["cpi_yoy_2024"]["points"]) == 9
        missing = {p["period"]["key"]: p for p in series["cpi_yoy_2012"]["points"] if p["value"] is None}
        assert set(missing) == {"2020-04", "2020-05"}
        assert missing["2020-04"]["retrieved_at"] is None
        assert data["policies"][0]["active"] and data["policies"][0]["validity"]["start"] == "2026-04-01"
        current = next(s for s in data["summaries"] if s["current"]["series_id"] == "cpi_yoy_2024")
        assert current["comparison"]["period_key"] == "2026-08" and Decimal(current["value"]) == Decimal(
            "0.71"
        )
        assert asyncio.run(app.state.jobs["inflation"].collect_once())
        with app.state.db.connect() as db:
            assert (
                db.execute(
                    "SELECT count(*) FROM observations WHERE group_id IN ('inflation','inflation_policy')"
                ).fetchone()[0]
                == 82
            )

        async def fail(request):
            raise httpx.ReadTimeout("injected", request=request)

        app.state.jobs["inflation_policy"].client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
        assert not asyncio.run(app.state.jobs["inflation_policy"].collect_once())
        assert asyncio.run(app.state.jobs["inflation"].collect_once())
        after = client.get("/api/v1/panels/inflation", headers=bearer).json()
        assert after["state"] == "stale" and after["series"] == data["series"]
        states = {g["group_id"]: g for g in after["collection"]}
        assert states["inflation"]["last_error_kind"] is None
        assert states["inflation_policy"]["last_error_kind"] == "timeout"
        restart = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(fail)))
        with TestClient(restart) as again:
            assert again.get("/api/v1/panels/inflation", headers=bearer).json()["series"] == after["series"]
        expired = read_indicator(app.state.db, "inflation", app.state.jobs, datetime_timestamp(2031, 4, 1))
        assert not expired.policies[0].active
        boundary = datetime_timestamp(2031, 4, 1) - 19800  # Midnight IST, still March 31 in UTC.
        assert read_indicator(app.state.db, "inflation", app.state.jobs, boundary - 1).policies[0].active
        assert not read_indicator(app.state.db, "inflation", app.state.jobs, boundary).policies[0].active
        start = datetime_timestamp(2026, 4, 1) - 19800
        assert not read_indicator(app.state.db, "inflation", app.state.jobs, start - 1).policies[0].active
        assert read_indicator(app.state.db, "inflation", app.state.jobs, start).policies[0].active


def datetime_timestamp(y, m, d):
    from datetime import datetime, timezone

    return datetime(y, m, d, tzinfo=timezone.utc).timestamp()


def test_never_compare_across_cpi_base_change():
    url = manifest()[1]["url"]
    new = cpi.parse_current(body("cpi_2026-10-12"), url, "2026-10-15T12:00:00Z", date(2026, 10, 12))
    jan = [p for p in new if p.period.key == "2026-01"]
    old_meta = manifest()[2]
    old = cpi.parse_old(
        body("cpi_2026-01-12"), old_meta["url"], old_meta["checked_at"], date(2026, 1, 12), 2025
    )
    result = next(s for s in summaries(jan + old) if s.current.series_id == "cpi_yoy_2024")
    assert result.comparison is None and result.value is None


def test_changed_cpi_base_or_columns_fails_closed(monkeypatch):
    pages = cpi.pdf_pages(body("cpi_2026-10-12"), limit=30, layout=True)
    for old, new in [("BASE 2024=100", "BASE 2030=100"), ("Combined", "OtherSector")]:
        monkeypatch.setattr(cpi, "pdf_pages", lambda *a, **k: [p.replace(old, new) for p in pages])
        with pytest.raises(ValueError):
            cpi.parse_current(
                body("cpi_2026-10-12"), manifest()[1]["url"], "2026-10-15T12:00:00Z", date(2026, 10, 12)
            )
