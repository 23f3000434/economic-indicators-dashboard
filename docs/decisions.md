# Decisions and evidence log

Dates below are 15 October 2026 (IST); machine evidence uses UTC. Accepted user choices are distinguished from implementation recommendations. Update this log when evidence or scope changes, not with retrospective claims.

| Decision | Status | Basis/consequence |
| --- | --- | --- |
| D01 React → FastAPI → stored observations; independent scheduled collection | Accepted by user | Browser activity never drives provider traffic; upstream latency is outside API read latency. |
| D02 Private persistent SQLite, single API instance | Accepted by user | Remains default unless a concrete deployment/concurrency limitation appears. No managed database or ORM needed now. |
| D03 One accurate data-driven dashboard; fixtures only for tests | Accepted by user | Correct sample units/labels/periods; all visual presentations share canonical data. |
| D04 Reserved loading geometry, independent failures, retained stale data, null gaps, separate collection/freshness times | Accepted by user | Contract and failure tests enforce these behaviours; no invented zeroes or fresh timestamps on failed data. |
| D05 Refreshable server-revocable sessions | Accepted and locally implemented | Supersedes the earlier JWT-only recommendation. 15-minute memory-only JWT; configurable absolute maximum up to seven days; HttpOnly refresh cookie; hashed token storage; session checks/revocation; CSRF. Local auth implementation explicitly authorised before domain setup. |
| D06 HTTPS frontend/API subdomains of a user-controlled domain, on separate hosts | Accepted direction; concrete domain/setup pending | Removes reliance on third-party cookies while preserving separate hosting. Provider URLs alone are not the accepted auth deployment. |
| D07 Simplify schema and dependencies | Implemented | Two data tables plus three necessary auth tables; code-based series catalogue, no revision/snapshot/visualisation tables, no ORM/queue/scheduler framework. See architecture and locks. |
| D08 Exact Figma inspection and market access remain independent gates | Accepted by user | Continue macro/contracts work. Do not claim fidelity/live ticker complete while gates remain unresolved. |
| D09 Development docs cover engineering and submission only | Accepted by user | Track the required post-assessment video deliverable; keep rehearsal outside this project. |
| D10 Refresh concurrency and lost responses | Implemented; supersedes initial contract | Active → pending → confirmed rotation. Unacknowledged predecessors remain retryable until absolute expiry; hashes-only deterministic successor recovery. A 30-second settling window coalesces concurrent responses; retired reuse outside it revokes. Web Locks, per-tab single flight and logout broadcast supplement server authority. This adds one confirmation endpoint rather than storing recoverable plaintext tokens. |
| D11 Logout identity and authority | Implemented | Valid bearer authority works without a cookie. Recognised conflicting identities return 409 without mutation. Explicit invalid bearers cannot silently fall back to a cookie identity. Cookie-only logout requires CSRF. |
| D12 Local security boundary | Implemented | Explicit loopback development mode uses `dev_refresh`, HttpOnly/Strict without Secure over HTTP. Production configuration requires separate HTTPS subdomains, uses Secure `__Host-refresh`, and has no insecure override. Actual domain verification remains pending. |
| D13 GDP slice scope | Completed in 03aa914 | Historical scope: authenticated GDP only. The user now authorises D14; the working slice remains a regression boundary. |
| D14 Multi-provider backend | Authorised by user | Foundation/cooldown/history corrections, then one verified adapter at a time, then the protected stored-data dashboard aggregate. No frontend redesign or deployment. Unavailable sources remain explicit gates, never fabricated completed adapters. |
| D15 Contract/schema evolution | Implemented foundation | Preserve GDP v1. Migration 003 adds group/validated semantic snapshots to the existing observation table and permits unknown dataset-update dates. Code catalogue validates provider/unit identities; no ORM or extra chart/revision tables. New points include explicit period/status/methodology/publication provenance. |
| D16 Collection cooldown/history | Implemented and verified | Migration 002 adds durable provider deadlines. Delta-seconds and HTTP-date Retry-After are honoured within the request budget or deferred; later attempts/groups sharing that provider check the persisted deadline. History pruning is per group and preserves its last success and every running record. 47 backend tests plus 9 subtests pass at this increment, including existing GDP/authentication. |
| D17 GST compensation cess | Recommended assumption implemented; user preference can change presentation | User was asked; no answer had arrived after independent CGA work. Primary canonical series consistently excludes cess (reported total minus cess when included, reconciled against CGST/SGST/IGST). Preserve original reported totals and separately published cess with per-point definitions. Never mix older inclusive totals with current exclusive totals. |
| D18 CGA actual expenditure | Implemented and live verified | Official selector discovery → seven independently validated actual/provisional releases → 21 canonical observations → private SQLite → authenticated API 200. Five completed FYs plus current/prior August; all revenue + capital totals reconcile exactly. BE/RE are excluded. Original source bytes are compressed test-only fixtures with hashes and reviewed values. |
| D19 GST gross/averages | Implemented and live verified, limited history | Official statistics page discovers workbook; public GSTN news API discovers latest monthly PDF (September 2026, published October 1). 120 raw/normalised points from 42 months; fiscal sums/averages derive once from canonical monthly observations with input references. April 2023 onward is verified; earlier annual totals remain null. Narrowly documented Jan-25 column reversal/Daily heading and Nov-25 typo are validated against actual month headers. XML decimal text is preserved without binary float coercion. |
| D20 Merchandise trade | Implemented and live verified | Dynamic Commerce listing/node/PDF discovery plus verified official PIB historical bootstrap releases. Five completed FYs, matching current/prior month and FYTD. 33 canonical points; only merchandise, USD billion, source vintage explicit, balance derived from exports/imports. Historical legacy PDF URLs returned 404; their reachable search copies are not production collectors. |

## Historical source checkpoint evidence

1. Workspace initially contained only `.git`, with no commits or application code. Supplied references were read during planning without modification.
2. In the restricted execution environment, DNS failed for World Bank, IMF, MoSPI **and example.com**, before HTTP/TLS. This is environment evidence, not provider rejection. The earlier Node `fetch failed` messages lacked this diagnosis.
3. After network access was enabled, the control and World Bank succeeded; IMF returned HTTP 403; MoSPI returned an HTML application shell; GST returned a PDF; Commerce/CGA returned HTML. Record each source's actual verification level in `sources.md`.
4. World Bank indicator and India metadata succeeded. India uses fiscal-year national accounts ending 31 March. WDI's dataset update date is not a publication date for an individual GDP observation; blank `obs_status` does not prove finality.
5. A live-response GDP proof stores 12 annual India/World observations for 2020–2025, reads five years into one panel contract, checks decimal pp changes, reopens SQLite, checks idempotent ingestion, and injects a timeout to demonstrate retained stale data. The injected timeout is a test, not an upstream incident.
6. The Gazette URL failed Python TLS verification. A second certificate-verified client is used to distinguish trust-path failure from endpoint availability; see the source report/evidence. TLS verification is never disabled.
7. At the initial source checkpoint, authentication was specified but unimplemented. The subsequent authorised slice below supersedes that restriction.

Committed public evidence is linked from `sources.md`; ignored raw bodies/private SQLite files are not application inputs. The local proof does not establish Render egress, cloud persistence, browser rendering, authentication, or complete application delivery.

## Authenticated GDP slice evidence

- The application collector fetched the live rolling 2014–2025 window on 15 October: 24 non-null India/World observations, validated indicator/country metadata, private SQLite and database-only API projection. This replaces the fixed proof window in application code; the original probe stays historical.
- The live protected endpoint and React smoke check passed login, reload renewal, canonical card/table agreement, API-only browser data fetches, memory-only JWT, cookie attributes, responsive layout and access revocation after logout. Public data-only evidence: [gdp-slice-live.json](evidence/2026-10-15/gdp-slice-live.json). Screenshots and random local credentials remain ignored.
- Local acceptance is recorded in [verification.md](verification.md): backend/source suite, browser clock/failure scenarios, TypeScript production build and formatter/lint checks. Injected failures and fixture observations are test evidence, not upstream incidents.
- Browser verification found and repaired an 8-pixel loading geometry difference. The live desktop GDP panel now reserves 630 CSS pixels. A split build keeps chart code out of initial sign-in loading.
- Port 8000 was occupied; this project's local API uses 8010. No existing service was stopped. No domain/DNS or cloud resources were changed.

## Pending external inputs

- **Controlled domain and DNS access:** actual frontend/API names, DNS records, verified HTTPS certificates, exact-origin configuration. Required before production verification, not local implementation; select the documented proxy alternative if a controlled domain is unavailable.
- **Market data:** panel resolution of accepted NSE and BSE access/update/display arrangements. Do not automatically scrape around an access gate or label stale/delayed data live.
- **Figma:** connected account `monishmprogram@gmail.com` was denied design context/metadata/screenshot access to frame `1:2` on 15 October. Restored sharing has not been verified; SVG cannot establish fonts/prototypes/states or exact frame parity.
- **Submission:** portfolio/project links and role summaries; evaluation credentials shared separately; deployed frontend/API/docs/health URLs once deployed.

None of these inputs blocks independent backend sources. No rehearsal, portfolio construction, unrelated folder edits, frontend redesign or public deployment belongs to this stage.
