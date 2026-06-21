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
