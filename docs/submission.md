# Assignment submission handoff

Prepared for the supplied Interview Round II Full Stack Application Challenge. The DOCX defines assessment deliverables; the user's messages authorise engineering/deployment actions. Current implementation is complete locally through 596e4a7, with final delivery materials being reconciled. **Public deployment and production acceptance are not yet verified.** [Current commit/CI/URL/input status](delivery-status.md) is the release record.

## Deliverables reconciled

| Assignment deliverable | Material / evidence | Status |
| --- | --- | --- |
| React frontend + FastAPI backend, schema/migrations, README | `frontend/src`, `backend/app`, `backend/migrations`, locked dependencies, [README](../README.md) | Implemented; private GitHub delivery status tracked separately |
| Figma screen at 1214×2159 | [Measured frame/panels/fonts/screenshots](design-completion.md), [current interaction capture](evidence/2026-10-16/interaction-desktop.png) | Geometry/artwork verified locally. User accepted Roboto fallback; real-data corrections and remaining visual differences disclosed |
| Ticker + GDP/debt/trade/GST/CPI-policy/expenditure | [Current sources](sources.md), [canonical contracts](contracts.md), [actual source-to-screen](evidence/2026-10-16/source-to-screen.json), [two market polls](evidence/2026-10-16/interaction-live.json) | All implemented locally; production source egress/display acceptance pending |
| Loading/empty/error/stale/null states and visible controls | [Frontend](frontend.md), [verification chronology](verification.md) | Implemented and covered by recorded browser/unit tests |
| Independent validated scheduled collection, bounded/rate-aware refresh | [Architecture](architecture.md), [API/data contracts](contracts.md) | Implemented; browser reads never fetch upstream |
| Authentication, private database and parameterized SQL | [Auth contract](contracts.md#selected-authentication-contract), SQL migrations, [evaluation procedure](evaluation-access.md) | Implemented/local security tests; real provider-HTTPS/auth-rewrite acceptance pending |
| Separate frontend/API hosting, HTTPS/exact-origin CORS | [Deployment blueprint/config/runbook](deployment.md), [production acceptance](production-smoke.md) | Prepared and authorised; required concrete release inputs pending |
| Live frontend/API(or docs)/health URLs accessible during review | [URL register](delivery-status.md#urls) | Local URLs available; public URLs not yet deployed |
| API route/request/response/auth/config/DB/local-run documentation | Public OpenAPI at the API `/docs` and `/openapi.json`; [contracts](contracts.md), [README](../README.md), `.env.example` | Present locally; public docs URL awaits deployment |
| Private evaluation account/instructions | [Operator and evaluator procedure](evaluation-access.md) | Procedure ready; production account and private handoff pending |
| Assumptions, known limitations, public alternative sources | [Assumptions](assumptions.md), [sources](sources.md), [decisions](decisions.md) | Prepared with actual definitions and acceptance boundaries |
| Portfolio website + flagship projects with role/technologies/contribution | User supplies separately, per final-delivery instruction | Required by assignment; intentionally not populated in this repository |
| Post-assessment screen-recorded explanation | Requirements below | Required **after assessment**; not recorded/submitted here |

Assessment weights: design25, behaviour20, backend/data15, security/database15, performance/code quality15, deployment/documentation10. This mapping is evidence-oriented, not a self-awarded score.

## Evaluation access and repository

Repository: [economic-indicators-dashboard](https://github.com/23f3000434/economic-indicators-dashboard), private. Ensure named evaluators have access during review, or provide an owner-approved source handoff. No invitation, public visibility change or credential disclosure is implied by this document.

After deployment, privately deliver the frontend/API/docs/health URLs, account username/password, absolute session policy and availability window through an approved channel. Never put credentials in README, Issues, CI logs, screenshots, URL query strings or a repository commit. [Evaluation-access instructions](evaluation-access.md) provide the actual interactive provisioning command and safe sign-in steps.

## Required recording after assessment

The owner must submit a screen-recorded video in their own words demonstrating:

- The complete application flow and how frontend, API, collector and database work together.
- How the application was built, the main challenges and their resolutions.
- Important technical/design decisions and why they were chosen.
- Actual AI use: tasks assisted, incorporation of output, why AI was suitable and how results were checked. [Factual workflow/evidence](ai-workflow.md) supports this explanation.

The brief does not specify a duration, upload destination or deadline. Confirm those with the assessor when arranging the post-assessment submission; do not invent them. No recording link or completion claim is supplied. This is deliverable tracking, not interview rehearsal.

## Handoff boundary

The application, engineering materials and local evidence are reviewable. Final submission is not fully complete until working production URLs, bounded hosted acceptance, private account handoff and assessor repository access are verified. Portfolio/project links and the later recording remain owner-supplied external materials. The selected Roboto fallback is an accepted deviation from Segoe UI; sample-number differences are separately explained as accurate economic presentation.

Current zero-budget delivery: see [free-deployment.md](free-deployment.md). PostgreSQL and auth-only proxy are implemented/tested; the free database is created with external access blocked. API/frontend deployment and hosted acceptance remain blocked on the recorded repository/secret actions. Portfolio/project links and recording stay separate.
