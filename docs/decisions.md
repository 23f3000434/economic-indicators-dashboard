# Decisions and evidence log

Dates below are 15 October 2026 (IST); machine evidence uses UTC. Accepted user choices are distinguished from implementation recommendations. Update this log when evidence or scope changes, not with retrospective claims.

| Decision | Status | Basis/consequence |
| --- | --- | --- |
| D01 React → FastAPI → stored observations; independent scheduled collection | Accepted by user | Browser activity never drives provider traffic; upstream latency is outside API read latency. |
| D02 Private persistent SQLite, single API instance | Accepted by user | Remains default unless a concrete deployment/concurrency limitation appears. No managed database or ORM needed now. |
| D03 One accurate data-driven dashboard; fixtures only for tests | Accepted by user | Correct sample units/labels/periods; all visual presentations share canonical data. |
| D04 Reserved loading geometry, independent failures, retained stale data, null gaps, separate collection/freshness times | Accepted by user | Contract and failure tests enforce these behaviours; no invented zeroes or fresh timestamps on failed data. |
| D05 Refreshable server-revocable sessions | Accepted by user during this checkpoint | Supersedes the earlier JWT-only recommendation. 15-minute in-memory access JWT; configurable seven-day maximum session; rotated HttpOnly refresh cookie; hashed refresh tokens; immediate session checks/revocation; CSRF; reload/renewal/concurrent-tab acceptance. Contracts only, no auth implementation. |
| D06 HTTPS frontend/API subdomains of a user-controlled domain, on separate hosts | Accepted direction; concrete domain/setup pending | Removes reliance on third-party cookies while preserving separate hosting. Provider URLs alone are not the accepted auth deployment. |
| D07 Simplify schema and dependencies | Chosen for this checkpoint | Two data tables now; three auth tables later justified by D05; code-based series catalogue, no revision/snapshot/visualisation tables, no ORM/queue/scheduler framework. See architecture. |
| D08 Exact Figma inspection and market access remain independent gates | Accepted by user | Continue macro/contracts work. Do not claim fidelity/live ticker complete while gates remain unresolved. |
| D09 Development docs cover engineering and submission only | Accepted by user | Track the required post-assessment video deliverable; keep rehearsal outside this project. |
| D10 Refresh concurrency | Engineering contract default | Cross-tab coordination plus a 10-second previous-generation grace without a new Set-Cookie; reuse outside grace revokes the session. This bounds replay tolerance while handling concurrent tabs. Verify before auth delivery. |

## Evidence recorded in this checkpoint

1. Workspace initially contained only `.git`, with no commits or application code. Supplied references were read during planning without modification.
2. In the restricted execution environment, DNS failed for World Bank, IMF, MoSPI **and example.com**, before HTTP/TLS. This is environment evidence, not provider rejection. The earlier Node `fetch failed` messages lacked this diagnosis.
3. After network access was enabled, the control and World Bank succeeded; IMF returned HTTP 403; MoSPI returned an HTML application shell; GST returned a PDF; Commerce/CGA returned HTML. Record each source's actual verification level in `sources.md`.
4. World Bank indicator and India metadata succeeded. India uses fiscal-year national accounts ending 31 March. WDI's dataset update date is not a publication date for an individual GDP observation; blank `obs_status` does not prove finality.
5. A live-response GDP proof stores 12 annual India/World observations for 2020–2025, reads five years into one panel contract, checks decimal pp changes, reopens SQLite, checks idempotent ingestion, and injects a timeout to demonstrate retained stale data. The injected timeout is a test, not an upstream incident.
6. The Gazette URL failed Python TLS verification. A second certificate-verified client is used to distinguish trust-path failure from endpoint availability; see the source report/evidence. TLS verification is never disabled.
7. Authentication choice arrived before finalising documents. No login/session endpoints, auth tables, secrets, or browser auth code have been implemented.

Committed public evidence is linked from `sources.md`; ignored raw bodies/private SQLite files are not application inputs. The local proof does not establish Render egress, cloud persistence, browser rendering, authentication, or complete application delivery.

## Pending external inputs

- **Controlled domain and DNS access:** actual frontend/API names, DNS records, verified HTTPS certificates, exact-origin configuration. Required before auth implementation; use the documented proxy alternative only if the domain is unavailable and that alternative is selected.
- **Market data:** panel resolution of accepted NSE and BSE access/update/display arrangements. Do not automatically scrape around an access gate or label stale/delayed data live.
- **Figma:** connected account `monishmprogram@gmail.com` was denied design context/metadata/screenshot access to frame `1:2` on 15 October. Restored sharing has not been verified; SVG cannot establish fonts/prototypes/states or exact frame parity.
- **Submission:** portfolio/project links and role summaries; evaluation credentials shared separately; deployed frontend/API/docs/health URLs once deployed.

None of these inputs blocks further GDP/provider verification. No rehearsal, portfolio construction, unrelated folder edits, or full application build is part of this checkpoint.
