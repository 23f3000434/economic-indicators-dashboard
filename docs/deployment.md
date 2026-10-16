# Free deployment and recovery

The user requires a strict zero budget. Vercel Hobby frontend, Render Free FastAPI and Render Free PostgreSQL supersede Pages, paid Render, persistent disks and purchased domains. Actual resources and acceptance are recorded in [free-deployment.md](free-deployment.md); prepared configuration is not proof of a working hosted application.

## Deployment sequence

1. Confirm Hobby/free plans, no payment method or paid overage/add-on, and access limited to this repository. The inspected Render workspace has no card and $0 accrued/projected charges. Quotas are shared with its other projects; never change or suspend unrelated services. Vercel's Hobby project uses the basic build machine and disables paid on-demand concurrent builds.
2. Create one **Free, 1 GB PostgreSQL** database in Oregon. Remove every resource-level inbound IP rule and confirm **all internet traffic blocked**, even if a workspace rule says everywhere. Do this before attaching application data. Use the same region for the API and only the internal connection URL. Do not temporarily open external access for tests, provisioning or backups. The created instance is `dpg-db8vao67bikc73bdm49g-a` (PostgreSQL18), expiring **15 November2026**.
3. Create a **Free** Python API, one worker/instance, no disk/cron/worker/add-ons. Build: `sh deploy/build_api.sh`; start: `sh deploy/start_api.sh`; health: `/healthz`; automatic deploys off during acceptance. `render.yaml` is a reproducible blueprint for a new environment; do not sync it over the manually created database and accidentally create a duplicate.
4. Configure server environment only: `APP_ENV=production`, `DATABASE_URL` from the internal database connection, `AUTH_COOKIE_MODE=frontend_proxy`, exact `API_ORIGIN` and `FRONTEND_ORIGIN`; three distinct stable `JWT_SECRET`, `CSRF_SECRET`, `ROTATION_SECRET`; rotated `UPSTOX_ANALYTICS_TOKEN`; `SESSION_MAX_AGE_SECONDS=604800`; `COLLECTOR_ENABLED=true`. Preserve keys across restarts. Set the private evaluator bootstrap pair described below. Never expose any of these secret values in Git, logs, Vercel, chat or screenshots.
5. Deploy the reviewed commit. `app.serve` rejects ephemeral SQLite/external DB hostnames and starts one worker. Lifespan applies checksummed SQL migrations under a database lock. A separate advisory lease and persisted generation fence allow only one collector owner; a brief standby serves stored reads without interrupting active work. Normal collectors populate the new database using actual sources; do not upload the workstation database or fixtures.
6. With the actual HTTPS API URL, configure the three **public** Vercel build values below. Generate routing locally, review and commit the result:

```sh
VITE_API_BASE_URL=https://<actual-api>.onrender.com FRONTEND_ORIGIN=https://economic-indicators-dashboard-iota.vercel.app VITE_AUTH_SAME_ORIGIN_PROXY=true node deploy/configure_vercel.mjs
```

`vercel.json` deliberately requires a known API URL and is not fabricated while service creation is blocked. The generator refuses overwriting an existing file. It rewrites only `/api/v1/auth/:path*`, adds security headers/CSP and immutable asset caching. No dashboard/ticker rewrite or wildcard upstream proxy is generated. Commit this public configuration before deploying. Vercel builds refuse an auth destination differing from the compiled API URL.

7. Vercel project root is the repository; install `npm ci --prefix frontend`, build `node deploy/build_frontend.mjs`, output `frontend/dist`, Node22.x. CI/local builds pin22.23.3; Vercel manages the22.x patch and records it in public `build-config.json`. Locks remain frozen. Configure `VITE_API_BASE_URL`, `FRONTEND_ORIGIN`, `VITE_AUTH_SAME_ORIGIN_PROXY=true`; never copy the API `.env`. Remove the additional project SSO gate only with the explicit pending approval, keeping application login mandatory.
8. Execute the bounded [production smoke](production-smoke.md), including source access from Render, Secure refresh-cookie routing, concurrent refresh, logout, source-to-screen, database privacy and an API restart. Record actual URLs/results. A healthy API with a required unavailable provider is incomplete data acceptance.

## Authentication across provider domains

Cookie actions use relative frontend URLs, which Vercel forwards to FastAPI unchanged. FastAPI's Secure/HttpOnly/Strict host-only `__Host-refresh` is therefore stored on the frontend host. Same-origin session bootstrap uses **POST**, JSON and `X-CSRF-Protection:1`, so the browser supplies its real Origin. The proxy must preserve Origin, Set-Cookie and no-store; never manufacture trusted Origin or remove CSRF checks. Refresh/confirm/logout also require the session-bound CSRF token (valid bearer logout remains supported). Fifteen-minute JWTs stay in memory; the seven-day deadline is absolute.

Dashboard/ticker requests go **directly to Render**, bearer authenticated, with credentials omitted. CORS allows only the exact frontend origin. Third-party cookies, SameSite=None, insecure production cookies, wildcard CORS and DNS purchases are unnecessary. Local loopback mode is explicitly separate.

`TRUSTED_PROXY_CIDRS` defaults empty, ignoring spoofable forwarding headers. Only configure actual reviewed ingress addresses; Render outbound ranges are not proxy trust. With trust unset, the in-process login limiter can share a proxy IP across users; server sessions/Origin/CSRF remain authoritative. Do not enable wildcard/default-route trust to change this.

## Configuration names

| Location | Names |
| --- | --- |
| API required | `APP_ENV`, `DATABASE_URL` (internal, secret), `AUTH_COOKIE_MODE`, `API_ORIGIN`, `FRONTEND_ORIGIN`; host `PORT` |
| API secrets | `JWT_SECRET`, `CSRF_SECRET`, `ROTATION_SECRET`, replacement `UPSTOX_ANALYTICS_TOKEN` |
| Evaluator bootstrap | `BOOTSTRAP_USERNAME`, `BOOTSTRAP_PASSWORD_HASH` (Argon2id only); create-if-absent, never overwrites/reactivates an account |
| Session/collection | Existing `.env.example` intervals, rolling/reporting windows, `SESSION_MAX_AGE_SECONDS`, `REFRESH_SETTLE_SECONDS`, budgets and reviewed policy/appendix/history URLs |
| Vercel public build | `VITE_API_BASE_URL`, `FRONTEND_ORIGIN`, `VITE_AUTH_SAME_ORIGIN_PROXY=true`; managed Node22.x |
| Local only | `SQLITE_PATH`, loopback origins and `dev_refresh`; no production ephemeral SQLite |

## Free lifecycle and collection

Render Free sleeps after15 minutes without inbound traffic; wake can take roughly a minute. Browser requests retain their12s deadline and useful retry state. Collectors do **not** run while asleep. One task per provider/group checks persisted due times after wake, coalesces missed intervals and honours Retry-After cooldowns. Macro releases default daily; GDP/debt/policy weekly; quotes/status30s while awake. No paid cron, external keepalive service or promise of continuous collection is configured. Old observations preserve their reporting/publication/retrieval dates and stale/retained labels.

Render's750 instance-hours, bandwidth and build allowance are shared across the workspace. Without a card, excess use suspends service; never enable a paid fallback to preserve availability. Vercel Hobby is for this personal, noncommercial assessment and suspends/restricts over-limit usage. See [Render free limits](https://render.com/docs/free) and [Vercel Hobby](https://vercel.com/docs/plans/hobby).

Free PostgreSQL expires after30 days, becomes inaccessible, and is later deleted unless upgraded. The created database expires15 November2026. **No upgrade is authorised.** This is a time-limited evaluation deployment, not indefinite persistence. No managed free database backup exists. Restart persistence within that lifetime must be tested; it does not prove survival after expiry.

## Consistent backup and restore

Local SQLite online backup/isolated restore remains supported and tested:

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli backup .verification/backups/unique.sqlite3
PYTHONPATH=backend .venv/bin/python -m app.cli restore .verification/backups/unique.sqlite3 .verification/restore/private/dashboard.sqlite3
```

The command uses SQLite's backup API, private permissions, integrity/schema checks and exclusive publication; restore removes saved sessions. It refuses PostgreSQL rather than copying a nonexistent local file.

Free Render has no shell/SSH/one-off jobs or managed PostgreSQL backup. No private off-host PostgreSQL backup/export has been implemented or verified. Keep external ingress disabled. Before expiry, evaluation must finish or a separately authorised free recovery/export arrangement must be established. Published macro history can be recollected into a new private database; unrecoverable accounts, sessions, retained vintages and collection history must not be claimed preserved without a real backup. Fresh databases require fresh evaluator provisioning; never load test fixtures as recovery data.
