# Development

## Research Export

Build a local ignored package with:

```text
cd backend
python -m finnews.interfaces.cli.app research export build --profile memory --output ../.finnews-research-exports/latest
```

Validate or compare packages with `finnews research export validate --path <package>` and `finnews research export compare --left <a> --right <b>`. The commands are offline and use synthetic data by default.

## Lightweight Path

```text
python -m venv .venv
.venv\Scripts\python -m pip install -e backend[dev]
cd frontend
npm install
cd ..
python scripts/dev.py verify-lite
python scripts/dev.py verify-sources
python scripts/dev.py verify-source-reviews
python scripts/dev.py verify-ml
```

`verify-lite` runs backend tests with coverage threshold, Ruff, mypy, frontend ESLint, Prettier, TypeScript, Vitest, production build, memory demo, static export validation, and `git diff --check`.

`verify-sources` validates source YAML, runs source-focused backend unit/API/CLI
tests with local mocks only, and runs frontend Vitest once. It must not access
the internet.

`verify-source-reviews` validates source-review evidence and review/config
integrity, then runs review, override, smoke-gate, and review API tests with
mocked transports only. It must not access the internet.

`verify-ml` rebuilds and validates the synthetic NLP benchmark, runs NLP-focused
tests, runs the bounded benchmark, exports NLP static-demo JSON, and validates
static files. It is offline, CPU-only, and writes model binaries only under
ignored `.finnews-artifacts/`.

Current audited evidence is produced by `verify-lite`; live PostgreSQL tests are
skipped unless `FINNEWS_RUN_POSTGRES_TESTS=1` is set.

## Optional PostgreSQL

```text
python scripts/dev.py db-up
python scripts/dev.py verify-postgres
python scripts/dev.py db-down
```

`verify-postgres` uses Compose project `finnews_m2a_verify`, starts only the
`postgres` service from `postgres:16`, waits for health, runs Alembic migration
and PostgreSQL-marked tests, and always runs:

```text
docker compose -p finnews_m2a_verify down --volumes --remove-orphans
```

Do not leave Docker, dev servers, or watch processes running.
