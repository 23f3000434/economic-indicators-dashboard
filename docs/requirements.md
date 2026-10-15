# Requirements and verification

The supplied DOCX is the product/assessment brief; the user's instructions define the authorised work. Current scope is the complete local authenticated GDP vertical slice, including scaffold, migrations, scheduled collection, protected API, one React panel and verification. Other providers, public deployment and final Figma acceptance remain outside this stage. Domain/DNS does not block local implementation.

References read without modification:
- `Interview_Round_2_Full_Stack_Application_Challenge.docx` supplied from Downloads.
- Supplied Figma file `brsbeMh0t7dB6ibf3cJN4D`, assignment frame `1:2`; supplied URL opens page `0:1`.
- Supplied `Economic Indicator Assignment.svg` and the DOCX appendix image.

## Application acceptance

| ID | Required outcome | Verification |
| --- | --- | --- |
| R01 | React frontend; FastAPI backend; configurable API base URL; browser requests dashboard data only from FastAPI | Build/config checks; browser network audit; API reads tested with upstream access disabled |
| R02 | Faithful supplied design at **1214 × 2159 CSS pixels**, legible without clipping, unintended horizontal scrolling, or disruptive layout shifts | Exact-viewport screenshots and layout/asset review against frame `1:2`; reserved skeleton geometry |
| R03 | Live market ticker and GDP India/World, India debt/US comparison, trade, GST/monthly average, India inflation/RBI target, government total/capital expenditure | Metric/source catalogue, source checks, six-panel and ticker acceptance tests |
| R04 | Correct charts, cards, legends, labels, periods, comparisons, and visible controls | Values and summaries trace to canonical points; chart/table agreement and keyboard/interaction tests; reasonable unspecified behaviour documented |
| R05 | NSE principal source for applicable data; named public alternatives for indicators it does not publish | Source/access register; explicit non-NSE attribution in UI and README; market access still unresolved |
| R06 | Source and observation "as of" information for each indicator/group; transformations and limitations documented | Inspect panel metadata and compare selected stored observations with the source; collection time never substituted for the reporting period |
| R07 | Independent scheduled collector, timeouts, caching, validation, rate-aware refresh, frontend update mechanism | Job and failure tests, collection-run records, browser polling audit; more users do not increase upstream fetch rates |
| R08 | Provider failures isolated; last valid observations retained and marked stale; missing values shown as `—` | Malformed/timeout/missing-value fixtures; one provider fails while other panels still render; no replacement with invalid/zero data |
| R09 | Useful loading, empty, unavailable, API error/offline, and stale states | State and layout tests; fixed panel space during initial load; partial failures preserve dashboard structure |
| R10 | Sign-in protects dashboard/API; selected refreshable session behaviour | Authentication acceptance in `contracts.md`; separate evaluation account instructions; local slice implements it |
| R11 | Persistent private database; parameterized direct SQL; no untrusted SQL concatenation | SQL review; restart/redeploy and restore checks; filesystem permissions; no DB network listener or static-file exposure |
| R12 | Frontend and API on separate HTTPS websites and separate hosting environments; exact-origin CORS | Remote checks of both origins, certificates, allowed/disallowed CORS requests; hosting/domain setup recorded |
| R13 | Health route; API request/response/auth documentation; environment names; DB setup/migrations; local run instructions | OpenAPI and README review; clean-checkout setup; health does not call upstream providers |
| R14 | Maintainable, performant, explainable application | Focused tests, asset/bundle review, cached-read performance, stable rendering; document meaningful technical/AI-assisted decisions and their verification |

The SVG is `1248 × 2193`, has outlined text and embedded images, and cannot prove fonts, layout constraints, states, prototypes, or revision parity. Figma connection access was denied; exact inspection is pending. Preserve the design's structure while correcting illustrative numbers, misleading units, copied legends, and unsupported daily debt dates. Record corrections instead of inventing observations.

## Submission checklist

| Deliverable | Verification/completion gate |
| --- | --- |
| Repository with frontend/backend, schema/migrations, README | Locked local setup, tests and GDP slice are implemented; full multi-provider delivery is still pending |
| Frontend URL, API/docs URL, health URL | Accessible during evaluation; production HTTPS/CORS/health checks pass |
| Evaluation account or instructions shared separately | Login works; no passwords, signing keys, refresh tokens, or production credentials committed |
| Portfolio URL and flagship project links | User supplies working links plus accurate role, technologies, and contribution summaries |
| Assumptions, known limitations, fallback sources | README links to up-to-date decisions and source evidence |
| Post-assessment screen-recorded video explaining flow, architecture, challenges, decisions, and AI use/verification | Record and submit after assessment; this requirement is tracked here, with no rehearsal material in this repository |

Assessment weights: design 25, behaviour 20, backend/data 15, security/database 15, performance/code quality 15, deployment/documentation 10.
