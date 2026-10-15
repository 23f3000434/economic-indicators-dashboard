# Multi-provider backend evidence

The baseline is 03aa914. This stage preserves GDP/authentication and implements one source path at a time. Application inputs are live official responses; fixtures are compressed original responses used only by offline tests. Diagnostic caches and private proof databases stay ignored.

## CGA — implemented

- Discovery: [CGA home](https://cga.gov.in/Index.aspx), selected published month and latest fiscal-year options; archive document paths are period-validated, never blindly trusted.
- Actual source: [August 2026 accounts](https://cga.gov.in/writereaddata/MonthAccount/82026/DATA2627.htm); matching August 2025 and March 2022–2026 releases also fetched successfully. The fiscal window is configurable through the report-window setting.
- Validation: INR crore, unaudited provisional actuals, correct actual column beside BE/RE; revenue + capital equals total exactly for all seven accepted releases. March means a completed April–March FY. COPPY percentages are not comparison amounts.
- Storage/API: 21 points; protected `/api/v1/panels/expenditure` returned ready/200. [Live proof](evidence/2026-10-15/cga-live.json). Tests exercise repeated ingestion, failure retention, recovery, offline reads, restart persistence and exact YoY arithmetic.
- Unknown: observation publication date; collection time is not substituted. These are provisional monthly accounts, not audited final annual accounts.

Reproduce after local setup: `.venv/bin/python scripts/verify_sources.py --groups expenditure`. It fetches public data, creates an ignored private proof database, signs into FastAPI locally and logs out its random proof account. It never reads fixtures. Run network-enabled where outbound DNS/TLS is permitted.

## GST — implemented; earlier history incomplete

- Discovery: [statistics page](https://www.gst.gov.in/download/gststatistics) links the gross/net workbook. The page's public news client calls [GSTN news JSON](https://www.gst.gov.in/fomessage/newsupdates); title, month and exact PDF link select the latest monthly release. No permanent September URL is baked into the collector.
- Actual sources: [monthly workbook](https://tutorial.gst.gov.in/offlineutilities/gst_statistics/Gross_Net_Tax_collection.xlsx) and [September release](https://tutorial.gst.gov.in/downloads/news/final_gst_revenue_report_for_publishing_monthly_sep_2026.pdf). Five-page PDF reviewed; first-page A.3 gross band is separate from B refunds and C net. Monthly values and FYTD columns are not interchangeable.
- Definition: original totals include compensation cess in older sheets and exclude it in newer sheets. Primary comparable gross excludes cess, with original totals/methodologies and published cess kept separately. Gross components reconcile within publication rounding (workbook 0.02 crore, integer PDF 2 crore). Do not compare inclusive/exclusive reported totals across a methodology break.
- Workbook anomalies: Jan-25 uses B=current/C=prior with “Daily” heading; Nov-25 spells “Montly”. Accept these only for those exact sheet periods and valid adjacent-year month headers. Cached numeric XML values are read as Decimal text; formulas/macros are never executed.
- Storage/API: 120 raw/normalised observations; protected `/api/v1/panels/gst` ready/200. [Live proof](evidence/2026-10-15/gst-live.json). Derived annual totals/averages require 12 published months. FYTD averages divide by actual published-month count and identify their input months; missing months are not zeroes. Derived values carry canonical input references.
- Coverage: April 2023–September 2026, 42 months. Three completed FYs available; FY 2021–22 and 2022–23 have null annual totals. Older Council/Finance releases remain to be verified; statewise domestic collections are not substituted for national gross including imports. Monthly sums may differ slightly from independently rounded/restated published YTD totals; average uses the actual monthly observations.
- Reproduce: `scripts/verify_sources.py --groups gst` via the project Python environment. Offline tests verify original hashes/reviewed values, Jan-25 assignment, methodology separation, missing-month averages, idempotency, failure retention and restart/API reads.

## Dependencies

Beautiful Soup handles legacy official HTML tables; pypdf handles official machine-readable release PDFs. Existing HTTPX, sqlite3, Pydantic and Decimal remain the transport/storage/validation/arithmetic tools. No ORM, task queue, scheduler framework, spreadsheet writer or browser scraper is added. Locks pin exact versions.

## Merchandise trade — implemented

- Discovery: [Commerce release listing](https://www.commerce.gov.in/ministryofcommerce/taxonomy/term/530), normal pagination, monthly release node metadata and PDF attachments. The latest monthly document is parsed; April publication nodes are examined for the latest completed March FY. Every document's reporting headers and release date are validated. Page/node/PDF budgets bound discovery.
- Actual current sources: [August 2026 release](https://www.commerce.gov.in/files/d-m-y/PIB%20Release%20-%20August%202026.pdf) and [March 2026 release](https://www.commerce.gov.in/files/d-m-y/PIBRelease.pdf). The August document says September 15; its listing says September 16. Store the document's publication date, not the listing date.
- Historical sources: original Commerce WordPress March PDF URLs returned HTTP 404 at runtime despite search-engine copies. Accepted official Ministry releases on PIB remain accessible: [March 2024](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2017942&reg=48&lang=2), [March 2023](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1916220&reg=48&lang=2). These are explicit bootstrap references, configurable with `TRADE_HISTORY_URLS` (pipe-separated HTTPS PIB URLs), not a fixed collection-year ceiling. Future/current discovery remains dynamic.
- Validation: only the Merchandise block of Tables 1/2, USD billion, exact matching current/prior month/FYTD/FY headers. No service estimates, combined-trade balances or INR amounts. Per-point status is unspecified where merchandise finality is not explicit. Later publication dates win overlapping historical periods (FY 2022–23 exports 451.07 in the 2024 vintage replaces 447.46 in the 2023 vintage).
- Canonical balances subtract published exports/imports with input references. Their rounding can differ from source headlines: 437.06 − 677.24 = −240.18, while the 2024 release's separately rounded deficit headline is 240.17. Preserve arithmetic consistency; do not copy the headline into the canonical balance.
- Coverage/API: five completed FYs 2021–22 through 2025–26, current/prior August monthly and April–August FYTD, plus March monthly comparators. 33 stored raw/derived points; protected `/api/v1/panels/trade` ready/200. [Live proof](evidence/2026-10-15/trade-live.json). Earlier windows beyond these verified bootstrap releases remain incomplete if configured. Reproduce with `scripts/verify_sources.py --groups trade`.
- Transport extension: normal public listing POSTs can use the same retry/cooldown path. An outer monotonic request timeout also bounds slow streams; HTTPX's per-chunk read timeout alone does not bound a dripping response. No redirect or TLS-verification bypass was added.
