# Deployment and recovery readiness

Final delivery/deployment from 596e4a7 is authorised. The approved arrangement is separate Cloudflare Pages frontend and one paid Render API on HTTPS subdomains of a controlled domain, with private persistent SQLite. No project cloud service or public deployment has been created yet. All debt/market paths are implemented locally; actual host source access/display permission, domain/security/storage acceptance and evaluation handoff remain unverified. The user accepted the documented Roboto fallback on 16 October; exact Segoe typography is not claimed. See [current release inputs and URLs](delivery-status.md).

## Reproducible delivery

**API:** `render.yaml` prepares one paid Python service/instance with a 1 GB private persistent disk at `/var/data`. Python 3.12.14 and uv 0.10.2 are pinned. `sh deploy/build_api.sh` assembles `.delivery/api` from only `backend/app`, SQL migrations and dependency metadata, then runs `uv sync --frozen --no-dev --no-install-project`. Tests, fixtures, `.env`, source probes, local data, frontend and development dependencies do not enter that runtime. It is the ordinary application, not a fixture mode. `sh deploy/start_api.sh` changes into that runtime and starts `app.serve`.

The production entry requires a real mounted persistent directory, SQLite in its private subdirectory, production settings, and explicit trusted proxy IP/CIDR entries. It binds the provided `PORT` on `0.0.0.0`, disables access logs containing request paths, forces one Uvicorn worker, and holds an OS file lock before migrations/recovery. A duplicate process fails before it can mark another process's active runs interrupted. Lifespan applies idempotent migrations only after the runtime disk is available, then starts independent supervised collectors. Readiness is `/healthz`; upstream failures do not make a healthy stored-read service unavailable.

Use native Python here: it fulfils locked separate-host delivery without introducing a container build/runtime. Render's base OS is managed, so Linux TLS/source egress and filesystem acceptance still need hosting verification. Docker would offer tighter OS pinning but is not required for this assignment. No Docker build is claimed. [Render supports explicit Python/uv versions](https://render.com/docs/python-version) and [Blueprint service/disk configuration](https://render.com/docs/blueprint-spec). Its [disk constraints](https://render.com/docs/disks) mean migrations cannot run at build/predeploy time, one-off jobs/other services cannot access this disk, and redeploys incur downtime. Collection remains inside the API service.

**Frontend:** Pages project repository root is this repository; framework preset None; build command `node deploy/build_frontend.mjs`; output `frontend/dist`; Node `22.23.3` via `NODE_VERSION` (also `.node-version`); the build checks the exact version. The script runs `npm ci`, validates the concrete same-site HTTPS origins, compiles `VITE_API_BASE_URL`, and writes origin-specific CSP/security/cache rules in `_headers`. It rejects localhost, HTTP, foreign sites, URL paths/credentials/ports and identical frontend/API hosts. Runtime environment changes cannot repair a wrong Vite build; rebuild instead. Immutable caching applies only to hashed bundles/artwork, while HTML/config revalidate. The engineering asset manifest stays in Git and is removed from public deployment output. Self-hosted fonts/assets require no external image/font policy exceptions; chart inline styles require the explicit style policy. [Pages build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/) and [static headers](https://developers.cloudflare.com/pages/configuration/headers/) describe the host settings.

No Pages Functions or proxy was added. The previously documented same-origin API proxy remains an alternative only if the controlled-domain arrangement cannot be supplied. Do not switch to cross-site provider-domain cookies or browser-persistent JWTs.

## Deployment sequence

1. Select the controlled parent domain and use `dashboard`/`api` subdomains. In Pages, attach the custom domain in the project **before** creating its required CNAME; follow the actual DNS target shown by Pages. Apex delegation is not required merely to use a subdomain at an external DNS provider. For the API, add its Render custom domain and the exact verification/CNAME records shown there. Do not change unrelated records or buy a domain without a selected domain/budget. [Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/), [Render custom domains](https://render.com/docs/custom-domains).
2. Connect this private repository to each approved hosting account with access limited to this repository. Create the Render service from the reviewed `render.yaml`: legacy `starter` remains valid (`0.5c-512mb`,0.5 CPU / 512 MB), one instance,1 GB disk. Review current host billing before creating the paid service; no additional services/subscriptions are part of this plan. [Current plan IDs/legacy compatibility](https://render.com/docs/compute-plans). Keep auto-deploy off until acceptance.
3. Configure actual production origins/site, reviewed ingress trust and server-only secrets in Render. The blueprint now explicitly prompts for `UPSTOX_ANALYTICS_TOKEN`; use a rotated read-only credential under the accepted display arrangement. Generate the three distinct auth secrets once; preserve them across redeploys. Validate the mounted private directory and do not migrate at build/predeploy time.
4. Deploy the exact reviewed commit, wait for health and allow independent collectors to populate the mounted database. Verify each provider's actual response/validation/stored projection; a healthy API with required unavailable panels is not full data acceptance. Provision the private evaluator interactively on the disk owner. Do not transfer this workstation's database or credential file as a shortcut.
5. Configure Pages with the three public build-origin values and pinned Node version below, build the same commit and attach/verify HTTPS on the frontend domain. Verify `_headers`, public build origin, CSP and no test data/local URLs. Do not copy server environment variables into Pages.
6. Run the [bounded production smoke](production-smoke.md), including actual cookie renewal, two ticker polls and controlled API restart persistence. Record only observed results/URLs in delivery-status.md. If hosting inputs are absent, leave deployment pending rather than publishing cross-site provider URLs with broken refresh cookies.
7. Configure private off-host backup operation and share the evaluation account/URLs separately. The owner handles repository evaluator access and external portfolio/recording deliverables; see submission.md.

## Configuration names, never secret values

| Location | Names / purpose |
| --- | --- |
| Render required | `APP_ENV=production`, `API_ORIGIN`, `FRONTEND_ORIGIN`, `COOKIE_SITE_DOMAIN`, `SQLITE_PATH=/var/data/private/dashboard.sqlite3`, `PERSISTENT_DATA_DIR=/var/data`, host `PORT`, `TRUSTED_PROXY_CIDRS` |
| Render secrets | Server-only read-only `UPSTOX_ANALYTICS_TOKEN` (rotate the chat-supplied token before production); distinct `JWT_SECRET`, `CSRF_SECRET`, `ROTATION_SECRET`, generated once through the host/secret manager. Preserve across normal redeploys; back up separately and privately. No `VITE_` prefix |
| Session | Fixed 900s access JWT in memory; `SESSION_MAX_AGE_SECONDS` at most 604800; `REFRESH_SETTLE_SECONDS` 25–120. Production cookie is Secure/HttpOnly/Strict `__Host-refresh`, host-only, Path=/ |
| Collection | `COLLECTOR_ENABLED=true`; per-group intervals, rolling/reporting windows, request/attempt/job budgets and reviewed policy/history URLs in `.env.example`; browser traffic never changes these |
| Pages build | `NODE_VERSION=22.23.3`, `VITE_API_BASE_URL` (API HTTPS origin), `FRONTEND_ORIGIN`, `COOKIE_SITE_DOMAIN`. These are public configuration; no API secrets or credentials belong here |
| Local only | Existing loopback `.env` and `dev_refresh` cookie remain separate. Production cannot enable the insecure local cookie |

`TRUSTED_PROXY_CIDRS` must come from the reviewed actual ingress chain, not Render outbound IP ranges. The entry point rejects wildcard/default-route trust. Verify that spoofed forwarding headers from untrusted peers are ignored and that actual proxy-added client addresses support the per-IP login limiter. Platform ingress trust is unresolved until the hosting environment is inspected; do not guess broad ranges to pass startup. Exact-origin credentialed CORS, Origin/custom-header CSRF and server-side revocation remain authoritative.

## Consistent backup and restore

The CLI uses SQLite's online backup API, not a live file copy. It writes a private staged file, enforces a 30s budget, validates application schema/integrity/foreign keys, fsyncs, and exclusively publishes a mode-0600 snapshot into a mode-0700 directory. Existing destinations, public directories, corrupt and newer-schema snapshots are refused. Backups contain password hashes/session material and must remain private, even though observations are public. Never serve the disk or backup path as static content.

Run inside the assembled API runtime on the disk-owning service (or use the corresponding local `.venv`/`PYTHONPATH=backend`):

```sh
umask 077
mkdir -p /var/data/backups
chmod 700 /var/data/backups
PYTHONPATH=backend .venv/bin/python -m app.cli backup /var/data/backups/snapshot-UNIQUE.sqlite3
PYTHONPATH=backend .venv/bin/python -m app.cli restore /var/data/backups/snapshot-UNIQUE.sqlite3 /var/data/private/restored-UNIQUE.sqlite3
```

Restore writes a **new** path and upgrades older supported schemas; it never overwrites the active database. It removes all restored sessions/refresh tokens, preventing a saved session from resurrecting access revoked since the backup. Users/password hashes, canonical observations/provenance/retention, run history and cooldowns survive. All users must sign in again. A backup may also contain old account/password state; review active users and reset affected passwords as part of incident recovery. Secrets are not included in the SQLite snapshot and must be recovered through the secret manager.

Recovery sequence: take a fresh backup if possible; stop the old API; restore to a new private disk path; validate output; point `SQLITE_PATH` at it; start exactly one API; confirm health, fresh login, old-token rejection, stored dashboard/source timestamps, independent collection recovery and a second restart. Keep the prior database private until acceptance; change configuration back only under the same stopped-service procedure. Do not roll back SQLite by copying an inconsistent disk snapshot or blindly restore old server secrets.

Proposed operation: daily consistent snapshots, seven daily copies plus a pre-migration copy, encrypted private off-host storage, and a periodic restore drill. A same-disk backup does not protect against disk/account loss. Bucket/location, encryption/access policy, schedule/alert ownership and retention are pending operational inputs; no scheduled backup or off-host upload is claimed. A separate Render cron cannot access the API disk; invoke administrative backup in the disk-owning environment.

## CI and evidence boundaries

`.github/workflows/checks.yml` pins Actions to official verified commit IDs and uses locked Python/npm/browser dependencies. Dependency/action/browser downloads and the npm advisory lookup need network; application checks use fixture/mock responses and no live providers. It runs backend/auth/collector/recovery/delivery tests, frontend units/format/build, artwork hashes, deployment-origin/CSP checks, an allowlisted API dependency boundary and compiled Chrome-compatible browser scenarios. Linux uses Playwright's bundled Chromium; local macOS uses installed Chrome or `CHROME_PATH`. A fresh subprocess proves the normal API imports no tests, exposes no test controls, returns 401 for unauthenticated dashboard access and 404 for test endpoints. Production bundle checks reject test data/control routes/local API URLs.

The workflow requires no deployment or live-provider secrets. Local historical results are recorded in verification.md; actual remote runs are tracked in delivery-status.md after push. Pages rule application and Render acceptance require the real release inputs. A GitHub push/green offline suite does not itself deploy the application or prove cloud source access.

## Ready / blocked checklist

| Gate | State |
| --- | --- |
| Local authenticated dashboard, canonical data and independent collection regressions | Verified locally; see hardening evidence |
| Deterministic display assets and desktop/mobile cold transfer/screenshot checks | Verified locally |
| Existing-schema migration, online consistency and isolated restore/revocation | Verified locally, including a read-only snapshot of the ordinary private DB |
| Locked API assembly, one-owner entry, static build/origin/CSP rules, offline CI definition | Prepared; local commands checked as recorded |
| Public deployment authorisation | Authorised from 596e4a7; create only with actual release inputs and record hosted acceptance |
| Controlled parent domain, actual two hostnames, DNS/HTTPS/account/project access | Required input |
| Actual proxy CIDRs/chain, mounted disk identity/ownership and restart/redeploy persistence | Hosted acceptance pending |
| Linux verified TLS and each provider's egress/discovery/history behaviour | Hosted acceptance pending |
| Real-domain cookies with third-party cookies blocked; exact CORS/CSRF/reload/concurrent tabs | Hosted acceptance pending |
| Private off-host backups, operational schedule/alerts and restore drill on host | Required setup/input |
| Comparable debt and real NSE/BSE source-to-storage-to-API/UI paths | Verified locally; market public-display/redistribution and host egress acceptance remain pending |
| Figma frame1:2/design | Browser Properties, measured geometry and source artwork verified locally. User accepted Roboto fallback; disclose typography and real-data corrections |
| Evaluation URLs/account, portfolio roles/links, post-assessment video | Final submission inputs |
