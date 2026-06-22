# Milestone 0 Compliance Audit

This audit compares the local repository against `finnews_local_codex_master_prompt.md`.
PostgreSQL is verified locally through a disposable Docker Compose project.

| requirement | status before this task | repository evidence | verification command | final status | remaining limitation |
| --- | --- | --- | --- | --- | --- |
| Local branch, no remote work | PASS | Branch `feat/bootstrap-finnews-platform`; no push/PR commands run | `git status --short --branch` | PASS | None |
| Synthetic fixture scale | FAIL | 68 raw observations, 60 valid JSONL observations, 4 malformed JSONL observations, 12 companies, 5 loaded sources | `python -m pytest tests/unit/test_fixture_composition.py` | PASS | RSS feed adds 4 observations beyond JSONL manifest |
| Exact and near duplicates | PARTIAL | Pipeline reports 8 exact duplicate observations, 10 near-duplicate observations, 8 exact pairs, 10 near pairs, and 18 duplicate clusters in memory and PostgreSQL | `python -m pytest tests/unit/test_deduplication_accounting.py`; `python scripts/dev.py verify-postgres` | PASS | None for Milestone 0 synthetic fixtures |
| Event and sentiment coverage | PARTIAL | All 9 event categories and 4 sentiment labels in fixtures and tests | `python -m pytest tests/unit/test_nlp_baselines.py` | PASS | Baselines are deterministic rules, not trained models |
| Validation and normalization | PARTIAL | NFKC, whitespace, URL cleanup, timestamp, market date, malformed records, oversized fixtures | `python -m pytest tests/unit/test_normalization.py tests/unit/test_sources_and_validation.py` | PASS | Live-source validation is planned only |
| Company linking | PARTIAL | Ticker, legal name, short name, longest alias, unmatched behavior, evidence, confidence | `python -m pytest tests/unit/test_nlp_baselines.py` | PASS | Deterministic alias matching only |
| Aggregation and signals | PARTIAL | Digest and signal assertions for counts, weighted sentiment, novelty, source diversity, empty dates | `python -m pytest tests/unit/test_aggregation_repository.py` | PASS | Research features only, no trading recommendation |
| FastAPI endpoints and filters | PARTIAL | All required read endpoints, filters, error envelope, request ID, timestamp timezone tested | `python -m pytest tests/contract/test_api.py tests/contract/test_api_compliance.py` | PASS | No auth by design for local read-only demo |
| CLI commands | PARTIAL | Required commands and PostgreSQL-profile doctor, db upgrade, ingest, process, digest, and signals are tested | `python -m pytest tests/contract/test_cli.py`; `python -m pytest -m postgres` | PASS | No long-running process is started |
| Frontend pages and modes | PARTIAL | Overview, Article Explorer, Company Detail, Daily Digest, Methodology, static/API client tests | `npm run test:unit -- --run` | PASS | API mode is typed client behavior, not browser-tested against a live server |
| Backend coverage | FAIL | 92.09% total backend coverage with 80% threshold | `python -m pytest --cov=finnews --cov-report=term-missing --cov-fail-under=80` | PASS | PostgreSQL adapter code omitted from coverage because Docker is not used |
| Lightweight verification | PARTIAL | Sequential backend tests, coverage, Ruff, mypy, frontend lint/format/typecheck/tests/build, demo, diff check | `python scripts/dev.py verify-lite` | PASS | `git diff --check` prints CRLF warnings on Windows |
| PostgreSQL integration | NOT VERIFIED | Real PostgreSQL repository, Alembic upgrade/downgrade, schema inspection, constraint/rollback, JSONB/timestamptz/UUID, API, CLI, and full fixture pipeline are tested | `python scripts/dev.py verify-postgres` | PASS | GitHub Actions config is locally inspected, not remotely run |
| Resource safety | PASS | `.venv`, `node_modules`, `dist`, coverage and prompt ignored; only project-scoped PostgreSQL was started and cleaned up | `docker compose -p finnews_m0_verify down --volumes --remove-orphans`; Docker label checks | PASS | `postgres:16` image is intentionally retained to avoid re-download |

## Verified Dataset Counts

- Raw observations loaded by memory demo: 68
- Valid observations: 64
- Rejected observations: 4
- Canonical articles: 46
- Exact duplicate observations: 8
- Near-duplicate observations: 10
- Duplicate observations: 18
- Exact duplicate pairs: 8
- Near-duplicate pairs: 10
- Duplicate clusters: 18
- Companies: 12
- Loaded sources: 5
- Digests: 7
- Daily company signals: 46
- Synthetic label evaluation: 54/54 matched expected canonical/exact NLP labels; 68/68 matched expected observation dispositions

## PostgreSQL Verification Evidence

- Image: official `postgres:16`; it was absent before this task and was pulled.
- Compose project/service: `finnews_m0_verify` / `postgres`.
- Host port: `127.0.0.1:55432`.
- Resource limits: 0.50 CPU and 512 MB memory.
- Migration: Alembic upgrade from empty DB, downgrade to base, and re-upgrade to head passed.
- Integration tests: 5 passed with `python scripts/dev.py verify-postgres`.
- First-run PostgreSQL row counts: `article_company_links=46`, `article_duplicates=10`, `article_events=46`, `article_sentiments=46`, `articles=56`, `companies=12`, `company_aliases=56`, `daily_company_signals=46`, `daily_digests=7`, `ingestion_runs=68`, `observation_dispositions=68`, `pipeline_runs=1`, `raw_articles=64`, `sources=5`.
- Second-run PostgreSQL row counts keep canonical business tables stable; only audit tables change: `ingestion_runs=136`, `pipeline_runs=2`.
- Cleanup removed all containers, volumes, and networks with Compose project label `finnews_m0_verify`.

## Coverage Exclusions

Coverage omits only `src/finnews/__init__.py` and PostgreSQL-only persistence adapter files. Alembic migration code is outside `src/finnews` and is not part of the measured runtime package. Domain, application, memory repository, source adapters, NLP baselines, API, CLI, settings, and observability remain in coverage scope.
