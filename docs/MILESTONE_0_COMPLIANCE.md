# Milestone 0 Compliance Audit

This audit compares the local repository against `finnews_local_codex_master_prompt.md`.
PostgreSQL is intentionally **NOT VERIFIED** in this task because Docker must not be started.

| requirement | status before this task | repository evidence | verification command | final status | remaining limitation |
| --- | --- | --- | --- | --- | --- |
| Local branch, no remote work | PASS | Branch `feat/bootstrap-finnews-platform`; no push/PR commands run | `git status --short --branch` | PASS | None |
| Synthetic fixture scale | FAIL | 68 raw observations, 60 valid JSONL observations, 4 malformed JSONL observations, 12 companies, 5 loaded sources | `python -m pytest tests/unit/test_fixture_composition.py` | PASS | RSS feed adds 4 observations beyond JSONL manifest |
| Exact and near duplicates | PARTIAL | Pipeline reports 15 exact and 21 near-duplicate observations | `python -m finnews.interfaces.cli.app demo --profile memory` | PASS | Exact duplicate relationships are counted in memory pipeline; PostgreSQL relationship persistence is not verified |
| Event and sentiment coverage | PARTIAL | All 9 event categories and 4 sentiment labels in fixtures and tests | `python -m pytest tests/unit/test_nlp_baselines.py` | PASS | Baselines are deterministic rules, not trained models |
| Validation and normalization | PARTIAL | NFKC, whitespace, URL cleanup, timestamp, market date, malformed records, oversized fixtures | `python -m pytest tests/unit/test_normalization.py tests/unit/test_sources_and_validation.py` | PASS | Live-source validation is planned only |
| Company linking | PARTIAL | Ticker, legal name, short name, longest alias, unmatched behavior, evidence, confidence | `python -m pytest tests/unit/test_nlp_baselines.py` | PASS | Deterministic alias matching only |
| Aggregation and signals | PARTIAL | Digest and signal assertions for counts, weighted sentiment, novelty, source diversity, empty dates | `python -m pytest tests/unit/test_aggregation_repository.py` | PASS | Research features only, no trading recommendation |
| FastAPI endpoints and filters | PARTIAL | All required read endpoints, filters, error envelope, request ID, timestamp timezone tested | `python -m pytest tests/contract/test_api.py tests/contract/test_api_compliance.py` | PASS | No auth by design for local read-only demo |
| CLI commands | PARTIAL | Required commands and important behavior tested through Typer runner | `python -m pytest tests/contract/test_cli.py` | PASS | PostgreSQL command help exists; DB execution not run |
| Frontend pages and modes | PARTIAL | Overview, Article Explorer, Company Detail, Daily Digest, Methodology, static/API client tests | `npm run test:unit -- --run` | PASS | API mode is typed client behavior, not browser-tested against a live server |
| Backend coverage | FAIL | 92.09% total backend coverage with 80% threshold | `python -m pytest --cov=finnews --cov-report=term-missing --cov-fail-under=80` | PASS | PostgreSQL adapter code omitted from coverage because Docker is not used |
| Lightweight verification | PARTIAL | Sequential backend tests, coverage, Ruff, mypy, frontend lint/format/typecheck/tests/build, demo, diff check | `python scripts/dev.py verify-lite` | PASS | `git diff --check` prints CRLF warnings on Windows |
| PostgreSQL integration | NOT VERIFIED | Compose and Alembic schema exist | Not run by instruction | NOT VERIFIED | Docker was not started; no image pulled |
| Resource safety | PASS | `.venv`, `node_modules`, `dist`, coverage and prompt ignored; no server/Docker started | `git check-ignore`, process scan, `docker ps` attempted | PASS | Docker daemon unavailable, so Docker state cannot be queried beyond connection failure |

## Verified Dataset Counts

- Raw observations loaded by memory demo: 68
- Valid observations accepted or deduplicated: 64
- Rejected observations: 4
- Exact duplicate observations reported by pipeline: 15
- Near-duplicate observations reported by pipeline: 21
- Stored article records after exact-deduplication: 49
- Companies: 12
- Loaded sources: 5
- Digests: 7
- Daily company signals: 46
- Synthetic label evaluation: 58/58 matched expected labels

## Coverage Exclusions

Coverage omits only `src/finnews/__init__.py` and PostgreSQL-only persistence adapter files. Alembic migration code is outside `src/finnews` and is not part of the measured runtime package. Domain, application, memory repository, source adapters, NLP baselines, API, CLI, settings, and observability remain in coverage scope.
