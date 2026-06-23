# Milestone 3A Execution Plan

## Current-State Audit

- Repository is on `feat/research-export-contract`, created from `d7aeb9b Complete Milestone 2A release audit`.
- The working tree is clean except untracked local prompt files, which remain local inputs and must not be edited, staged, moved, or committed.
- Milestone 2A is present on `main`, including `docs/M2A_RELEASE_AUDIT.md`, synthetic NLP reports, model registry metadata, API routes, CLI commands, Vue NLP page, and offline verification tooling.
- The rule-based event classifier and sentiment analyzer remain the application defaults; trained synthetic NLP artifacts are evaluation-lab tools only.
- Existing source pilots are disabled by default, reviewed, and not suitable for research export input in this milestone.
- Existing synthetic fixtures provide 12 fictional companies and canonical article/event/sentiment/link records, but they do not define a market-calendar contract or a dense session/window research panel.
- Memory and PostgreSQL repository adapters exist for news, source, NLP, digest, and signal metadata. Research export metadata will be added without changing the domain dependency direction.

## Scope

Milestone 3A implements a local, deterministic, point-in-time research export contract named `finnews-research-export-v1` at semantic contract version `1.0.0`.

Implemented scope:

- Versioned export contract schemas and feature catalog.
- Deterministic synthetic A-share-style 60-session calendar.
- Local CSV/JSON calendar import and validation.
- Point-in-time information-availability and decision-cutoff assignment.
- Dense company/session/window news-factor panel with exactly `60 x 12 x 4 = 2,880` default demo rows.
- Leakage checks, quality report, lineage records, package hashes, and byte-stable serialization.
- Memory and PostgreSQL metadata persistence for calendar, export run, feature rows, and lineage.
- Read-only CLI, API, Vue, and static-demo surfaces.
- Documentation and offline verification.

## Non-Goals

- No price, volume, return, forward-return, benchmark, index, constituent, universe, portfolio, backtest, optimizer, transaction-cost, alpha, or recommendation logic.
- No live market/news data, live calendar lookup, exchange scraping, official A-share calendar claim, paid data, cloud service, scheduler, queue, model download, GPU code, or background daemon.
- No Milestone 2B real-world corpus work and no Milestone 4 LLM work.
- No implementation inside the future `ashare-research-platform` repository.

## Repository Ownership Boundary

FinNews owns article provenance, source/first-seen timestamps, company links, event/sentiment predictions, news aggregation, feature lineage, and the export contract. The future `ashare-research-platform` owns prices, corporate actions, universes, factor evaluation, returns, IC/Rank IC, walk-forward validation, portfolios, and attribution. The handoff must work from files alone; consumers must not import FinNews internals or access the FinNews database.

## Contract Files

Tracked location:

```text
contracts/finnews-research-export/v1/
```

Planned files:

- `README.md`
- `manifest.schema.json`
- `feature-row.schema.json`
- `lineage-row.schema.json`
- `calendar-row.schema.json`
- `company-row.schema.json`
- `feature-catalog.json`
- `examples/synthetic-demo/` with a small deterministic package

Supported package files:

- `manifest.json`
- `calendar.csv`
- `companies.csv`
- `feature_rows.csv`
- `feature_rows.jsonl`
- `lineage.jsonl`
- `quality_report.json`
- `leakage_audit.json`

## Timestamp Model

For each article/company observation:

- `source_published_at`: source-supplied publication timestamp when available.
- `first_seen_at`: timestamp when the platform first observed the record.
- `processed_at`: operational model-processing timestamp.
- `information_available_at`: point-in-time availability timestamp.

Default formula:

```text
information_available_at = max(source_published_at, first_seen_at)
```

If publication time is missing, `first_seen_at` is used and a quality flag is set. If publication time is in the future relative to first seen, availability is not moved earlier than the safely known timestamp and an anomaly flag is retained.

## Calendar And Session Model

The default demo calendar is synthetic, `Asia/Shanghai`, and exactly 60 trading sessions. Weekends and at least four explicit synthetic non-session holidays are excluded. Each session stores date, open, break start, break end, close, sequence, timezone, and optional special-session metadata. Validation rejects duplicate sessions, non-monotonic sequences, invalid timezone, and bad open/break/close ordering.

Local user-supplied calendars are accepted only from explicit local CSV/JSON paths, with UTF-8, size, schema, timezone, ordering, duplicate, and hash validation. Imported calendars are not copied into tracked paths automatically.

## Alignment Policy

Supported cutoff policies:

- `pre_open_15m`: 15 minutes before the session open; default.
- `session_close`: exact session close timestamp.

Exact-cutoff information is included. Information after a cutoff is assigned to the next applicable session/cutoff. Observations before the first session or after the final session are excluded with typed reasons. Rolling windows count sessions, not calendar days.

## Feature Definitions

The feature catalog will include:

- Counts and coverage: `news_count`, `unique_article_count`, `unique_source_count`, `has_news`, `missing_published_time_count`, `abstained_prediction_count`.
- Sentiment labels and shares: positive, neutral, negative, uncertain counts and shares.
- Sentiment scores: mean, confidence-weighted mean, standard deviation, min, max.
- Event features: count and share for every current `EventType`, plus `event_type_count` and zero-safe entropy.
- Novelty/source diversity: `mean_novelty_score`, `max_novelty_score`, `source_diversity_ratio`.
- Recency/decay: `hours_since_latest_news`, `decayed_news_count`, `decayed_sentiment_score`.
- Quality flags: low coverage, missing timestamp, abstention, multi-company article, and backfilled information.

Zero means no counted item for count fields. Null means the statistic is undefined, not zero. No feature expresses bullish/bearish advice.

## Rolling-Window Policy

Default windows are `1, 3, 5, 10` sessions. For a row at session sequence `n` and window `w`, eligible observations are those assigned to sessions with sequence in `[n - w + 1, n]`. The implementation must never use calendar-day arithmetic for rolling windows.

## Lineage Model

Lineage rows include feature-row logical key, canonical article ID, source ID/key, company link/company ID, source publication timestamp, first-seen timestamp, information-available timestamp, event and sentiment provider/version, labels/scores/confidence, optional novelty, inclusion/exclusion reason, assigned session/cutoff, and synthetic-data flag. Lineage must not include article title, summary, body, source response, local path, raw headers, or personal metadata.

## Database Migration Plan

Add a PostgreSQL migration for safe metadata only:

- Research calendars and sessions.
- Research export runs.
- Research feature rows with features stored as JSONB.
- Research lineage rows.

The migration will include UUID primary keys, unique business keys, useful indexes, timezone-aware timestamps, JSONB round trips, idempotent upsert behavior, downgrade support, and no package bytes or article text.

## API, CLI, And Frontend Plan

CLI:

- `finnews research calendar build-demo`
- `finnews research calendar validate --path`
- `finnews research calendar summary --path`
- `finnews research export build`
- `finnews research export validate --path`
- `finnews research export summary --path`
- `finnews research export compare --left --right`
- `finnews research export lineage --path --row-id`
- `finnews research export-static`

API:

- `GET /api/v1/research/overview`
- `GET /api/v1/research/calendars`
- `GET /api/v1/research/exports`
- `GET /api/v1/research/exports/{export_id}`
- `GET /api/v1/research/features`
- `GET /api/v1/research/lineage/{lineage_row_id}`
- `GET /api/v1/research/feature-catalog`

Frontend:

- Add `/research-export` page using Vue 3 Composition API and existing CSS.
- Support static-demo and API modes.
- Display contract, calendar, dense-panel metrics, feature catalog, quality, leakage, safe lineage sample, and handoff boundary.
- Persist notices for synthetic data, no official market-calendar claim, no prices/returns, and not investment advice.

## Test Matrix

- Contract/schema validation, package hashes, CSV/JSONL equivalence, stable column order, null/zero semantics, and no article text.
- Calendar generation/import validation, exact 60 sessions, timezone, holidays/weekends, monotonicity, bad ordering, duplicate rejection, size/encoding failures, and deterministic hash.
- Availability and cutoff assignment edge cases: exact cutoff, microsecond after cutoff, weekends, holidays, missing publication time, future timestamp anomaly, backfill, multi-company links, abstention, ML/rule provenance, and out-of-coverage exclusion.
- Feature formulas with hand-calculated fixtures for every feature group.
- Leakage invariants, future mutation, late backfill, row-order determinism, generated-at exclusion, and session-window boundaries.
- Lineage/accounting invariants and no text/path leakage.
- Memory/PostgreSQL repository parity.
- CLI/API/frontend/static-demo regression coverage.

## Deterministic Output Plan

Research packages write to ignored `.finnews-research-exports/` by default. Writers use temporary directories, stable row sorting, fixed CSV column order, deterministic JSON key ordering, stable float formatting, SHA-256 file hashes, and package-level content hashes. Operational timestamps are excluded from deterministic content unless documented as non-hash metadata. Two clean builds must be byte-identical.

## Resource Budget

- CPU only, single process, no parallel pytest workers.
- No network, no browser automation requirement, no model training, no market-data download.
- Dense demo panel exactly 2,880 rows.
- Full demo package below 10 MB and each package file below 5 MB.
- Static research demo below 1 MB where practical.
- No tracked file over 50 MB.
- Temporary outputs cleaned and local exports ignored.

## CI Plan

Update local workflow files only. CI should run offline contract, calendar, alignment, feature, leakage, CLI/API, source, NLP, frontend, and PostgreSQL checks with synthetic data only. PostgreSQL remains the only service container. Do not claim remote GitHub Actions have run.

## Definition Of Done

- Contract `finnews-research-export-v1` version `1.0.0` is documented and schema-validated.
- Demo calendar has exactly 60 synthetic sessions.
- Default dense panel has exactly 2,880 feature rows over 12 fictional companies and windows `1,3,5,10`.
- Local calendar import validates offline.
- PIT availability, cutoff assignment, feature formulas, leakage, lineage, package hashing, deterministic output, API, CLI, Vue, static demo, memory/PostgreSQL parity, and documentation pass verification.
- No article text, real market data, live source data, prices, returns, or recommendations are exported.
- Local exports remain ignored.
- Docker resources are cleaned after PostgreSQL verification.
- Local commits exist; no push or PR is attempted.

## Deferred Work

Milestone 3B and the future `ashare-research-platform` will handle consumer-side package ingestion, real market-data governance, calendars from approved data vendors or user files, universes, prices, returns, IC/Rank IC, backtests, risk, portfolios, and performance attribution. Those items are documented only here and are not implemented in Milestone 3A.
