import asyncio
import gzip
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path

import httpx
import pytest
from app.derived import gst_aggregates
from app.main import create_app
from app.providers.gst import discover_release, discover_workbook, parse_pdf, parse_workbook
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, login

FIXTURES = Path(__file__).parent / "fixtures/providers/gst"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def body(name):
    return gzip.decompress((FIXTURES / f"{name}.gz").read_bytes())


def gst_response(request):
    mapping = {m["url"]: m["name"] for m in MANIFEST}
    return httpx.Response(200, content=body(mapping[str(request.url)]))


def points():
    return parse_workbook(body("gst_gross_net"), discover_workbook(body("gst_index")), "2026-10-15T12:00:00Z")


def test_original_gst_responses_and_definition_change():
    for m in MANIFEST:
        assert hashlib.sha256(body(m["name"])).hexdigest() == m["sha256"]
    parsed = points()
    lookup = {f"{p.series_id}:{p.period.key}": p for p in parsed}
    for key, value in MANIFEST[2]["reviewed_values"].items():
        assert lookup[key].value == value
    assert (
        lookup["gst_reported_gross:2025-09"].definition.methodology == "gross_including_compensation_cess"
    )  # The latest September PDF subsequently restates this comparator excluding cess.
    assert lookup["gst_reported_gross:2023-04"].definition.methodology == "gross_including_compensation_cess"
    assert lookup["gst_gross_ex_cess:2023-04"].definition.inputs[1].series_id == "gst_cess"
    ym, url, published = discover_release(body("gst_news_api"))
    latest = parse_pdf(body("gst_pdf"), url, "2026-10-15T12:00:00Z", ym, published)
    assert [(p.period.key, p.value) for p in latest if p.series_id == "gst_gross_ex_cess"] == [
        ("2025-09", "177365"),
        ("2026-09", "203521"),
    ]


def test_averages_require_published_months_and_complete_annuals():
    base = points()
    derived = gst_aggregates(base, 5)
    totals = [p for p in derived if p.series_id == "gst_fy_total"]
    assert [p.value is None for p in totals] == [True, True, False, False, False]
    averages = {p.period.key: p for p in derived if p.series_id == "gst_fy_average"}
    for total in totals:
        if total.value is not None:
            with localcontext() as ctx:
                ctx.prec = 80
                assert Decimal(averages[total.period.key].value) == Decimal(total.value) / 12
    # A missing month invalidates that FY total. FYTD still divides only by published months.
    missing = [
        p for p in base if not (p.series_id == "gst_gross_ex_cess" and p.period.key in {"2024-05", "2026-05"})
    ]
    derived = gst_aggregates(missing, 5)
    assert (
        next(p for p in derived if p.series_id == "gst_fy_total" and p.period.key == "FY2024-25").value
        is None
    )
    fytd = max((p for p in derived if p.series_id == "gst_fytd_average"), key=lambda p: p.period.end)
    assert len(fytd.definition.inputs) == 4
    inputs = {p.period.key: Decimal(p.value) for p in missing if p.series_id == "gst_gross_ex_cess"}
    with localcontext() as ctx:
        ctx.prec = 80
        assert Decimal(fytd.value) == sum(inputs[r.period_key] for r in fytd.definition.inputs) / 4


def test_gst_path_protected_persistent_and_failure_retains(settings, clock):
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(gst_response))
    app = create_app(settings, clock, upstream)
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        assert client.get("/api/v1/panels/gst").status_code == 401
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        assert asyncio.run(app.state.jobs["gst"].collect_once())
        response = client.get("/api/v1/panels/gst", headers=bearer).json()
        assert response["state"] == "ready"
        assert len(next(s for s in response["series"] if s["id"] == "gst_gross_ex_cess")["points"]) == 42
        assert asyncio.run(app.state.jobs["gst"].collect_once())
        with app.state.db.connect() as db:
            assert db.execute("SELECT count(*) FROM observations WHERE group_id='gst'").fetchone()[0] == 120

        async def reject(request):
            return httpx.Response(503)

        app.state.jobs["gst"].client = httpx.AsyncClient(transport=httpx.MockTransport(reject))
        assert not asyncio.run(app.state.jobs["gst"].collect_once())
        failed = client.get("/api/v1/panels/gst", headers=bearer).json()
        assert failed["state"] == "stale" and failed["series"] == response["series"]
        restart = create_app(settings, clock, app.state.jobs["gst"].client)
        with TestClient(restart) as again:
            assert again.get("/api/v1/panels/gst", headers=bearer).json()["series"] == response["series"]


def test_gst_rejects_wrong_period_and_error_page():
    ym, url, published = discover_release(body("gst_news_api"))
    with pytest.raises(ValueError):
        parse_pdf(body("gst_pdf"), url, "2026-10-15T12:00:00Z", (2026, 8), published)
    with pytest.raises(ValueError):
        parse_pdf(b"<html>access denied</html>", url, "2026-10-15T12:00:00Z", ym, published)
