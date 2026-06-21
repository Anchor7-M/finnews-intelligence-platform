# Development

## Lightweight Path

```text
python -m venv .venv
.venv\Scripts\python -m pip install -e backend[dev]
cd frontend
npm install
cd ..
python scripts/dev.py verify-lite
```

## Optional PostgreSQL

```text
python scripts/dev.py db-up
python scripts/dev.py verify-postgres
python scripts/dev.py db-down
```

Do not leave Docker, dev servers, or watch processes running.
