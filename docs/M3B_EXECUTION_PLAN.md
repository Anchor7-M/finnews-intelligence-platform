# Milestone 3B Execution Plan

## Starting State

- Branch: `feat/official-cross-asset-sources`
- Base commit: `5bc0a1e Fix self-referential trading-surface audit`
- Working tree at start: clean except untracked local milestone prompt files.
- Existing source framework: strict YAML configs, review records, bounded HTTP client, disabled-by-default network sources, local-only overrides, guarded smoke tests, source health, API/CLI/static/frontend visibility.
- Existing revised M3A: cross-asset registry, event-to-asset hypotheses, `finnews-market-signal-v1`, MT5 readiness boundary, and trading-surface audit.

## Source-Framework Audit

The current framework already provides source definitions, source-review records, source-config digests, stale-review detection, local enable overrides, bounded HTTP GET, and mockable tests. Milestone 3B will reuse those mechanics and extend them narrowly for official numeric/tabular/regulatory sources.

Needed changes:

- allow reviewed `POST` where required by BLS;
- add strict official-data config fields without arbitrary secret/header injection;
- keep local overrides limited to enabling reviewed sources;
- add no-persist smoke gates and source-specific adapters;
- add official-data domain/repository concepts separate from HTTP, FastAPI, Typer, and SQLAlchemy.

## Source-Review Schema

Reuse `config/source-reviews/*.yaml` and `source_config_digest`.

Planned minimal schema updates:

- allow `POST` in `allowed_methods`;
- capture official-data review notes in existing strict fields where possible;
- add fields only if existing fields cannot express authentication, revision, redistribution, and smoke evidence clearly.

Unknown fields and duplicate review records remain rejected. Security-sensitive source-config changes must stale the review digest.

## Official-Source Decisions

Four candidates will be reviewed using official documentation only:

- `bls-public-data`: BLS Public Data API, default no-key v1 path, optional local `FINNEWS_BLS_API_KEY` for v2.
- `eia-open-data-v2`: EIA API v2, local-only `FINNEWS_EIA_API_KEY`, non-price inventory/storage/production/supply-demand pilot.
- `cftc-cot-pre`: CFTC public reporting/COT profile, no token, bounded public query profiles.
- `federal-register-api`: FederalRegister.gov API, no key, metadata and source-provided abstract only.

If official evidence is insufficient, the review decision will be `needs_review` rather than forced approval.

## Domain Model

Milestone 3B will introduce typed domain entities for official datasets, series/query profiles, observations, observation revisions, release runs, regulatory-document metadata, asset associations, and derived official release events.

Authoritative numeric values will use `Decimal` semantics. Regulatory documents will store metadata, source-provided abstract, official/public URLs, CFR/RIN metadata, timestamps, and provenance; no full document body is stored.

## Revision And Vintage Model

Observation business key:

`source + dataset + series/query profile + period + normalized dimensions`

Rules:

- first value creates revision 1;
- identical repeat is idempotent;
- changed value appends a new revision;
- current revision is explicit;
- previous revisions remain stored;
- period date is never treated as information availability;
- `information_available_at = max(source_updated_at, first_seen_at)` when source time is reliable, otherwise `first_seen_at`;
- naive timestamps are rejected;
- future-dated source timestamps are handled by documented anomaly policy.

## API Transport Changes

The bounded HTTP client will gain reviewed `POST` support and redacted request metadata. Tests and CI remain offline and use mocked transports. Live smoke requests require explicit gates and are no-persist.

## Data-To-Asset Mapping

`SeriesAssetAssociation` records map official series/query profiles to canonical asset IDs as relevance hypotheses. Mappings are not directions, predictions, recommendations, or executable signals.

Synthetic fixture target: 80 associations across the existing cross-asset universe without all-to-all mapping.

## Derived Event Policy

Synthetic official observations and documents may produce transparent derived release events. The events preserve source/dataset/series/document references, revision number, provenance, and point-in-time cutoff. No live smoke data creates persisted events or signal candidates.

## Migration Plan

Add one Alembic revision after the current head for:

- official data datasets;
- official data series/query definitions;
- observations and observation revisions;
- release runs;
- regulatory documents;
- series asset associations.

The schema will use UUID primary keys, stable logical keys, timezone-aware timestamps, Numeric/Decimal values, JSONB provenance/quality metadata, useful uniqueness constraints, and point-in-time indexes.

## Live-Smoke Budget

Live smoke tests are manual, one-time, and bounded:

- at most four total requests;
- one request per source;
- 120 seconds total;
- `--no-persist` required;
- BLS v1/no-key default;
- Federal Register max five metadata records;
- CFTC max five rows;
- EIA runs only if `FINNEWS_EIA_API_KEY` exists locally.

No live values, titles, abstracts, rows, headers, raw responses, keys, or local reports are committed.

## Secret Handling

Allowed credential environment variables only:

- `FINNEWS_BLS_API_KEY`
- `FINNEWS_EIA_API_KEY`

No config, review, docs, API, CLI, static data, PostgreSQL row, or log output may contain key values. Arbitrary secret/header injection is not supported.

## Test Matrix

Offline tests will cover:

- source reviews/configs and stale digest behavior;
- BLS, EIA, CFTC, and Federal Register adapters with mocked HTTP;
- revision/as-of logic;
- deterministic fixture counts and hashes;
- asset associations and derived events;
- memory/PostgreSQL repository parity;
- CLI/API safe outputs;
- Vue static/API modes;
- no live network in automated tests;
- MT5/trading-surface regression.

Backend coverage target remains at least 80%.

## Resource Budget

- No paid APIs, cloud databases, schedulers, queues, model downloads, live prices, or MT5 packages.
- PostgreSQL verification may use one disposable `postgres:16` service under project `finnews_m3b_verify`, localhost-only, 512 MB, 0.50 CPU, `restart: "no"`.
- Fixture size remains below 5 MB.

## CI And Offline Plan

CI remains offline and requires no API keys. It validates reviews/configs, mock adapters, deterministic fixtures, backend/frontend checks, and PostgreSQL integration. GitHub workflows are modified locally only; no GitHub API, push, or PR is used in this task.

## Definition Of Done

Milestone 3B is done when:

- four official source reviews and four disabled configs exist;
- deterministic official-data fixture counts pass exactly;
- adapters work through offline mocks;
- revision/as-of history is append-only;
- read-only API/CLI/frontend/static demo expose safe synthetic official data;
- PostgreSQL parity passes;
- all verification wrappers pass;
- no live data, API key, smoke report, prompt file, MT5 import, trading endpoint, or order field is tracked.

## Deferred Work

Deferred to M3C/M4 or later:

- market-reaction labels;
- event studies and walk-forward validation;
- consensus forecast/surprise modeling;
- live price ingestion;
- read-only MT5 terminal work;
- demo execution, risk controls, reconciliation, and any trading research.
