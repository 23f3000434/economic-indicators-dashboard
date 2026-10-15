"""Live source → private SQLite → authenticated API proof. Never imports test fixtures."""

import argparse
import asyncio
import json
import secrets
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", nargs="+", default=["expenditure"])
    parser.add_argument("--output", default=".verification/multi-live.json")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT):
        parser.error("Output must remain in the workspace")
    settings = replace(
        Settings.load(),
        database=ROOT / ".verification/source-proof/dashboard.sqlite3",
        collector_enabled=False,
    )
    app = create_app(settings)
    unknown = set(args.groups) - set(app.state.jobs)
    if unknown:
        parser.error(f"No implemented adapter: {sorted(unknown)}")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "groups": {}}
    with TestClient(app) as client:
        username = "proof_" + secrets.token_hex(8)
        password = secrets.token_urlsafe(32)
        app.state.auth.create_user(username, password)
        tokens = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            headers={"Origin": settings.frontend_origin, "X-CSRF-Protection": "1"},
        ).json()
        bearer = {"Authorization": f"Bearer {tokens['access_token']}"}
        for group in args.groups:
            job = app.state.jobs[group]
            ok = asyncio.run(job.collect_once())
            response = client.get(f"/api/v1/panels/{job.panel}", headers=bearer)
            panel = response.json()
            report["groups"][group] = {
                "collected": ok,
                "api_status": response.status_code,
                "state": panel.get("state"),
                "collection": panel.get("collection"),
                "summaries": panel.get("summaries"),
                "series": [
                    {
                        "id": s["id"],
                        "unit": s["unit"],
                        "points": len(s["points"]),
                        "first": s["points"][0] if s["points"] else None,
                        "last": s["points"][-1] if s["points"] else None,
                    }
                    for s in panel.get("series", [])
                ],
            }
        # Proof accounts are ephemeral; never leave their sessions active.
        client.post(
            "/api/v1/auth/logout",
            json={},
            headers={**bearer, "Origin": settings.frontend_origin, "X-CSRF-Protection": "1"},
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                g: {k: v for k, v in value.items() if k not in {"series", "summaries"}}
                for g, value in report["groups"].items()
            }
        )
    )
    return 0 if all(r["collected"] and r["api_status"] == 200 for r in report["groups"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
