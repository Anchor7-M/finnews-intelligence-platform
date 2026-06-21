# Resume Alignment

| Resume capability | Implemented repository evidence | Status |
| --- | --- | --- |
| Modular architecture | `backend/src/finnews/domain`, `application`, `infrastructure`, `interfaces` | implemented |
| FastAPI service | `backend/src/finnews/interfaces/api/app.py` | implemented |
| Typed CLI | `backend/src/finnews/interfaces/cli/app.py` | implemented |
| PostgreSQL schema design | Alembic migration and SQLAlchemy models; Docker integration not run in audit | partially implemented |
| Offline data pipeline | `NewsPipeline` with 68 raw synthetic observations and deterministic fixture generator | implemented |
| Entity/event/sentiment baselines | deterministic NLP modules | implemented |
| Vue 3 dashboard | `frontend/src/pages` plus 8 Vitest assertions | implemented |
| CI and Pages readiness | `.github/workflows` | planned for future remote use |
| Live RSS/official source adapters | documented only | planned |
| ML model evaluation | synthetic label check only | planned |
