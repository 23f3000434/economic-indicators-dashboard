# Working agreement

- Work only in this repository. Read the supplied references without modifying them.
- Read `docs/requirements.md`, `docs/decisions.md`, and `docs/contracts.md` before application changes.
- Build one data-driven dashboard. Fixtures belong to tests, never a production reference mode.
- React requests data only from FastAPI. Collection runs independently; API reads never fetch upstream data.
- Keep SQLite private and persistent. Use parameterized SQL; preserve valid values when collection fails.
- Keep units, periods, publication metadata, and retrieval times distinct. Missing values are null/`—`, never invented zeroes.
- Derive cards, charts, tooltips, and tables from the same observations and selectors.
- Record decisions as accepted, proposed, or pending; record source evidence without claiming a page is a proven collector.
- The user authorised the complete local authenticated GDP slice: scaffolding, migrations, scheduled collection, protected API, one React panel, authentication and verification. Remaining providers, public deployment and final Figma acceptance stay outside this stage.
- Authentication uses the selected 15-minute memory-only JWT and refreshable, server-revocable session with a configurable seven-day absolute maximum. Follow the pending/confirm rotation and identity-conflict contracts. Domain/DNS is a production verification gate, not a local implementation gate.
- Run the documented offline tests after probe/contract changes. Keep secrets, local databases, and raw diagnostic caches out of Git.
- Keep documentation about engineering and submission requirements. Rehearsal material is outside this project.
