# Zero-budget deployment checkpoint — 16 October 2026

Strictly free: Vercel Hobby frontend, Render Free API, same-region Render Free PostgreSQL. No paid resource, card, disk, cron, purchased domain or upgrade was created.

| Resource | Actual state |
| --- | --- |
| Render database | Created `economic-indicators-db`, PostgreSQL18, Free/1GB, Oregon, `dpg-db8vao67bikc73bdm49g-a`. Saved resource rules block all internet traffic; external URL unavailable. Internal hostname verified. Empty: API attachment pending. Expires15 November2026. |
| Vercel | Created Hobby project `economic-indicators-dashboard`, `prj_8aV7ClNPsz0BMJRVpxo6c7ilnbNp`. Node22.x saved; basic build machine, paid concurrent builds disabled. Assigned `economic-indicators-dashboard-iota.vercel.app`; **no production deployment**. Standard SSO protection retained. |
| Render API | Repository access resolved: `23f3000434/economic-indicators-dashboard` is selected on `main`. Oregon/Free, `sh deploy/build_api.sh` and `sh deploy/start_api.sh` are prepared in the new-service form. Not submitted: server-secret configuration remains pending. |
| Hosted URLs/smoke | Frontend/API/docs/health are not working submission URLs yet. Hosted source egress, refresh cookies, restart persistence and evaluation access have not been verified. |

## Completed changes and checks

PostgreSQL migrations/direct bound SQL, serialized auth writes, repeatable-read projections, advisory collector ownership and generation fencing are implemented. Existing SQLite/auth/GDP behaviour remains compatible. Real PostgreSQL tests cover concurrent refresh, lost responses/revocation, idempotent migrations, persisted data, standby/fencing, cooldown precision/history and an actual read-only outage recovering without restart. Auth-only frontend proxy and POST session bootstrap preserve Origin/CSRF and Secure/HttpOnly/Strict production cookies; bearer data reads stay direct to Render.

Ticker now uses the measured red badge, outlined red dot, reference colours/type/spacing/separators and one row. Actual uniform/mixed status labels replace unconditional LIVE/QUOTES. Motion, pause, reduced motion/manual navigation and update continuity remain. Completed-FY labels are explicit; newer monthly/matched-FYTD data stays accessible in Details. Roboto/Manrope loaded; Segoe UI unavailable locally and the accepted fallback remains disclosed. Longer truthful status labels and concise inline source/as-of text necessarily occupy more width than the illustrative LIVE reference.

Verification reused/performed: full backend108 passed +9 subtests; affected collection/recovery13 passed; actual PostgreSQL source/auth/dashboard/trade24 passed, with latest five PostgreSQL-specific checks also passing; frontend25 unit tests; compiled full browser25/27 initially passed, then all four affected checks passed after correcting the setup-inclusive deadline and auth-origin assertion. Existing cross-tab/data-clearing assertions remain intact. Build, format/lint, artwork check, allowlisted runtime and routing/CSP checks passed. PostgreSQL CI18 is configured; the new remote run is not yet claimed passed.

[Official release inventory](evidence/2026-10-16/free-official-releases.json), [normal database/API proof](evidence/2026-10-16/free-source-to-screen.json), [newer periods on screen](evidence/2026-10-16/free-screen-current-periods.json), [two actual market cycles](evidence/2026-10-16/free-market-cycles.json), [ticker comparison](evidence/2026-10-16/free-ticker-comparison.png), [geometry/fonts](evidence/2026-10-16/free-ticker-geometry.json). The normal collector refreshed all ten groups; a new Commerce PDF wrapping failure was reproduced and repaired with actual-response fixtures and strict year validation.410 non-null canonical/derived API points were checked against412 stored observations. Evidence is local, not Render egress acceptance.

## Exact remaining actions

1. Connect the Render integration for secure server configuration, or complete server-secret entry through the hosting UI. Regenerate the chat-exposed Upstox Analytics Token, save its replacement in the project's ignored `.env` as `UPSTOX_ANALYTICS_TOKEN`, and reply “replacement configured”; never paste it into chat. Applicable market display permission for the evaluation audience remains unverified. Repository access is already resolved and does not need another grant.
2. Additional Vercel SSO removal was rejected by automatic approval review because it would expose deployments; no protection was disabled. The specific approval question is pending. Retain Standard Protection unless actual production-alias access requires a change.

After secure configuration is available: submit the prepared free Oregon API, attach the internal DB URL, configure stable secrets/exact origins and evaluator bootstrap, then generate/review `vercel.json` with the actual API URL and deploy the frontend. Run only the essential hosted smoke. Per the owner's latest instruction, stop while deployment inputs are blocked; do not continue independent implementation, polish or verification.

Render sleep stops collection; wake coalesces due jobs and preserves stale states. The database's30-day expiry is a hard evaluation availability limit. No PostgreSQL off-host backup is implemented. Portfolio/project links and the post-assessment recording remain separate owner deliverables.
