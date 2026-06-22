# Milestone 1B Execution Plan

Milestone 1B adds engineering source-review evidence, two disabled official
pilot definitions, guarded local smoke testing, API/frontend visibility, and
offline verification. It does not add production readiness, scheduling, paid
services, full-text storage, trained ML, or A-share live network integration.

## Current-State Audit

- Branch for this work: `feat/approved-live-source-pilot`, created from
  `main` at `bf8a3bf Complete Milestone 1A release audit`.
- Main contains Milestone 1A source registry, bounded HTTP client, RSS/Atom and
  documented JSON adapters, source state, source attempts, read-only API, CLI,
  Vue Source Health, static demo data, and release audit.
- Working tree at branch creation was clean except untracked local prompt files:
  `finnews_milestone_1a_codex_prompt.md` and
  `finnews_milestone_1b_codex_prompt.md`.
- Existing source approval is a field on source config. It is not yet backed by
  independent repository-owned review evidence.
- Existing documented JSON parsing handles array-of-records only. It does not
  yet handle SEC EDGAR Submissions parallel arrays.
- Existing source fetch dry-run/no-persist behavior is tested for M1A ordinary
  fetch/import paths, but no live-smoke command exists.
- Existing API source routes are read-only and no mutation/fetch/approval API
  exists.
- Existing Vue source page shows source health but not review evidence.
- Existing CI and dev scripts are offline for default/source tests.

## Scope And Non-Goals

In scope:

- Typed source-review evidence loaded from `config/source-reviews/*.yaml`.
- Config/review integrity validation with stale-review detection.
- Disabled official pilot configs for Federal Reserve RSS and SEC EDGAR
  Submissions JSON.
- SEC columnar JSON parsing using generic documented JSON mapping extensions.
- Guarded CLI smoke-test command with no-persist default and safe output.
- One user-authorized Federal Reserve no-persist smoke test after offline gates
  pass.
- Optional SEC smoke test only when local contact and test CIK prerequisites
  exist.
- Read-only API review metadata and Vue Source Catalog/Health visibility.
- Static-demo export with synthetic review examples only.
- Documentation, tests, CI updates, and local verification.

Out of scope:

- Milestone 2 ML/model work.
- Permanent schedulers, daemons, queues, Redis, Kafka, search services, pgAdmin,
  or browser automation.
- Paid APIs, cloud databases, cloud schedulers, model downloads, or telemetry.
- Publisher article-page scraping or linked filing-document downloads.
- Raw live response commits, real item text commits, or personal contact
  metadata in tracked files.
- A-share live source fetching or undocumented endpoint discovery.

## Requirements-To-Files Matrix

| Requirement | Primary Files |
| --- | --- |
| Review evidence schema and validation | `backend/src/finnews/infrastructure/sources/reviews.py`, `config/source-reviews/*.yaml`, tests |
| Config/review integrity and stale detection | `backend/src/finnews/infrastructure/sources/registry.py`, new review module, tests |
| Local override support | new source override module or registry extension, `.gitignore`, `config/sources.local.example.yaml`, tests |
| Official pilot configs | `config/sources/federal-reserve-press-releases.yaml`, `config/sources/sec-edgar-submissions.yaml` |
| Candidate review docs | `docs/source-reviews/*.md` |
| SEC columnar JSON mapping | `backend/src/finnews/infrastructure/sources/announcements.py`, fixtures, tests |
| Smoke command/gates | `backend/src/finnews/application/services/source_smoke.py`, `backend/src/finnews/interfaces/cli/app.py`, tests |
| API review exposure | `backend/src/finnews/interfaces/api/app.py`, static export, tests |
| Vue catalog/review UI | `frontend/src/types/models.ts`, `frontend/src/api/client.ts`, `frontend/src/pages/SourceHealth.vue`, tests |
| Static demo review data | `backend/src/finnews/application/services/export_static.py`, `frontend/public/demo-data/*.json` |
| Dev tooling | `scripts/dev.py` |
| CI offline guards | `.github/workflows/*.yml` |
| Docs | README, AGENTS, CHANGELOG, roadmap, source/security/data/development/threat docs, release audit |

## Source-Review Workflow Design

- Review records are repository-owned YAML files under
  `config/source-reviews/`.
- They are loaded and validated independently from source definitions.
- CLI commands:
  - `finnews source review list`
  - `finnews source review validate`
  - `finnews source review show --source <source_id>`
- Review files contain paraphrased engineering usage-policy evidence and links,
  not copied terms pages.
- A network source is considered review-approved only when a matching approved
  review exists and config/review integrity passes.
- Approval remains separate from runtime enablement. Tracked real network
  source configs remain `enabled: false`.

## Source-Review Evidence Schema

Each review record will include:

- identity and decision: `source_id`, `review_schema_version`,
  `review_decision`, `review_scope`, `reviewed_at`, `reviewer`;
- ownership and evidence: `official_owner`, `official_source`,
  `documentation_url`, `terms_or_policy_url`, `evidence_urls`,
  `evidence_checked_at`;
- usage policy: `access_cost`, `authentication_requirement`,
  `allowed_methods`, `allowed_hostnames`, `documented_endpoint_patterns`,
  `rate_limit_evidence`, `user_agent_requirement`, `redistribution_assessment`,
  `attribution_requirement`, `robots_or_automated_access_notes`,
  `privacy_notes`, `known_risks`;
- storage policy: `content_available`, `content_to_store`,
  `content_not_to_store`;
- live verification: `live_smoke_status`, `live_smoke_checked_at`;
- `review_notes`;
- normalized source-definition SHA-256 linkage for stale-review detection.

Unknown review fields, duplicate reviews, invalid reviewers, missing evidence
URLs, and stale review/config links fail validation.

## Source Config And Review Integrity Model

- Security-sensitive source fields are normalized and hashed:
  source ID, type, base URL or endpoint template, approved hostnames,
  documentation URL, terms URL, storage policy, response-size limit, retry
  policy, minimum interval, field mapping, and risk classification.
- Review records store the expected digest. A mismatch marks the review stale.
- Allowed hosts in review must cover every runtime host.
- Documented endpoint patterns must match the configured base URL or template.
- Runtime ordinary fetch and smoke-test gates use review integrity validation
  before allowing an approved network source to run.
- Local overrides may enable a reviewed source but may not alter hostnames,
  endpoints, TLS policy, response size, retries, timeouts, field mapping, or
  inject headers/secrets.

## Official Pilot Decision Criteria

- Use only official domains authorized for this task.
- Record exact evidence URLs and checked date.
- Paraphrase cost, authentication, User-Agent, rate-limit, storage, and
  redistribution notes.
- Do not force approval if evidence conflicts with expected outcomes.
- Correct decision labels are engineering review decisions, not legal advice.

## Federal Reserve Adapter And Config Plan

- Use the existing RSS parser and bounded HTTP client.
- Add disabled config `federal-reserve-press-releases` pointing to
  `https://www.federalreserve.gov/feeds/press_all.xml`.
- Allow only Federal Reserve hostnames required by the feed.
- Store title, official URL, source-provided ID, timestamp, feed summary,
  category/provenance metadata, hashes, and derived features.
- Do not request linked press-release pages.
- Smoke test maximum five parsed items, no-persist, one GET by default, and one
  optional conditional follow-up.

## SEC Columnar JSON Mapping Plan

- Extend documented JSON parsing generically to support:
  array-of-records mode and columnar/parallel-array mode.
- Add mapping fields for `items`, `record_mode`, `columns_path`, required and
  optional column names, maximum records, derived ID/title/URL templates, and
  entity metadata paths.
- Normalize CIK to exactly ten digits.
- Use accession number as source item ID.
- Derive filing URL from documented SEC fields and templates only.
- Retain filing metadata such as form type and dates; discard unused live
  fields and never fetch primary documents, exhibits, HTML pages, or archives.
- Unequal required arrays fail safely as parse/validation errors.

## Local Override And Personal-Contact Handling

- Tracked configs remain disabled.
- Ignored local override path: `config/sources.local.yaml`.
- Tracked example: `config/sources.local.example.yaml`.
- Overrides can only set `enabled: true|false` for an already approved source.
- SEC smoke requires `FINNEWS_SEC_CONTACT` and `FINNEWS_SEC_TEST_CIK` locally.
- Contact metadata is used only to build the SEC-declared User-Agent and is
  never printed, logged, persisted, documented, or committed.

## Smoke-Test Gate Design

`finnews source smoke-test --source <source_id>` will default to memory profile,
no-persist, maximum five items, and no conditional follow-up.

Required gates:

- source config exists;
- review exists, is approved, and integrity passes;
- source is enabled through ignored local override;
- `FINNEWS_ALLOW_LIVE_NETWORK=1`;
- `--confirm-live`;
- host and endpoint match reviewed evidence;
- source-specific prerequisites pass;
- request budget is within limits.

Safe output contains metadata/counts only: source ID, review decision, host,
HTTP status, duration, bytes, parsed count, accepted/rejected/duplicate counts,
validator availability booleans, conditional outcome, persistence mode,
sanitized error category, and optional ignored report path.

## No-Persist Guarantees

No-persist smoke mode must not mutate source definitions, review records, fetch
state, attempts, validators, cursors, raw observations, articles, links, events,
sentiments, digests, signals, ingestion runs, or pipeline runs. Tests will take
repository snapshots before and after mocked smoke runs.

## Test Matrix

- Review schema: valid decisions, missing evidence/terms, unknown fields,
  duplicate reviews, ID mismatch, host mismatch, endpoint mismatch, stale digest,
  invalid reviewer/date, approval without documentation.
- Overrides: ignored path, enabling approved sources, blocking unapproved or
  unknown sources, preventing security-policy weakening or secret injection.
- Federal Reserve: official config validation, RSS metadata parsing,
  item bound, no linked-page request, conditional metadata, no-persist snapshot,
  safe output, review gating.
- SEC: CIK normalization, missing contact, contact redaction, columnar arrays,
  unequal arrays, optional fields, accession identity, URL derivation, max five
  filings, deterministic parse, no document fetch.
- Smoke gates: missing live env, missing confirmation, missing/stale review,
  disabled source, host mismatch, missing prerequisites, request budget,
  success, no-change, parse failure, timeout, safe exit codes, ignored report.
- API: review list/detail, filters, pagination, not found, request ID, safe
  fields only, no mutation routes.
- Frontend: review metrics, filters, loading/empty/error, API/static modes,
  official links, no contact/raw validators, disabled-by-default labels,
  status distinctions, synthetic/disclaimer notices.
- Regression: M0 accounting, M1A source behavior, memory/PostgreSQL parity,
  backend coverage at least 80%.

## Docker And Resource Budget

- Default/source/review/frontend tests remain offline.
- PostgreSQL final verification uses only `postgres:16`, Compose project
  `finnews_m1b_verify`, localhost port `55432` or a free `55433-55450`,
  512 MB memory, 0.50 CPU, restart `no`, and disposable project-owned
  volume/network.
- Always run `docker compose -p finnews_m1b_verify down --volumes --remove-orphans`.
- Do not modify unrelated Docker resources.

## Live-Network Request Budget

- Review/documentation access only to official authorized Federal Reserve and
  SEC domains.
- Federal Reserve smoke: at most two GET requests total, one source, one at a
  time, maximum five parsed items, maximum 2 MB, maximum 60 seconds, no article
  pages, no-persist.
- SEC smoke: at most one GET and five filings only when local contact and CIK
  prerequisites exist; otherwise report NOT RUN.
- Automated tests and CI never access Federal Reserve or SEC.

## Documentation Plan

Update README, AGENTS, CHANGELOG, roadmap, source policy/config/health,
live-source security, architecture, data model, development, cost/resource
guardrails, threat model, source review docs, A-share boundary, execution plan,
and release audit.

## Exact Definition Of Done

- Typed review evidence and integrity validation are implemented.
- Federal Reserve and SEC review decisions are evidence-backed.
- Both official configs are committed disabled.
- Local overrides cannot weaken security.
- SEC columnar JSON parsing works with synthetic fixtures.
- Smoke command has hard live gates and no-persist tests.
- One bounded Federal Reserve smoke test is attempted after offline gates.
- SEC smoke is run only if prerequisites exist.
- API remains read-only and frontend shows safe review/live status.
- Static demo remains synthetic.
- CI remains offline.
- `verify-lite`, `verify-sources`, `verify-source-reviews`, and
  `verify-postgres` pass.
- No raw live response, real item text, personal contact, paid service, push,
  or PR is introduced.

## Deferred A-Share Source Work

Milestone 1B will document why SSE, SZSE, CNINFO, CSRC, PBOC, and similar
A-share network sources are not scraped. User JSON/CSV import remains the safe
current A-share path until a future task verifies official documented APIs or
feeds and acceptable automated-use evidence.

## Deferred Scheduler Work

All source fetches remain explicit CLI runs. Scheduler, daemon, queue, and
background watcher work is deferred.

## Deferred Milestone 2 Work

No trained classifier, calibration, model registry, LLM extraction, or paid
model provider work is implemented in Milestone 1B.
