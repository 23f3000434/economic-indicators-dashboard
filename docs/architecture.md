# Architecture

## Boundaries

```mermaid
flowchart LR
    P[Public providers] --> C[Scheduled collector in API process]
    C --> V[Validate and normalise]
    V --> D[(Private persistent SQLite)]
    D --> A[FastAPI stored-data reads]
    A --> R[React dashboard]
```

React never scrapes providers. HTTP reads never trigger collection or wait for its network calls. The collector and request handlers share storage, not an upstream request path. Use short database transactions after complete validation, keeping HTTP waits outside transactions. Scope failures to a provider's collection group; commit unrelated groups independently.

One data-driven screen owns canonical panel data and shared selectors/formatters. Cards reference their current/comparison points; charts, tooltips, and accessible tables use those same points. Keep fixtures in tests. Do not create a second production reference screen or a fixture-mode deployment.

## Collector and UI

Start one cancellable supervised `asyncio` task per implemented group in FastAPI's lifespan, with exactly one API worker/instance. Fixed jobs and a due-time check suffice; no scheduler framework or persistent job queue is justified. Groups are GDP, expenditure, GST, trade, CPI and inflation policy. They prevent overlaps, persist outcomes, coalesce missed intervals after restart and honour durable provider-wide cooldowns. A slow provider does not cancel other groups or block request handling. HTML/workbook/PDF normalisation runs in worker threads; API reads run against short SQLite snapshots.

Use HTTPX for bounded async HTTP, explicit connect/read timeouts, and limited backoff on transient failures/429. Do not bypass 403s or certificate verification. Collect permitted market data at most once/minute; check monthly macro releases daily and annual WDI/IMF series weekly. Frequencies are configuration, subject to source-specific permission and feasibility. Store last-valid data in SQLite; conditional upstream requests are optional when supported.

The browser polls the stored-data endpoint once/minute while visible, with abortable requests and no overlapping polls. Initial loading reserves panel/chart geometry. A browser/API failure retains already loaded data with a separate connection-error state; upstream failures are returned as panel states. Update freshness from collection outcomes and release expectations, not from a recent fetch alone. Use publication calendars/grace periods once each source is verified; until then report freshness assessment as unknown rather than fabricating an overdue date.

## Database and dependency budget

| Structure/dependency | Decision and reason |
| --- | --- |
| `observations` | Necessary: one latest-valid record per series/reporting period, decimal value, provenance, and provider status/notes. Historical periods satisfy assignment history. A full archive of every revision is not required. |
| `collection_runs` | Necessary: per-group attempts, successful retrieval/validation time, and failure category, so stale status survives restarts. Bound/clean old diagnostics. |
| `provider_cooldowns` | Necessary: Retry-After deadlines shared by that provider's groups and persisted across attempts/restarts. Neither job history pruning nor a new browser request removes them. |
| `users`, `sessions`, `refresh_tokens` | Implemented for the selected session contract. Session rows supply immediate revocation; active/pending/retired token digests support delivery-confirmed rotation. No plaintext token cache. |
| Schema version | Use ordered SQL migrations with SQLite `PRAGMA user_version`; no migration-history table/framework is needed for this small database. |
| Series definitions and source configuration | Versioned application configuration, not separate mutable `sources`/`series` tables. Preserve period and methodology semantics there; use different series IDs for incompatible bases. |
| Raw snapshot, transformation, card, chart, and table tables | Omit. Source URLs, dataset metadata, response hashes, provider notes, and versioned transforms suffice initially. Keep raw bodies only in ignored diagnostic output unless a later source demonstrates a retention need. |
| Probe dependencies | Historical probes still use only the Python standard library. Application dependencies are locked separately in `uv.lock` and `frontend/package-lock.json`. |
| First backend slice | FastAPI/Pydantic, Uvicorn, HTTPX; `sqlite3` and `asyncio` from standard library. Direct parameterized SQL, no ORM/Redis/Celery/APScheduler. |
| First frontend slice | React, TypeScript, Vite, scoped CSS, Recharts for the required bar/line/stacked chart types. A single fetch/polling hook suffices initially; defer routing/query-state libraries until demonstrated need. |
| Authentication dependencies | PyJWT, Argon2 and python-dotenv are now authorised/implemented. Initial refresh tokens have 256 random bits; successors use a dedicated HMAC key plus the predecessor secret. Only SHA-256 digests persist. Domain setup gates production verification. |
| Publication parsing | Beautiful Soup for actual official HTML tables; pypdf for actual PDF data tables. A bounded read-only stdlib XLSX reader preserves cached numeric XML text without float coercion; no spreadsheet-writer dependency. Native `truststore` context is needed for verified Gazette TLS chain resolution. No additional PDF parser/OCR stack. |

The historical proof remains disposable. Numbered SQL migrations apply transactionally with `PRAGMA user_version`: 001 initial data/auth, 002 per-provider cooldown/group identity, 003 compatible measurement semantics. Existing GDP rows/auth remain intact. New observations snapshot their typed period/definition in JSON alongside authoritative decimal/provenance columns; a code catalogue validates identities/units. Unknown dataset-update dates are SQL NULL. SQLite's default journal is sufficient for this low-write assignment. Connections require an existing file; readiness cannot silently create a replacement database. Directory/file permissions are 0700/0600, with no static database route. Valid corrections replace a period after validation; no revision archive is promised.

Application code lives in `backend/app/` and `frontend/src/`. Development dependencies are pytest/Ruff/Pillow and Vitest/Playwright/Prettier; no ORM, scheduler, query cache, router or state framework is introduced. The chart is lazy-loaded after sign-in. Fonts are self-hosted with OFL licences. Auth, protected reads, validation and failures are covered by the verification matrix.

GDP input defaults to the 12 years ending in the previous UTC year; explicit start/end overrides and a 2–50-year reporting window are supported. The displayed window is shared across both series; absent requested periods stay null instead of silently moving a card to another year. Both countries and their metadata form one WDI collection group. Validation completes before a short commit. Non-null corrections replace prior data; provider omissions retain existing values with their original point provenance and a visible retained/stale flag. A new gap stays null. Collection lateness (twice the configured interval), source failure and unknown economic-release freshness are distinct concepts.

The supervisor starts in FastAPI lifespan, coalesces missed jobs, prevents overlap, records cancellation/restart interruption and retries after failure on the shorter of one hour or the configured interval. Each request has a timeout, byte limit and bounded retry budget; the group also has an overall deadline. Reads never enqueue work. Process supervision belongs to the host; `/healthz` checks storage and task liveness without calling providers. Run exactly one worker/replica with this scheduler/SQLite arrangement.

Each group's retained history comprises its latest 200 completed outcomes, its last success and all running records. High-frequency groups cannot prune other groups. Both Retry-After forms establish a minimum deadline: wait only if it fits the remaining monotonic request budget, otherwise defer and expose the persisted cooldown. A per-request outer deadline also bounds dripping bodies.

`/api/v1/dashboard` is a protected stored-data aggregate; the GDP v1 route remains compatible while the frontend uses the complete aggregate. Other panels carry typed observations and current/comparison references for each supported grain. GST annual/FYTD values are calculated once from canonical monthly points with input references. Trade balance is canonical exports minus imports. CPI bases stay in separate series; policy validity is an independent group. Read projections emit null gaps without invented provenance. There is no fixture production mode.

Trade/GST current and historical inputs form one atomic source group to protect reconciliation and comparison consistency. A bad required archive can therefore leave that group's current observations stale; other groups continue. Policy is separate from CPI because its authority, dates, transport and collection frequency differ. Debt has no adapter until access/metadata are proven; market items remain explicit gates. Wider configured history is not a promise that a source supplies it; actual coverage and missing annual slots are explicit.

## Planned hosting, not deployed hosting

Frontend: Cloudflare Pages. API: one paid Render instance with an attached persistent disk. SQLite, its sidecars, backups, and collector state stay under that disk's mount path, outside anything the frontend/static server can serve. Restrict directories to the service identity and database files to owner access. SQLite has no TCP listener, so a database bind address/proxy/firewall port is unnecessary; document the absence of network exposure. API binds its HTTP port, not a database port.

Use private daily consistent SQLite backups and a private off-host copy, then verify restore. A disk snapshot is not a substitute for a consistent database backup. Disk mounting, non-public file access, restart/redeploy persistence, backups, and restore remain deployment acceptance checks, not local-proof claims.

[Render disks](https://render.com/docs/disks) support the intended single instance but prevent zero-downtime deployment and cannot be shared with a separate cron service. Run collection inside the API environment. Separate static and API environments meet the brief; do not colocate them to solve cookie issues.

Authentication requires `https://dashboard.<controlled-domain>` on Pages and `https://api.<controlled-domain>` on Render: separate origins/hosts, one HTTPS site. Required setup and a same-origin proxy alternative are in `contracts.md`. No domain, deployed origins, provider account access, or cloud source egress has been verified.

The production API start command must bind the host-provided HTTP port (for Render: `--host 0.0.0.0 --port "$PORT" --workers 1`), unlike the local loopback command. No database port is opened. Configure the static build's HTTPS API base URL and production secrets/origins explicitly before deploying.

Only a concrete limitation should trigger PostgreSQL: multiple API replicas, separate collector machines requiring shared storage, unsupported persistent-disk semantics, or measured write contention. A move would use a private connection boundary and blocked public DB ingress; a public HTTP proxy would not provide database isolation.

## Complete frontend

`App` owns a single user-scoped aggregate snapshot. Reads are bounded to 12 seconds, share a single in-flight promise, pause while hidden, and resume on visibility/online events. A failed poll retains the last snapshot with a connection notice. Logout/account changes synchronously abort the read and clear its snapshot; late responses cannot repopulate another account. Authentication renewal retains the existing memory JWT/cookie protocol.

The GDP/IndicatorPanel discriminated union is represented directly in TypeScript. Shared presentation projections preserve canonical string values, source/period/status metadata, and summary references. Only plot coordinates use numbers. Display conversions/rounding use decimal strings and BigInt; comparisons/sums/averages stay in FastAPI. Period controls select the same grain for cards and chart/table data. Legend controls toggle chart/tooltip/table series; cards retain the selected grain's headline summary. History controls trim the returned periods without fetching providers.

GDP and additional panels load lazily after authentication and share a chart module. Each slot has a recovery boundary; component failures can retry a fresh stored-data read, and failed module downloads have an explicit reload path that preserves the server session. Tables provide keyboard-accessible alternatives to charts; chart arrow-key inspection, native controls, visible focus and a skip link complement them. Null values never connect line/area segments; CPI methodologies are selected separately. Policy display coordinates reference the dated canonical value only within its validity, with its source and validity preserved.

The supplied SVG is a visual reference, never an application screenshot. Its embedded raster artwork has deterministic proportional display variants with original/output hashes and dimensions. Lossless WebP preserves resized RGBA pixels; native lazy images preserve the established CSS crops and reserve geometry. No remote font/image dependency or replacement artwork is introduced. See hardening.md for measured cold transfers and explicit design deviations.
