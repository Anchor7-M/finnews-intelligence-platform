# Cost And Resource Guardrails

## M4A MT5 Read-Only Guardrails

M4A remains zero-cost and local-first:

- No paid broker API, cloud database, market-data subscription, model download,
  telemetry, or hosted bridge is added.
- `MetaTrader5` is optional and not installed by CI or default setup.
- The platform never launches a terminal executable.
- Local exports are bounded by symbol count, bar count, timeframe range, and
  ignored output path.
- PostgreSQL verification uses one disposable `postgres:16` service under the
  `finnews_m4a_verify` Compose project, localhost binding, 512 MB memory, 0.50
  CPU, restart disabled, and cleanup with `down --volumes --remove-orphans`.

## Milestone 3A Research Export

The default dense panel is exactly 2,880 rows and runs CPU-only in one local process. Research packages stay below 10 MB, individual package files below 5 MB, and local exports under ignored `.finnews-research-exports/`. Do not add live market dependencies, schedulers, queues, model downloads, cloud services, or background daemons.

- Milestone 0 runs offline with synthetic data.
- No paid API, paid hosting, telemetry, browser automation, model weight, or live news source is required.
- Milestone 1A source tests use local mocks only and do not fetch from real publishers.
- Milestone 1B review/source tests remain offline. The only authorized live path
  is a manually confirmed no-persist smoke command for reviewed official
  sources.
- Milestone 2A NLP training uses only committed synthetic records, CPU-only
  scikit-learn, `n_jobs=1`, and ignored local artifacts. It does not download
  datasets, embeddings, tokenizers, model weights, or use hosted experiment
  trackers.
- Source fetching is run-once and bounded: default 2 MB response limit, hard 5 MB ceiling, no article-page downloads, no media downloads, and no background worker.
- Default verification does not require Docker.
- Python dependencies belong in `.venv`; frontend dependencies belong in `frontend/node_modules`.

## PostgreSQL

Start the optional database:

```text
python scripts/dev.py db-up
```

Stop it:

```text
python scripts/dev.py db-down
```

The Compose file starts one PostgreSQL 16 container bound to `127.0.0.1:55432`
with `restart: "no"`, 0.50 CPU, 512 MB memory, a project-scoped network, and a
project-scoped disposable volume. PostgreSQL data is never bind-mounted from the
host filesystem.

Never run `docker system prune` for this project.

## Audit Status

The non-Docker lightweight path is verified. PostgreSQL integration was verified
locally with `python scripts/dev.py verify-postgres`; the official `postgres:16`
image was pulled because it was absent before the task. No paid services,
external databases, pgAdmin, Redis, Kafka, or cloud resources are used. M1B
continues to use zero paid services; SEC contact metadata, if supplied, remains
local and untracked.

M2A continues the zero-cost policy. The benchmark is below 5 MB, each generated
model artifact is below 25 MB, and `.finnews-artifacts/` is ignored.

Revised M3A continues the zero-cost policy. The cross-asset fixture is
deterministic and synthetic; local market-signal exports are written only under
ignored `.finnews-market-signals/`; the committed example contract package is
small; and no live price source, broker terminal, cloud service, model download,
scheduler, queue, telemetry, or paid API is required.

M3C continues the zero-cost policy. Synthetic market bars are generated
deterministically in-process; committed static demo files contain bounded bar
samples rather than the full generated bar set. The market-bar import contract
accepts only explicit local CSV/JSONL paths, enforces a 5 MB file limit, and
rejects credentials, account fields, order fields, and future-return sentinel
columns. No paid market-data provider, browser binary, model download, broker
terminal, scheduler, queue, telemetry, or cloud service is required.
