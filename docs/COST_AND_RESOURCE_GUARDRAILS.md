# Cost And Resource Guardrails

- Milestone 0 runs offline with synthetic data.
- No paid API, paid hosting, telemetry, browser automation, model weight, or live news source is required.
- Milestone 1A source tests use local mocks only and do not fetch from real publishers.
- Milestone 1B review/source tests remain offline. The only authorized live path
  is a manually confirmed no-persist smoke command for reviewed official
  sources.
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
