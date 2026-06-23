# Agent Notes

## Layout

- `backend/src/finnews/domain`: framework-free entities, enums, value objects, and errors.
- `backend/src/finnews/application`: ports, use cases, and pipeline orchestration.
- `backend/src/finnews/infrastructure`: memory/PostgreSQL adapters, source adapters, NLP baselines, settings, and logging.
- `backend/src/finnews/interfaces`: FastAPI and Typer entrypoints.
- `frontend`: Vue 3 TypeScript dashboard.
- `contracts/finnews-market-signal/v1`: versioned local research signal handoff contract.
- `config/integrations`: example-only local integration schemas. Do not commit personal broker config.

## Commands

- Lightweight verification: `python scripts/dev.py verify-lite`
- Cross-asset verification: `python scripts/dev.py verify-cross-asset`
- Backend tests: `cd backend && python -m pytest`
- Backend lint/type checks: `cd backend && ruff check . && ruff format --check . && mypy src tests`
- Frontend checks: `cd frontend && npm run lint && npm run format:check && npm run typecheck && npm run test:unit -- --run && npm run build`
- Optional PostgreSQL: `python scripts/dev.py db-up`, then `python scripts/dev.py db-down`

## Rules

- Do not push, open PRs, or modify remotes during this local phase.
- Do not add React, paid APIs, paid hosting dependencies, proprietary data, copied article bodies, telemetry, or analytics.
- Keep Milestone 0 honest: synthetic offline data only, no investment advice, no live intelligence claims.
- For Milestone 1A source work, keep real sources disabled by default, use local mocks for automated tests, expose no arbitrary URL fetch endpoint, and store no raw response bodies.
- For Milestone 1B source work, keep official source configs disabled by default, require typed review evidence for approved network sources, use ignored local overrides for manual smoke tests, never commit personal contact metadata or raw live responses, and keep automated tests offline.
- For Milestone 2A NLP work, use only the committed synthetic benchmark, keep model binaries under ignored `.finnews-artifacts/`, never train on live-source output, and never claim real-world production accuracy.
- For Milestone 3A research-export work, keep packages synthetic/offline, write local exports only under ignored `.finnews-research-exports/`, never fetch live A-share calendars/prices/announcements, and never add returns, backtests, or recommendations.
- For revised Milestone 3A cross-asset work, keep FinNews product language cross-asset-first. The A-share research export is optional and must not dominate the homepage, architecture, nav, or roadmap.
- Do not import MT5 client packages, contact a terminal, accept credentials, query account data, or add execution routes in this repository during this milestone.
- Write local market-signal packages only under ignored `.finnews-market-signals/`.
- Stop any temporary services before handing work back.
- Update docs when behavior changes.

## Definition Of Done

- Memory-profile demo runs end to end.
- Backend coverage is at least 80% for core modules.
- Backend and frontend checks pass or failures are reported precisely.
- Implemented versus planned features are clearly separated.
