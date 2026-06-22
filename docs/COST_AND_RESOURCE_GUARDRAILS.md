# Cost And Resource Guardrails

- Milestone 0 runs offline with synthetic data.
- No paid API, paid hosting, telemetry, browser automation, model weight, or live news source is required.
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
external databases, pgAdmin, Redis, Kafka, or cloud resources are used.
