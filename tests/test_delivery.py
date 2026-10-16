import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from app.serve import configuration, sqlite_owner
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

ROOT = Path(__file__).resolve().parents[1]


def production(settings, tmp_path, monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8,127.0.0.1")
    monkeypatch.setenv("PORT", "10000")
    return replace(
        settings,
        environment="production",
        database_url="postgresql://user:private@dpg-internal-a/economic",
        auth_cookie_mode="frontend_proxy",
        frontend_origin="https://economic-dashboard.vercel.app",
        api_origin="https://economic-api.onrender.com",
        site_domain="example.org",
    )


def test_production_entry_enforces_storage_single_worker_and_explicit_proxy_trust(
    settings, tmp_path, monkeypatch
):
    config = production(settings, tmp_path, monkeypatch)
    options = configuration(config)
    assert options["workers"] == 1 and options["host"] == "0.0.0.0" and not options["access_log"]
    for invalid in ["*", "0.0.0.0/0", "::/0", "garbage", "10.0.0.0/8, "]:
        monkeypatch.setenv("TRUSTED_PROXY_CIDRS", invalid)
        with pytest.raises(ValueError):
            configuration(config)
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "")
    assert not configuration(config)["proxy_headers"]
    with pytest.raises(ValueError, match="ephemeral SQLite"):
        configuration(replace(config, database_url=""))
    for url in [
        "postgresql://user:private@external.example.org/db",
        "postgresql://user:private@dpg-internal-a.oregon-postgres.render.com/db",
    ]:
        with pytest.raises(ValueError, match="internal hostname"):
            configuration(replace(config, database_url=url))


def test_second_api_owner_cannot_recover_or_start_until_first_exits(tmp_path):
    path = tmp_path / "private/dashboard.sqlite3"
    with sqlite_owner(path):
        with pytest.raises(BlockingIOError):
            with sqlite_owner(path):
                pytest.fail("Second owner must not reach application startup/recovery")
    with sqlite_owner(path):
        assert path.parent.stat().st_mode & 0o777 == 0o700
        assert (path.parent / ".api-owner.lock").stat().st_mode & 0o777 == 0o600


def test_forwarding_headers_are_ignored_from_untrusted_peers():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["client"][0])

    async def check():
        middleware = ProxyHeadersMiddleware(app, trusted_hosts=["10.0.0.0/8"])
        for peer in ["203.0.113.1", "10.0.0.1"]:
            await middleware(
                {
                    "type": "http",
                    "scheme": "https",
                    "client": (peer, 1234),
                    "headers": [(b"x-forwarded-for", b"198.51.100.5, 10.0.0.2")],
                },
                None,
                None,
            )

    asyncio.run(check())
    assert seen == ["203.0.113.1", "198.51.100.5"]


def test_allowlisted_runtime_has_no_tests_fixtures_control_routes_or_environment(tmp_path):
    destination = ROOT / ".delivery/test-api"
    subprocess.run(
        [sys.executable, str(ROOT / "deploy/prepare_api.py"), "--output", str(destination)], check=True
    )
    try:
        files = [str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()]
        assert all(
            p in {"pyproject.toml", "uv.lock"} or p.startswith(("backend/app/", "backend/migrations/"))
            for p in files
        )
        assert not any("fixtures" in p or "browser_server" in p or ".env" in p for p in files)
        script = """
import asyncio, sys
import httpx
from app.main import create_app
app=create_app()
assert not any(name == 'tests' or name.startswith('tests.') for name in sys.modules)
assert not any('/__test' in route.path for route in app.routes)
async def check():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://api.example.org') as client:
            assert (await client.get('/healthz')).status_code == 200
            assert (await client.get('/api/v1/dashboard')).status_code == 401
            assert (await client.post('/__test/reset')).status_code == 404
            assert (await client.post('/__test/collect/success')).status_code == 404
asyncio.run(check())
"""
        env = {key: value for key, value in os.environ.items() if key in {"PATH", "SYSTEMROOT"}}
        env.update(
            PYTHONPATH="backend",
            APP_ENV="production",
            API_ORIGIN="https://api.example.org",
            FRONTEND_ORIGIN="https://dashboard.example.org",
            COOKIE_SITE_DOMAIN="example.org",
            SQLITE_PATH=str(tmp_path / "private/runtime.sqlite3"),
            COLLECTOR_ENABLED="false",
            JWT_SECRET="test-j" * 10,
            CSRF_SECRET="test-c" * 10,
            ROTATION_SECRET="test-r" * 10,
        )
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=destination,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        shutil.rmtree(destination, ignore_errors=True)
