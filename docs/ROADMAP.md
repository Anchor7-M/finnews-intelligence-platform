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

Milestone 2A implemented locally: versioned synthetic bilingual NLP benchmark,
leakage-safe splits, dummy/rule/scikit-learn baselines, validation-only
selection, probability calibration, confidence/coverage, abstention analysis,
deterministic error reports, trusted local artifact manifests, model-registry
metadata, read-only API, CLI, Vue evaluation dashboard, and static demo export.

Milestone 2B remains deferred: licensed or user-owned real-world corpus
acquisition, terms review, and human-reviewed annotation.

## Milestone 3

Documented only: A-share research platform export contract, market-calendar alignment, rolling news factors, leakage checks.

## Milestone 4

Documented only: optional provider-based LLM extraction evaluation, disabled by default with cost controls and citations.
