# Development

## Research Export

Build a local ignored package with:

```text
cd backend
python -m finnews.interfaces.cli.app research export build --profile memory --output ../.finnews-research-exports/latest
```

Validate or compare packages with `finnews research export validate --path <package>` and `finnews research export compare --left <a> --right <b>`. The commands are offline and use synthetic data by default.

## Cross-Asset Signal Contract

Build and validate a local ignored signal package with:

```text
cd backend
python -m finnews.interfaces.cli.app signal export --output ../.finnews-market-signals/latest
python -m finnews.interfaces.cli.app signal validate --path ../.finnews-market-signals/latest
```

Inspect the offline readiness boundary with:

```text
cd backend
python -m finnews.interfaces.cli.app asset validate
python -m finnews.interfaces.cli.app cross-asset summary
python -m finnews.interfaces.cli.app mt5 readiness
python -m finnews.interfaces.cli.app mt5 validate-symbol-map --path ../config/integrations/mt5-symbol-map.example.yaml
```

`python scripts/dev.py verify-cross-asset` runs the cross-asset CLI smoke checks,
package validation, symbol-map validation, API/CLI tests, and trading-surface
audit.

## Market-Reaction Validation

Validate the local market-bar import contract examples with:

```text
cd backend
python -m finnews.interfaces.cli.app market-data contract validate --path ../contracts/finnews-market-bars/v1/examples/synthetic-bars.csv
python -m finnews.interfaces.cli.app market-data contract validate --path ../contracts/finnews-market-bars/v1/examples/synthetic-bars.jsonl
```

Build and inspect deterministic synthetic scenarios with:

```text
cd backend
python -m finnews.interfaces.cli.app market-data build-demo --scenario synthetic-planted-reaction-v1
python -m finnews.interfaces.cli.app reaction overview
python -m finnews.interfaces.cli.app reaction evaluate --scenario synthetic-planted-reaction-v1
python -m finnews.interfaces.cli.app reaction compare --left synthetic-null-reaction-v1 --right synthetic-planted-reaction-v1
```

`python scripts/dev.py verify-market-reaction` validates the contract examples,
runs all three synthetic scenarios, exports static-demo JSON samples, runs M3C
backend tests, runs frontend Vitest once, and checks the static manifest.

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
python scripts/dev.py verify-cross-asset
python scripts/dev.py verify-market-reaction
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

`verify-postgres` uses Compose project `finnews_m3c_verify`, starts only the
`postgres` service from `postgres:16`, waits for health, runs Alembic migration
and PostgreSQL-marked tests, and always runs:

```text
docker compose -p finnews_m3c_verify down --volumes --remove-orphans
```

Do not leave Docker, dev servers, or watch processes running.
