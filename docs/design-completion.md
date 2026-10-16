# Design and data completion (from af5ff07)

Public deployment is pending completion review. This stage implements the measured reference layout and actual market/debt paths while preserving authentication, GDP v1 and independent collection. Exact Segoe UI typography remains pending. Fixtures remain test-only.

## Reference access and viewport mapping

On 16 October 2026 IST, the existing Figma browser view provided read-only Properties for assignment frame `1:2`. Edit permission is **not needed** for this inspection. Earlier MCP edit-access denials do not describe browser access. A browser frame-export download timed out; the supplied SVG remains the pixel reference, with browser Properties supplying typography and geometry.

Properties reports a local frame width **2193**, height **1248**, rotation **−90°**. Its visual bounds are **1248 × 2193**, matching the SVG viewBox. Child panel positions are already visual canvas coordinates; do not rotate them again.

At the required **1214 × 2159 CSS viewport**, fit the 1248-wide visual canvas uniformly by `1214 / 1248 = 0.9727564103`. Its height is then **2133.2548 CSS px**, leaving **25.7452 px** of background below. Preserve this aspect ratio; neither crop 17 px from every edge nor stretch the height independently. At mobile widths, use a single-column responsive arrangement; there is no supplied mobile frame.

## Measurements from read-only Properties

Coordinates below are design pixels, relative to the visual frame unless stated otherwise.

| Element | x / y | Width × height | Other |
| --- | --- | --- | --- |
| GDP `1:65` | 30 / 162 | 582 × 544 | radius 12; #001671 at 20% |
| Debt `1:288` | 636 / 162 | 583 × 544 | radius 12; same measured fill |
| Trade `1:136` | 30 / 730 | 582 × 544 | radius 12; same measured fill |
| GST `1:351` | 636 / 730 | 583 × 544 | radius 12; same measured fill |
| Inflation `1:234` | 30 / 1298 | 582 × 544 | radius 12; same measured fill |
| Expenditure `1:437` | 636 / 1298 | 583 × 544 | radius 12; same measured fill |
| Masthead artwork `1:63` | 1 / 0 | 1248 × 86 | crop; opacity 36% |
| Masthead title | 423 / 23 | 402 × 40 | Segoe UI 700, 36px, white |

Measured heading offsets **inside each panel**: GDP 26/26, debt 28/23, trade 37/26, GST 19/24, inflation 22/25, expenditure 29/22. All headings use **Roboto 500, 20px, 100% line height, 0% tracking**. GDP/GST suffixes use #0FCBF0. Header strips are 68px, #2C2C2D at 60%; some are offset −1px in the SVG.

| Element inside panel/card | Measured geometry / typography |
| --- | --- |
| GDP cards | visual 254 × 111, x=26/302, y=90; local rotated frames 111 × 254 at −90° |
| GST cards | visual 254 × 110/111, x=27/303, y=88 |
| Expenditure cards | visual 254 × 116, x=26/302, y=95 |
| GDP India icon | card x=12,y=7,43.14 × 42.5, rounded crop |
| GDP value | card x=12.12,y=55.46; Segoe UI 600,36px |
| GDP label | card x=63.12,y=16; Segoe UI 400,18px |
| GDP legends | panel x=388/479.91,y=213; groups 59.5/70.5 × 21; Segoe UI 600,16px |
| GDP chart group | visual 532.91 × 299.23 at x=18.09,y=238.53; plot grid measured from SVG x=55.12..550.40,y≈248..499 |
| GDP axes / years | Segoe UI 600,16px; year text bounds 50.65 × 29.04 at y=508.72 |
| Trade values | Segoe UI 600,32px, card x=13,y=34 |
| GST gross / average values | Segoe UI 600,32px, card x=12,y=30/32 |
| GST labels | Segoe UI 400,18px, card x=12,y=8/9 |
| Inflation / target values | Segoe UI 600,36px, card x=15.85/21,y=34/35 |
| Inflation / target labels | Segoe UI 400,18px, card x=16/21,y=10/16 |
| Expenditure total value / label | Segoe UI 600,36px / 400,18px; x=12,y=36/11 |
| Capital value / label | Segoe UI 600,36px / 600,16px; x=15/18,y=35/11 |
| Expenditure chart | visual 532.91 × 280.38 at x=24,y=241; legend Segoe UI 600,16px |
| Inflation year labels | Segoe UI 600,18.73px |
| Ticker SENSEX / values | Segoe UI 600,17.08px; line height 21.32px; positive #69F6B8 |
| Ticker NIFTY BANK label | Manrope 700,17.08px; line height 21.32px |

Measured illustration slots inside cards: exports 86.12×58 at157.88/48; imports84×70.14 at161/41; inflation106×87 at140/29; target99×98.45 at162/28; GST107.12×107.12 at164/25; GST average91×84 at168/35; total96×96.54 at159/30; capital99×99 at156/24. Preserve original SVG clipping and image transforms, including artwork extending beyond its frame. These are not generic interchangeable icon sizes.

Roboto and Manrope can be self-hosted under their OFL licences. Segoe UI is proprietary; licensed webfonts or the user's acceptance of an installed-font/fallback approach are pending. Do not claim a fallback is the exact Figma font.

## Necessary content corrections

- Use actual annual real GDP growth and pp changes; label India FY versus World CY.
- Debt is annual general-government gross debt/GDP, with vintage/status and coverage differences; do not reproduce the illustrative daily debt curve or copied 3.82% values.
- Merchandise trade uses USD billion, negative balances and matching comparison periods. Design bars labelled percentages are not valid trade units.
- GST/expenditure are monetary amounts, not percentages. GST consistently excludes compensation cess under D17; published-month averages and full-year totals use their recorded definitions.
- All-India combined CPI bases remain separate; dated policy applies only within validity. Do not copy a target-change badge without a valid comparison.
- Ticker prices, comparisons, timestamps and state come from stored validated snapshots; a closed/delayed/stale feed must not carry an unconditional LIVE label.

Tables, extended provenance, controls beyond the reference and diagnostics belong in accessible modal drawers. Required period/source/as-of information stays concise and visible within the measured panel footprint. Values, charts, tooltips and drawer tables keep the same canonical observations and backend summary references.

Further individual Properties checks: trade/GST axes and value labels use Segoe UI600/16px; trade legend text uses 600/16px. Expenditure axes use 600/16px, plotted total/segment labels 600/15px. Debt axes use400/18.73px; inflation axes use 600/18.73px. Reference bar widths are 25.4254px for grouped GDP/trade, 34.78px for GST and 37px for expenditure. GDP/GST/trade value labels are16px; expenditure labels15px. These are measured individually, not inherited from GDP. Gradients/strokes are read from the supplied vector definitions; the bars remain data driven.

Measured plot borders (panel-local design pixels): GDP x55.12–550.40/y248–498.86; trade x60.02–555.30/y264.44–492.41; GST x59.12–554.40/y264.44–492.41; expenditure x61.02–556.30/y281.76–489.04. Chart units/ranges, periods and marks necessarily follow the canonical observations rather than illustrative source values. Real three-digit US debt places its comparison text at the right of the original badge to avoid overlap; monetary unit suffixes use smaller type within the original cards.

## Implemented data and release verification

These are proven local application paths, not documentation-only collectors. Production-host egress and public market display/redistribution acceptance remain separate gates.

| Source / feature | Current verified observation or release | Status |
| --- | --- | --- |
| World Bank WDI GDP | Annual source year 2025: India FY2025–26 7.56666179284244%; World CY2025 2.92127318539153%. Dataset updated 8 Oct 2026; individual publication date is not supplied. | Proven source → validation → SQLite → protected API → UI |
| IMF WEO, official World Bank Data360 mirror | Vintage 13 Oct 2026; India FY2025–26 84.260729% estimate; US CY2025 124.376732% actual. Same headline general-government gross-debt/GDP definition; institutional coverage/accounting and FY/CY differences remain explicit. | Proven; direct IMF listing/workbook403 routes are superseded by the retrievable official mirror/appendix path |
| Commerce / PIB merchandise trade | September 2026 exports44.40/imports74.61/balance−30.21 USD billion, released15 Oct. Matching prior month/FYTD comparisons. The live PIB index fixes the older Commerce archive's August lead. | Proven; five completed FYs plus explicit current/prior published monthly/FYTD windows. Other monthly gaps remain null. |
| GSTN | September 2026 gross excluding compensation cess203,521 INR crore, released1 Oct. Annual totals/averages and FYTD averages derive from published months. April2020–September2026 coverage. | Proven; the recorded compensation-cess assumption remains explicit |
| MoSPI CPI | All-India combined September2026 YoY5.54%, released12 Oct, base2024=100, provisional. Last base2012 release ends December2025; no bridge across bases. | Proven |
| Gazette inflation policy | S.O.1580(E),25 Mar2026: target4%, tolerance2–6%, valid1 Apr2026–31 Mar2031. Applied only within validity. | Proven; successor notification requires review/configuration |
| CGA expenditure | Latest published selector: August2026; FY2026–27 April–August actual revenue1,568,009 + capital509,949 = total2,077,958 INR crore. Publication date not supplied; not replaced with retrieval time. BE/RE excluded. | Proven; five completed FYs plus matching current/prior FYTD |
| NSE NIFTY BANK / NIFTY IT | Actual previous-close fields and official index-listing timestamps; minute precision. Today's changing quotes reached normal storage/API/UI. Older cached responses are rejected. | Proven locally; fresh open state Snapshot, delayed/stale when warranted; no latency SLA asserted |
| BSE SENSEX via Upstox | Actual `BSE_INDEX|SENSEX` quotes, exchange milliseconds, documented net-change comparison. Read-only Analytics Token verified. Separate exchange statuses and dated regular-session timings establish live/closed classification. | Proven locally; exact source attribution visible. Public BSE summary without a timestamp is not used. |

[Current macro fetch/read proof](evidence/2026-10-16/macro-release-check.json), [debt vintage/status proof](evidence/2026-10-16/debt-live.json), [current trade and actual closed-market API proof](evidence/2026-10-16/trade-markets-live.json), [actual open-market timeout/retention/recovery proof](evidence/2026-10-16/market-flow.json), and [normal source-to-screen/automatic refresh evidence](evidence/2026-10-16/source-to-screen.json) distinguish observation periods, publication/vintage, provider timestamps and collection time.

The read-only Upstox token is free according to its [official Analytics Token documentation](https://upstox.com/developer/api-documentation/analytics-token/), and actual responses prove coverage. The [V3 quote fields](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/), [status API](https://upstox.com/developer/api-documentation/get-market-status/) and [standard request limits](https://upstox.com/developer/api-documentation/rate-limiting/) define the integration. Default collection makes one SENSEX request, two status requests and one shared dated timetable request per 30-second cycle, below those published limits. Credentials stay server-side. No trading request or permission bypass was used. Public redistribution rights are not inferred from token possession or a successful response.

## Visual evidence and acceptance boundary

[Matched reference/application comparison](evidence/2026-10-16/reference-application.png) uses 1214×2159 CSS pixels at identical scale. [Measured geometry and actual loaded fonts](evidence/2026-10-16/geometry-fonts.json) verifies all six positions/dimensions within 0.1 CSS px. [Mobile view](evidence/2026-10-16/application-mobile.png) checks a 390×844 viewport; no mobile Figma frame is supplied. [Current reporting selections](evidence/2026-10-16/current-reporting-view.png) show September trade/GST and actual April–August expenditure in the same layout.

These normal-application captures were recorded at 09:42–09:49 IST on 16 October, before the final axis-label/bar-width refinements and cross-tab dialog fix. They establish the measured panel geometry, artwork, real observations and font fallback at that checkpoint; they are not a claim of final pixel equality. The later compiled browser checks are recorded separately in verification.md.

The comparison separates: (1) verified frame/panel/plot bounds and original decorative artwork, (2) necessary changes for real units, reporting windows, annual debt, CPI methodology, null gaps and signed comparisons, (3) functional account/details/source controls within the original footprint, and (4) the unresolved Segoe UI font difference. Real values, period counts and chart ranges cannot equal the illustrative marks. The original static masthead title remains outlined source artwork. No full-reference screenshot or sample economic curve is part of the production UI.

**Exact typography remains pending.** Roboto Medium500/20px headings and Manrope are loaded/verified. Segoe UI is not installed locally; cards, axes and SENSEX currently render Roboto fallback. Licensed Segoe UI webfonts or the user's acceptance of the installed-font/fallback approach are required before calling the design fully accepted. The browser Properties connection works; additional Figma edit access is not required. A frame-export download timed out, so SVG plus measured Properties remains the comparison basis. No prototype/alternate/mobile interaction states were supplied or inferred.

Cold local Chrome measurements (cache disabled; response overhead included) keep desktop artwork near 399 KiB at 1× and 798 KiB at 2×. Mobile starts near 334 KiB/603 KiB and defers lower-panel artwork until scrolling; full artwork near394/785 KiB. These are transfer measurements, not production CDN/Lighthouse claims. [Detailed measurements](evidence/2026-10-16/completion-performance.json) record requests and geometry. Original resized RGBA identity, 20 decorative layout hashes and CSP image rendering are verified. No production CSP weakening was necessary.

## Remaining inputs before public acceptance

The subsequent focused interaction pass preserves the measured layout while replacing the tall provenance tooltip with a compact selection overlay and adding continuous accessible quote scrolling. [Current desktop capture](evidence/2026-10-16/interaction-desktop.png) and [mobile capture](evidence/2026-10-16/interaction-mobile.png) show the normal application after those repairs; [two-poll source/UI evidence](evidence/2026-10-16/interaction-live.json) preserves actual prices, exchange timestamps and labels. See verification.md for the focused checks; these additions do not establish exact Segoe UI acceptance or public deployment.

- Licensed Segoe UI webfonts, or an explicit acceptance of the provisional fallback; final visual review distinguishes data corrections from font differences.
- Replace the token supplied through chat before production; confirm the accepted market display/redistribution arrangement for the deployed audience.
- The agreed controlled domain/two HTTPS origins, deployment account/project access, actual proxy trust/mount/egress/cookie checks and private off-host backup operation remain the later deployment stage. None is claimed as already deployed.
- Final submission still needs deployed frontend/API/docs/health URLs, separately shared evaluation credentials, portfolio/project role links and the required post-assessment recording. Rehearsal remains outside the repository.
