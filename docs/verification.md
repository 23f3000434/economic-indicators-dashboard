# Local GDP slice verification

Run the commands in README from a locked checkout. This is local acceptance, not deployment or final design acceptance. Fixtures and clock/control endpoints exist only under `tests/`; the normal app imports none of them. The browser fixture server is a test harness on ports 8001/5174 and must never be deployed.

| Check | Evidence |
| --- | --- |
| Protected reads, login, generic failures, JWT/session checks, absolute maximum and expiry cap | `tests/test_auth.py`; browser sign-in and accelerated renewal/expiry |
| Reload and persistent HttpOnly cookie, automatic renewal without a login loop | Real browser cookies and controlled browser/server clocks; token storage remains empty |
| Bearer-only logout without cookie; conflicting/invalid identities; immediate revocation | Backend tests verify 204/409/401 and no mutation of conflicting sessions |
| Concurrent refresh with/without Web Locks; lost response before cookie, after cookie and at confirmation | Eight simultaneous backend refreshes; predecessor retry after an hour and a new Auth instance; browser abort/truncated-body/confirmation-loss cases converge on a valid successor |
| Retired reuse and logout/refresh races | Backend tests prove family revocation and rejection of already-issued JWTs; no path restores a revoked row |
| CSRF, exact Origin/CORS, JSON/custom headers, cookie attributes, throttling | Negative backend checks and production-config Secure/HttpOnly/Strict/host-only test. Real production HTTPS cookies remain unverified |
| Validation, canonical points, Decimal pp changes, legitimate zero, missing gaps | Backend source/missing-data tests; frontend selector test; browser card/table/tooltip and bar-gap checks |
| Rejection, timeout, invalid batch, stale retention and recovery | Injected failures preserve values and success timestamps; valid collection recovers. These are tests, not provider incidents |
| Supervised collection, no overlap, slow upstream isolation, shutdown/restart | Scheduler startup, persisted run state, cancellation/recovery, idempotency and restart checks |
| Database-only reads with upstream networking disabled | Outbound socket connect and HTTPX send replaced with assertions; protected reads and health still pass |
| Storage permissions and exposure | 0700 directory/0600 file, migrations/reopen, 503 readiness on missing storage, no static database route |
| Loading geometry, API error retention/retry, responsive layout | Initial read held while panel boxes compared (≤1 pixel); aborted polls, retry and null gaps; desktop 1214×2159 and mobile 390×844 without horizontal overflow |
| Real source → SQLite → protected HTTP → React | `scripts/smoke_local.mjs` uses a random local account and actual World Bank observations; public evidence in `docs/evidence/2026-10-15/gdp-slice-live.json` |

The live smoke records 11 checks against the production bundle after an API restart, no browser runtime errors, canonical card/table agreement, reload renewal and rejection of the old access JWT after logout. Ten local cached reads measured roughly 1–5 ms; this is a single-machine smoke measurement, not a load benchmark. Live GDP input is 2014–2025 (24 stored observations); five displayed source years are 2021–2025. India 2025 is FY 2025–26, World 2025 is CY 2025. Growth and pp changes derive from stored decimals, never SVG sample figures.

The build separates initial application code (about 235 kB / 74 kB gzip) from the lazy GDP/chart chunk (about 377 kB / 110 kB gzip). Self-hosted fonts add about 67 kB with OFL licences. No chart-size warning remains. The locked Starlette test adapter emits a deprecation warning for HTTPX; tests pass. No compatibility dependency was added solely to suppress a test warning.

Final result: **40 backend/source tests plus 9 subtests, 2 frontend selector/precision tests, 5 browser scenarios, production build, Ruff and formatting checks passed.** Commands/results are recorded in [slice-checks.json](evidence/2026-10-15/slice-checks.json). Screenshots, traces, credentials, `.env`, databases and raw source bodies stay ignored. Public evidence contains economic data and safe configuration attributes only.

Remaining gates: controlled domain/DNS/HTTPS and third-party-cookie-blocked browser check on actual hosting; private disk restart/redeploy/backup/restore; market feed access; other extractors; exact Figma inspection/full dashboard acceptance; complete submission URLs/account/portfolio/video. None is marked complete here.
