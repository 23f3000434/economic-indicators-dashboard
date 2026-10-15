# Multi-provider backend evidence

The baseline is 03aa914. This stage preserves GDP/authentication and implements one source path at a time. Application inputs are live official responses; fixtures are compressed original responses used only by offline tests. Diagnostic caches and private proof databases stay ignored.

## CGA — implemented

- Discovery: [CGA home](https://cga.gov.in/Index.aspx), selected published month and latest fiscal-year options; archive document paths are period-validated, never blindly trusted.
- Actual source: [August 2026 accounts](https://cga.gov.in/writereaddata/MonthAccount/82026/DATA2627.htm); matching August 2025 and March 2022–2026 releases also fetched successfully. The fiscal window is configurable through the report-window setting.
- Validation: INR crore, unaudited provisional actuals, correct actual column beside BE/RE; revenue + capital equals total exactly for all seven accepted releases. March means a completed April–March FY. COPPY percentages are not comparison amounts.
- Storage/API: 21 points; protected `/api/v1/panels/expenditure` returned ready/200. [Live proof](evidence/2026-10-15/cga-live.json). Tests exercise repeated ingestion, failure retention, recovery, offline reads, restart persistence and exact YoY arithmetic.
- Unknown: observation publication date; collection time is not substituted. These are provisional monthly accounts, not audited final annual accounts.

Reproduce after local setup: `.venv/bin/python scripts/verify_sources.py --groups expenditure`. It fetches public data, creates an ignored private proof database, signs into FastAPI locally and logs out its random proof account. It never reads fixtures. Run network-enabled where outbound DNS/TLS is permitted.

## Dependencies

Beautiful Soup handles legacy official HTML tables; pypdf handles official machine-readable release PDFs. Existing HTTPX, sqlite3, Pydantic and Decimal remain the transport/storage/validation/arithmetic tools. No ORM, task queue, scheduler framework, spreadsheet writer or browser scraper is added. Locks pin exact versions.
