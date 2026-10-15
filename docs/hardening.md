# Hardening and deployment readiness

Authorised from 42d9d4a. Public deployment is excluded. Keep engineering findings tied to reproductions and performed checks.

| Risk | Assessment before changes | Action/status |
| --- | --- | --- |
| High: late auth responses | Renewal/bootstrap can publish state after a logout or account change; second read after renewal bypasses the original 401 handler | Reproduce with controlled delayed responses before changing behaviour |
| High: recovery/deployment | No verified backup/restore procedure or deliverable production configuration; restored old sessions must not resurrect revoked access | Prepare isolated backup/restore, migration checks and single-worker private-disk deployment |
| Medium: loading cost | 10,891,124 artwork bytes, with full-resolution card art | Measure cold transfers first; deterministic resized variants and lazy offscreen loading; compare screenshots |
| Medium: source/comparison correctness | Retained/null observations and reporting methodology must survive failure/recovery and control changes | Review validation, arithmetic and original regression boundaries; fix only reproduced defects |
| Delivery blockers | Debt/market required features unavailable; Figma exact acceptance and production domain/hosting remain unverified | Bounded source attempts; precise missing inputs; no fabricated completion |

Figma design context and screenshot still deny frame 1:2 on 16 October 2026. Debug IDs: e7d1dbfd-7167-48c5-a05b-46f3056e15c3 and 7242c37c-92e7-433c-9334-9e464d037c0e. Connected account sharing was requested. SVG fallback remains available. Current UI is not exact: its panels are taller for controls/tables/provenance, typography cannot be confirmed, and sample axes/data/debt/market are deliberately corrected. SVG export 1248×2193 is distinct from the required 1214×2159 viewport.

## Session response authority

Confirmed before changing behaviour with four failing Vitest tests: late confirm overwrote cross-tab logout, old account renewal overwrote a newer login, a second 401 after renewal left the client signed in, and a pre-cancelled read still began cookie renewal. The client now versions authentication work, checks that version before publishing responses or issuing the next cookie mutation, and ignores obsolete failures. Reads check cancellation before renewal and after waits; shared renewal remains available to other readers. Both attempts handle revocation. The server rotation/logout protocol is unchanged.

Verification at this increment: 12 frontend unit checks pass; all six compiled Chrome GDP/auth scenarios pass, including a newly held confirm response followed by cross-tab logout and reviewer login without Web Locks. Existing interrupted refresh, reload, automatic renewal, expiry, canonical reads and mobile checks pass. This establishes local behaviour only; production HTTPS/cookie acceptance remains pending.
