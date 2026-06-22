# Milestone 2A Release Audit

Date: 2026-06-22
Branch: `feat/nlp-evaluation-lab`

Milestone 2A status: synthetic NLP evaluation lab implemented locally.

Key evidence:

- Benchmark records: 1,296.
- Language counts: Chinese 864, English 432.
- Split counts: train 648, validation 324, test 324.
- Challenge records: 432 total, 108 in test.
- Dataset SHA-256: `5eba057ef83198c5a35d29da2c821a5624d813885806cab4f48ecb22dbda67aa`.
- Split SHA-256: train `78c03f095f38b7f40408e63c76924544659a3bbac1c34710f66a67cf5039fb7b`, validation `8dfe819e5dd65118175f400e99bc863c9bb162d5ce0cd717e3db693cdf97791c`, test `2f0b409caa29a341e122d1ff28b4f34b09208d0b6f2f0dff323b5d469657172b`.
- Selected event model: `m2a-event-word_char_tfidf_logreg`.
- Selected sentiment model: `m2a-sentiment-word_char_tfidf_logreg`.
- Selected ML test macro F1: 1.000000 for both tasks on the synthetic benchmark.
- Rule baseline test macro F1: event 0.755556, sentiment recorded in `evaluation.json`.
- Dummy baseline test macro F1: event 0.022222, sentiment recorded in `evaluation.json`.
- Model binaries are ignored under `.finnews-artifacts/`.
- No live-source or external corpus content is used.

Final verification:

- `python scripts/dev.py verify-lite`: passed.
- Backend lightweight tests: 100 passed, 7 PostgreSQL tests skipped, 1
  Starlette TestClient warning.
- Backend coverage: 83.62%, above the 80% gate.
- Ruff check, Ruff format check, and mypy: passed.
- Frontend ESLint, Prettier check, TypeScript check, Vitest, and production
  build: passed.
- Vitest: 3 files, 10 tests passed.
- Memory-profile demo: passed with 46 articles, 12 companies, 7 digests, and
  46 daily company signals.
- `python scripts/dev.py verify-sources`: passed with source config validation,
  37 source tests, and 10 frontend tests.
- `python scripts/dev.py verify-source-reviews`: passed with review validation
  and 17 source-review tests.
- `python scripts/dev.py verify-ml`: passed with benchmark build, benchmark
  validation, 7 NLP tests, model registration, and static NLP export.
- `python scripts/dev.py verify-postgres`: passed with Alembic head
  `0003_nlp_model_registry`, migration downgrade and re-upgrade, and 7
  PostgreSQL integration tests.
- `git diff --check`: passed.

Docker verification:

- PostgreSQL verification used Compose project `finnews_m2a_verify`, service
  `postgres`, image `postgres:16`, and localhost-only port `127.0.0.1:55432`.
- Task-created container, network, and volume were removed by
  `docker compose -p finnews_m2a_verify down --volumes --remove-orphans`.

Repository safety:

- Branch: `feat/nlp-evaluation-lab`.
- Prompt files remain untracked local instruction inputs.
- No model binaries are tracked; artifacts remain under ignored
  `.finnews-artifacts/`.
- No push, pull request, GitHub API call, remote mutation, global Git
  configuration change, paid API, model download, or live/external corpus use
  was performed.

The platform remains research tooling and does not provide investment advice.
