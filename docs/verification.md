# Local verification

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

Baseline 03aa914 result: **40 backend/source tests plus 9 subtests, 2 frontend selector/precision tests, 5 browser scenarios, production build, Ruff and formatting checks passed.** Commands/results are recorded in [slice-checks.json](evidence/2026-10-15/slice-checks.json). Screenshots, traces, credentials, `.env`, databases and raw source bodies stay ignored. Public evidence contains economic data and safe configuration attributes only.

At the GDP baseline, remaining gates were: controlled domain/DNS/HTTPS and third-party-cookie-blocked browser check on actual hosting; private disk restart/redeploy/backup/restore; market/debt source access; remaining frontend panels; exact Figma inspection/full dashboard acceptance; complete submission URLs/account/portfolio/video. None is marked complete here.

## Multi-provider stage

**73 backend/source tests plus 9 subtests, 2 frontend unit tests, 5 existing Chrome scenarios, TypeScript/Vite production build, backend Ruff and frontend formatting all pass.** See [recorded checks](evidence/2026-10-15/multi-checks.json). The browser suite first hit a restricted-runtime localhost bind error; rerunning with local binding enabled passed all five scenarios. It verifies existing GDP/auth behaviour; it does not claim new frontend panels.

| New verification | Evidence |
| --- | --- |
| Actual bytes, SHA-256, reviewed values, discovery and parser → SQLite → protected read | `tests/fixtures/providers/*/manifest.json`, provider test modules, per-source live proofs |
| Independent provider failure, slow scheduled request, stale retention/recovery, null gaps, restart persistence, network-disabled aggregate reads | `tests/test_dashboard.py`; HTTPX/socket calls are rejected during stored-only read checks |
| Delta-seconds/HTTP-date Retry-After, short wait/long deferral, durable cooldown shared by provider, slow dripping stream | `tests/test_collection.py` |
| Per-group retention regression | 205 frequent-group outcomes cannot erase GDP’s API last-success metadata or another running group; separate tests preserve each group’s last success |
| Units, actual-vs-estimate columns, source corrections/vintages, matching periods and Decimal arithmetic | CGA/GST/trade tests; five-FY sums, published-month averages, zero comparison, source rounding and expanded-window nulls |
| CPI methodology and policy separation | Current/old-base fixtures, no cross-base badge, unknown-base rejection, independent policy failure and validity expiry |
| Existing JWT/session behaviour | Original backend suite and all five Chrome scenarios rerun; authentication implementation unchanged |

[Final live proof](evidence/2026-10-15/multi-provider-live.json) collected every implemented group independently into one private proof database and read the protected aggregate. [Normal application proof](evidence/2026-10-15/local-multi-api.json) verifies live scheduled collection into persistent `data/dashboard.sqlite3`, API/health 200 and post-logout dashboard 401. Three local aggregate reads took roughly 23–43 ms; this is a smoke measurement, not a load benchmark. No test fixture entered either live database.

At b3ca864, debt (IMF 403/FRED timeouts), accepted market feed, production-host source/TLS tests, hosting/DNS/persistence/restore, frontend expansion and final Figma acceptance remained incomplete. Frontend expansion is now implemented below. The current local API runs at port 8010. Port 5173 belongs to another checkout and was left untouched; no frontend was launched or changed for this backend stage.

## Complete frontend stage

**77 backend tests plus 9 subtests, 6 frontend unit tests and 17 compiled-production Chrome scenarios pass.** TypeScript strict/unused checks, Vite build, Ruff lint, changed-Python-file formatting and frontend Prettier pass. Backend reliability checks exercise simultaneous storage/failure-recording outages in GDP/CGA without restarting, active SQL cancellation, exact scoped omissions, untouched older history and recovery. No auth implementation changed.

The browser matrix covers every connected panel, canonical cards/table/tooltips, controls, independent provider/policy failures, offline recovery, null segments and CPI bases, dated targets, expired/logout sessions, concurrent/lost refresh, keyboard/chart/table operation, component and compiled-chunk recovery, missing/empty data, 12-second reads, single-flight cancellation and all-slot loading geometry. Both 1214×2159 and 390×844 have no horizontal overflow or clipped headline values. The measured mobile loading shift was repaired; all six reserved heights match their populated state within 1px.

Figma frame 1:2 still denies design-context and screenshot access. The SVG was rendered and visually compared. Eleven local artwork assets pass source/output hashes, dimensions and decoded RGBA identity. Source and accurate-data differences, geometry and typography limits are documented in [frontend acceptance](frontend.md). [Checks](evidence/2026-10-16/frontend-checks.json) and [asset evidence](evidence/2026-10-16/design-assets.json) contain safe reproducible results; screenshots/traces remain ignored. Original-resolution artwork totals 10,891,124 bytes; main JavaScript is about 243kB/77kB gzip with a separate chart chunk about 404kB/117kB gzip. These are build measurements, not load/performance acceptance.

Debt/market feeds, exact Figma acceptance, production-domain browser checks, separate hosting/private disk/redeploy/backup/restore and submission deliverables remain open.

The normal application factory was restarted with its existing private database and `FRONTEND_ORIGIN=http://localhost:5175`; no fixtures were seeded. The production frontend at 5175 and API at 8010 pass 11 live-data checks, including ten canonical headline/table values across all implemented panels, login/reload, API-only traffic, no runtime errors and post-logout protected 401. [Live UI evidence](evidence/2026-10-16/frontend-live.json) preserves collection metadata and actual unavailable ticker states. Five local aggregate reads measured roughly 18–39ms; this is a smoke measurement. The unrelated service on 5173 remains untouched. Four focused compiled-browser checks additionally pass after the final explicit GDP FY/CY table headings and available-year label correction.
