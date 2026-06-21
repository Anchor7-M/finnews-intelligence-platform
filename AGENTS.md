# Agent Notes

## Layout

- `backend/src/finnews/domain`: framework-free entities, enums, value objects, and errors.
- `backend/src/finnews/application`: ports, use cases, and pipeline orchestration.
- `backend/src/finnews/infrastructure`: memory/PostgreSQL adapters, source adapters, NLP baselines, settings, and logging.
- `backend/src/finnews/interfaces`: FastAPI and Typer entrypoints.
- `frontend`: Vue 3 TypeScript dashboard.

## Commands

- Lightweight verification: `python scripts/dev.py verify-lite`
- Backend tests: `cd backend && python -m pytest`
- Backend lint/type checks: `cd backend && ruff check . && ruff format --check . && mypy src tests`
- Frontend checks: `cd frontend && npm run lint && npm run format:check && npm run typecheck && npm run test:unit -- --run && npm run build`
- Optional PostgreSQL: `python scripts/dev.py db-up`, then `python scripts/dev.py db-down`

## Rules

- Do not push, open PRs, or modify remotes during this local phase.
- Do not add React, paid APIs, paid hosting dependencies, proprietary data, copied article bodies, telemetry, or analytics.
- Keep Milestone 0 honest: synthetic offline data only, no investment advice, no live intelligence claims.
- Stop any temporary services before handing work back.
- Update docs when behavior changes.

## Definition Of Done

- Memory-profile demo runs end to end.
- Backend coverage is at least 80% for core modules.
- Backend and frontend checks pass or failures are reported precisely.
- Implemented versus planned features are clearly separated.
