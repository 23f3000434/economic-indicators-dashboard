import asyncio
import sqlite3
import time
from contextlib import asynccontextmanager, suppress
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

from .auth import Auth, AuthError
from .config import Settings
from .db import Database
from .gdp import Collector, read_panel
from .indicators import IndicatorPanel, read_indicator
from .macro_collector import MacroCollector
from .models import EmptyBody, ErrorEnvelope, Health, Login, Panel, SessionInfo, Tokens, User
from .providers.cga import CGA


def create_app(settings: Settings | None = None, clock=time.time, upstream_client=None):
    settings = settings or Settings.load()
    database = Database(settings.database)
    auth = Auth(settings, database, clock)
    collector = Collector(settings, database, clock, upstream_client)
    jobs = {a.group: MacroCollector(a, settings, database, clock, upstream_client) for a in [CGA(settings)]}
    enabled = set(
        settings.macro_groups
        if settings.macro_groups is not None
        else ([] if settings.environment == "test" else jobs)
    )

    @asynccontextmanager
    async def lifespan(app):
        database.migrate()
        collector.recover()
        for job in jobs.values():
            job.recover()
        if settings.collector_enabled:
            collector.task = asyncio.create_task(collector.supervise(), name="gdp-collector-supervisor")
            for group, job in jobs.items():
                if group in enabled:
                    job.task = asyncio.create_task(job.supervise(), name=f"{group}-collector-supervisor")
        yield
        tasks = [job.task for job in [collector, *jobs.values()] if job.task]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="Economic Indicators API",
        version="0.1.0",
        lifespan=lifespan,
        description="Authenticated GDP slice. Data reads use private SQLite only. Upstream collection runs independently.",
        responses={status: {"model": ErrorEnvelope} for status in (401, 403, 409, 422, 429, 503)},
    )
    app.state.db, app.state.auth, app.state.collector = database, auth, collector
    app.state.jobs = jobs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-CSRF-Protection"],
    )

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.exception_handler(AuthError)
    async def auth_error(request, exc):
        return JSONResponse(
            status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}}
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": "Request fields are invalid."}},
        )

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, exc):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "storage_unavailable",
                    "message": "Storage is temporarily unavailable. Try again.",
                }
            },
        )

    security = HTTPBearer(auto_error=False)
    cookie_security = APIKeyCookie(
        name=settings.cookie_name,
        auto_error=False,
        scheme_name="RefreshCookie",
        description="Host-only HttpOnly refresh cookie. Cookie state changes also require exact Origin, JSON, X-CSRF-Protection: 1 and a session-bound X-CSRF-Token.",
    )

    def bearer_value(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if request.headers.get("authorization") and not credentials:
            raise AuthError("invalid_access_token")
        return credentials.credentials if credentials else None

    def current_user(token=Depends(bearer_value)):
        if not token:
            raise AuthError("authentication_required", "Please sign in.")
        return auth.bearer(token)

    def origin(
        origin_header: Annotated[
            str | None,
            Header(
                alias="Origin",
                description="Exact configured frontend origin; missing or foreign values return 403.",
            ),
        ] = None,
    ):
        if origin_header != settings.frontend_origin:
            raise AuthError("origin_forbidden", "Request origin is not allowed.", 403)

    def action(
        request: Request,
        protection: Annotated[
            str | None,
            Header(alias="X-CSRF-Protection", description="Must be 1; missing/wrong values return 403."),
        ] = None,
        verified_origin=Depends(origin),
    ):
        if (
            request.headers.get("content-type", "").split(";", 1)[0] != "application/json"
            or protection != "1"
        ):
            raise AuthError("csrf_failed", "JSON and request verification are required.", 403)

    def csrf(
        token: Annotated[
            str | None,
            Header(
                alias="X-CSRF-Token",
                description="Session-bound token from login or session bootstrap; required, otherwise 403.",
            ),
        ] = None,
    ):
        if not token:
            raise AuthError("csrf_failed", "Request verification failed.", 403)
        return token

    def set_cookie(response, token, expiry):
        response.set_cookie(
            settings.cookie_name,
            token,
            max_age=max(0, expiry - int(clock())),
            httponly=True,
            secure=settings.environment == "production",
            samesite="strict",
            path="/",
        )

    @app.get("/healthz", response_model=Health, tags=["operations"], responses={503: {"model": Health}})
    def health(response: Response):
        try:
            with database.connect() as db:
                db.execute("SELECT 1 FROM observations LIMIT 1").fetchone()
        except sqlite3.Error:
            response.status_code = 503
            return dict(status="unavailable", database="unavailable", collector="stopped")
        state = (
            "disabled"
            if not settings.collector_enabled
            else "running"
            if collector.task and not collector.task.done()
            else "stopped"
        )
        if settings.collector_enabled and any(not jobs[g].task or jobs[g].task.done() for g in enabled):
            state = "stopped"
        if state == "stopped":
            response.status_code = 503
        return dict(status="ok" if state != "stopped" else "unavailable", database="ready", collector=state)

    @app.post(
        "/api/v1/auth/login", response_model=Tokens, tags=["authentication"], dependencies=[Depends(action)]
    )
    def login(body: Login, request: Request, response: Response):
        result, token, expiry = auth.login(
            body.username, body.password, request.client.host if request.client else "unknown"
        )
        set_cookie(response, token, expiry)
        return result

    @app.get(
        "/api/v1/auth/session",
        response_model=SessionInfo,
        tags=["authentication"],
        dependencies=[Depends(origin)],
    )
    def session(token=Depends(cookie_security)):
        return auth.bootstrap(token)

    @app.post(
        "/api/v1/auth/refresh", response_model=Tokens, tags=["authentication"], dependencies=[Depends(action)]
    )
    def refresh(
        body: EmptyBody, response: Response, cookie=Depends(cookie_security), csrf_token=Depends(csrf)
    ):
        result, token, expiry = auth.refresh(cookie, csrf_token)
        set_cookie(response, token, expiry)
        return result

    @app.post(
        "/api/v1/auth/confirm", status_code=204, tags=["authentication"], dependencies=[Depends(action)]
    )
    def confirm(body: EmptyBody, cookie=Depends(cookie_security), csrf_token=Depends(csrf)):
        auth.confirm(cookie, csrf_token)
        return Response(status_code=204)

    @app.post("/api/v1/auth/logout", status_code=204, tags=["authentication"], dependencies=[Depends(action)])
    def logout(
        body: EmptyBody,
        token=Depends(bearer_value),
        cookie=Depends(cookie_security),
        csrf_token: Annotated[
            str | None,
            Header(
                alias="X-CSRF-Token",
                description="Required for cookie-only logout; optional with a valid bearer.",
            ),
        ] = None,
    ):
        auth.logout(token, cookie, csrf_token or "")
        response = Response(status_code=204)
        response.delete_cookie(
            settings.cookie_name,
            path="/",
            secure=settings.environment == "production",
            httponly=True,
            samesite="strict",
        )
        return response

    @app.get("/api/v1/me", response_model=User, tags=["authentication"])
    def me(user=Depends(current_user)):
        return dict(id=user["user_id"], username=user["username"])

    @app.get("/api/v1/panels/gdp", response_model=Panel, tags=["dashboard"])
    def gdp(user=Depends(current_user)):
        return read_panel(database, settings, clock())

    @app.get("/api/v1/panels/expenditure", response_model=IndicatorPanel, tags=["dashboard"])
    def expenditure(user=Depends(current_user)):
        return read_indicator(database, "expenditure", jobs, clock())

    return app
