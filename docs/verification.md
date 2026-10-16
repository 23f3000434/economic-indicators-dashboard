# Current completion verification

Completion stage from af5ff07: measured Figma reproduction, real market snapshots, comparable debt and official-release/source-to-screen verification. Public deployment remains pending. The dated sections below are historical checkpoints; their former debt/market/Figma gates are superseded by the current completion evidence in [design-completion.md](design-completion.md).

- Backend: **107 tests + 9 subtests passed in 41.22s**, including GDP/authentication, provider isolation/cooldowns, retention, strict parsers, annual debt gaps and schema 4 recovery.
- Frontend: **14 units pass**; strict TypeScript, production builds, formatting, locked dependencies and zero npm audit findings are checked. Actual source/style font inspection distinguishes Roboto/Manrope from the provisional Segoe fallback.
- Compiled browser acceptance covers full canonical panels, drawers/controls, nulls, source and browser failures, lazy/component recovery, fixed geometry, ticker polling, authentication/reload/renewal/expiry/revocation and concurrent/interrupted sessions. Final requested sequence: cross-tab dialog regression **1/1 passed (25.5s)**, then complete suite **22/23 passed (5.6m)** with one 35-second test deadline during held-confirmation setup. Its second tab used wall-clock time against the fixed first-tab/server clock; align that fixture clock without changing assertions. Only that case was rerun: **1/1 passed (31.8s)**. No second full suite followed the fixture repair; a fully green final full-suite result is not claimed.
- Normal application: actual provider data in private persistent SQLite; 12 default card/table agreements plus 6 current-release agreements, automatic ticker refresh with advancing source retrieval, API-only data traffic, reload/HttpOnly persistence, mobile layout, and logout401. No test harness/fixtures seed that database.
- Real markets: actual closed-session responses/protected reads, actual open-session SENSEX/NSE snapshots, explicitly injected NSE timeout, actual rejection of a regressing cached timestamp, original quote provenance retention, real recovery and network-disabled stored reads/restart proof.
- Online normal-database backup/isolated restore: 412 observations, 3 quotes, 2 status/schedule snapshots and run/cooldown/user records preserved exactly; restored sessions removed; source snapshot unchanged; 0700/0600 permissions. The active database was never restored or overwritten. [Evidence](evidence/2026-10-16/recovery-v4.json).
- Delivery: locked 27-package API runtime excludes pytest/Pillow/tests/fixtures; production frontend origin/CSP/hash guards pass with non-deployed example domains. SVG artwork renders under the unchanged production image/font policy; test-only API connection origin is mapped locally. No cloud resources or DNS were changed.

Precise screenshots, transfer measurements, source definitions and remaining inputs are in [design-completion.md](design-completion.md). Exact Segoe UI font acceptance and real-host/domain/market-display acceptance remain open. Existing Starlette HTTPX deprecation and rotated-PDF diagnostics are reported, not hidden.

## Final logout checkpoint

The cross-tab regression first reproduced a retained authenticated market dialog: `toHaveCount(0)` received one dialog after logout. Keying the ticker subtree by the authenticated session identity unmounts that dialog on logout/account change. The original strict zero-dialog assertion, sign-in visibility and zero-ticker-item assertions remain intact. GDP/panel subtrees and session-owned reads retain their existing clearing/cancellation behaviour.

The final commands used the compiled production bundle with test-only servers on 5174/8001, one Playwright worker and no overlapping browser invocations. The prior in-flight suite was allowed to close before the requested focused → full sequence. An earlier overlapping invocation had caused a trace-file ENOENT; it is distinct from the final held-confirmation timeout. The timeout trace/screenshots remain in ignored verification storage. No application authentication behaviour or timeout/expectation limits were relaxed. The earlier compiled run passed 23/23; it does not replace the final 22/23 result. Backend/unit/delivery/performance checks above were already performed during this stage and were not repeated at the finish checkpoint.

See [completion-checks.json](evidence/2026-10-16/completion-checks.json) for the exact final command results and remaining gates. The local normal-API build is refreshed after the focused rerun; no public deployment occurs.

## Focused interaction pass after a59bb96

- **10 focused compiled-browser scenarios passed in 2.4m**: canonical values and fixed geometry across all six panels, keyboard/Details access, CPI gaps/policy validity, market failure retention/recovery, unchanged cross-tab logout assertions, reload/memory-only authentication, pointer period changes, shared tooltips, missing bars, mobile tap/dismissal and ticker pause/manual/reduced-motion/two-poll phase continuity.
- Browser inspection then measured a 325px trailing ticker spacer. A scoped flex correction removes it; the ticker case, including a new boundary-gap assertion, **passed 1/1 in 28.7s**. Other application behaviour was unchanged; unaffected tests were not repeated.
- After the band-centre repair, pointer/grouped-bar and mobile tap cases **passed 2/2**. The added alignment assertion initially used an obsolete tick selector and timed out; correcting it to the rendered label layer preserved the coordinate assertion, and the six-panel case **passed 1/1 in 24.9s**. Crosshair and last source-year tick both measure x=482.5 in the normal GDP chart. No final interaction assertion remains failing.
- **3 tooltip-placement unit tests passed**; strict TypeScript and compiled builds for the test API and normal API passed. No dependencies, backend code, SQL, authentication or collection cadence changed. No full browser/backend suite was claimed or repeated during this focused pass.
- Initial new pointer/tap checks failed pinning, and were repaired with native pointer events plus the chart's mapped category centres. Screenshot inspection also caught the initial band-start crosshair offset; explicit band centres repair both the crosshair alignment and selection on either grouped bar. Focused assertions check both bars and compare crosshair/tick coordinates without increasing timeouts or weakening expectations. Canonical missing observations have no fabricated bars/dots. Full notes remain accessible inside Details.
- Normal Chrome inspection confirms compact GDP/debt tooltips, accurate FY/CY and estimate/actual labels, crosshairs/active marks, native manual quote scrolling/focus pause, and zero trailing seam gap. The normal-source proof records three actual stored snapshots across two automatic polling intervals; original quote values, exchange times and statuses agree with the UI. See [interaction evidence](evidence/2026-10-16/interaction-live.json) and [recorded checks](evidence/2026-10-16/interaction-checks.json).

Current screenshots: [desktop tooltip](evidence/2026-10-16/interaction-preview.png), [full desktop](evidence/2026-10-16/interaction-desktop.png), [mobile](evidence/2026-10-16/interaction-mobile.png). They use the normal application and real stored observations, not the fixture server. Segoe UI fallback, public market display/credential rotation, production hosting/domain/recovery acceptance and final submission deliverables remain open as listed in design-completion.md. No deployment occurred.

## Earlier checkpoint records

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

## Hardening stage — 16 October 2026 IST

Final full backend run: **88 tests + 9 subtests passed in 49.33s**. Final frontend: **12 units** under patched Vitest 4.1.11/Node 22.23.3; strict TypeScript/unused checks, production build and Prettier pass. Ruff checks backend/tests/new tooling; shell syntax and deployment-origin/CSP/artifact guards pass. Final compiled Chrome run: **19/19 passed in 3.5 minutes**. The normal private-data application also passes **11 checks / 10 canonical headline/table agreements**, reload, mobile layout and logout. [Recorded results](evidence/2026-10-16/hardening-checks.json), [normal interface](evidence/2026-10-16/hardening-live-interface.json).

Four auth unit regressions and one proactive-renewal browser regression failed before their fixes. Recovery's two incomplete-schema negative checks also failed before strict migration-based validation was added. An early broad browser run had one fixture setup deadline while the full backend suite ran concurrently; its final isolated rerun passes all 19. An initial race-reproduction attempt ended at an ECONNRESET before reaching its assertion; the later reproduction reached and demonstrated the false notice. These are distinguished from application/provider failures. Existing Starlette HTTPX deprecation and rotated-PDF extraction messages remain diagnostics.

All 21 artwork variants pass source/output hashes, dimensions and exact resized RGBA checks; regeneration is deterministic with the recorded encoder. Cold transfer/screenshot geometry/quality evidence covers desktop/mobile at 1×/2×. [Performance measurements](evidence/2026-10-16/hardening-performance.json). The required viewport is tested, but the UI does **not** exactly match the supplied SVG or an accessible Figma frame; see [material differences and denied access](hardening.md).

Existing version-1 migrations preserve GDP/auth; current version-3 migration is idempotent. Online snapshots are consistent during WAL writes. The ordinary database's 388 observations/run metadata survive isolated backup/restore with private permissions, strict schema/integrity/FK validation and no restored sessions. [Recovery evidence](evidence/2026-10-16/recovery-checks.json). Source data/session state on the ordinary database was not restored or overwritten.

Locked API/frontend runtime assembly builds locally. A fresh normal API process has no tests/fixture imports or control routes; actual normal HTTP checks also return 404 for test and database-file paths. Development dependencies are absent from the API artifact. npm audit is zero after the targeted test-tool patch; the public API-package advisory lookup returns no matches. These are scoped checks, not a comprehensive security audit.

The GitHub workflow is prepared and pins official Actions commits; it has not run remotely. No public deployment occurred. Actual controlled-domain cookies, DNS/HTTPS/CORS, Linux CI/source egress/trust, persistent mount/redeploy/proxy acceptance and off-host backup operation remain pending. Debt/market data and exact design acceptance still fail the corresponding assignment completion gates; unavailable UI states do not complete those features. See the [ready/blocked deployment checklist](deployment.md).
