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

The Compose file starts one PostgreSQL 16 container bound to `127.0.0.1:55432` with `restart: "no"`. Volumes are preserved by default.

Never run `docker system prune` for this project.

## Audit Status

The non-Docker lightweight path is verified. PostgreSQL integration is **not verified** in the compliance audit because Docker was not started and no image was pulled.
