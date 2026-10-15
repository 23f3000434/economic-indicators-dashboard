# Economic Indicators Dashboard

Implemented local slice: scheduled World Bank GDP collection → validation → private SQLite → protected FastAPI → one React/TypeScript panel. Provider traffic is independent of browser reads. Five other panel positions and the ticker are reserved without invented observations. Other providers, public deployment and final Figma acceptance remain outside this stage.

## Local setup

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22.12+ and npm. Verified with Python 3.12.14, SQLite 3.53.1 and Node 25.6.1. Dependencies are pinned in `uv.lock` and `frontend/package-lock.json`. Start from the repository root:

```sh
uv sync --frozen --cache-dir .verification/uv-cache
.venv/bin/python scripts/setup_local.py
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/python -m app.cli create-user analyst
```

Setup generates three distinct secrets into owner-only `.env` and creates the frontend's public API configuration. It never replaces existing keys. Provisioning prompts for a password (12+ characters); no default application credentials exist. Share evaluation credentials separately. Run setup once and preserve `.env` and `data/` across restarts. For an existing username, choose another name.

Run the frontend in its own terminal:

```sh
cd frontend
npm ci --cache ../.verification/npm-cache
npm run dev
```

Run the API from the root in another terminal:

```sh
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:create_app --factory --host localhost --port 8010 --workers 1 --no-access-log
```

- Frontend: [localhost:5173](http://localhost:5173)
- Health: [localhost:8010/healthz](http://localhost:8010/healthz)
- API docs: [localhost:8010/docs](http://localhost:8010/docs), [OpenAPI schema](http://localhost:8010/openapi.json)
- Protected data: `GET http://localhost:8010/api/v1/panels/gdp`

The startup supervisor collects immediately when due; the first page can show reserved loading/empty space until that independent job finishes. Default collection is weekly; failures retry after the shorter of one hour or the configured interval. Outcomes persist. The browser polls stored data each minute while visible. “Refresh view” reads SQLite and never calls World Bank. Ctrl-C stops each server; restarting preserves users, sessions and observations. Run one worker/replica. Never serve `data/` statically.

For an explicit diagnostic collection or stored projection (stop the API before manually collecting, so the supervisor remains the sole owner during normal operation):

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli collect-gdp
PYTHONPATH=backend .venv/bin/python -m app.cli read-gdp
```

## Configuration and security

Server defaults/names are in `.env.example`; only `VITE_API_BASE_URL` is public. SQLite defaults to `data/dashboard.sqlite3` (0700 directory/0600 file), with numbered SQL migrations and `PRAGMA user_version`. Back it up consistently before schema changes; production backup/restore remains a deployment gate. Keep the file outside all frontend/static paths. Secrets, databases and generated output are ignored.

GDP uses a rolling 12-year input window ending in the previous UTC year. `GDP_START_YEAR`/`GDP_END_YEAR` override it; `GDP_REPORT_YEARS=5` controls display. Include a comparison year; at most 100 input years, within 1960–2199. Source gaps remain null. Newly omitted previously valid values retain original provenance and are labelled stale. India fiscal years and World calendar-year aggregates are visibly different. Dataset update, collection and unknown observation-release freshness stay distinct.

Auth: 15-minute memory-only JWT, persistent server session with configurable absolute lifetime up to seven days, rotated HttpOnly refresh cookie, hashed token storage, session checks on every protected read. Pending/confirm delivery recovery and a 30-second settling window handle interrupted/concurrent refresh. Refresh never extends expiry. Valid bearer logout works without a cookie; conflicting identities are rejected. See [the complete auth/API contract](docs/contracts.md).

Local development explicitly uses matching loopback HTTP hosts and `dev_refresh` (HttpOnly, SameSite=Strict, Secure=false). Use **localhost for both URLs**, not a mix with 127.0.0.1. Ports do not isolate cookies; use trusted local services. Production requires separate HTTPS subdomains of `COOKIE_SITE_DOMAIN`, exact frontend Origin, and Secure `__Host-refresh`, Path=/, no Domain attribute. No production insecure-cookie override exists. Domain/DNS gates production verification, not local implementation.

Planned hosting: static frontend on Pages, FastAPI on one paid Render instance with a private persistent disk. Build the frontend with `VITE_API_BASE_URL` set to the actual HTTPS API URL. Set server `APP_ENV=production`, actual HTTPS origins/domain, secrets and disk-mounted `SQLITE_PATH`. Preserve the disk across deploys and verify private backup/restore. If a controlled domain is unavailable, select/verify the same-origin API proxy in the contracts; do not silently use cross-site provider cookies.

## Verification

```sh
.venv/bin/pytest -q
.venv/bin/ruff check backend tests
cd frontend
npm test
npm run format:check
npm run build
npm run test:browser
```

Browser tests start/stop isolated fixture servers on localhost:5174/8001 and use real cookies with controlled clocks. They use installed Chrome; set `CHROME_PATH` elsewhere. Fixtures/control endpoints never enter the normal app. The [verification matrix](docs/verification.md) covers renewal/reload/expiry, CSRF/revocation, concurrent tabs, interrupted responses, invalid/missing data, failure retention/recovery, restart persistence, disabled upstream networking and layout.

Optional live check: place **local-only** account credentials in ignored, owner-only `.verification/local-access.json` (`username`/`password`) and run `node scripts/smoke_local.mjs` with the normal servers running. Overrides: `LOCAL_SMOKE_CREDENTIALS`, `LOCAL_FRONTEND_URL`, `LOCAL_API_URL`, `CHROME_PATH`. It records economic-data-only evidence and ignored screenshots. Never commit credentials or use production credentials for this check.

Historical stdlib probes still run independently:

```sh
python3 scripts/probe_sources.py --environment local --output-dir .verification/local
python3 scripts/prove_gdp.py --input-dir .verification/local --output-dir .verification/gdp-local
```

## Engineering and submission records

- [Requirements and deliverables](docs/requirements.md)
- [Architecture/dependencies](docs/architecture.md)
- [Decisions/outstanding inputs](docs/decisions.md)
- [API/data/session contracts](docs/contracts.md)
- [Source feasibility/access](docs/sources.md)
- [Verification/limitations](docs/verification.md)
- [Live GDP evidence](docs/evidence/2026-10-15/gdp-slice-live.json)

Exact Figma access was denied. This slice uses the supplied SVG's navy/cyan/amber cards and grid with accurate GDP data/periods; fonts, states and final frame parity remain unverified. Market access and other extractors remain unresolved. Final submission still requires deployed frontend/API/health URLs, separately shared credentials, user-supplied portfolio/project roles and the post-assessment video. Rehearsal stays outside this repository.
