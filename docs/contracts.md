# API and data contracts

Version 1 is a design contract. Only the GDP probe's stored-data payload is executable now; no HTTP application or authentication exists. The reviewed live-response example is [panel.ready.json](evidence/2026-10-15/panel.ready.json), with the explicitly injected failure in [panel.stale.json](evidence/2026-10-15/panel.stale.json).

## Data read boundary

| Route | Contract |
| --- | --- |
| `GET /api/v1/dashboard` | Bearer access JWT plus active-session check. `{schema_version: "1", panels: [...], ticker: [...]}`. Each panel/item has independent status; provider failure does not make the entire request fail. Always reads SQLite. |
| `GET /api/v1/panels/gdp` | Same authentication and the GDP panel object described below; useful for the first slice. No provider calls. |
| `GET /healthz` | Public, minimal API/database readiness; upstream outage alone remains degraded data, not process failure. Return 503 for an unusable required database. Do not expose credentials or tracebacks. |
| `GET /docs`, `/openapi.json` | Public route/schema documentation. Data routes remain authenticated. |

Return JSON; use `Cache-Control: no-store` for authenticated API/auth responses. SQLite is the durable provider cache; browser memory retains already loaded data during a failed poll. Use 401 for authentication failures, 403 for CSRF/origin failure, 422 for invalid requests, 429 for throttling, and 503 for an unavailable API/storage dependency. Do not return an upstream 403 as the dashboard's authentication error. Error shape: `{error: {code, message}}`, with stable safe codes and no raw provider HTML.

## Canonical panel

- `schema_version`, `id`, `state`, `collection`, `series`, `summaries`, `notes`.
- `series[]`: stable `id`, label, explicit unit and reporting basis, source metadata, ordered `points[]`.
- `points[]`: source `period_key`, human-readable `period_label`, actual period start/end dates, decimal-string `value` or `null`, estimate status, provider status, footnote. Future adapters add a separate methodology series rather than silently joining incompatible bases.
- `summaries[]`: `series_id`, `current_period_key`, `comparison_period_key`, and `{kind, value}` change. Card values are looked up by those keys; they are not separately stored/copied figures.
- Chart, tooltip, table, and card selectors consume the same point arrays. Only the backend computes comparison arithmetic using Decimal; client selectors resolve references and format numbers consistently. Conversion to finite JS numbers is for plotting, not independent arithmetic or storage.
- Decimal strings are percentages already when unit is `percent` (e.g. `7.566...` means about 7.57%, not 756.6%). Format at most two decimals for GDP display; keep full source precision in storage/JSON. Zero is a valid value. `null` renders `—` and a chart gap; never coerce it to zero or interpolate it.

| Field | Meaning |
| --- | --- |
| `period_start`, `period_end` | Economic reporting window, not fetch time |
| `source.published_at` | Actual observation-release timestamp/date when supplied; otherwise null |
| `source.dataset_updated_on` | Provider dataset-level update metadata; never treated as this observation's release date |
| `source.retrieved_at` | Time that the successful source response supplying the value was received |
| `collection.last_attempt_at` | Latest collection attempt, including failures |
| `collection.last_success_at` | Latest validated successful collection; a failure never advances it |
| `collection.last_error_kind` | Safe classified failure or null; not a diagnostic body |

Machine timestamps are UTC ISO 8601; display times in IST. Explicitly label the period on every card/group. An old annual observation can be the latest published value. Release-calendar freshness/overdue assessment must be unknown until the calendar is verified; recently fetching old data does not reset its economic age.

`state`: `ready` (usable retained data, no failed latest attempt), `stale` (retained data after a failed refresh or verified overdue release), `empty` (successful/initial scope with no observations), or `unavailable` (no retained usable data and a failed/unavailable source). Historical gaps can exist in a ready panel. Client `loading` and API connection-error states are separate from these provider states; retained browser data during a failed poll gets a visible connection/stale notice. Reserve the panel's final geometry in all states.

The aggregate can include panel-local error information and source failure even when other panels succeed. Source scopes are independently collected/committed. Related inputs such as trade exports/imports must share a period/definition before computing a balance; unrelated sources must not be held in one transaction.

## Metric and comparison definitions

| Metric | Unit, period, and calculations |
| --- | --- |
| GDP India/World | WDI `NY.GDP.MKTP.KD.ZG`, annual real GDP growth in percent. India source year `Y` maps to FY `Y–Y+1` (Apr–Mar); World is the published annual aggregate. Show the reporting-window difference. Card change = current growth minus prior annual growth, in pp. |
| India/US debt | Proposed IMF general-government gross debt/GDP, percent, annual. Show coverage, fiscal/calendar basis, vintage, and estimate status. Never substitute external or central-government debt without an explicit definition change. Change in pp; values above 100% are valid. |
| Trade | Merchandise only, source USD million converted to USD billion by `/1000` when needed. Balance = exports − imports, with negative deficits supported. FYTD/prior FYTD compare identical months; annual chart uses completed FYs. YoY amount change uses `(current/prior − 1) × 100`, null if prior is zero or absent. |
| GST | Gross collections before refunds, stored INR crore. Display ₹ lakh crore using `/100000`. FYTD average = sum of published FY months / number of months; never divide an incomplete year by 12. Annual bars = gross total, line = total/12 only for a complete year, both on the same monetary scale. Cards compare matching periods. |
| Inflation | All-India combined headline CPI YoY rate in percent, monthly. Badge is rate minus prior month's rate, in pp. Policy target/tolerance is a dated policy value, not a monthly economic observation. Keep CPI base changes explicit. |
| Expenditure | CGA Union Government actual revenue/capital/total, INR crore, with provisional/final status. FYTD compares equal months. Stacked completed-FY revenue + capital must reconcile to total; keep BE/RE distinct from actuals. |
| Ticker | Named NSE/BSE source as appropriate, index points, exchange timestamp; daily % = change from previous close. Live/delayed/closed/stale labels depend on verified feed latency/market calendar. No quote access is established yet. |

The GDP proof uses 2020–2025 input and displays 2021–2025: six source periods provide five chart periods and the initial comparison. Its paired latest/previous input requirement is a bounded proof check, not evidence that other providers or future windows are complete. WDI blank observation status remains `unspecified`, not invented final/actual status. WDI's fiscal-label assignment is documented in its [reporting convention](https://datahelpdesk.worldbank.org/knowledgebase/articles/201203-are-all-wdi-series-on-a-calendar-year-reporting-pe) and confirmed against fetched India metadata.

## Selected authentication contract — not implemented

The user selected this after comparing a 30-minute memory-only JWT (reload login, no immediate per-session token revocation) with persistent sessions (reload persistence and revocation, additional cookie/session handling). The earlier JWT-only recommendation is superseded. JWT is retained for access requests and the assignment preference; session state supplies revocation.

**Lifetime and storage.** Access JWT: 15 minutes, in memory only, containing issuer/audience/subject/session ID/issued-at/expiry. Cap access expiry at the session's absolute expiry. Session: configurable **seven-day maximum**, measured from login, never extended by refresh or polling. Refresh token: at least 256 random bits, sent only in `__Host-refresh`; `Secure; HttpOnly; SameSite=Strict; Path=/`, no Domain attribute, persistent Max-Age limited to the remaining session lifetime. Never return refresh tokens in JSON, store them in browser storage, or log them. Store only SHA-256 refresh-token digests; password hashing uses Argon2.

Every protected API request verifies JWT signature/claims and reads its session: active, unexpired, correct user, not revoked/disabled. Thus logout revokes all associated access JWTs immediately, including JWTs that have not expired. No access-token denylist is necessary.

| Route | Request/response and protection |
| --- | --- |
| `POST /api/v1/auth/login` | JSON credentials, exact allowed Origin, JSON-only request and required `X-CSRF-Protection: 1` header (preflight). Success creates session/refresh hash, sets refresh cookie, returns access JWT, `expires_in: 900`, absolute `session_expires_at`, and session-bound CSRF token. Generic invalid-credential error; rate limited. |
| `GET /api/v1/auth/session` | Refresh cookie and exact allowed Origin, no state change/rotation. Return expiry and a session-bound CSRF token for reload bootstrap; no access JWT. Invalid/expired/revoked session returns 401. |
| `POST /api/v1/auth/refresh` | Refresh cookie, exact Origin, and `X-CSRF-Token`. Rotate atomically; return new access JWT/expiry and set new refresh cookie. Session maximum stays unchanged. |
| `POST /api/v1/auth/logout` | Refresh cookie plus exact Origin and CSRF token; revoke that session/token family and expire cookie, return 204. Works without a currently valid access JWT. Invalid/absent session may still clear the cookie; no unrelated session is revoked. |
| `GET /api/v1/me` | Bearer access JWT plus active-session check; return safe user identity only. |

CSRF tokens are signed/session-bound values derived with a dedicated server secret, returned only to the allowed frontend and kept in memory. Validate them on cookie-authenticated state changes; reject missing/foreign Origins and form/simple content types. Login requires the Origin/custom-header/JSON protections before a session exists. SameSite and CORS add protection but do not replace server-side checks. No wildcard origin with credentials. Bearer dashboard requests use `credentials: omit`; cookie auth/bootstrap requests use `credentials: include`.

**Rotation and concurrent tabs.** One active refresh token per session; persist used hashes until session expiry so known reuse is detectable. A short SQLite transaction validates the session, consumes the current token, and inserts its successor. Only the first rotation response sets a cookie. For a known immediately previous token used concurrently within **10 seconds**, issue a session-checked access JWT without rotating or setting a cookie. Reuse outside that narrow previous-generation grace revokes the family/session; arbitrary unknown tokens simply fail, avoiding revocation from guessed identifiers. The grace is a deliberate concurrency/security tradeoff, not indefinite replay tolerance.

Use a per-tab single-flight refresh and, where available, a cross-tab Web Lock; BroadcastChannel distributes renewal/logout state. With no Web Locks, the bounded server grace handles overlapping refreshes. A reload bootstraps session/CSRF and refreshes automatically. Renew shortly before expiry, or once on `access_token_expired`, then retry the original read once. Revocation/absolute expiry clears auth and requires login; network/5xx failures display retry state rather than falsely claiming expiry. Logout/refresh races must never resurrect a revoked session. Broadcast logout clears tabs promptly; server revocation remains authoritative even if a tab misses the broadcast.

**Required hosting setup before auth implementation.** Obtain the concrete controlled domain and DNS access. Configure `dashboard.<domain>` to Pages and `api.<domain>` to Render, verify HTTPS on both, and set the exact frontend origin/API URL. These are same-site HTTPS subdomains with different origins/environments; the refresh cookie stays host-only on the API. Confirm browser cookie behaviour with third-party cookies blocked. None of this DNS/deployment setup is complete yet.

If a controlled domain is unavailable, propose a same-origin `/api/*` proxy on the frontend host forwarding exclusively to the separately hosted FastAPI HTTPS origin. Forward required cookies/authorization/CSRF headers, preserve host-only Set-Cookie semantics, and disable caching. This keeps processing/storage/collection in FastAPI and avoids third-party cookies, but adds a thin proxy and needs its own verification/selection. Do not silently switch to `SameSite=None` provider-domain refresh cookies or localStorage tokens.

Configuration to document at implementation: `VITE_API_BASE_URL`, `FRONTEND_ORIGIN`, `SQLITE_PATH`, `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`, `ACCESS_TOKEN_TTL_SECONDS=900`, `SESSION_MAX_AGE_SECONDS=604800`, `CSRF_SECRET`, `REFRESH_REUSE_GRACE_SECONDS=10`, and provider refresh settings. All secrets remain server-side; evaluation account provisioning uses an interactive/secret-manager flow, never committed default passwords.

Cookie/security basis: [MDN cookie scope and SameSite](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies), [Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie), and [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html). Provider-domain cross-site refresh was a hosting concern, not a claim that separate hosting prevents secure sessions.

## Acceptance checks

- Reload a signed-in page/new tab: recover a JWT through session/refresh without asking for credentials.
- Advance beyond 15 minutes: automatic renewal and one retried read; no login loop or repeated request storm.
- Advance beyond seven-day/configured maximum: refresh and protected access fail; refreshing never moves the maximum.
- Logout: old access JWT and refresh token fail immediately, cookie expires, other tabs clear or fail at next request; a logout/refresh race cannot restore the session.
- Concurrent tabs: simultaneous expiry/refresh works with and without Web Locks; no stale Set-Cookie overwrites the winner. Reuse after grace revokes the session; rotation is atomic.
- CSRF: absent/wrong token, foreign/missing Origin, and form requests are rejected without changing auth state. Host-only/Secure/HttpOnly/SameSite and exact credentialed CORS are inspected.
- Cookie persistence works with third-party cookies blocked on the chosen same-site domains; default provider domains are not treated as equivalent.
- Data: invalid/partial required batches do not overwrite valid observations; repeat ingestion is idempotent; reopen preserves values; failed refresh changes status/times correctly; missing historical points stay null; API reads have no network dependency.
- UI: reserved panel geometry, one-source failure isolation, consistent values/units/periods across card/chart/tooltip/table, and explicit FY/CY/source/freshness notes.

Only the offline data/probe checks and local SQLite proof run in this checkpoint. Browser, session, API, cloud persistence, Figma fidelity, and remaining-source checks are future acceptance gates.
