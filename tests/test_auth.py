from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from app.auth import AuthError
from app.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, headers, login


def test_protected_login_cookie_and_reload(client):
    assert client.get("/api/v1/panels/gdp").status_code == 401
    assert login(client, password="wrong").status_code == 401
    response = login(client)
    tokens = response.json()
    assert tokens["expires_in"] == 900
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Secure" not in response.headers["set-cookie"]  # explicit loopback test mode only
    bootstrap = client.get("/api/v1/auth/session", headers={"Origin": "http://localhost:5173"})
    assert bootstrap.status_code == 200 and "access_token" not in bootstrap.json()
    renewed = client.post("/api/v1/auth/refresh", json={}, headers=headers(tokens))
    assert renewed.status_code == 200
    assert client.post("/api/v1/auth/confirm", json={}, headers=headers(tokens)).status_code == 204
    read = client.get(
        "/api/v1/panels/gdp", headers={"Authorization": "Bearer " + renewed.json()["access_token"]}
    )
    assert read.status_code == 200 and read.headers["cache-control"] == "no-store"
    assert (
        client.get("/api/v1/me", headers={"Authorization": "Bearer " + tokens["access_token"]}).json()[
            "username"
        ]
        == "analyst"
    )


def test_renewal_and_absolute_expiry(client, clock):
    token = login(client).json()
    clock.advance(901)
    expired = client.get("/api/v1/me", headers={"Authorization": "Bearer " + token["access_token"]})
    assert expired.json()["error"]["code"] == "access_token_expired"
    renewed = client.post("/api/v1/auth/refresh", json={}, headers=headers(token)).json()
    assert renewed["session_expires_at"] == token["session_expires_at"]
    clock.advance(604800)
    assert client.post("/api/v1/auth/refresh", json={}, headers=headers(renewed)).status_code == 401
    assert (
        client.get("/api/v1/me", headers={"Authorization": "Bearer " + renewed["access_token"]}).status_code
        == 401
    )


def test_access_capped_at_session_limit(settings, clock):
    with TestClient(
        create_app(replace(settings, session_max_age=10), clock), base_url="http://localhost:8000"
    ) as c:
        c.app.state.auth.create_user("analyst", PASSWORD)
        token = login(c).json()
        assert token["expires_in"] == 10
        clock.advance(11)
        assert c.get("/api/v1/auth/session", headers={"Origin": settings.frontend_origin}).status_code == 401


def test_bearer_only_logout_and_revoke(client):
    token = login(client).json()
    client.cookies.clear()
    h = headers(token) | {"Authorization": "Bearer " + token["access_token"]}
    assert client.post("/api/v1/auth/logout", json={}, headers=h).status_code == 204
    assert client.get("/api/v1/me", headers=h).status_code == 401


def test_cookie_logout_without_access_and_no_resurrection(client, app):
    token = login(client).json()
    old_cookie = client.cookies.get("dev_refresh")
    renewed = client.post("/api/v1/auth/refresh", json={}, headers=headers(token)).json()
    assert client.post("/api/v1/auth/logout", json={}, headers=headers(token)).status_code == 204
    assert (
        client.get("/api/v1/me", headers={"Authorization": "Bearer " + renewed["access_token"]}).status_code
        == 401
    )
    with pytest.raises(AuthError):
        app.state.auth.refresh(old_cookie, token["csrf_token"])
    with pytest.raises(AuthError):
        app.state.auth.confirm(old_cookie, token["csrf_token"])


def test_conflicting_identities_do_not_revoke_either(client, app):
    first = login(client).json()
    first_cookie = client.cookies.get("dev_refresh")
    second = login(client).json()
    second_cookie = client.cookies.get("dev_refresh")
    h = headers(first) | {"Authorization": "Bearer " + first["access_token"]}
    response = client.post("/api/v1/auth/logout", json={}, headers=h)
    assert response.status_code == 409 and "set-cookie" not in response.headers
    assert app.state.auth.bootstrap(first_cookie)
    assert app.state.auth.bootstrap(second_cookie)
    assert (
        client.post(
            "/api/v1/auth/logout", json={}, headers=headers(second) | {"Authorization": "Bearer invalid"}
        ).status_code
        == 401
    )


def test_lost_response_before_or_after_cookie_and_restart(client, app, settings, clock):
    tokens = login(client).json()
    original = client.cookies.get("dev_refresh")
    auth = app.state.auth
    _, successor, _ = auth.refresh(original, tokens["csrf_token"])
    # Response is entirely lost; an ordinary retry long after the old grace still works.
    clock.advance(3600)
    assert auth.refresh(original, tokens["csrf_token"])[1] == successor
    restarted = create_app(settings, clock).state.auth
    # Headers installed cookie, body lost: pending cookie can bootstrap and retry.
    assert restarted.bootstrap(successor)
    assert restarted.refresh(successor, tokens["csrf_token"])[1] == successor
    restarted.confirm(successor, tokens["csrf_token"])
    restarted.confirm(successor, tokens["csrf_token"])  # lost confirm response, idempotent retry
    assert restarted.refresh(successor, tokens["csrf_token"])[1] == successor
    with app.state.db.connect() as db:
        assert not db.execute(
            "SELECT 1 FROM refresh_tokens WHERE digest IN (?, ?)", (original, successor)
        ).fetchone()
        assert db.execute("SELECT COUNT(*) FROM refresh_tokens WHERE state='active'").fetchone()[0] == 1


def test_concurrent_refresh_without_client_lock(client, app, clock):
    tokens = login(client).json()
    original = client.cookies.get("dev_refresh")
    auth = app.state.auth
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: auth.refresh(original, tokens["csrf_token"])[1], range(8)))
    assert len(set(results)) == 1
    successor = results[0]
    auth.confirm(successor, tokens["csrf_token"])
    assert auth.refresh(original, tokens["csrf_token"])[1] == successor
    assert auth.refresh(successor, tokens["csrf_token"])[1] == successor
    clock.advance(31)
    with pytest.raises(AuthError):
        auth.refresh(original, tokens["csrf_token"])
    with pytest.raises(AuthError):
        auth.bearer(tokens["access_token"])


def test_csrf_origin_content_type_cors_and_rate_limit(client):
    tokens = login(client).json()
    for h in [
        headers(tokens) | {"Origin": "https://evil.example"},
        headers(tokens) | {"X-CSRF-Token": "wrong"},
        headers(tokens) | {"Content-Type": "text/plain"},
        {"Content-Type": "application/json"},
    ]:
        assert client.post("/api/v1/auth/refresh", json={}, headers=h).status_code == 403
    assert client.get("/api/v1/auth/session").status_code == 403
    preflight = client.options(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in preflight.headers
    for _ in range(4):
        assert login(client, password="incorrect").status_code == 401
    assert login(client).status_code == 429


def test_production_config_never_downgrades(settings, clock):
    with pytest.raises(ValueError):
        replace(settings, environment="production")
    production = replace(
        settings,
        environment="production",
        frontend_origin="https://dashboard.example.com",
        api_origin="https://api.example.com",
        site_domain="example.com",
    )
    with TestClient(create_app(production, clock), base_url=production.api_origin) as c:
        c.app.state.auth.create_user("analyst", PASSWORD)
        response = c.post(
            "/api/v1/auth/login",
            json={"username": "analyst", "password": PASSWORD},
            headers={"Origin": production.frontend_origin, "X-CSRF-Protection": "1"},
        )
        cookie = response.headers["set-cookie"]
        assert (
            cookie.startswith("__Host-refresh=")
            and "Secure" in cookie
            and "HttpOnly" in cookie
            and "Domain=" not in cookie
            and "Path=/" in cookie
        )


def test_logout_refresh_race_stays_revoked(client, app):
    tokens = login(client).json()
    original = client.cookies.get("dev_refresh")
    auth = app.state.auth

    def refresh():
        try:
            return auth.refresh(original, tokens["csrf_token"])
        except AuthError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(refresh)
        auth.logout(tokens["access_token"], None, "")
        result = future.result()
    if result:
        with pytest.raises(AuthError):
            auth.bearer(result[0]["access_token"])
    with pytest.raises(AuthError):
        auth.refresh(original, tokens["csrf_token"])
