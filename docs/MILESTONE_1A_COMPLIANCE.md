# Milestone 1A Compliance

Milestone 1A status: infrastructure implemented with deterministic local mocks.
Live source verification: `NOT RUN - infrastructure verified with deterministic
local mocks; live source selection and terms approval deferred to Milestone 1B.`

## Implemented

- Typed YAML source registry with approval and enabled gates.
- Disabled-by-default RSS, documented JSON API, and user JSON/CSV export examples.
- Bounded HTTP client with HTTPS, allowlist, redirect, private-address,
  content-type, and response-size controls.
- ETag and Last-Modified conditional requests plus `304 Not Modified` handling.
- Bounded retries and per-source minimum interval state.
- RSS/Atom parser, documented JSON mapping, and local JSON/CSV import adapters.
- Source fetch state and attempts in memory and PostgreSQL profiles.
- Read-only source API endpoints, source CLI commands, static-demo export, and
  Vue Source Health page.

## Verification

- Source-focused backend/API/CLI tests: 21 passed.
- Frontend tests: 9 passed.
- `python scripts/dev.py verify-sources` passed locally without external network
  dependency.
- Existing Milestone 0 accounting remains unchanged in memory-profile tests.

## Deferred

- Real source selection and terms approval evidence.
- User-authorized live smoke test.
- Approval workflow UI or mutation API.
- Scheduler/daemon operation.
- Milestone 2 trained machine-learning models.

## Policy

All committed source-health data is synthetic/static-demo data. The platform is
research tooling and does not provide investment advice.
