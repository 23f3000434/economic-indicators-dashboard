# Source verification

## Completion checkpoint — 16 October 2026 IST

Debt is now implemented and proved through actual official responses → validation → private SQLite → authenticated API. [Public evidence](evidence/2026-10-16/debt-live.json) records the World Bank Data360 IMF WEO mirror's metadata vintage 13 October 2026 and original response/supporting-source hashes. The matching [official WEO appendix](https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf) supplies India/US reporting conventions, coverage/accounting and latest actual government-finance years. India FY2025–26 is 84.260729% (estimate); US CY2025 is 124.376732% (actual). India coverage is central/state and cash; US includes local government and uses accrual. These differences limit cross-country comparability. Source flag A means Normal value, not actual.

The stable CSV/metadata routes work without credentials. The IMF dataset listing and whole-workbook route returned403 in this runtime; the appendix PDF returned200. New mirror vintages must match a reviewed DEBT_APPENDIX_URL; mismatch preserves the prior data and marks collection stale. This replaces the earlier debt-blocked checkpoint below. No external/central-government substitute was used.

Figma read-only browser Properties works for frame1:2; connector edit restrictions do not prevent inspection. Measurements and font requirements are recorded in [design-completion.md](design-completion.md).

Market verification now has actual authenticated Upstox200 quote responses for SENSEX, NIFTY BANK and NIFTY IT, plus exchange status. NSE public allIndices200 independently agrees on the NIFTY observations and previous closes. Credential is server-only/ignored. Adapter integration and source-to-screen acceptance are still in progress at this checkpoint. The BSE public summary is reachable but lacks an exchange timestamp and is not promoted as the ticker feed.


Initial verification on 15 October 2026; bounded debt/market and Figma rechecks on 16 October (IST), from this workstation with network-enabled execution. **No source has been tested from Render.** Transport reports are diagnostic evidence; their successful HTTP status is not a working collector. The GDP baseline and subsequent multi-provider proofs establish the implemented paths below; see [adapter evidence and coverage](multi-provider.md).

- **Proven:** actual source responses validated and passed through SQLite/readback into the agreed panel contract, for the stated series/window only.
- **Blocked:** a concrete access/network barrier on the tested route/environment; this does not prove global provider unavailability or absent data coverage.
- **Unverified:** a publication/site is reachable or identified, but extraction, definitions, history, and/or release discovery are not established as a collector.

## Results

| Proposed source | Status | Evidence and remaining check |
| --- | --- | --- |
| World Bank India annual GDP growth | **Proven** | HTTPS 200, correct indicator/country, six 2020–2025 observations, fetched fiscal-year metadata, exact decimal validation, persisted/read back. Local proof only. |
| World Bank World annual GDP growth | **Proven** | HTTPS 200, same indicator/window; paired GDP panel, summaries and five chart years derived from stored points. Local proof only. |
| IMF India/US general-government debt | **Blocked** | Tested DataMapper v2 route resolved DNS and returned HTTP **403**. This is an HTTP/CDN/provider-route rejection, not a DNS failure or proof of unsuitable coverage. No spoofing/retry loop. Need an accepted working route/download, validated metadata and annual histories. |
| MoSPI CPI | **Proven** | Normal public POST listing → current and last-2012-base PDFs → strict combined/headline parsers → SQLite → protected API. Separate 2012/2024 series, null pandemic gaps, explicit status/publication metadata. GET rejection was resolved by using the site’s actual POST method. |
| MoSPI GDP alternative | **Unverified** | Same portal reachability only; no NAS observation request validated. Not used by the proven GDP slice. Quarterly India GDP must not be silently compared with annual World GDP. |
| GST gross revenue | **Proven** | Discovered workbook, latest monthly PDF and year-report history; 78 published months, five completed FYs, consistent ex-cess gross and original reported definitions, canonical averages/references. Live SQLite/protected-API proof. |
| Commerce merchandise trade | **Proven** | Current/annual release discovery plus official PIB historical mirrors. Five completed FYs, matching monthly/FYTD comparators, USD billion, canonical exports − imports. Dead legacy PDFs are excluded. |
| CGA expenditure | **Proven** | Official selector discovery; five completed FYs and matching current/prior FYTD; actual/provisional columns distinct from BE/RE; exact revenue + capital reconciliation; private SQLite and protected API. |
| Gazette/RBI inflation-target policy | **Proven locally** | Native system-store TLS resolves issuer-chain failure without disabling verification. Parsed March 25 notification, 4% target/2–6% tolerance, April 2026–March 2031 validity. Independent policy collector/SQLite/protected API. Actual production-host trust chain remains unverified. |
| NSE indices | **Blocked** | The hardening probe returned 200 quote JSON with NIFTY 50/BANK/IT identities and a dated timestamp. Authorised collection/display terms, latency/timezone contract and a complete adapter remain unresolved. This is an access-arrangement gate, not an HTTP failure. |
| BSE SENSEX | **Blocked** | Official index-details URL returned an HTML application shell, not quote data. Accepted BSE route/access remains unresolved. SENSEX is not an NSE index. |
| Figma frame `1:2` | **Blocked** | Available connection denied design context, metadata and screenshot in the planning turn. Frontend and hardening context/screenshot rechecks still deny access; hardening.md records the latest debug IDs and connected account. Supplied SVG can guide structure but cannot establish fonts, constraints, states, prototypes, revision parity or the exact 1214 × 2159 frame. |

World Bank's 2025 values in the captured responses: India **7.56666179284244%** (FY 2025–26) and World **2.92127318539153%** (annual aggregate). These are captured observations, not hardcoded application defaults. The committed payload is authoritative if inspecting full precision. Its dataset metadata says updated **2026-10-08**; `published_at` is null because no individual release date was supplied. The blank provider status does not establish finality.

## Reproducible evidence

```sh
python3 scripts/probe_sources.py --environment local --output-dir .verification/local
python3 scripts/prove_gdp.py --input-dir .verification/local --output-dir .verification/gdp-local
python3 scripts/probe_tls.py --output-dir .verification/tls-local
python3 -m unittest discover -s tests -v
```

All writes stay inside the repository. New output paths preserve earlier evidence. The TLS comparison additionally needs curl >= 7.70. No probe uses credentials, market requests, certificate-verification bypasses, browser impersonation, or automatic retries. Raw responses are size-bounded and ignored by Git. `--environment` is a caller-supplied label; compare actual diagnostic stages, not that label alone.

| Evidence | Meaning |
| --- | --- |
| [sandbox-report.json](evidence/2026-10-15/sandbox-report.json) | DNS errors for control and providers; requests never reached HTTP. |
| [network-report.json](evidence/2026-10-15/network-report.json) | Same runtime after network permission: successful control/WDI requests, IMF 403, other responses, Python TLS failure. |
| [tls-report.json](evidence/2026-10-15/tls-report.json) | Certificate-verified Python/curl GET comparison. An earlier HEAD returned 404; HEAD is not an appropriate substitute for this successful GET. |
| [gdp-proof.json](evidence/2026-10-15/gdp-proof.json) | Response hashes/URLs/timestamps; 12 observations, duplicate-ingestion check, reopen/readback, injected timeout retention. Replays the same HTTP batch; does not claim a second fetch. |
| [panel.ready.json](evidence/2026-10-15/panel.ready.json), [panel.stale.json](evidence/2026-10-15/panel.stale.json) | Same canonical points and summaries before/after a simulated failure. Test artifacts, not alternative production dashboards. |
| [source-status.json](evidence/2026-10-15/source-status.json) | Overall per-source status, combining transport and end-to-end evidence without promoting publication links to collectors. |
| [Public fixtures](../tests/fixtures/README.md) | Byte-identical WDI responses for deterministic offline validation tests. |

The restricted runtime's all-host DNS failure was removed by enabling network execution. IMF still returned 403, so its failure is different. Gazette's differing verified clients indicate a trust-path/chain-resolution difference; the evidence does not identify which CA/intermediate differs. Test the intended container trust chain before choosing an HTTPX policy adapter. Cloud IP rejection, certificate-chain behaviour and release changes remain host-specific unknowns. The new local adapters and their historical coverage are proven separately in [multi-provider.md](multi-provider.md).

## Source references and interpretation

- [WDI indicator data](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG), [API queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures), and [fiscal-year labelling](https://datahelpdesk.worldbank.org/knowledgebase/articles/201203-are-all-wdi-series-on-a-calendar-year-reporting-pe). Attribute World Bank/underlying national-account sources; retain supplied notes. No independent rebasing or FY-to-CY transformation was performed.
- [IMF API documentation](https://www.imf.org/external/datamapper/api/help) and [India reporting/coverage notes](https://www.elibrary.imf.org/abstract/book/9798229042758/CH004.xml) inform the proposed debt definition; they do not override the recorded 403 or prove a collector.
- [NSE terms](https://www.nseindia.com/static/nse-terms-of-use) and [BSE index disclaimer](https://www.bseindices.com/legal-disclaimer) motivate the unresolved market-access gate. Obtain panel resolution rather than claiming an endpoint's visibility satisfies access and display conditions.

Implemented sources preserve the working GDP path. Debt and market remain explicit unavailable states; wider-than-proven history and MoSPI GDP alternatives remain unverified. Recheck every chosen adapter from the actual API host before submission.

## Current-stage access diagnosis

[Network-enabled request evidence](evidence/2026-10-15/multi-source-access.json) distinguishes transport from collector completion:

- IMF DataMapper v1/v2, dataset and WEO download routes returned HTTP 403. No validated debt response exists. The definition remains comparable general-government gross debt/GDP for India/US; central-government or external debt is unsuitable as a substitute.
- FRED’s official IMF mirror was checked as an alternative: both series pages and both CSV requests hit read timeouts before any HTTP response. This is a runtime timeout, not evidence of provider rejection or a working CSV collector. Debt remains blocked.
- Legacy Commerce WordPress PDFs returned 404. Accepted official PIB mirrors supply the required historical tables. A search-engine PDF copy was never used as an application input.
- The CPI legacy host timed out; the newer site’s GET API returned 403. The public client’s POST listing works, and its actual linked PDFs are parsed. No secret/header spoofing was used.
- Gazette’s default Python CA path failed; native system-store verification succeeded. The explicit native SSL context is used only for policy; TLS/hostname verification stays enabled.
- GST Council archive PDFs were reachable, but January 2022 was not extractable and early figures were revised. They remain an unimplemented alternative; the discovered GSTN year report supplies revised history. Statewise domestic GST is unsuitable for national gross including imports. BIS/RBI speech mirrors were diagnostic alternatives, not policy collectors.

Current aggregate proof: [all implemented sources](evidence/2026-10-15/multi-provider-live.json). Normal persistent local API/collection/logout proof: [local-multi-api.json](evidence/2026-10-15/local-multi-api.json). Figma and market access were not retested or bypassed in this backend stage.

## Hardening recheck — 16 October 2026 IST

`probe_delivery_sources.py` makes one bounded request per route using the native verified TLS store, honest diagnostic User-Agent, no retries/credentials/browser impersonation. [HTTP/transport evidence](evidence/2026-10-16/delivery-source-access.json). The control returned 200, establishing that this is not an all-host runtime DNS outage.

| Required feature | Actual result | Status / precise missing input |
| --- | --- | --- |
| Comparable annual general-government gross debt/GDP, India and US | IMF DataMapper pair 403 after DNS/HTTP; FRED's two series pages and two CSV routes timed out before HTTP headers | **Blocked.** Need an accepted retrievable official WEO vintage/download or working official mirror route, with India FY/US CY notes, observed/estimated cutoff and historical coverage. No substituted central-government debt and no inferred estimate status. Intended-host egress remains untested. |
| NSE indices | Public `/api/allIndices` returned 200 JSON (113,866 bytes), with NIFTY 50, NIFTY BANK and NIFTY IT identities and global timestamp `15-Oct-2026 15:30` | **Access arrangement blocked; response shape reachable.** This is no longer an observed network gate. Timezone/latency guarantees and permitted collection/display/update terms remain unverified; no collector/persistence/API path promoted. This dated snapshot is not proof of a live feed. |
| BSE SENSEX | Official index-details URL returned 200, 20,048-byte application HTML shell, no quote observations | **Unverified quote route and blocked accepted feed.** Need an authorised SENSEX endpoint/feed and its instrument, timestamp/timezone/delay/display contract. A publication page is not an adapter. |

The current [NSE website terms](https://www.nseindia.com/static/nse-terms-of-use), use clauses 8–9, restrict republication/storage and automated collection; a successful public request is not an accepted recurring feed. [NSE data subscription information](https://www.nseindia.com/static/market-data/real-time-data-subscription) is a concrete route to an authorised product/vendor. The BSE disclaimer remained an application shell in text inspection; its contents were not independently verified. The user was asked for the approved arrangement/permission and credentials outside Git. There is no scheduled market collection, no committed raw quote fixture, and no bypass attempt. Debt/market features remain unmet, despite useful unavailable UI states.

The existing WDI, CGA, GSTN, Commerce, MoSPI and Gazette adapters remain implemented with their earlier live evidence and offline regressions. This bounded recheck does not claim fresh live ingestion of those unchanged sources or Render egress verification.
