# Working agreement

- Work only in this repository. Read the supplied references without modifying them.
- Read `docs/requirements.md`, `docs/decisions.md`, and `docs/contracts.md` before application changes.
- Build one data-driven dashboard. Fixtures belong to tests, never a production reference mode.
- React requests data only from FastAPI. Collection runs independently; API reads never fetch upstream data.
- Keep SQLite private and persistent. Use parameterized SQL; preserve valid values when collection fails.
- Keep units, periods, publication metadata, and retrieval times distinct. Missing values are null/`—`, never invented zeroes.
- Derive cards, charts, tooltips, and tables from the same observations and selectors.
- Record decisions as accepted, proposed, or pending; record source evidence without claiming a page is a proven collector.
- Current stage is the authorised multi-provider backend extension from commit 03aa914: shared collection/cooldown/retention foundations, verified debt/trade/GST/CPI/policy/CGA adapters one at a time, and stored-data dashboard API. Preserve the working GDP endpoint and authentication. Frontend redesign, deployment and final Figma acceptance remain later stages; market access remains gated.
- Promote an adapter only after actual response → reviewed test fixture → validated normalisation → SQLite → authenticated API read. Record release discovery and historical coverage separately from reachability. Continue independent sources when one is blocked; never load test fixtures in application code.
- Current verified adapters: World Bank GDP, CGA actual expenditure, GSTN gross collections/history, Commerce merchandise trade, MoSPI CPI and dated Gazette inflation policy. Debt remains blocked by IMF 403/FRED runtime timeouts; market has no accepted feed. Do not promote these gates or unimplemented alternatives as completed sources.
- Authentication uses the selected 15-minute memory-only JWT and refreshable, server-revocable session with a configurable seven-day absolute maximum. Follow the pending/confirm rotation and identity-conflict contracts. Domain/DNS is a production verification gate, not a local implementation gate.
- Run the documented offline tests after probe/contract changes. Keep secrets, local databases, and raw diagnostic caches out of Git.
- Keep documentation about engineering and submission requirements. Rehearsal material is outside this project.
