# Data Model

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
