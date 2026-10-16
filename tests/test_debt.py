import asyncio
import csv
import gzip
import hashlib
from io import StringIO
from pathlib import Path

import httpx
import pytest
from app.config import Settings
from app.gdp import timestamp
from app.main import create_app
from app.providers.debt import DATA, METADATA, parse
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, login

FIXTURES = Path(__file__).parent / "fixtures/providers/debt"


APPENDIX = Settings.__dataclass_fields__["debt_appendix_url"].default


def appendix():
    return gzip.decompress((FIXTURES / "weo_oct2026_appendix.pdf.gz").read_bytes())


def body(metadata=False):
    name = "data360_weo_2026-10-13.metadata.json.gz" if metadata else "data360_weo_2026-10-13.csv.gz"
    return gzip.decompress((FIXTURES / name).read_bytes())


def debt_response(request):
    assert str(request.url) in {DATA, METADATA, APPENDIX}
    if str(request.url) == APPENDIX:
        return httpx.Response(200, content=appendix())
    return httpx.Response(200, content=body(str(request.url) == METADATA))


def test_actual_mirror_definition_values_vintage_and_status():
    points = parse(body(), body(True), "2026-10-16T00:00:00Z", 2020, 2025, appendix(), APPENDIX)
    assert len(points) == 12 and len(points.expected) == 12
    latest = {p.series_id: p for p in points if p.period.start.year == 2025}
    assert latest["debt_india"].value == "84.260729"
    assert latest["debt_us"].value == "124.376732"
    assert latest["debt_india"].period.key == "FY2025-26"
    assert latest["debt_us"].period.key == "2025"
    for p in points:
        assert str(p.definition.vintage_date) == "2026-10-13"
        assert p.definition.published_at is None
        assert p.definition.source_status == "A: Normal value"
        assert p.definition.status == (
            "estimate" if p.series_id == "debt_india" and p.period.start.year == 2025 else "actual"
        )
        assert p.response_sha256 == hashlib.sha256(body()).hexdigest()
        assert p.definition.supporting_sources[0].response_sha256 == hashlib.sha256(body(True)).hexdigest()


@pytest.mark.parametrize(
    "field,value",
    [("UNIT_MEASURE", "USD"), ("COMP_BREAKDOWN_1", "V_OLD"), ("OBS_STATUS", "X"), ("OBS_VALUE", "-1")],
)
def test_reject_changed_definition_or_bad_value(field, value):
    rows = list(csv.DictReader(StringIO(body().decode())))
    row = next(r for r in rows if r["REF_AREA"] == "IND" and r["TIME_PERIOD"] == "2025")
    row[field] = value
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    with pytest.raises(ValueError):
        parse(out.getvalue().encode(), body(True), "2026-10-16T00:00:00Z", 2020, 2025, appendix(), APPENDIX)


def test_debt_collector_protected_read_idempotency_failure_and_restart(settings, clock, monkeypatch):
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(debt_response))
    app = create_app(settings, clock, upstream)
    with TestClient(app) as client:
        app.state.auth.create_user("analyst", PASSWORD)
        assert client.get("/api/v1/panels/debt").status_code == 401
        bearer = {"Authorization": "Bearer " + login(client).json()["access_token"]}
        job = app.state.jobs["debt"]
        assert asyncio.run(job.collect_once())
        before = client.get("/api/v1/panels/debt", headers=bearer).json()
        assert before["state"] == "ready" and before["availability"] == "implemented"
        assert {s["current"]["series_id"]: s["value"] for s in before["summaries"]} == {
            "debt_india": "-0.544476",
            "debt_us": "2.042455",
        }
        assert all(s["kind"] == "percentage_points" for s in before["summaries"])
        assert asyncio.run(job.collect_once())
        with app.state.db.connect() as db:
            assert db.execute("SELECT count(*) FROM observations WHERE group_id='debt'").fetchone()[0] == 12
        job.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
        clock.advance(10)
        assert not asyncio.run(job.collect_once())
        failed = client.get("/api/v1/panels/debt", headers=bearer).json()
        assert failed["state"] == "stale" and failed["series"] == before["series"]
        assert failed["collection"][0]["last_success_at"] == before["collection"][0]["last_success_at"]

        async def disabled(*args, **kwargs):
            raise AssertionError("Stored read attempted upstream networking")

        monkeypatch.setattr(httpx.AsyncClient, "send", disabled)
        aggregate = client.get("/api/v1/dashboard", headers=bearer).json()
        assert next(p for p in aggregate["panels"] if p["id"] == "debt") == failed
        restarted = create_app(settings, clock)
        with TestClient(restarted) as again:
            assert again.get("/api/v1/panels/debt", headers=bearer).json() == failed


def test_missing_scope_retains_original_point(settings, clock):
    from app.batches import MeasurementBatch
    from app.indicators import store_batch

    app = create_app(settings, clock)
    app.state.db.migrate()
    job = app.state.jobs["debt"]
    points = parse(body(), body(True), timestamp(clock()), 2020, 2025, appendix(), APPENDIX)
    run = job.state.begin(timestamp(clock()), 2020, 2025)
    store_batch(app.state.db, job.state, run, points)
    omitted = points[-1]
    run = job.state.begin(timestamp(clock()), 2020, 2025)
    store_batch(app.state.db, job.state, run, MeasurementBatch(points[:-1], points.expected))
    with app.state.db.connect() as db:
        row = db.execute(
            "SELECT * FROM observations WHERE series_id=? AND period_key=?",
            (omitted.series_id, omitted.period.key),
        ).fetchone()
        assert row["value"] == omitted.value and row["retained"] == 1
        assert row["response_sha256"] == omitted.response_sha256


def test_absent_annual_pairs_are_null_gaps_with_distinct_reporting_bases(settings, clock):
    from app.batches import MeasurementBatch
    from app.indicators import read_indicator, store_batch

    app = create_app(settings, clock)
    app.state.db.migrate()
    job = app.state.jobs["debt"]
    rows = parse(body(), body(True), timestamp(clock()), 2020, 2025, appendix(), APPENDIX)
    missing = [p for p in rows if p.period.start.year != 2023]
    run = job.state.begin(timestamp(clock()), 2020, 2025)
    store_batch(app.state.db, job.state, run, MeasurementBatch(missing, rows.expected))
    panel = read_indicator(app.state.db, "debt", app.state.jobs, clock(), 5)
    gaps = [p for s in panel.series for p in s.points if p.period.start.year == 2023]
    assert {p.period.key for p in gaps} == {"FY2023-24", "2023"}
    assert all(p.value is None and p.source_url is None and p.retrieved_at is None for p in gaps)
    assert all(p.definition.vintage_date is None and p.definition.supporting_sources == [] for p in gaps)
