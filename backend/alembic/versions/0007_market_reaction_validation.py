"""market reaction validation

Revision ID: 0007_market_reaction
Revises: 0006_official_data
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_market_reaction"
down_revision: str | None = "0006_official_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_data_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("package_id", sa.String(length=160), nullable=False),
        sa.Column("contract_name", sa.String(length=120), nullable=False),
        sa.Column("contract_version", sa.String(length=40), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("asset_count", sa.Integer(), nullable=False),
        sa.Column("bar_count", sa.Integer(), nullable=False),
        sa.Column("session_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("user_imported", sa.Boolean(), nullable=False),
        sa.Column("live_data", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("package_id"),
    )

    op.create_table(
        "market_bar_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("series_id", sa.String(length=160), nullable=False),
        sa.Column("package_id", sa.String(length=160), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("provider_symbol", sa.String(length=160), nullable=False),
        sa.Column("granularity", sa.String(length=40), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("series_id"),
        sa.UniqueConstraint("package_id", "asset_id", "provider_symbol", "granularity"),
    )
    op.create_index("ix_market_bar_series_asset", "market_bar_series", ["asset_id"])

    op.create_table(
        "market_bars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bar_id", sa.String(length=240), nullable=False),
        sa.Column("series_id", sa.String(length=160), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column("bar_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bar_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("open", sa.Numeric(24, 6), nullable=False),
        sa.Column("high", sa.Numeric(24, 6), nullable=False),
        sa.Column("low", sa.Numeric(24, 6), nullable=False),
        sa.Column("close", sa.Numeric(24, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 6), nullable=False),
        sa.Column("quote_volume", sa.Numeric(24, 6), nullable=True),
        sa.Column("market_state", sa.String(length=80), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("bar_id"),
    )
    op.create_index("ix_market_bars_asset_time", "market_bars", ["asset_id", "bar_start_at"])
    op.create_index("ix_market_bars_scenario", "market_bars", ["scenario_id"])

    op.create_table(
        "market_bar_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bar_id", sa.String(length=240), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(24, 6), nullable=False),
        sa.Column("high", sa.Numeric(24, 6), nullable=False),
        sa.Column("low", sa.Numeric(24, 6), nullable=False),
        sa.Column("close", sa.Numeric(24, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 6), nullable=False),
        sa.Column("quote_volume", sa.Numeric(24, 6), nullable=True),
        sa.Column("value_hash", sa.String(length=64), nullable=False),
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("bar_id", "revision_number"),
    )
    op.create_index("ix_market_bar_revisions_available", "market_bar_revisions", ["available_at"])

    op.create_table(
        "market_reaction_studies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("study_id", sa.String(length=240), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("signal_id", sa.String(length=120), nullable=False),
        sa.Column("impact_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("event_family", sa.String(length=100), nullable=False),
        sa.Column("decision_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reaction_window", sa.String(length=40), nullable=False),
        sa.Column("bar_coverage", sa.Integer(), nullable=False),
        sa.Column("raw_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("benchmark_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("abnormal_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("excluded_reason", sa.String(length=120), nullable=True),
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("study_id"),
    )
    op.create_index(
        "ix_market_reaction_studies_scenario",
        "market_reaction_studies",
        ["scenario_id"],
    )
    op.create_index("ix_market_reaction_studies_asset", "market_reaction_studies", ["asset_id"])

    op.create_table(
        "market_reaction_labels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label_id", sa.String(length=260), nullable=False),
        sa.Column("study_id", sa.String(length=240), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("signal_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("horizon", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("threshold_version", sa.String(length=80), nullable=False),
        sa.Column("abnormal_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("coverage", sa.Integer(), nullable=False),
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "point_in_time_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("label_id"),
    )
    op.create_index("ix_market_reaction_labels_scenario", "market_reaction_labels", ["scenario_id"])
    op.create_index("ix_market_reaction_labels_label", "market_reaction_labels", ["label"])

    op.create_table(
        "signal_quality_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("run_id"),
    )

    op.create_table(
        "signal_quality_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_id", sa.String(length=240), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("slice_type", sa.String(length=80), nullable=False),
        sa.Column("slice_value", sa.String(length=160), nullable=False),
        sa.Column("evaluated_signal_count", sa.Integer(), nullable=False),
        sa.Column("coverage", sa.Numeric(12, 6), nullable=False),
        sa.Column("directional_consistency_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("opposite_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("muted_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("metric_id"),
    )
    op.create_index("ix_signal_quality_metrics_scenario", "signal_quality_metrics", ["scenario_id"])

    op.create_table(
        "signal_error_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("error_case_id", sa.String(length=240), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("signal_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("event_family", sa.String(length=100), nullable=False),
        sa.Column("expected_direction", sa.String(length=40), nullable=False),
        sa.Column("observed_label", sa.String(length=80), nullable=False),
        sa.Column("abnormal_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("horizon", sa.String(length=40), nullable=False),
        sa.Column("regime", sa.String(length=80), nullable=False),
        sa.Column("error_category", sa.String(length=120), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("error_case_id"),
    )
    op.create_index("ix_signal_error_cases_scenario", "signal_error_cases", ["scenario_id"])


def downgrade() -> None:
    op.drop_index("ix_signal_error_cases_scenario", table_name="signal_error_cases")
    op.drop_table("signal_error_cases")
    op.drop_index("ix_signal_quality_metrics_scenario", table_name="signal_quality_metrics")
    op.drop_table("signal_quality_metrics")
    op.drop_table("signal_quality_runs")
    op.drop_index("ix_market_reaction_labels_label", table_name="market_reaction_labels")
    op.drop_index("ix_market_reaction_labels_scenario", table_name="market_reaction_labels")
    op.drop_table("market_reaction_labels")
    op.drop_index("ix_market_reaction_studies_asset", table_name="market_reaction_studies")
    op.drop_index("ix_market_reaction_studies_scenario", table_name="market_reaction_studies")
    op.drop_table("market_reaction_studies")
    op.drop_index("ix_market_bar_revisions_available", table_name="market_bar_revisions")
    op.drop_table("market_bar_revisions")
    op.drop_index("ix_market_bars_scenario", table_name="market_bars")
    op.drop_index("ix_market_bars_asset_time", table_name="market_bars")
    op.drop_table("market_bars")
    op.drop_index("ix_market_bar_series_asset", table_name="market_bar_series")
    op.drop_table("market_bar_series")
    op.drop_table("market_data_packages")
