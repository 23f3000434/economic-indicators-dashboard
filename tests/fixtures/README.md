# Public source fixtures

These four files are unchanged public World Bank API response bodies captured on 15 October 2026. They match the SHA-256 digests and source URLs in [the live proof](../../docs/evidence/2026-10-15/gdp-proof.json): India and World GDP growth for 2020–2025, India country metadata, and indicator metadata.

They provide deterministic offline tests for decimal precision, identities, fiscal periods, validation failures and storage behaviour. Tests mutate in-memory copies to exercise invalid/missing cases. They are not production data defaults, a separate dashboard, or evidence of a new live fetch when an offline test runs.

Attribution: World Bank, World Development Indicators, with underlying national statistics/OECD/World Bank sources identified by the indicator metadata. See the [source and interpretation notes](../../docs/sources.md). Response metadata and blank observation-status values are retained without inventing finality or publication dates.
