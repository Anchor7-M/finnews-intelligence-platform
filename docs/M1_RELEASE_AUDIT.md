# Milestone 1A Release Audit

Date: 2026-06-22
Branch: `feat/live-source-ingestion`

Milestone 1A status: infrastructure complete for safe local testing with
deterministic mocks and disabled example sources. No real source has been
selected, enabled, fetched, or marked as live-production ready.

## Scope

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Branch ancestry | PASS | `origin/main` is an ancestor of `HEAD` | Work started from the updated Milestone 0 mainline. |
| Real source enablement | PASS | `config/sources/*.yaml`, `config/sources.example.yml` | Committed source examples are disabled. Approved user export examples are local-file only. |
| Source registry validation | PASS | `backend/src/finnews/infrastructure/sources/registry.py`, `backend/tests/unit/test_source_registry.py` | Unknown fields and secret-like fields are rejected. |
| API mutation surface | PASS | `backend/src/finnews/interfaces/api/app.py` | Source API routes are read-only `GET` endpoints. No approve, enable, reset, fetch, or arbitrary URL API exists. |
| CLI source selection | PASS | `backend/src/finnews/interfaces/cli/app.py`, `backend/tests/contract/test_source_api_cli.py` | `source fetch --all-approved` returns a no-work result when no approved enabled network sources exist. |
| Dry-run behavior | PASS | `backend/src/finnews/application/services/source_ingestion.py`, `backend/tests/unit/test_source_ingestion.py` | Dry runs do not persist articles, attempts, fetch state, validators, cursor, digest, or signal side effects. |
| HTTP safety | PASS | `backend/src/finnews/infrastructure/http/client.py`, `backend/tests/unit/test_http_safety.py` | HTTPS, host allowlist, redirect revalidation, blocked IP ranges, response size, content type, proxy isolation, and redirect caps are covered. |
| Retry behavior | PASS | `backend/src/finnews/application/services/source_ingestion.py`, `backend/tests/unit/test_source_ingestion.py` | Timeout/connection/transient errors retry within per-source bounds; ordinary 4xx errors do not retry. |
| Retry-After handling | PASS | `backend/src/finnews/application/services/source_ingestion.py`, `backend/tests/unit/test_source_ingestion.py` | Numeric seconds and HTTP-date values are bounded by the source max delay. |
| Sanitized output | PASS | `backend/src/finnews/application/services/source_ingestion.py`, API/CLI tests | Error summaries redact secret-like values, local Windows paths, and PostgreSQL URLs. |
| Static/API frontend modes | PASS | Frontend tests and production build | Source health and existing dashboard paths remain local-demo oriented. |
| PostgreSQL profile | PASS | PostgreSQL verification | Repository state and source fetch persistence are production-shaped and idempotent. |
| Live network fetch | NOT RUN | Policy decision | Milestone 1A uses deterministic mocked transports only. Live source selection and terms evidence are deferred to Milestone 1B. |

## Findings Closed

- Added hostname resolution checks so every resolved IPv4 or IPv6 address is
  evaluated against blocked destination ranges before requests and redirects.
- Documented the remaining DNS rebinding time-of-check/time-of-use limitation.
- Made dry-run source ingestion persistence-free even when prior fetch state is
  already stored in the repository.
- Added deterministic retry jitter injection for tests and bounded HTTP-date
  `Retry-After` handling.
- Ensured `source fetch --all-approved` is a successful no-work command when no
  approved enabled network source exists.
- Rejected unknown source YAML fields and kept committed source examples
  disabled by default.

## Verification Results

Latest local verification on 2026-06-22:

| Command | Status | Result |
| --- | --- | --- |
| `python scripts/dev.py verify-lite` | PASS | Backend `80 passed, 6 skipped`, coverage `85.75%`; Ruff, Ruff format check, mypy, frontend lint, Prettier check, Vue typecheck, Vitest `9 passed`, production build, memory demo, and `git diff --check` passed. |
| `python scripts/dev.py verify-sources` | PASS | Source registry validation passed; source-focused backend/API/CLI tests `35 passed`; Vitest `9 passed`. |
| `python scripts/dev.py verify-postgres` | PASS | PostgreSQL integration tests `6 passed`; Alembic upgrade/downgrade/re-upgrade and idempotency paths passed. |

Docker/PostgreSQL verification used the project-scoped Compose project
`finnews_m1_verify` and cleaned up task-created containers, volumes, and
networks after completion.

## Known Limitations

- No real external source has been approved, enabled, or smoke-tested.
- DNS rebinding cannot be fully eliminated because the HTTP connection is not
  pinned to the pre-validated address.
- The source registry is repository-owned; approval workflow UI and mutation
  APIs are intentionally deferred.
- Scheduler/daemon operation is deferred.
- NLP remains deterministic baseline research tooling and is not investment
  advice.
