# Working agreement

- Work only in this repository. Read the supplied references without modifying them.
- Read `docs/requirements.md`, `docs/decisions.md`, and `docs/contracts.md` before application changes.
- Build one data-driven dashboard. Fixtures belong to tests, never a production reference mode.
- React requests data only from FastAPI. Collection runs independently; API reads never fetch upstream data.
- Keep SQLite private and persistent. Use parameterized SQL; preserve valid values when collection fails.
- Keep units, periods, publication metadata, and retrieval times distinct. Missing values are null/`—`, never invented zeroes.
- Derive cards, charts, tooltips, and tables from the same observations and selectors.
- Record decisions as accepted, proposed, or pending; record source evidence without claiming a page is a proven collector.
- Current stage is authorised design/data completion from af5ff07: measure and reproduce frame 1:2 precisely, implement actual stored market snapshots and comparable debt, verify current official releases, and demonstrate normal source-to-screen and visual acceptance. Preserve authentication, GDP v1, canonical contracts, independent collection and delivery safeguards. Public deployment remains pending completion review.
- Figma is inspectable in the existing browser's read-only Properties panel. MCP edit-access restrictions do not establish browser inaccessibility. Measure individual elements and use available exports/SVG; do not extrapolate typography or expand reference panels. Put extended tables, diagnostics and provenance in accessible drawers.
- Promote an adapter only after actual response → reviewed test fixture → validated normalisation → SQLite → authenticated API read. Record release discovery and historical coverage separately from reachability. Continue independent sources when one is blocked; never load test fixtures in application code.
- Verified adapters: World Bank GDP, CGA actual expenditure, GSTN gross collections/history, Commerce merchandise trade, MoSPI CPI and dated Gazette inflation policy. Comparable IMF WEO debt and NSE/Upstox market snapshots now pass actual-response validation, persistence and protected reads. Keep release discovery/history and public-host/display acceptance distinct; reachability/documentation alone is not completion. Keep credentials server-side and exchange/observation timestamps distinct from retrieval.
- Authentication uses the selected 15-minute memory-only JWT and refreshable, server-revocable session with a configurable seven-day absolute maximum. Follow the pending/confirm rotation and identity-conflict contracts. Domain/DNS is a production verification gate, not a local implementation gate.
- Production must use the allowlisted runtime and single-owner `app.serve` entry in `docs/deployment.md`; hosted mount/proxy/domain acceptance and off-host backups remain pending.
- Run the documented offline tests after probe/contract changes. Keep secrets, local databases, and raw diagnostic caches out of Git.
- Keep documentation about engineering and submission requirements. Rehearsal material is outside this project.
- Current exact-font gate: Figma uses Segoe UI for cards/axes/ticker. Use only licensed webfonts or a user-accepted installed-font/fallback approach; current local fallback is provisional. Roboto/Manrope and measured geometry are verified. Do not describe MCP edit denial as browser inaccessibility.
- Current interaction pass: compact viewport-clamped chart tooltips, obvious shared period selection with pointer/keyboard/tap dismissal, and a seamless accessible quote scroll that survives refreshes. Preserve measured geometry, canonical values/statuses, authentication and backend architecture. Run focused checks/browser inspection and verify two real polling cycles. No unrelated features/refactors or deployment.
