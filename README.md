# Economic Indicators Dashboard

React/TypeScript + FastAPI dashboard with six economic panels, a three-index market ticker, private persistent SQLite and refreshable server-revocable authentication. Scheduled collectors validate upstream responses independently of browser requests. Every card, chart, tooltip and table resolves canonical observations and backend comparison references.

**Implemented and locally verified:** GDP, comparable India/US general-government debt, merchandise trade, gross GST excluding compensation cess, combined CPI with dated inflation policy, CGA actual expenditure, NSE NIFTY BANK/IT and Upstox BSE SENSEX snapshots. These are working source → storage → protected API → UI paths, not placeholder unavailable panels. Production hosting/source access is a separate acceptance step. [Delivery status and remaining inputs](docs/delivery-status.md).

The measured Figma frame is reproduced at 1214 × 2159 CSS pixels with six fixed 544-design-pixel panels. Extended data/provenance and controls use accessible dialogs. The user accepted the **Roboto fallback for Segoe UI** on 16 October 2026; this is a disclosed typography difference, not an exact-font claim. Real units, periods and observations necessarily correct illustrative design figures. [Measurements, screenshots and differences](docs/design-completion.md).

## Run locally

Use Python **3.12.14**, uv **0.10.2**, Node **22.23.3** (`.python-version` / `.node-version`) and npm. Locks are `uv.lock` and `frontend/package-lock.json`. From the repository root:

```sh
uv sync --frozen --python 3.12.14 --cache-dir .verification/uv-cache
.venv/bin/python scripts/setup_local.py
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/python -m app.cli create-user analyst
npm ci --prefix frontend --cache .verification/npm-cache
```

Setup exclusively creates ignored owner-only `.env`, three distinct server secrets and `frontend/.env`; it refuses to overwrite existing secrets. Do not copy `.env.example` with blank secrets over an existing installation. User creation prompts for a password of at least 12 characters; there is no default account. Preserve `.env` and `data/` across restarts. Existing installations skip setup and user creation.

Run these in separate terminals:

```sh
# API, repository root
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:create_app --factory --host localhost --port 8010 --workers 1 --no-access-log
```

```sh
# Frontend, repository root
npm run dev --prefix frontend -- --port 5173 --strictPort
```

| Local service | URL |
| --- | --- |
| Frontend, default clean setup | http://localhost:5173 |
| Current verified preview in this workspace | http://localhost:5175 |
| API / interactive route documentation | http://localhost:8010/docs |
| OpenAPI | http://localhost:8010/openapi.json |
| Health | http://localhost:8010/healthz |

Port 5173 currently belongs to an unrelated checkout: leave it alone. To use 5175, pass `--port 5175` to Vite and prefix the API command with `FRONTEND_ORIGIN=http://localhost:5175`. Both hosts must be `localhost`; mixing 127.0.0.1 and localhost breaks the cookie/origin assumptions. For a compiled local preview, build with `VITE_API_BASE_URL=http://localhost:8010 npm run build --prefix frontend`, then `npm run preview --prefix frontend -- --port 5175 --strictPort` with the matching API Origin.

The initial empty database is populated by independent startup collectors. A missing market credential leaves those affected snapshots unavailable; it does not invent quotes or disable macro panels. Configure a replacement read-only `UPSTOX_ANALYTICS_TOKEN` only in the ignored server `.env` or API secret manager. Never put it in a `VITE_` variable, browser code, command-line argument or Git. The chat-supplied credential must be replaced before production. Accepted collection/display terms remain a release input.

## Data and request flow

1. One supervised task per group fetches bounded upstream responses, validates identities/periods/units/status/consistency, then commits a short SQLite transaction. GDP/debt/policy default weekly; CGA/GST/trade/CPI daily; quotes/status every 30 seconds. Durable provider cooldowns and independent last-success/history survive restart.
2. Protected FastAPI reads use SQLite only. A source timeout does not delay a dashboard request. Failed or scoped-omitted observations retain original provenance and become stale; never-seen missing observations remain null.
3. React polls `/api/v1/dashboard` each minute and `/api/v1/ticker` every 30 seconds while visible, with cancellation and single-flight requests. Browser connection failures retain the prior screen with a notice. “Refresh view” reads storage; it never calls a provider.
4. Backend Decimal comparisons and canonical summary references drive cards/charts/compact shared tooltips/Details tables. Missing values display `—` and chart gaps. Period/legend controls operate on those same observations.

NSE principally supplies NIFTY BANK/IT; Upstox supplies BSE SENSEX, exchange status and dated session timings. Live/Snapshot/Delayed/Stale/Closed follow actual exchange times and the verified schedule. NSE snapshots have no latency SLA and are never described as streaming. Quote refresh does not restart continuous scrolling; hover/focus/reduced-motion and manual scrolling are supported. [Source catalogue](docs/sources.md) and [complete contracts](docs/contracts.md).

GDP input is a rolling 12-year window ending in the previous UTC year, with configurable collection/reporting windows. India GDP/debt FY differs from World/US CY. Debt retains IMF vintage and actual/estimate status. GST averages use published months; ex-cess methodology is consistent. Trade compares matching merchandise periods with signed exports minus imports. CPI bases remain separate; policy applies only during its legal validity. CGA actual revenue + capital reconciles to total, excluding BE/RE. Publication, observation, dataset-update and collection times remain distinct; unknown economic freshness stays unknown.

## Authentication, storage and deployment

Login returns a 15-minute access JWT held only in memory. A persistent session has a configurable absolute lifetime of at most seven days. HttpOnly refresh cookies and hashed active/pending/retired tokens support rotation, concurrent tabs and lost-response recovery. Server-side session checks immediately revoke associated JWTs on logout. Account/logout changes clear authenticated data/dialogs; CSRF uses exact Origin, JSON/custom headers and session-bound tokens. [Auth/API request and response contracts](docs/contracts.md#selected-authentication-contract).

Local mode uses `dev_refresh`, HttpOnly/Strict without Secure on loopback HTTP. Production requires **separate same-site HTTPS subdomains** on different hosting environments, with Secure host-only `__Host-refresh`, exact-origin credentialed CORS and no insecure override. API secrets stay server-only. SQLite has no network listener or public/static route; directories/files use 0700/0600 and queries bind parameters.

Approved delivery: **Cloudflare Pages frontend + one paid Render API instance with a 1 GB private persistent disk**, locked allowlisted runtime and a single SQLite owner. `render.yaml` and `deploy/` prepare reproducible builds. The real parent domain, origins, proxy trust, host source access and cookies must be verified; provider domains alone are not the accepted cookie arrangement. [Deployment/configuration/backup/restore instructions](docs/deployment.md), [bounded production acceptance](docs/production-smoke.md). No public deployment is claimed until that checklist has actual results.

## Verification

```sh
.venv/bin/pytest -q
.venv/bin/ruff check backend tests deploy
npm test --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
.venv/bin/python scripts/verify_design.py
node deploy/check_frontend.mjs
```

For one sequential compiled browser suite:

```sh
# Linux: first run `npx --no-install playwright install --with-deps chromium` inside frontend.
VITE_API_BASE_URL=http://localhost:8001 npm run build --prefix frontend -- --outDir ../.verification/browser-dist --emptyOutDir
E2E_PREVIEW=1 npm run test:browser --prefix frontend
```

Browser tests own isolated ports 5174/8001; do not overlap invocations. macOS uses installed Chrome or `CHROME_PATH`; Linux uses locked Playwright Chromium. Fixtures, synthetic clocks and failure controls exist only under tests and are excluded from the production runtime. Live proof scripts instead use actual providers and ignored private databases; see `scripts/verify_sources.py --help` and `scripts/verify_market_flow.py --help`. Do not use the local smoke script with production credentials.

[Verification record](docs/verification.md) distinguishes passed tests, historical failures/repairs, current source-to-screen evidence and production-unverified checks. [CI](.github/workflows/checks.yml) installs locked dependencies and runs offline regressions/build/delivery checks; it does not deploy or fetch live providers.

## Submission and engineering records

- [Submission handoff and assignment deliverables](docs/submission.md)
- [Current delivery status / URLs / external inputs](docs/delivery-status.md)
- [Private evaluation-access procedure](docs/evaluation-access.md)
- [Actual AI-assisted workflow and verification](docs/ai-workflow.md)
- [Assumptions and known limitations](docs/assumptions.md)
- [Architecture and dependency decisions](docs/architecture.md), [decision/evidence log](docs/decisions.md)
- [Requirements](docs/requirements.md), [API/data/session contracts](docs/contracts.md), [sources](docs/sources.md)
- [Measured design and screenshots](docs/design-completion.md), [frontend](docs/frontend.md)

The repository is private; evaluator repository access must be granted separately. Portfolio/project links are supplied by the user outside this repository. The brief also requires a screen-recorded explanation **after assessment**; that is a tracked external submission deliverable, not a recording already produced here. No interview rehearsal is included.
