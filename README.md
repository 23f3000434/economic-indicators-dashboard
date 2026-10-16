# Economic Indicators Dashboard

Implemented locally: independent GDP/debt/CGA/GST/trade/CPI/policy and market collection → strict validation → private persistent SQLite → authenticated FastAPI → one canonical React dashboard. NSE principally supplies NIFTY BANK/IT; read-only Upstox supplies BSE SENSEX and verified exchange status/schedules. The measured Figma layout now uses six 544-pixel panels and accessible data/control dialogs. Exact Segoe UI font delivery remains pending; public deployment is not performed. See [current source/design evidence and remaining inputs](docs/design-completion.md).

## Local setup

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22.12+ and npm. Verified with Python 3.12.14, SQLite 3.53.1 and Node 25.6.1; delivery build/unit checks also use pinned Node 22.23.3 (`.node-version`). Dependencies are pinned in `uv.lock` and `frontend/package-lock.json`. Start from the repository root:

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
- Protected data: `GET http://localhost:8010/api/v1/dashboard`; dedicated GDP/debt/expenditure/GST/trade/inflation panel routes under `/api/v1/panels/`.

Independent startup supervisors collect when due: GDP/debt/policy weekly, CGA/GST/trade/CPI daily, market quotes/status every30 seconds by default. Failures retry after the shorter of one hour or their configured interval, subject to durable provider cooldowns. Each group commits independently and keeps its own history/last success. The frontend polls the protected stored-data dashboard each minute and the smaller `/api/v1/ticker` every30 seconds while visible; “Refresh view” never triggers upstream work. Ctrl-C stops each server; restart preserves users, sessions and observations. Run one worker/replica. Never serve `data/` statically.

If frontend port 5173 is occupied, leave unrelated services alone. For example, run Vite with `npm run dev -- --port 5175 --strictPort` and start this API with `FRONTEND_ORIGIN=http://localhost:5175` prefixed to its command. Both hosts must remain `localhost`. The unrelated 5173 service is left untouched; its URL is not this repository's frontend. The verified current production preview runs at [localhost:5175](http://localhost:5175), using API 8010 with that matching frontend Origin.

For an explicit diagnostic collection or stored projection (stop the API before manually collecting, so the supervisor remains the sole owner during normal operation):

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli collect-gdp
PYTHONPATH=backend .venv/bin/python -m app.cli read-gdp
PYTHONPATH=backend .venv/bin/python -m app.cli collect debt expenditure gst trade inflation inflation_policy market_nse market_bse market_status
PYTHONPATH=backend .venv/bin/python -m app.cli read-dashboard
```

Manual collection exits nonzero on failure/defer without deleting valid data or bypassing a cooldown. `read-dashboard` is local private-database administration; HTTP dashboard reads always require a valid bearer/session.

## Configuration and security

Server defaults/names are in `.env.example`; only `VITE_API_BASE_URL` is public. SQLite defaults to `data/dashboard.sqlite3` (0700 directory/0600 file), with numbered SQL migrations and `PRAGMA user_version`. Use the verified online backup/new-path restore commands in [the recovery runbook](docs/deployment.md) before schema changes; host backup scheduling/off-host storage remain deployment gates. Keep the file outside all frontend/static paths. Secrets, databases and generated output are ignored.

GDP uses a rolling 12-year input window ending in the previous UTC year. `GDP_START_YEAR`/`GDP_END_YEAR` override it; `GDP_REPORT_YEARS=5` controls display. Include a comparison year; at most 100 input years, within 1960–2199. Source gaps remain null. Newly omitted previously valid values retain original provenance and are labelled stale. India fiscal years and World calendar-year aggregates are visibly different. Dataset update, collection and unknown observation-release freshness stay distinct.

`MACRO_REPORT_YEARS=5` independently controls the additional macro reporting/history window (2–20; wider coverage is not guaranteed). Current verified CGA/trade/GST history supports five completed April–March FYs. `CGA/GST/TRADE/CPI/POLICY_COLLECTION_INTERVAL_SECONDS` configure each group; `COLLECTION_GROUPS` optionally selects implemented non-GDP groups (empty disables them). `COLLECTOR_ENABLED=false` disables all scheduling. Request attempts/timeouts and `COLLECTION_JOB_BUDGET_SECONDS` bound work. History retention is per group: latest 200 completed records plus last success and running records.

GST's comparable primary series excludes compensation cess, preserving original totals/cess definitions separately. Annual sums/averages require 12 published months; FYTD averages use actual published-month counts. Trade compares matching merchandise periods and calculates exports minus imports. CPI 2012/2024 bases remain separate; dated policy validity is independent. Original source/hash/status/publication/period/retrieval metadata and canonical summary/input references supply cards, charts, tooltips and tables without duplicated figures. Freshness assessment stays unknown where release calendars are not implemented.

`INFLATION_POLICY_URL` selects the reviewed official Gazette notification; no policy extension is assumed after expiry. `TRADE_HISTORY_URLS` accepts pipe-separated reviewed official PIB bootstrap references for older completed FYs. These need maintenance as the rolling window advances on a fresh database. TLS verification is always enabled; policy uses native system trust to resolve the observed issuer-chain failure. Verify source egress and the CA chain on the eventual API host before deployment.

Auth: 15-minute memory-only JWT, persistent server session with configurable absolute lifetime up to seven days, rotated HttpOnly refresh cookie, hashed token storage, session checks on every protected read. Pending/confirm delivery recovery and a 30-second settling window handle interrupted/concurrent refresh. Refresh never extends expiry. Valid bearer logout works without a cookie; conflicting identities are rejected. See [the complete auth/API contract](docs/contracts.md).

Local development explicitly uses matching loopback HTTP hosts and `dev_refresh` (HttpOnly, SameSite=Strict, Secure=false). Use **localhost for both URLs**, not a mix with 127.0.0.1. Ports do not isolate cookies; use trusted local services. Production requires separate HTTPS subdomains of `COOKIE_SITE_DOMAIN`, exact frontend Origin, and Secure `__Host-refresh`, Path=/, no Domain attribute. No production insecure-cookie override exists. Domain/DNS gates production verification, not local implementation.

Prepared hosting configuration: static frontend on Pages, FastAPI on one paid Render instance with a private persistent disk; [build/start commands and ready/blocked checklist](docs/deployment.md). Build the frontend with `VITE_API_BASE_URL` set to the actual HTTPS API URL. Set server `APP_ENV=production`, actual HTTPS origins/domain, secrets and disk-mounted `SQLITE_PATH`. Preserve the disk across deploys and verify private backup/restore. If a controlled domain is unavailable, select/verify the same-origin API proxy in the contracts; do not silently use cross-site provider cookies.

## Verification

```sh
.venv/bin/pytest -q
.venv/bin/ruff check backend tests
cd frontend
npm test
npm run format:check
npm run build
npm run test:browser
# To exercise compiled chunks rather than the dev server:
VITE_API_BASE_URL=http://localhost:8001 npm run build -- --outDir ../.verification/browser-dist
E2E_PREVIEW=1 npm run test:browser
```

Browser tests start/stop isolated fixture servers on localhost:5174/8001 and use real cookies with controlled clocks. The harness seeds all implemented providers exclusively from reviewed test fixtures and isolates independent failures. On macOS they use installed Chrome or `CHROME_PATH`; Linux CI installs the locked Playwright Chromium build. Fixtures/control endpoints never enter the normal app. The [verification matrix](docs/verification.md) covers renewal/reload/expiry, CSRF/revocation, concurrent tabs, interrupted responses, invalid/missing data, failure retention/recovery, restart persistence, disabled upstream networking and layout.

Optional live check: place **local-only** account credentials in ignored, owner-only `.verification/local-access.json` (`username`/`password`) and run `node scripts/smoke_local.mjs` with the normal servers running. Overrides: `LOCAL_SMOKE_CREDENTIALS`, `LOCAL_FRONTEND_URL`, `LOCAL_API_URL`, `CHROME_PATH`. It records economic-data-only evidence and ignored screenshots. Never commit credentials or use production credentials for this check.

Historical stdlib probes still run independently:

```sh
python3 scripts/probe_sources.py --environment local --output-dir .verification/local
python3 scripts/prove_gdp.py --input-dir .verification/local --output-dir .verification/gdp-local
```

Reproduce current live source-to-private-SQLite-to-authenticated-API evidence separately from normal application storage:

```sh
.venv/bin/python scripts/verify_sources.py --groups gdp expenditure gst trade inflation inflation_policy
```

This uses actual public responses and an ignored private proof database with random local accounts; it imports no test fixtures. See `scripts/source_fetch.py --help` for bounded per-URL diagnostics, including native CA diagnosis. Network-restricted execution may need outbound network permission; a documentation link or cached search result never establishes a collector.

## Engineering and submission records

- [Hardening findings, performance and design differences](docs/hardening.md)
- [Separate-environment deployment and recovery runbook](docs/deployment.md)
- [Requirements and deliverables](docs/requirements.md)
- [Architecture/dependencies](docs/architecture.md)
- [Decisions/outstanding inputs](docs/decisions.md)
- [API/data/session contracts](docs/contracts.md)
- [Source feasibility/access](docs/sources.md)
- [Verification/limitations](docs/verification.md)
- [Live GDP evidence](docs/evidence/2026-10-15/gdp-slice-live.json)
- [Multi-provider evidence and source limitations](docs/multi-provider.md)
- [Backend-stage checks](docs/evidence/2026-10-15/multi-checks.json)
- [Complete frontend/design acceptance](docs/frontend.md)
- [Frontend-stage checks](docs/evidence/2026-10-16/frontend-checks.json)
- [Normal full-interface live-data check](docs/evidence/2026-10-16/frontend-live.json)

Figma frame1:2 is inspectable through the browser's read-only Properties panel; additional edit access is not required. Connector edit restrictions remain specific to MCP. [Measurements, matched screenshots, loaded fonts and necessary content corrections](docs/design-completion.md) identify the provisional Segoe UI fallback. Comparable debt and the three real market indices now have proven source/storage/protected-API paths. Source access from the production host, public market display/redistribution acceptance, real domain/cookie setup, hosted recovery and final design acceptance remain pending. Submission still needs deployed URLs, evaluation credentials shared separately, portfolio/project roles and the post-assessment video.

`UPSTOX_ANALYTICS_TOKEN` belongs only in the ignored server `.env` or API secret manager. No `VITE_` equivalent. The free read-only Analytics Token was verified against actual quotes/status/timings; it does not authorise trading. Replace the credential supplied through chat before production. `MARKET_COLLECTION_INTERVAL_SECONDS` defaults30 (30–3600); `MARKET_REQUEST_TIMEOUT_SECONDS` defaults10. NSE has no verified latency SLA, so its fresh open-state label is Snapshot. Closed/live/delayed/stale classification uses exchange time and a verified schedule, not collection time. See [contracts](docs/contracts.md).
