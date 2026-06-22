# Development

## Lightweight Path

```text
python -m venv .venv
.venv\Scripts\python -m pip install -e backend[dev]
cd frontend
npm install
cd ..
python scripts/dev.py verify-lite
python scripts/dev.py verify-sources
```

`verify-lite` runs backend tests with coverage threshold, Ruff, mypy, frontend ESLint, Prettier, TypeScript, Vitest, production build, memory demo, static export validation, and `git diff --check`.

`verify-sources` validates source YAML, runs source-focused backend unit/API/CLI
tests with local mocks only, and runs frontend Vitest once. It must not access
the internet.

Current audited evidence is produced by `verify-lite`; live PostgreSQL tests are
skipped unless `FINNEWS_RUN_POSTGRES_TESTS=1` is set.

## Optional PostgreSQL

```text
python scripts/dev.py db-up
python scripts/dev.py verify-postgres
python scripts/dev.py db-down
```

`verify-postgres` uses Compose project `finnews_m1_verify`, starts only the
`postgres` service from `postgres:16`, waits for health, runs Alembic migration
and PostgreSQL-marked tests, and always runs:

```text
docker compose -p finnews_m1_verify down --volumes --remove-orphans
```

Do not leave Docker, dev servers, or watch processes running.
