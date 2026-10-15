# Hardening and deployment readiness

Authorised from 42d9d4a. Public deployment is excluded. Keep engineering findings tied to reproductions and performed checks.

| Risk | Assessment before changes | Action/status |
| --- | --- | --- |
| High: late auth responses | Renewal/bootstrap can publish state after a logout or account change; second read after renewal bypasses the original 401 handler | Four initial client defects reproduced and fixed; one proactive-notice defect subsequently reproduced in Chrome and fixed |
| High: recovery/deployment | No verified backup/restore procedure or deliverable production configuration; restored old sessions must not resurrect revoked access | Isolated migration/online backup/new-path restore verified; single-owner private-disk runtime prepared; hosted acceptance remains pending |
| Medium: loading cost | 10,891,124 artwork bytes, with full-resolution card art | Baseline/optimised cold transfers measured; 21 variants and lazy loading verified with unchanged panel geometry |
| Medium: source/comparison correctness | Retained/null observations and reporting methodology must survive failure/recovery and control changes | Existing validation, comparison, failure/isolation/cooldown/retention/restart regressions pass; no speculative data-contract rewrite |
| Delivery blockers | Debt/market required features unavailable; Figma exact acceptance and production domain/hosting remain unverified | IMF 403/FRED timeouts; NSE JSON reachable but feed not accepted; BSE quotes unverified; Figma/domain/host gates explicit |

Figma design context and screenshot still deny frame 1:2 on 16 October 2026. Debug IDs: e7d1dbfd-7167-48c5-a05b-46f3056e15c3 and 7242c37c-92e7-433c-9334-9e464d037c0e. Connected account sharing was requested. SVG fallback remains available. Current UI is not exact: its panels are taller for controls/tables/provenance, typography cannot be confirmed, and sample axes/data/debt/market are deliberately corrected. SVG export 1248×2193 is distinct from the required 1214×2159 viewport.

## Session response authority

Confirmed before changing behaviour with four failing Vitest tests: late confirm overwrote cross-tab logout, old account renewal overwrote a newer login, a second 401 after renewal left the client signed in, and a pre-cancelled read still began cookie renewal. The client now versions authentication work, checks that version before publishing responses or issuing the next cookie mutation, and ignores obsolete failures. Reads check cancellation before renewal and after waits; shared renewal remains available to other readers. Both attempts handle revocation. The server rotation/logout protocol is unchanged.

Verification at this increment: 12 frontend unit checks pass; all six compiled Chrome GDP/auth scenarios pass, including a newly held confirm response followed by cross-tab logout and reviewer login without Web Locks. Existing interrupted refresh, reload, automatic renewal, expiry, canonical reads and mobile checks pass. This establishes local behaviour only; production HTTPS/cookie acceptance remains pending.

## Artwork and design acceptance

Baseline source artwork: 10,891,124 file bytes. Deterministic Pillow 12.1.1/libwebp 1.6.0 processing now creates 21 proportional, lossless RGBA WebP variants totalling 1,097,882 bytes, including both display densities. Original SVG image identities/hashes, output hashes, dimensions and encoding are in the manifest. Full source images are resized without cropping; existing CSS crop positions and transparency remain. Small illustrations use lazy/async `<img>` elements with reserved geometry and 1×/2× `srcSet`; hashed filenames support immutable caching. The original masthead pixels are unchanged. No generated replacement art or remote images/fonts are used.

Cold Chrome measurements use fresh contexts, disabled HTTP cache, the normal private local application and identical stored observations/default controls. Transfer bytes include HTTP response overhead. These are unthrottled local measurements, not cloud/network speed predictions. Full-page screenshots match panel geometry before/after; their mean absolute RGB difference is 0.10–0.28 on a 0–255 scale. Visual review found the original illustration crops/transparent edges intact. Pixel checks separately establish exact identity with the deterministic resized originals, not identity with the original resolution.

| CSS viewport / density | Before artwork, initial | After artwork, initial | After artwork, all panels visited | Total cold transfer, before → after |
| --- | ---: | ---: | ---: | ---: |
| 1214×2159 / 1× | 10,894,106 B | 331,058 B | 389,658 B | 11,486,490 → 982,908 B |
| 390×844 / 1× | 10,894,106 B | 308,750 B | 389,658 B | 11,471,333 → 967,751 B |
| 1214×2159 / 2× | 10,894,106 B | 788,502 B | 788,502 B | 11,486,333 → 1,381,595 B |
| 390×844 / 2× | 10,894,106 B | 540,354 B | 788,502 B | 11,471,333 → 1,366,595 B |

Native lazy loading defers six mobile card images initially (GST, inflation/policy and expenditure). Chrome may prefetch images near the viewport; it need not defer every offscreen illustration. All desktop panels are near/in the tall viewport. Full 1× artwork transfer drops 96.4%; full total transfer drops about 91%. Timing varies: local mobile ready time was 1068→1381ms at 1× and 820→824ms at 2×, so no general speedup claim is made. [Safe measurement evidence](evidence/2026-10-16/hardening-performance.json); screenshots/raw diagnostics remain ignored.

The UI still does **not** exactly match the SVG. Verified SVG geometry: 1248×2193 export; left panels x=30/w=582, right x=636/w=583, rows y=162/730/1298, height=544, gap=24. At the assignment viewport 1214×2159, the app uses x=29/w=566, 24px gaps and 630px panels, with a 2204px document (45px scrolling). On mobile the document is 4490px tall. Extra controls/tables/provenance, smaller chart area, compact typography, borders/background treatment, honest unavailable debt/markets, corrected units/data and the footer are material differences. The SVG's large bottom blank area is not preserved. Figma access is still required to verify frame dimensions, fonts, revision parity and final acceptance; sharing was requested with the connected account. No pixel-exact acceptance claim is made.

A separate compiled-browser reproduction also found a false connection notice after an obsolete **proactive** renewal completed for a previous account. State authority was already guarded, but the background callback still published its error. The callback now checks the originating session and ignores cancellation. The focused browser test failed with that exact notice before the change and passes afterwards (15.2s). No server authentication protocol changed. An earlier reproduction attempt stopped at a fixture connection reset; it did not establish the bug. The successful reproduction reached the wrong-notice assertion.

## Dependency and delivery checks

The locked npm install reported affected development test-tool versions: one moderate and two critical aggregate findings. Confirmed versions were Vitest 3.2.7/mocker and its Tinypool dependency. The [Vitest maintainer advisory](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9) identifies 4.1.11 as patched; the [Tinypool advisory](https://github.com/tinylibs/tinypool/security/advisories/GHSA-85c8-ppgw-ccpr) describes its pollution precondition. No application exploit was demonstrated. The targeted upgrade to exact Vitest 4.1.11 removes Tinypool, keeps Vite 7.3.7 and all existing production dependency versions, and passes all 12 unit tests. Frozen npm install/audit now report zero findings. npm 10's update command failed internally; npm 11 produced the update, then the deployment's pinned Node 22.23.3/npm 10 clean install and build succeeded. [Safe audit evidence](evidence/2026-10-16/dependency-checks.json).

The public OSV batch lookup returned no known-advisory matches for the 27 locked API runtime distributions. This is a version/advisory lookup, not an exploit test or comprehensive audit. [API package evidence](evidence/2026-10-16/api-package-audit.json).

Delivery uses exact Python 3.12.14/uv 0.10.2 and Node 22.23.3, verified locally with an isolated official Node archive and SHA-256. A build check caught uv selecting another installed interpreter; the script now explicitly supplies the prechecked Python path and checks the resulting environment. The assembled API installs 27 runtime packages without pytest/Pillow or fixture modules. Actual frontend production/test/local builds and origin/CSP/artifact checks pass. Public hosting/ingress/certificates and Linux CI execution are not established by these checks.

Twenty sequential warm keepalive reads of the ordinary local dashboard returned 200, with p50 22.00ms, p95 27.22ms and a 332,736-byte uncompressed response. This is a small local sample, not a load test or production latency guarantee. Health returned 200; unauthenticated dashboard and post-logout access returned 401; test-reset and database-file paths returned 404. [Normal API evidence](evidence/2026-10-16/local-api-hardening.json).

Final Figma design-context recheck also denied edit access to frame 1:2 (debug 7e50c0ba-c62e-4de8-ad17-5d08e35786f3). Connected account: `monishmprogram@gmail.com`. No restored access or frame dimensions were confirmed.

## Final checkpoint

Final verification: 88 backend tests + 9 subtests, 12 frontend units, 19 compiled Chrome scenarios, strict/unused TypeScript, production builds, format/lint and 21 resized-pixel/hash asset checks pass. The normal private-data interface separately passes 11 checks with 10 canonical value agreements. The new recovery tooling rejected two incomplete logical schemas only after focused negative reproductions; final validation reuses immutable migrations for table-column/foreign-key structure. Current schema stays version 3; no new migration or runtime dependency is introduced for recovery/deployment.

[Full check record](evidence/2026-10-16/hardening-checks.json), [normal UI proof](evidence/2026-10-16/hardening-live-interface.json), and [deployment/recovery checklist](deployment.md). Public hosting and GitHub CI were not run; the source and design gates above remain unresolved.
