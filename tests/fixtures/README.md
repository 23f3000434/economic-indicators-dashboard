# Public source fixtures

These four files are unchanged public World Bank API response bodies captured on 15 October 2026. They match the SHA-256 digests and source URLs in [the live proof](../../docs/evidence/2026-10-15/gdp-proof.json): India and World GDP growth for 2020–2025, India country metadata, and indicator metadata.

They provide deterministic offline tests for decimal precision, identities, fiscal periods, validation failures and storage behaviour. Tests mutate in-memory copies to exercise invalid/missing cases. They are not production data defaults, a separate dashboard, or evidence of a new live fetch when an offline test runs.

Attribution: World Bank, World Development Indicators, with underlying national statistics/OECD/World Bank sources identified by the indicator metadata. See the [source and interpretation notes](../../docs/sources.md). Response metadata and blank observation-status values are retained without inventing finality or publication dates.

`providers/{cga,gst,trade,inflation}/` contains gzip-compressed original official responses. Gzip timestamps are fixed at zero; decompressed bytes match each manifest's SHA-256. Manifests record exact URLs, fetch dates, HTTP metadata and reviewed values. Tests separately verify discovery, normalisation, units/periods/status and protected API readback. Files include the complete relevant HTML/XLSX/PDF responses for reproducibility; production modules never import them.

Attribution: Controller General of Accounts; Goods and Services Tax Network; Ministry of Commerce and Industry (including its official PIB release mirrors); Ministry of Statistics and Programme Implementation/National Statistics Office; Ministry of Finance/DEA and Gazette of India. Historical/revised figures, compensation cess treatment, CPI bases, provisional status, rounding and policy validity are documented in [multi-provider.md](../../docs/multi-provider.md). Offline fixture tests are not new live fetches.
