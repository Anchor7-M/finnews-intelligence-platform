# Data Model

Implemented Milestone 0 tables in the PostgreSQL schema:

- `sources`
- `ingestion_runs`
- `raw_articles`
- `articles`
- `article_duplicates`
- `companies`
- `company_aliases`
- `article_company_links`
- `article_events`
- `article_sentiments`
- `daily_digests`
- `daily_company_signals`
- `pipeline_runs`

The domain model is separate from SQLAlchemy models and API schemas. PostgreSQL JSONB is confined to the PostgreSQL adapter and migration. Demo data uses fictional companies and synthetic article metadata only.

Audited fixture composition:

- 68 raw memory-demo observations.
- 60 valid JSONL observations, 4 malformed JSONL validation records, and 4 local RSS observations.
- 12 fictional companies.
- 15 exact duplicate observations and 21 near-duplicate observations reported by the memory pipeline.
- 49 stored article records after exact deduplication.
- 7 daily digests and 46 daily company signals.
