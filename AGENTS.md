# Working agreement

- Work only in this repository. Read the supplied references without modifying them.
- Read `docs/requirements.md`, `docs/decisions.md`, and `docs/contracts.md` before application changes.
- Build one data-driven dashboard. Fixtures belong to tests, never a production reference mode.
- React requests data only from FastAPI. Collection runs independently; API reads never fetch upstream data.
- Keep SQLite private and persistent. Use parameterized SQL; preserve valid values when collection fails.
- Keep units, periods, publication metadata, and retrieval times distinct. Missing values are null/`—`, never invented zeroes.
- Derive cards, charts, tooltips, and tables from the same observations and selectors.
- Record decisions as accepted, proposed, or pending; record source evidence without claiming a page is a proven collector.
- Current stage is authorised hardening/deployment readiness from 42d9d4a: reproduce suspected defects, fix focused correctness/security issues, deterministically optimise existing artwork, measure cold loads and design differences, make bounded debt/market attempts, and prepare separate-environment deployment, private backup/restore and offline CI. Preserve the working app, authentication, GDP endpoint, canonical contracts and independent collection. Public deployment remains unauthorised for this stage. Request Figma sharing if the exact frame remains inaccessible; continue independent work with the supplied SVG.
- Promote an adapter only after actual response → reviewed test fixture → validated normalisation → SQLite → authenticated API read. Record release discovery and historical coverage separately from reachability. Continue independent sources when one is blocked; never load test fixtures in application code.
- Current verified adapters: World Bank GDP, CGA actual expenditure, GSTN gross collections/history, Commerce merchandise trade, MoSPI CPI and dated Gazette inflation policy. Debt remains blocked by IMF 403/FRED runtime timeouts; NSE public quote JSON is reachable but market still has no accepted collection/display feed. Do not promote these gates or unimplemented alternatives as completed sources.
- Authentication uses the selected 15-minute memory-only JWT and refreshable, server-revocable session with a configurable seven-day absolute maximum. Follow the pending/confirm rotation and identity-conflict contracts. Domain/DNS is a production verification gate, not a local implementation gate.
- Production must use the allowlisted runtime and single-owner `app.serve` entry in `docs/deployment.md`; hosted mount/proxy/domain acceptance and off-host backups remain pending.
- Run the documented offline tests after probe/contract changes. Keep secrets, local databases, and raw diagnostic caches out of Git.
- Keep documentation about engineering and submission requirements. Rehearsal material is outside this project.
