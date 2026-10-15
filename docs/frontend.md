# Complete frontend integration

Authorised from `b3ca864`. The first increment (`a6dba8f`) repairs collection write-outage recovery and scoped omission retention; GDP v1 and authentication stay compatible. This stage connects and verifies the dashboard locally. Deployment remains later.

## Data and controls

`App` reads only `GET /api/v1/dashboard` through the existing authenticated client. It owns one user-scoped snapshot, one bounded in-flight read and a visible-page 60-second poll. Reconnection/visibility triggers a stored-data read. Failed polls retain the snapshot with a fixed connection/retry notice. Logout/account changes abort outstanding work and clear data; old responses cannot populate a new account. No browser action schedules provider work.

TypeScript models the GDP/IndicatorPanel union directly. Shared projections and formatters resolve canonical points and backend summaries for cards, charts, tooltips and tables. Economic arithmetic remains on the backend. Decimal/BigInt display conversion/rounding preserves INR crore → ₹ lakh crore, USD billion, percent, pp and signed balances. Numeric conversions are used for plot coordinates only.

| Control | Result |
| --- | --- |
| Refresh view / Retry connection | One protected database read; no upstream request |
| GDP history window | Last 3/5/all returned source years, shared by chart/table; headline cards remain the latest summary |
| Trade reporting grain | Completed FY, equal FYTD windows or months; cards/chart/table switch together; balance retains its sign |
| GST reporting grain | Completed FY total and total/12; FYTD published-month mean/current and matched prior; monthly gross/current and matched prior. No monthly resampling of annual/FYTD averages |
| Expenditure reporting grain | Completed FY or matching FYTD actuals; revenue/capital stack and canonical total in the table reconcile |
| CPI methodology | Separate base-2012/base-2024 series, never spliced or compared across bases |
| Monthly history window | Last 12/24/all returned periods, preserving null slots |
| Legend buttons | Chart, tooltip and table columns toggle together; headline cards retain the selected grain. Keep at least one plot series visible |
| Sources/reporting details | Original publication links, methodology, coverage, attempts/success/cooldown and observation metadata |
| Retry panel / Reload application | Fetch repaired stored data/remount a failed component, or reload failed application chunks while preserving the server session |

GDP explicitly distinguishes India fiscal years from the World calendar-year aggregate. CPI changes are pp; policy target/tolerance is independently dated. Policy coordinates resolve the canonical notification only for complete months within its validity; the current-policy explanation also checks `active`. Unknown publication dates/freshness stay unknown. GST consistently excludes compensation cess under D17. Debt and NSE/BSE remain unavailable, with no fake values/curves/timestamps/live labels.

## Reference and visual differences

Both Figma MCP design-context (with screenshot requested) and screenshot requests for frame `1:2` remain denied. D27 records the debug IDs. The supplied SVG was read and rendered locally without modifying it. Its export measures 1248 × 2193, whereas the required viewport is 1214 × 2159. It cannot establish exact fonts, editable constraints, responsive rules, interaction/loading/error states or revision parity with frame `1:2`.

The implementation follows the export's centred title/candlestick header, dark background, six panels in design order, two-column spacing, grey panel headers/corner treatment, cyan/amber gradients, grouped/composed/stacked charts and supplied card artwork. At 1214px, panel x=29px, width=566px and gap=24px follow the export's horizontal proportions. Panel height is 630px rather than the export's 544px: functional controls, reporting notes, accessible tables and provenance add necessary content. The desktop document is approximately 2204px tall and scrolls slightly in the required viewport. At 390 × 844 it becomes one column, reserving 680px per panel so initial data loading does not move later panels.

Deliberate differences: accurate annual monetary axes replace copied percent axes; correct labels replace inconsistent legends; negative trade balances have a visible zero crossing; CPI bases/target validity stay explicit; unavailable debt replaces the illustrative daily curve; market access status replaces invented live quotes. DM Sans is self-hosted with its existing OFL licence; exact original typography cannot be verified from outlined SVG text. Metadata uses compact type and expandable details. No pixel-perfect Figma claim is made.

The hardening stage replaces original-resolution public artwork with 21 deterministic display variants from the same eleven SVG images. Pillow is a locked development dependency; whole-image LANCZOS resizing plus lossless WebP preserves alpha and CSS crops. Generated source/output provenance and hashes are in `frontend/public/design/assets.json`; hashed filenames and 1×/2× selection reduce loading costs. Card images use native lazy loading. See [current measurements and design differences](hardening.md).

Reproduce (after locked Python and frontend dependency installation):

```sh
.venv/bin/python scripts/prepare_artwork.py '/path/to/Economic Indicator Assignment.svg'
.venv/bin/python scripts/verify_design.py '/path/to/Economic Indicator Assignment.svg' --pixels
```

The source SVG is external/read-only and not copied into application code. CI can check output hashes/dimensions/callsites without the external reference; exact resized-pixel verification needs the supplied SVG.

## Verification and limits

Verified: 77 backend tests plus 9 subtests, 6 frontend unit tests and 17 production-bundle Chrome scenarios. TypeScript (including unused declarations), Vite build, Ruff lint and frontend Prettier pass. Asset hashes/dimensions/decoded pixel identity pass for all eleven assets. See [recorded results](evidence/2026-10-16/frontend-checks.json) and [asset checks](evidence/2026-10-16/design-assets.json). The all-panel geometry test found and fixed a 25–27px mobile shift; reserved heights now match populated heights within 1px. A previous policy assertion counted an empty SVG element; its corrected check verifies the absence of drawn geometry. Existing Starlette HTTPX deprecation and known rotated-PDF text warnings remain diagnostics, not failed application tests.

`frontend/tests/dashboard.spec.ts` exercises canonical card/table/tooltip agreement, every reporting/history control, legend effects, CPI null segments and policy dates, independent provider failures/recovery, offline retention/reconnect, single-flight cancellation/account clearing, keyboard focus/chart/table alternatives, isolated component recovery, actual compiled-chunk failure/reload, empty/mobile states, all-slot loading geometry and a 12-second API deadline. The five GDP/auth browser scenarios remain regression tests. Fixtures and control endpoints stay under `tests/`; the normal application imports neither.

The production bundle is tested with its API URL compiled for the isolated harness:

```sh
cd frontend
VITE_API_BASE_URL=http://localhost:8001 npm run build -- --outDir ../.verification/browser-dist
E2E_PREVIEW=1 npm run test:browser
```

The compiled test bundle stays in ignored `.verification/browser-dist`, separate from the normal frontend `dist`. Build the normal bundle with its public/local API URL before serving it. Build-time Vite environment values are not runtime overrides. Normal live-data verification uses `scripts/smoke_local.mjs` against the application factory/private database and records safe evidence separately; it never seeds fixtures. All 11 checks pass, including ten canonical headline/table values across the five implemented panels. See [live UI evidence](evidence/2026-10-16/frontend-live.json). Four focused compiled-browser checks also pass after the final GDP table FY/CY/source-year labels and all-available-year correction.

Exact Figma inspection/final acceptance, accepted comparable debt and market feeds, production-domain cookies, separate hosting, persistent private disk/backups/restore and final submission URLs/account/portfolio/video remain unresolved. Keyboard/browser checks do not replace a complete assistive-technology audit or performance load test. Engineering documentation contains no rehearsal material.
