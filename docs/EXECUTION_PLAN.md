# Execution Plan

## Assumptions

- This repository is a clean bootstrap with an existing MIT license.
- Milestone 0 must be implemented locally only and must not push to GitHub.
- The default runtime and verification path uses the memory profile and synthetic data.
- PostgreSQL is optional for bounded integration checks and must not be required for normal tests.
- The local prompt file is treated as an instruction artifact and is not committed by default.

## Risks

- The project is broad for a first milestone, so implementation favors a compact vertical slice over premature abstraction.
- PostgreSQL verification may require a Docker image pull; that step is optional and should be run only with explicit approval if the image is missing.
- Demo analytics are synthetic and deterministic, not predictive finance claims.

## File Plan

- `backend/`: Python package, domain/application/infrastructure/interfaces layers, tests, Alembic migration.
- `frontend/`: Vue 3 TypeScript app with API/static-demo data modes and tests.
- `data/fixtures/`: fictional companies, synthetic articles, local feed, and expected labels.
- `docs/`: architecture, API, data model, resource, source, threat-model, roadmap, resume alignment, and ADRs.
- `scripts/dev.py`: cross-platform local workflow commands.
- `.github/`: future CI, Pages, templates, and Dependabot configuration.

## Architecture Decisions

- Use a modular monolith with ports and adapters.
- Keep source metadata-first: titles, snippets, URLs, provenance, hashes, and derived signals only.
- Keep memory repositories as the default lightweight profile and PostgreSQL as the production-shaped adapter.
- Keep static demo export separate from the API so GitHub Pages can later host the Vue app without a backend.

## Verification Plan

- Run backend unit and API contract tests in the memory profile.
- Run Ruff check, Ruff format check, and mypy.
- Run frontend lint, type check, Vitest once, and production build.
- Run `finnews demo --profile memory` through `scripts/dev.py verify-lite`.
- Run PostgreSQL checks only through `scripts/dev.py verify-postgres`, which starts and stops the optional container.

## Resource Plan

- Install Python dependencies only inside `.venv`.
- Install JavaScript dependencies only inside `frontend/node_modules`.
- Do not download models, browser binaries, large datasets, or paid-service SDK assets.
- Do not leave dev servers, watchers, or Docker containers running.
- Preserve Docker volumes unless a future explicit destructive cleanup is requested.
