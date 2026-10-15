"""Test-only fixture server. Never imported by app code or used for local/live preview."""

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from app.config import Settings
from app.main import create_app

from tests.conftest import PASSWORD, Clock, fixture_response
from tests.test_dashboard import provider_response

ROOT = Path(__file__).resolve().parents[1]
clock = Clock()
settings = Settings(
    database=ROOT / ".verification/browser/dashboard.sqlite3",
    jwt_secret="test-j" * 10,
    csrf_secret="test-c" * 10,
    rotation_secret="test-r" * 10,
    environment="test",
    api_origin="http://localhost:8001",
    frontend_origin="http://localhost:5174",
    collector_enabled=False,
    start_year=2020,
    end_year=2025,
    collection_years=6,
    upstream_attempts=1,
)
upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider_response))
app = create_app(settings, clock, upstream)
original_lifespan = app.router.lifespan_context


async def reset():
    clock.value = Clock().value
    with app.state.db.connect(write=True) as db:
        for table in (
            "refresh_tokens",
            "sessions",
            "users",
            "observations",
            "collection_runs",
            "provider_cooldowns",
        ):
            db.execute(f"DELETE FROM {table}")  # fixed test-only table names
    app.state.auth.attempts.clear()
    app.state.auth.create_user("analyst", PASSWORD)
    app.state.auth.create_user("reviewer", PASSWORD)
    app.state.collector.client = upstream
    await app.state.collector.collect_once()
    for job in app.state.jobs.values():
        job.client = upstream
        await job.collect_once()


@asynccontextmanager
async def lifespan(app):
    async with original_lifespan(app):
        await reset()
        yield
    await upstream.aclose()


app.router.lifespan_context = lifespan


@app.post("/__test/reset")
async def reset_endpoint():
    await reset()
    return {"now": clock.value * 1000}


@app.post("/__test/advance/{seconds}")
def advance(seconds: int):
    clock.advance(seconds)
    return {"now": clock.value * 1000}


@app.post("/__test/collect/{mode}")
async def collect(mode: str):
    def respond(request):
        if mode == "failure":
            raise httpx.ReadTimeout("injected browser-test timeout", request=request)
        response = fixture_response(request)
        if mode == "missing" and "/indicator/" in request.url.path and "/country/" in request.url.path:
            data = response.json()
            data[1] = [p for p in data[1] if p["date"] != "2023"]
            data[0]["total"] = len(data[1])
            return httpx.Response(200, json=data)
        return response

    if mode == "missing":
        with app.state.db.connect(write=True) as db:
            db.execute("DELETE FROM observations WHERE group_id='gdp'")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as source:
        app.state.collector.client = source
        ok = await app.state.collector.collect_once()
    app.state.collector.client = upstream
    return {"ok": ok}


@app.post("/__test/group/{group}/{mode}")
async def group_collect(group: str, mode: str):
    job = app.state.jobs[group]
    if mode == "failure":

        def response(request):
            raise httpx.ReadTimeout("injected independent provider failure", request=request)
    else:
        response = provider_response
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as source:
        job.client = source
        ok = await job.collect_once()
    job.client = upstream
    return {"ok": ok}
