# Data Model

## MT5 Read-Only Metadata

M4A adds metadata-only PostgreSQL tables:

- `mt5_readonly_profiles`
- `mt5_readonly_symbol_mappings`
- `mt5_readonly_runs`
- `mt5_bar_export_manifests`

These tables hold safe profile identifiers, canonical asset mappings, run
statuses, counts, manifest summaries, and JSONB safe metadata. They do not
store raw bar file bytes, local absolute export paths, terminal paths,
credentials, account identifiers, account balances, open orders, positions,
trade history, order requests, stop loss, take profit, or margin-required data.

Historical bars exported from MT5 remain local ignored files unless the user
separately imports them through the existing market-bars contract workflow.

## Paper Execution Metadata

M4B-0 adds metadata-only PostgreSQL tables:

- `paper_risk_policies`
- `paper_risk_decisions`
- `paper_order_intents`
- `paper_manual_reviews`
- `paper_fills`
- `paper_positions`
- `paper_nav`
- `paper_execution_runs`

These tables store paper-only policy metadata, risk decisions, paper intents,
manual-review states, simulated fills, paper positions, NAV, counts, and JSONB
safe metadata. They do not store broker servers, account IDs, login/passwords,
terminal paths, MT5 symbols, tickets, real lot sizes, leverage, margin,
stop-loss, take-profit, order types, `order_check`, or `order_send`.

Implemented Milestone 0 tables in the PostgreSQL schema:

Milestone 3A adds `research_calendars`, `research_sessions`, `research_export_runs`, `research_feature_rows`, and `research_lineage_rows`. These tables store safe metadata, timezone-aware timestamps, JSONB feature values, quality summaries, and lineage IDs. They do not store package bytes, article text, raw source responses, local paths, prices, returns, or recommendations.

- `sources`
- `ingestion_runs`
- `raw_articles`
- `articles`
- `article_duplicates`
- `observation_dispositions`
- `companies`
- `company_aliases`
- `article_company_links`
- `article_events`
- `article_sentiments`
- `daily_digests`
- `daily_company_signals`
- `pipeline_runs`
- `source_definitions`
- `source_fetch_states`
- `source_fetch_attempts`

The domain model is separate from SQLAlchemy models and API schemas. PostgreSQL JSONB is confined to the PostgreSQL adapter and migration. Demo data uses fictional companies and synthetic article metadata only.

Audited fixture composition:

- 68 raw memory-demo observations.
- 60 valid JSONL observations, 4 malformed JSONL validation records, and 4 local RSS observations.
- 12 fictional companies.
- 46 canonical articles after deduplication.
- 8 exact duplicate observations and 10 near-duplicate observations.
- 8 exact duplicate pairs, 10 near-duplicate pairs, and 18 duplicate clusters.
- 7 daily digests and 46 daily company signals.

PostgreSQL stores UUID primary keys as PostgreSQL `uuid`, JSON payloads as
`jsonb`, and timestamp columns as timezone-aware `timestamptz`.

Milestone 1A source tables persist validated YAML source definitions, one
current fetch state per source, and append-only fetch attempts. They store cache
validators, cursors, counters, health, sanitized error summaries, and JSONB
metadata such as retry policy and field mapping. They do not store raw response
bodies or full article bodies.

Milestone 1B source-review evidence is repository-owned YAML, not a new
PostgreSQL table. Runtime/API/static views expose safe summaries only:
source ID, official owner, review decision, reviewed date, access cost,
authentication category, storage policy, official links, enabled status,
live-smoke status, and known limitations. Personal contact values, raw
User-Agent strings, raw responses, complete headers, and local override contents
are not persisted or exposed.

Milestone 2A adds two PostgreSQL metadata tables:

- `nlp_model_registry`
- `nlp_evaluation_runs`

These tables persist safe model/evaluation metadata: logical IDs, task,
provider, model kind, status, dataset hashes, split hashes, label sets, metrics,
calibration summaries, slice summaries, artifact hashes, artifact sizes, config
hashes, and timestamps. They do not store model binaries, sparse matrices,
feature vocabularies, raw live text, absolute paths, secrets, or user input.

Revised Milestone 3A adds cross-asset metadata tables:

- `assets`
- `asset_symbol_aliases`
- `asset_provider_symbols`
- `broker_symbol_mappings`
- `asset_relationships`
- `cross_asset_events`
- `asset_impact_hypotheses`
- `market_signal_candidates`
- `signal_publication_runs`

These tables persist canonical asset identity, aliases, provider symbols,
offline local broker-symbol mappings, deterministic relationships, event
metadata, impact hypotheses, signal candidates, package hashes, JSONB metadata,
arrays of evidence/risk/quality tags, UUID primary keys, and timezone-aware
timestamps. They do not store broker credentials, account identifiers, market
prices, positions, package bytes, execution instructions, or investment advice.

Revised Milestone 3A synthetic fixture counts:

- 40 canonical assets.
- 211 aliases.
- 100 cross-asset events.
- 240 impact hypotheses.
- 80 signal candidates.

Milestone 3C adds market-reaction validation metadata tables:

- `market_data_packages`
- `market_bar_series`
- `market_bars`
- `market_bar_revisions`
- `market_reaction_studies`
- `market_reaction_labels`
- `signal_quality_runs`
- `signal_quality_metrics`
- `signal_error_cases`

These tables persist package hashes, bar-series identity, point-in-time bar
timestamps, append-only bar revisions, event-study windows, reaction labels,
quality metrics, error-analysis cases, JSONB metadata, UUID primary keys, and
timezone-aware timestamps. They do not store raw imported files, local paths,
credentials, account identifiers, broker state, order fields, or full market
data vendor payloads.

Milestone 3C synthetic counts:

- 3 synthetic scenarios.
- 24 assets per scenario.
- 90 sessions per scenario.
- 2,160 bars per scenario and 6,480 total generated bars.
- 645 event-study records and 645 reaction labels.
- 132 signal-quality metric rows.
- 72 deterministic error-analysis cases.
