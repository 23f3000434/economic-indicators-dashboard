import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import psycopg
import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from psycopg import sql

FIXTURES = Path(__file__).parent / "fixtures"
PASSWORD = "Test-only password 93!"


class Clock:
    def __init__(self):
        self.value = datetime(
            2026, 10, 15, 22, tzinfo=UTC
        ).timestamp()  # After captured market responses; test-only clock.

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def fixture_response(request):
    path = request.url.path
    name = (
        "world_bank_india_metadata"
        if "metadata" in path
        else "world_bank_indicator"
        if "/country/" not in path
        else "world_bank_india"
        if "/IND/" in path
        else "world_bank_world"
    )
    payload = json.loads((FIXTURES / f"{name}.json").read_text())
    if name in {"world_bank_india", "world_bank_world"}:
        start, end = map(int, request.url.params["date"].split(":"))
        payload[1] = [p for p in payload[1] if start <= int(p["date"]) <= end]
        payload[0]["total"] = len(payload[1])
    return httpx.Response(200, json=payload)


@pytest.fixture
def postgres_url():
    target = os.getenv("TEST_DATABASE_URL", "")
    if not target:
        yield ""
        return
    schema = "test_" + secrets.token_hex(12)
    with psycopg.connect(target, autocommit=True) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    url = urlsplit(target)
    query = dict(parse_qsl(url.query))
    query["options"] = "-csearch_path=" + schema
    try:
        yield urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), url.fragment))
    finally:
        with psycopg.connect(target, autocommit=True) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def settings(tmp_path, postgres_url):
    return Settings(
        database=tmp_path / "private/dashboard.sqlite3",
        database_url=postgres_url,
        jwt_secret="j" * 48,
        csrf_secret="c" * 48,
        rotation_secret="r" * 48,
        environment="test",
        collector_enabled=False,
        start_year=2020,
        end_year=2025,
        collection_years=6,
        upstream_attempts=1,
    )


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def app(settings, clock):
    return create_app(settings, clock)


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://localhost:8000") as client:
        app.state.auth.create_user("analyst", PASSWORD)
        yield client


def login(client, username="analyst", password=PASSWORD):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": "http://localhost:5173", "X-CSRF-Protection": "1"},
    )


def headers(tokens):
    return {
        "Origin": "http://localhost:5173",
        "Content-Type": "application/json",
        "X-CSRF-Protection": "1",
        "X-CSRF-Token": tokens["csrf_token"],
    }
