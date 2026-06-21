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

`verify-lite` runs backend tests with coverage threshold, Ruff, mypy, frontend ESLint, Prettier, TypeScript, Vitest, production build, memory demo, static export validation, and `git diff --check`.

Current audited evidence: 39 backend tests passed, 92.09% backend coverage, and 8 frontend tests passed.

## Optional PostgreSQL

```text
python scripts/dev.py db-up
python scripts/dev.py verify-postgres
python scripts/dev.py db-down
```

Do not leave Docker, dev servers, or watch processes running.
