# Roadmap

## Milestone 0

Implemented: deterministic local synthetic data, modular backend, memory profile, PostgreSQL schema and Alembic migration, FastAPI read API, Typer CLI, Vue static/API dashboard, tests, coverage gate, docs, resource-safe scripts.

Not verified in the local compliance audit: PostgreSQL integration runtime, because Docker was not started.

## Milestone 1

Milestone 1A implemented: safe source registry, disabled-by-default source definitions, bounded HTTP client, mocked RSS/Atom and documented JSON ingestion, user JSON/CSV announcement imports, ETag and Last-Modified state, `304` handling, bounded retries, source health, fetch attempts, API/CLI, static demo, and Vue Source Health page.

Milestone 1B implemented locally: source-review evidence, disabled official
Federal Reserve RSS and SEC EDGAR Submissions pilot definitions, local-only
overrides, guarded no-persist smoke testing, review API/frontend visibility, and
A-share source boundary documentation. Reviewed sources are not production-ready
and remain disabled by default.

## Milestone 2

Documented only: labeled evaluation data, traditional scikit-learn classifiers, calibration, error analysis, model registry metadata.

## Milestone 3

Documented only: A-share research platform export contract, market-calendar alignment, rolling news factors, leakage checks.

## Milestone 4

Documented only: optional provider-based LLM extraction evaluation, disabled by default with cost controls and citations.
