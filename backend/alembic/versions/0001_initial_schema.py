from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_key", sa.String(120), nullable=False, unique=True),
        sa.Column("display_name", sa.String(240), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("terms_url", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("language_hints", postgresql.JSONB(), nullable=False),
        sa.Column("ingestion_policy", sa.String(64), nullable=False),
        sa.Column("rate_limit", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False
        ),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("cursor_before", sa.Text()),
        sa.Column("cursor_after", sa.Text()),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("exact_duplicate_count", sa.Integer(), nullable=False),
        sa.Column("near_duplicate_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column("code_version", sa.String(80), nullable=False),
        sa.Column("configuration_version", sa.String(80), nullable=False),
    )
    op.create_table(
        "raw_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False
        ),
        sa.Column("source_article_id", sa.String(240), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("source_summary", sa.Text(), nullable=False),
        sa.Column("source_language", sa.String(16), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_content_hash", sa.String(64), nullable=False),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_runs.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("source_id", "source_article_id"),
    )
    op.create_index("ix_raw_source", "raw_articles", ["source_id"])
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "canonical_raw_article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_articles.id"),
            nullable=False,
        ),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("normalized_summary", sa.Text(), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_market_date", sa.Date(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("exact_content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("processing_state", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_state", "articles", ["processing_state"])
    op.create_table(
        "article_duplicates",
        sa.Column(
            "candidate_article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id"),
            primary_key=True,
        ),
        sa.Column(
            "canonical_article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id"),
            primary_key=True,
        ),
        sa.Column("duplicate_type", sa.String(40), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("algorithm_name", sa.String(120), nullable=False),
        sa.Column("algorithm_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "observation_dispositions",
        sa.Column("observation_id", sa.String(240), primary_key=True),
        sa.Column("source_key", sa.String(120), nullable=False),
        sa.Column("disposition", sa.String(40), nullable=False),
        sa.Column("canonical_observation_id", sa.String(240)),
        sa.Column(
            "canonical_article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id"),
        ),
        sa.Column("duplicate_type", sa.String(40)),
        sa.Column("similarity_score", sa.Float()),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("fixture_group", sa.String(80), nullable=False),
    )
    op.create_index(
        "ix_observation_dispositions_canonical",
        "observation_dispositions",
        ["canonical_article_id"],
    )
    op.create_index(
        "ix_observation_dispositions_disposition",
        "observation_dispositions",
        ["disposition"],
    )
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("legal_name", sa.String(240), nullable=False),
        sa.Column("short_name", sa.String(160), nullable=False),
        sa.Column("sector", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("ticker", "exchange"),
    )
    op.create_index("ix_companies_ticker", "companies", ["ticker"])
    op.create_table(
        "company_aliases",
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id"),
            primary_key=True,
        ),
        sa.Column("alias", sa.String(240), primary_key=True),
        sa.Column("normalized_alias", sa.String(240), nullable=False),
        sa.Column("alias_type", sa.String(80), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.UniqueConstraint("company_id", "normalized_alias"),
    )
    op.create_table(
        "article_company_links",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id"),
            primary_key=True,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("matched_alias", sa.String(240), nullable=False),
        sa.Column("evidence_text_span", sa.Text(), nullable=False),
        sa.Column("linker_name", sa.String(120), nullable=False),
        sa.Column("linker_version", sa.String(40), nullable=False),
    )
    op.create_index("ix_article_company_links_company", "article_company_links", ["company_id"])
    op.create_table(
        "article_events",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id"),
            primary_key=True,
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("classifier_name", sa.String(120), nullable=False),
        sa.Column("classifier_version", sa.String(40), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_article_events_type", "article_events", ["event_type"])
    op.create_table(
        "article_sentiments",
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id"),
            primary_key=True,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("label", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("analyzer_name", sa.String(120), nullable=False),
        sa.Column("analyzer_version", sa.String(40), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_article_sentiments_label", "article_sentiments", ["label"])
    op.create_table(
        "daily_digests",
        sa.Column("digest_date", sa.Date(), primary_key=True),
        sa.Column("timezone", sa.String(80), primary_key=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("company_count", sa.Integer(), nullable=False),
        sa.Column("event_counts", postgresql.JSONB(), nullable=False),
        sa.Column("sentiment_counts", postgresql.JSONB(), nullable=False),
        sa.Column("digest_payload", postgresql.JSONB(), nullable=False),
        sa.Column("generator_name", sa.String(120), nullable=False),
        sa.Column("generator_version", sa.String(40), nullable=False),
    )
    op.create_table(
        "daily_company_signals",
        sa.Column("signal_date", sa.Date(), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id"),
            primary_key=True,
        ),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("unique_source_count", sa.Integer(), nullable=False),
        sa.Column("weighted_sentiment_score", sa.Float(), nullable=False),
        sa.Column("negative_event_count", sa.Integer(), nullable=False),
        sa.Column("event_distribution", postgresql.JSONB(), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=False),
        sa.Column("source_diversity_score", sa.Float(), nullable=False),
        sa.Column("signal_schema_version", sa.String(40), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_company_signals_date", "daily_company_signals", ["signal_date"])
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("per_step_timings", postgresql.JSONB(), nullable=False),
        sa.Column("per_step_counts", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("errors", postgresql.JSONB(), nullable=False),
        sa.Column("configuration_version", sa.String(80), nullable=False),
        sa.Column("code_version", sa.String(80), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "pipeline_runs",
        "daily_company_signals",
        "daily_digests",
        "article_sentiments",
        "article_events",
        "article_company_links",
        "company_aliases",
        "companies",
        "observation_dispositions",
        "article_duplicates",
        "articles",
        "raw_articles",
        "ingestion_runs",
        "sources",
    ]:
        op.drop_table(table)
