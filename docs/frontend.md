# Current frontend and design acceptance

Current stage from af5ff07 completes measured design/data integration locally. Public deployment remains pending review. Earlier expanded panels and debt/market placeholders are replaced; GDP v1, authentication and independent collection remain compatible.

## Data flow

React reads only FastAPI: `/api/v1/dashboard` every 60 seconds and the small protected `/api/v1/ticker` every 30 seconds while visible. Separate bounded single-flight requests pause when hidden, cancel on logout/account change and resume on online/visibility events. A failed poll retains its prior snapshot with a connection/stale notice. Server collection is independently scheduled and never requested by a browser read.

The GDP/IndicatorPanel union and ticker response mirror explicit API models. Canonical observations and backend summary references supply cards, plots, tooltips and dialog tables. Only coordinates use numbers; display conversions/rounding use exact decimal strings/BigInt. Sums, averages, previous-close changes and comparisons stay in FastAPI. GDP India FY/World CY and debt India FY/US CY remain visible. Debt source-year plot coordinates never replace the original canonical period keys. Annual/monthly null gaps are neither zeroes nor connected lines.

Period controls choose the same canonical reporting grain for cards/chart/table. Legends toggle chart, tooltip and table series; headline cards retain their selected-grain summaries. CPI bases remain separate, and policy coordinates reference the dated target only within validity. GST consistently excludes compensation cess under D17. No sample observations or market changes are simulated.

## Measured reference

Figma browser Properties is readable without edit permission. Frame 1:2 local 2193×1248 at−90° has visual 1248×2193 bounds. Uniformly fit width1214; do not rotate its children, crop edges or stretch height. All six panels use their measured582/583×544 geometry and positions. Extended tables, controls and provenance use native modal dialogs outside the scaled canvas, with focus containment, Escape, focus return and visible focus. Concise periods/sources/as-of stay visible. Mobile has no supplied reference frame; use a legible single-column layout.

The original decorative geometry, corner treatments, gradients, clips, masthead crop and static outlined title are extracted deterministically from the supplied SVG. Desktop skins embed the existing lossless display-size WebP variants. Mobile surfaces contain no rasters; separate lazy images preserve artwork proportions/crops. No economic sample values, labels, axes or curves enter panel skins. `prepare_layout.py`, `verify_design.py`, manifest hashes and browser measurements make this reproducible.

Roboto headings500/20px and Manrope ticker labels are self-hosted under their OFL licences. Figma's proprietary Segoe UI400/600/700 is not installed here; the current installed-font/Roboto fallback is provisional. CDP verifies actual loaded fonts rather than inferring them from CSS. Exact typography is not accepted until licensed webfonts arrive or the user accepts the fallback. Additional Figma permission is not currently needed.

## Resilience and accessibility

Fixed panel geometry is identical during loading and after data/lazy modules arrive. Error boundaries isolate components and allow retry/reload for failed chunks. Native dialog tables provide full canonical values, periods, publication/retrieval times, source links, status and retention; charts support keyboard inspection. Nulls remain gaps, original provenance survives failures and source-group notices remain independent. Market UI shows verified state and exchange time; browser connection loss overrides a retained Live/Snapshot label with Stale.

Browser scenarios cover all panels, drawers, canonical agreement, controls, CPI gaps/policy validity, provider failures, offline recovery, fixed geometry, slow/cancelled reads, account changes, lazy/component failures, ticker polling/retention, reload/renewal, expiry, logout, concurrent tabs and interrupted refresh. A session-keyed ticker subtree unmounts its authenticated dialog on logout/account changes, including logout broadcast from another tab; its regression requires zero remaining dialogs and ticker items. Evidence, screenshots, measurements and limitations are in [design-completion.md](design-completion.md) and [verification.md](verification.md). No fixture/control route enters the normal application.

## Focused interaction pass after a59bb96

All charts use the same compact tooltip: selected reporting period(s), visible series, canonical formatted values/units and essential missing/retained/estimate/provisional/actual status. It is a body-level portal with opaque background, 14px text unaffected by the scaled canvas, and measured viewport flip/clamp positioning. Full methodology, source dates and footnotes remain in the existing Details dialog, including an expandable individual-observation selector. No economic arithmetic moved into the chart.

Native pointer coordinates resolve to the nearest category centre mapped by the installed chart library's axis scale; they never interpolate economic observations. Band centres are explicit, so either bar within a grouped period selects the same period and its crosshair aligns with the axis tick. A vertical/horizontal crosshair, white bar outline and line/area point markers identify selection. Nulls keep their period and dash but receive no fabricated mark. Pointer movement updates the shared period; click/tap pins or dismisses, outside interaction/Escape clears, and arrows/Home/End inspect periods. Touch drags remain browser scroll gestures. Only one chart selection is active at a time. Measured panel/plot geometry and canonical period keys remain unchanged.

The quote strip scrolls native `scrollLeft` through two identical groups, wrapping modulo their measured width with no trailing spacer. It pauses on hover/focus, while hidden, for manual interaction and under reduced motion; wheel/touch/keyboard scrolling remains available. The loop is mounted independently of quote payload updates, so polling does not reset its phase. Source values and LIVE/SNAPSHOT/DELAYED/STALE/CLOSED rules are unchanged. `scripts/verify_interactions.mjs` records the normal application's initial snapshot plus two automatic polls against original exchange timestamps, without fixtures or a fake clock.
