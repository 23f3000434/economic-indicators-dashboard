"""Real quotes → isolated private SQLite → normal protected API, controlled failure/recovery.

No fixture imports. The injected timeout is a diagnostic fault, never an upstream-incident claim.
"""

import asyncio
import json
import secrets
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
from dotenv import load_dotenv
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main():
    load_dotenv(ROOT / ".env")
    settings = replace(
        Settings.load(),
        database=ROOT / ".verification/market-flow/dashboard.sqlite3",
        database_url="",
        collector_enabled=False,
    )
    app = create_app(settings)
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "mode": "Actual responses, normal application factory, isolated private storage; timeout explicitly injected for retention verification",
        "snapshots": {},
    }
    output = ROOT / ".verification/completion/market-flow.json"

    def save():
        output.write_text(json.dumps(report, indent=2) + "\n")

    job = app.state.jobs["market_nse"]
    original_collect = job.adapter.collect
    original_store = job.adapter.persist

    async def diagnose(fetch, at):
        try:
            return await original_collect(fetch, at)
        except ValueError as exc:
            report.setdefault("validation_rejections", []).append({"stage": "parse", "reason": str(exc)})
            save()
            raise

    def diagnose_store(*args):
        try:
            return original_store(*args)
        except ValueError as exc:
            report.setdefault("validation_rejections", []).append(
                {"stage": "persistence", "reason": str(exc)}
            )
            save()
            raise

    job.adapter.collect = diagnose
    job.adapter.persist = diagnose_store
    with TestClient(app) as client:
        name, password = "proof_" + secrets.token_hex(8), secrets.token_urlsafe(32)
        app.state.auth.create_user(name, password)
        assert client.get("/api/v1/ticker").status_code == 401
        tokens = client.post(
            "/api/v1/auth/login",
            json={"username": name, "password": password},
            headers={"Origin": settings.frontend_origin, "X-CSRF-Protection": "1"},
        ).json()
        headers = {"Authorization": "Bearer " + tokens["access_token"]}
        for group in ("market_nse", "market_bse", "market_status"):
            assert asyncio.run(app.state.jobs[group].collect_once()), group
        initial = client.get("/api/v1/ticker", headers=headers).json()
        report["snapshots"]["actual"] = initial
        save()
        job = app.state.jobs["market_nse"]

        def timeout(request):
            raise httpx.ReadTimeout("controlled diagnostic timeout", request=request)

        job.client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
        assert not asyncio.run(job.collect_once())
        failed = client.get("/api/v1/ticker", headers=headers).json()
        for old, new in zip(initial["ticker"], failed["ticker"]):
            if new["exchange"] == "NSE":
                assert new["state"] == "stale" and new["retained"]
                assert all(
                    new[f] == old[f]
                    for f in ("value", "exchange_timestamp", "retrieved_at", "source_url", "response_sha256")
                )
            else:
                assert new == old
        report["snapshots"]["injected_nse_failure"] = failed
        save()
        job.client = None
        for attempt in range(3):
            if asyncio.run(job.collect_once()):
                break
            if attempt == 2:
                raise RuntimeError("NSE recovery remained blocked; partial evidence saved")
            time.sleep(settings.market_interval)
        recovered = client.get("/api/v1/ticker", headers=headers).json()
        assert all(q["error_kind"] is None for q in recovered["ticker"])
        report["snapshots"]["actual_recovery"] = recovered
        with patch("httpx.AsyncClient.send", side_effect=AssertionError("Network forbidden during read")):
            assert client.get("/api/v1/dashboard", headers=headers).json()["ticker"] == recovered["ticker"]
            with TestClient(create_app(settings)) as restarted:
                assert (
                    restarted.get("/api/v1/ticker", headers=headers).json()["ticker"] == recovered["ticker"]
                )
        client.post(
            "/api/v1/auth/logout",
            json={},
            headers={**headers, "Origin": settings.frontend_origin, "X-CSRF-Protection": "1"},
        )
        assert client.get("/api/v1/ticker", headers=headers).status_code == 401
    report["checks"] = [
        "protected reads",
        "actual quotes and sessions persisted",
        "independent provider failure",
        "original provenance retained",
        "actual recovery",
        "DB-only reads with upstream disabled",
        "restart persistence",
        "logout revocation",
    ]
    save()
    print(
        json.dumps(
            {
                "result": "passed",
                "states": [q["state"] for q in recovered["ticker"]],
                "checks": len(report["checks"]),
            }
        )
    )


if __name__ == "__main__":
    main()
