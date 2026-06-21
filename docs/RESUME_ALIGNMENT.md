# Resume Alignment

| Resume capability | Implemented repository evidence | Status |
| --- | --- | --- |
| Modular architecture | `backend/src/finnews/domain`, `application`, `infrastructure`, `interfaces` | implemented |
| FastAPI service | `backend/src/finnews/interfaces/api/app.py` | implemented |
| Typed CLI | `backend/src/finnews/interfaces/cli/app.py` | implemented |
| PostgreSQL schema design | Alembic migration and SQLAlchemy models | partially implemented |
| Offline data pipeline | `NewsPipeline` with synthetic fixtures | implemented |
| Entity/event/sentiment baselines | deterministic NLP modules | implemented |
| Vue 3 dashboard | `frontend/src/pages` | implemented |
| CI and Pages readiness | `.github/workflows` | planned for future remote use |
| Live RSS/official source adapters | documented only | planned |
| ML model evaluation | synthetic label check only | planned |
