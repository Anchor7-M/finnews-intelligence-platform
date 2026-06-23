"""research export metadata

Revision ID: 0004_research_export_metadata
Revises: 0003_nlp_model_registry
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_research_export_metadata"
down_revision: str | None = "0003_nlp_model_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_calendars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("calendar_id", sa.String(length=160), nullable=False),
        sa.Column("calendar_version", sa.String(length=80), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("calendar_hash", sa.String(length=64), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("calendar_id", "calendar_version"),
    )
    op.create_index(
        "ix_research_calendars_calendar",
        "research_calendars",
        ["calendar_id", "calendar_version"],
    )
    op.create_table(
        "research_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("calendar_id", sa.String(length=160), nullable=False),
        sa.Column("calendar_version", sa.String(length=80), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("open_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("break_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("break_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("special_session", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("calendar_id", "calendar_version", "session_date"),
        sa.UniqueConstraint("calendar_id", "calendar_version", "sequence"),
    )
    op.create_index(
        "ix_research_sessions_calendar_sequence",
        "research_sessions",
        ["calendar_id", "calendar_version", "sequence"],
    )
    op.create_table(
        "research_export_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("export_id", sa.String(length=180), nullable=False),
        sa.Column("contract_version", sa.String(length=40), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("calendar_id", sa.String(length=160), nullable=False),
        sa.Column("calendar_version", sa.String(length=80), nullable=False),
        sa.Column("calendar_hash", sa.String(length=64), nullable=False),
        sa.Column("cutoff_policy", sa.String(length=80), nullable=False),
        sa.Column("windows", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("company_universe_hash", sa.String(length=64), nullable=False),
        sa.Column("package_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("leakage_status", sa.String(length=40), nullable=False),
        sa.Column("leakage_hash", sa.String(length=64), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "export_id",
            "contract_version",
            "config_hash",
            "calendar_hash",
            "package_hash",
        ),
    )
    op.create_index("ix_research_export_runs_export", "research_export_runs", ["export_id"])
    op.create_table(
        "research_feature_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("export_id", sa.String(length=180), nullable=False),
        sa.Column("logical_key", sa.Text(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("decision_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("window_sessions", sa.Integer(), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=80), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lineage_row_id", sa.String(length=80), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("export_id", "logical_key"),
    )
    op.create_index(
        "ix_research_feature_rows_lookup",
        "research_feature_rows",
        ["export_id", "ticker", "session_date"],
    )
    op.create_index(
        "ix_research_feature_rows_window",
        "research_feature_rows",
        ["window_sessions"],
    )
    op.create_table(
        "research_lineage_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("export_id", sa.String(length=180), nullable=False),
        sa.Column("lineage_row_id", sa.String(length=80), nullable=False),
        sa.Column("feature_row_key", sa.Text(), nullable=False),
        sa.Column("canonical_article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", sa.String(length=160), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("information_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_cutoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inclusion_reason", sa.String(length=80), nullable=False),
        sa.Column("event_provider", sa.String(length=120), nullable=True),
        sa.Column("event_model_version", sa.String(length=80), nullable=True),
        sa.Column("sentiment_provider", sa.String(length=120), nullable=True),
        sa.Column("sentiment_model_version", sa.String(length=80), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("export_id", "lineage_row_id"),
    )
    op.create_index("ix_research_lineage_export", "research_lineage_rows", ["export_id"])
    op.create_index(
        "ix_research_lineage_article",
        "research_lineage_rows",
        ["canonical_article_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_lineage_article", table_name="research_lineage_rows")
    op.drop_index("ix_research_lineage_export", table_name="research_lineage_rows")
    op.drop_table("research_lineage_rows")
    op.drop_index("ix_research_feature_rows_window", table_name="research_feature_rows")
    op.drop_index("ix_research_feature_rows_lookup", table_name="research_feature_rows")
    op.drop_table("research_feature_rows")
    op.drop_index("ix_research_export_runs_export", table_name="research_export_runs")
    op.drop_table("research_export_runs")
    op.drop_index("ix_research_sessions_calendar_sequence", table_name="research_sessions")
    op.drop_table("research_sessions")
    op.drop_index("ix_research_calendars_calendar", table_name="research_calendars")
    op.drop_table("research_calendars")
