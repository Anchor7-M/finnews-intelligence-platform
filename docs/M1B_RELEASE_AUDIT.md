# Milestone 1B Release Audit

Date: 2026-06-22
Branch: `feat/approved-live-source-pilot`

Milestone 1B status: local-first source-review workflow and two disabled
official pilot definitions implemented. Reviewed does not mean legally
certified, live-smoke passed does not mean production availability, and no
source is production-ready in this milestone.

## Source Decisions

| Source | Engineering Review | Committed Enabled | Local Override | Live Smoke | Production Ready | Cost | Auth / Prerequisite | Storage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Federal Reserve Board RSS | approved | false | used for one local smoke run | passed | no | free | no auth identified | metadata only |
| SEC EDGAR Submissions API | approved | false | not used | not run | no | free | local contact and test CIK required | metadata only |

## Review And Integrity

- Review records live under `config/source-reviews/*.yaml`.
- Unknown review fields, duplicate review records, invalid reviewers/dates,
  missing evidence URLs, stale source-config digests, host mismatches, and
  endpoint mismatches fail validation.
- Real network source configs remain disabled by default.
- `config/sources.local.yaml` is ignored and may only set `enabled`.
- Review approval is an engineering usage-policy review, not legal advice.

## Federal Reserve Smoke

One bounded Federal Reserve no-persist smoke test was attempted after offline
source/review gates passed.

Safe metadata:

- attempt status: passed
- source ID: `federal-reserve-press-releases`
- host: `www.federalreserve.gov`
- request count: 2
- initial HTTP status: 200
- response bytes: 15042
- parsed count: 5
- persistence mode: `no_persist`
- conditional behavior: `not_modified`
- ETag available: true
- Last-Modified available: true

No raw response, live item title, live item summary, raw ETag, raw
Last-Modified, complete headers, cookies, or linked press-release page content
is committed.

## SEC Smoke

Status: `NOT RUN - SEC contact metadata and/or test CIK was not supplied locally.`

No SEC live request was made. No CIK, contact metadata, raw User-Agent, SEC
response, or SEC filing metadata from a live response is committed.

## API And Frontend

- API remains read-only.
- Added `GET /api/v1/source-reviews` and
  `GET /api/v1/source-reviews/{source_id}`.
- No approve/reject/enable/disable/fetch/smoke/cursor-reset/arbitrary-URL
  mutation endpoint exists.
- Vue Source Catalog displays safe review status, access cost, auth category,
  official links, enabled state, live-smoke state, health, and limitations.
- The browser never fetches Federal Reserve or SEC endpoints.

## Static Demo

Static data includes safe review summaries and synthetic review examples for
approved-disabled, needs-review, rejected, smoke-passed, and missing-prerequisite
states. It does not include real live response text.

## Verification Results

- `python scripts/dev.py verify-lite`: passed.
  - Backend: 93 passed, 6 skipped, coverage 84.12%.
  - Ruff check, Ruff format check, mypy: passed.
  - Frontend ESLint, Prettier check, TypeScript, Vitest: passed.
  - Vue production build: passed.
  - Memory demo and `git diff --check`: passed.
- `python scripts/dev.py verify-sources`: passed.
  - Source config validation: passed.
  - Source-focused backend tests: 37 passed.
  - Frontend Vitest: 9 passed.
- `python scripts/dev.py verify-source-reviews`: passed.
  - Review validation and integrity: passed.
  - Review-focused backend tests: 17 passed.
- `python scripts/dev.py verify-postgres`: passed.
  - PostgreSQL tests: 6 passed.
  - Alembic reached `0002_source_fetch_state`.
  - First-run and repeated-run fixture pipeline idempotency passed.
  - Project-scoped Docker resources were removed afterward.

Known local warning: Starlette currently emits a TestClient deprecation warning
from the installed FastAPI/Starlette dependency stack. The warning does not
change Milestone 1B behavior.

## Known Limitations

- No scheduler or background source worker exists.
- DNS rebinding is mitigated but not fully eliminated because HTTP connections
  are not pinned to pre-validated addresses.
- SEC smoke requires local contact and CIK values and was not run here.
- A-share network integration remains deferred.
- NLP remains deterministic baseline research tooling.
- The platform does not provide investment advice.

## Deferred Work

- Production source operations, scheduling, and monitoring.
- Approval workflow mutation UI or API.
- A-share official source review and integration.
- Milestone 2 trained ML models and evaluation.
