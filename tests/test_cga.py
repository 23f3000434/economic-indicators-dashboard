import asyncio
import gzip
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path

import httpx
import pytest
from app.indicators import read_indicator
from app.main import create_app
from app.measurements import Measurement
from app.providers.cga import HOME, discover, parse, release_url
from fastapi.testclient import TestClient

from tests.conftest import login

FIXTURES = Path(__file__).parent / "fixtures/providers/cga"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def body(name):
    return gzip.decompress((FIXTURES / f"{name}.gz").read_bytes())


def cga_response(request):
    if str(request.url) == HOME:
        name = "cga_home"
    else:
        mapping = {
            release_url(int(m["name"][-4:]), 8 if "aug" in m["name"] else 3): m["name"]
            for m in MANIFEST
            if m["name"] != "cga_home"
        }
        name = mapping[str(request.url)]
    return httpx.Response(200, content=body(name))


def test_actual_cga_responses():
    assert discover(body("cga_home")) == (2026, 8)
    for meta in MANIFEST:
        raw = body(meta["name"])
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
        if meta["name"] == "cga_home":
            continue
        year = int(meta["name"][-4:])
        m = 8 if "aug" in meta["name"] else 3
        points = parse(raw, release_url(year, m), meta["checked_at"], year, m)
        assert {p.series_id: p.value for p in points} == meta["reviewed_values"]
        assert all(p.definition.status == "provisional" and p.definition.published_at is None for p in points)
        assert points[0].period.model_dump(mode="json") == meta["period"]


@pytest.mark.parametrize(
    "old,new", [(b"2077958", b"2077959"), (b"Budget", b"Other"), (b"Crore", b"Rupee")]
)
def test_reject_changed_headers_units_or_unreconciled_actuals(old, new):
    raw = body("cga_aug2026")
    assert old in raw
    with pytest.raises(ValueError):
        parse(raw.replace(old, new), release_url(2026, 8), "2026-10-15T12:00:00Z", 2026, 8)


def test_cga_end_to_end_auth_retention_and_restart(settings, clock):
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(cga_response))
    app = create_app(settings, clock, upstream)
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", "Test-only password 93!")
        assert client.get("/api/v1/panels/expenditure").status_code == 401
        token = login(client).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert asyncio.run(app.state.jobs["expenditure"].collect_once())
        result = client.get("/api/v1/panels/expenditure", headers=headers).json()
        assert result["state"] == "ready"
        assert sum(len(s["points"]) for s in result["series"]) == 21
        total = next(s for s in result["series"] if s["id"] == "expenditure_total")
        assert total["points"][-1]["value"] == "2077958"
        summary = next(s for s in result["summaries"] if s["current"]["series_id"] == "expenditure_total")
        assert summary["comparison"]["period_key"] == "FY2025-26:08"
        with localcontext() as ctx:
            ctx.prec = 80
            assert Decimal(summary["value"]) == (Decimal(2077958) / 1880862 - 1) * 100
        assert asyncio.run(app.state.jobs["expenditure"].collect_once())
        with app.state.db.connect() as db:
            assert (
                db.execute("SELECT count(*) FROM observations WHERE group_id='expenditure'").fetchone()[0]
                == 21
            )

        async def timeout(request):
            raise httpx.ReadTimeout("injected", request=request)

        app.state.jobs["expenditure"].client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
        clock.advance(1)
        assert not asyncio.run(app.state.jobs["expenditure"].collect_once())
        stale = client.get("/api/v1/panels/expenditure", headers=headers).json()
        assert stale["state"] == "stale" and stale["series"] == result["series"]
        assert stale["collection"][0]["last_error_kind"] == "timeout"
        assert stale["collection"][0]["last_success_at"] == result["collection"][0]["last_success_at"]
        # Network is unavailable; these reads and a new app instance use storage only.
        restart = create_app(settings, clock, app.state.jobs["expenditure"].client)
        with TestClient(restart) as again:
            assert (
                again.get("/api/v1/panels/expenditure", headers=headers).json()["series"] == result["series"]
            )
        app.state.jobs["expenditure"].client = upstream
        assert asyncio.run(app.state.jobs["expenditure"].collect_once())
        assert read_indicator(app.state.db, "expenditure", app.state.jobs, clock()).state == "ready"


def test_strict_measurement_identity():
    p = parse(body("cga_aug2026"), release_url(2026, 8), "2026-10-15T12:00:00Z", 2026, 8)[0].model_dump()
    p["definition"]["unit"] = "percent"
    with pytest.raises(ValueError):
        Measurement.model_validate(p)
