# Design and data completion (from af5ff07)

Public deployment is pending completion review. This stage closes the required design, market and debt features; it preserves authentication, GDP v1 and independent collection. Fixtures remain test-only.

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
