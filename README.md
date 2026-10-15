# Economic Indicators Dashboard

Source verification and application contracts for the supplied React/FastAPI assignment. This commit contains documentation, bounded source probes, public test fixtures, and an offline SQLite/contract proof. The application and authentication are not implemented.

## Documents

- [Requirements and submission checklist](docs/requirements.md)
- [Architecture and dependency rationale](docs/architecture.md)
- [Accepted decisions and open inputs](docs/decisions.md)
- [API and data contracts](docs/contracts.md)
- [Source results and reproduction](docs/sources.md)
- [Recorded evidence](docs/evidence/2026-10-15/)

## Reproduce

Python 3.11+ with its standard library is sufficient. Verified here with Python 3.12.14 and SQLite 3.53.1. No package installation is required.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/probe_sources.py --environment local --output-dir .verification/local
python3 scripts/prove_gdp.py --input-dir .verification/local --output-dir .verification/gdp-local
```

The second command needs normal DNS/HTTPS access; the proof command needs successful World Bank responses plus indicator and India country metadata from that run. Use a new output directory for every run. Probes make bounded requests, without retries or credentials, and deliberately skip gated market sources. Probe exit success means the diagnostic run completed, not that every source passed. `prove_gdp.py` fails if required responses, hashes, metadata, or assertions fail.

`.verification/` contains ignored raw responses, diagnostics, and disposable private SQLite files. Only reviewed public evidence and fixtures are committed. Offline tests use fixtures; they do not claim to be live source verification. No production fixture/reference-dashboard mode is planned.

## Current result

World Bank India and World annual GDP growth are proven through HTTP fetch, validation, SQLite persistence/reopen, and a panel JSON contract. An injected timeout preserves data and marks the panel stale. Other sources are explicitly classified in [the source report](docs/sources.md); no cloud deployment has been tested.

## Proposed first vertical slice

1. Convert the proven GDP pipeline into one scheduled backend job and a database-only FastAPI panel read; expose health and OpenAPI documentation.
2. Render one GDP panel in the single React dashboard using the same points for cards, chart, tooltip, and table; reserve the other panels' geometry. Include missing/error/stale tests.
3. Set up the user's HTTPS frontend/API subdomains on separate hosts and then implement the selected session contract. Verify the complete GDP flow, including renewal and revocation, before adding the remaining providers.

Exact Figma access and accepted market-data access remain independent completion gates. Credentials, a real controlled domain, deployment URLs, portfolio links, and project-role summaries are still user-supplied inputs. Do not publish an authentication-free evaluation deployment as a completed application.
