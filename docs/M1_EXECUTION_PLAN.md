# Milestone 1A Execution Plan

Milestone 1A adds production-shaped, zero-cost live-source ingestion
infrastructure while keeping every automated test deterministic and offline.
No real source is enabled by default, no live endpoint is contacted by default,
and Milestone 2 machine-learning work remains deferred.

## Current-State Audit

- Repository branch for this work: `feat/live-source-ingestion`, created from
  updated `origin/main` at `95ee19a Verify PostgreSQL integration`.
- Milestone 0 includes memory and PostgreSQL profiles, synthetic JSONL and local
  RSS/Atom fixtures, read-only FastAPI endpoints, Typer CLI, Vue static/API
  dashboard, Alembic migration `0001_initial_schema`, and PostgreSQL verification
  tooling.
- Existing source support is local only: `JsonlFixtureSource` and
  `LocalFeedSource`.
- Existing persistence contract is a single `NewsRepository` protocol with
  memory and PostgreSQL implementations.
- Existing API source metadata is embedded in article/static payloads; there are
  no source-health endpoints.
- Existing docs still describe Milestone 1 as planned only and must be updated
  after implementation.
- Local prompt files remain untracked and are not part of the project.

## Requirements-To-Files Matrix

| requirement | primary files |
| --- | --- |
| source registry and approval gates | `config/sources/*.example.yaml`, `backend/src/finnews/domain/entities/__init__.py`, `backend/src/finnews/domain/enums.py`, `backend/src/finnews/infrastructure/sources/registry.py`, tests |
| bounded HTTP client | `backend/src/finnews/application/ports/http.py`, `backend/src/finnews/infrastructure/http/client.py`, tests |
| RSS/Atom network adapter | `backend/src/finnews/infrastructure/sources/feed.py`, tests |
| documented JSON adapter | `backend/src/finnews/infrastructure/sources/announcements.py`, tests |
| local JSON/CSV import | `backend/src/finnews/infrastructure/sources/announcements.py`, CLI tests |
| source fetch state and attempts | domain entities, `repositories.py`, memory repo, PostgreSQL models/repository, new Alembic migration |
| pipeline integration | `backend/src/finnews/application/services/source_ingestion.py`, `pipeline.py`, CLI |
| source CLI | `backend/src/finnews/interfaces/cli/app.py` |
| source API | `backend/src/finnews/interfaces/api/app.py`, `schemas.py` |
| static demo export | `backend/src/finnews/application/services/export_static.py`, `frontend/public/demo-data/*.json` |
| Vue source-health page | `frontend/src/types/models.ts`, `frontend/src/api/client.ts`, `frontend/src/router/index.ts`, `frontend/src/App.vue`, `frontend/src/pages/SourceHealth.vue`, tests |
| verification scripts | `scripts/dev.py`, `.github/workflows/*.yml` |
| documentation | README, roadmap, source/security/data/development docs, new M1A docs |

## Architecture Decisions

- Preserve dependency direction: domain dataclasses and enums stay framework-free;
  application defines ports and orchestration; infrastructure implements YAML,
  HTTP, parser, memory, and PostgreSQL adapters; interfaces expose API and CLI.
- Do not accept arbitrary source URLs from API or CLI. Fetch URLs come only from
  validated repository-owned source definitions.
- Keep source fetching as a bounded run-once operation. No scheduler, daemon,
  Celery, Redis, Kafka, browser automation, or background worker is introduced.
- Use `httpx` for mocked and bounded HTTP fetches because it is already a
  project dependency.
- Use Python standard CSV/JSON parsing for user exports. XML parsing will reject
  DTD/entity constructs before parsing and will not download linked pages.
- Store metadata, summaries/snippets, provenance, hashes, validators, and derived
  fields only. Do not store raw response bodies or copied full article bodies.

## Domain/Application Changes

- Add source concepts: `SourceDefinition`, `SourceApproval`,
  `SourceFetchState`, `SourceFetchAttempt`, `SourceHealth`, `FetchOutcome`,
  `RetryDecision`, and `CursorCheckpoint`.
- Extend repository ports with source-definition, fetch-state, and fetch-attempt
  methods while keeping existing Milestone 0 methods stable.
- Add a source-ingestion service that validates approval, checks rate limits,
  fetches/imports bounded responses, parses records, hands records to the
  existing normalization/deduplication pipeline, and commits state only after
  successful parse/persistence.

## Infrastructure Changes

- Add YAML source registry validation with explicit approval status, host
  allowlist, storage policy, response-size limit, retry policy, rate limit,
  field mapping, and user-agent validation.
- Add bounded HTTP client with HTTPS enforcement, redirect revalidation,
  approved-host checks, private/loopback destination blocking in live mode,
  max decompressed response size, safe content-type checks, deterministic retry
  hooks for tests, and no cookie/proxy/browser behavior.
- Add adapters for network RSS/Atom, documented JSON announcement APIs, and
  local JSON/CSV official announcement exports.
- Add memory and PostgreSQL persistence for source definitions, fetch states,
  and fetch attempts.

## Interface Changes

- CLI source group:
  `source list`, `source validate-config`, `source fetch --source --dry-run`,
  `source fetch --source`, `source fetch --all-approved`, `source health`, and
  `source import-announcements --source --path`.
- API read endpoints:
  `/api/v1/sources`, `/api/v1/sources/{source_id}`,
  `/api/v1/sources/{source_id}/health`, and `/api/v1/source-fetch-attempts`.
- Vue adds a Source Health page with static-demo and API modes and no browser
  requests to real external feeds.

## Migration Plan

- Add a new Alembic migration after `0001_initial_schema`; do not edit the
  merged initial migration.
- Expected tables: `source_fetch_states` and `source_fetch_attempts`. Source
  definitions may be stored in the existing `sources` table where fields fit and
  supplemented through fetch-state/attempt metadata when needed.
- Verify upgrade, downgrade, and re-upgrade against disposable PostgreSQL.

## Source-State Model

- `SourceFetchState` is keyed by source ID/key and stores ETag, Last-Modified,
  cursor/checkpoint, last attempted/successful timestamps, next allowed time,
  last status, last response hash/bytes/item count, consecutive failures, last
  error category/summary, health, and adapter version.
- `SourceFetchAttempt` stores one bounded run outcome with timings, status,
  counts, byte size, retry count, outcome, error category, sanitized summary,
  and validator booleans.
- Cursor and validators update only after valid parse and persistence. `304 Not
  Modified` is a successful no-change attempt.

## Security Model

- No default-enabled real sources.
- Unreviewed, rejected, suspended, or disabled sources cannot be fetched.
- No secrets in YAML, logs, API responses, or CLI output.
- No arbitrary public fetch endpoint.
- Live mode blocks loopback, private, link-local, multicast, and unspecified
  destinations. Local HTTP is allowed only through explicit test wiring.
- Response bodies are never persisted or exposed through logs/API.

## Retry And Rate-Limit Policy

- Retry only timeouts, connection errors, 408, 429, and selected transient 5xx.
- No retry for normal 4xx, parse failures, policy violations, oversized
  responses, invalid content type, or malformed JSON/XML.
- Maximum two retries after the initial request.
- Exponential backoff with deterministic jitter injection in tests.
- Honor valid `Retry-After`; cap waits at 30 seconds; unit tests do not sleep.
- Per-source minimum interval is enforced through `next_allowed_at`.

## Test Matrix

- Source config: valid/invalid YAML, approval gate, host allowlist, duplicate
  IDs, limits, secret-like fields, enabled false default.
- HTTP safety: HTTPS, blocked private/loopback live destinations, redirect
  revalidation, oversized response, content type, timeout, connection error,
  no raw body exposure.
- Conditional requests: first fetch stores validators, second sends conditional
  headers, `304` no-change, parse failure keeps prior validators.
- Retry: retryable statuses/errors, `Retry-After`, cap, no real sleep, recovery,
  permanent failure health.
- Parsers/imports: RSS, Atom, malformed item isolation, unsafe XML rejection,
  JSON mapping/cursor, CSV import, malformed row and encoding failure.
- Pipeline: source records enter existing normalization/dedup/link/classify path,
  idempotency, source failure isolation, M0 accounting regression.
- Repository parity: shared memory/PostgreSQL contracts for fetch state/attempts.
- API/CLI/frontend: source endpoints, filters, pagination, safe output, static
  and API modes.

## Resource Budget

- Default max response size: 2 MB; hard configurable ceiling: 5 MB.
- Default source concurrency: 1 in CLI, maximum 2 globally.
- No article page, image, media, model, or large dataset downloads.
- PostgreSQL verification uses only Compose project `finnews_m1_verify`, service
  `postgres`, official `postgres:16`, localhost binding, 512 MB, 0.50 CPU, and
  project-scoped disposable resources.

## Completion Criteria

- All source configs are typed, approval-gated, and disabled by default.
- RSS/Atom, documented JSON, and local JSON/CSV import paths are implemented
  through deterministic tests and local mocks.
- ETag, Last-Modified, `304`, retries, rate limits, cursors, health, and attempts
  are persisted in memory and PostgreSQL.
- Existing Milestone 0 accounting remains unchanged.
- New API, CLI, Vue page, static demo export, docs, and CI config are complete.
- `verify-lite`, `verify-sources`, `verify-postgres`, and `git diff --check`
  pass, with Docker cleanup confirmed.

## Deferred Work

- Milestone 1B: selection, terms review, explicit approval evidence, and optional
  user-authorized live smoke test for real sources.
- Milestone 2: trained ML classifiers, calibration, model registry, and model
  evaluation beyond deterministic baselines.
- Auth, paid providers, browser automation, schedulers, queues, search systems,
  full-text article storage, and deployment automation remain out of scope.
