"""official data foundation

Revision ID: 0006_official_data
Revises: 0005_cross_asset_signal
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_official_data"
down_revision: str | None = "0005_cross_asset_signal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "official_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("documentation_url", sa.Text(), nullable=False),
        sa.Column("revision_policy", sa.String(length=120), nullable=False),
        sa.Column("frequency", sa.String(length=40), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("dataset_id"),
    )

    op.create_table(
        "official_series_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", sa.String(length=160), nullable=False),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("query", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("frequency", sa.String(length=40), nullable=False),
        sa.Column("seasonal_adjustment", sa.String(length=80), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("profile_id"),
    )
    op.create_index(
        "ix_official_series_source_dataset",
        "official_series_profiles",
        ["source_id", "dataset_id"],
    )

    op.create_table(
        "official_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("observation_key", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("profile_id", sa.String(length=160), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("current_value", sa.Numeric(24, 6), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("information_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("observation_key"),
    )
    op.create_index(
        "ix_official_observations_profile_period",
        "official_observations",
        ["profile_id", "period_start"],
    )
    op.create_index("ix_official_observations_dataset", "official_observations", ["dataset_id"])

    op.create_table(
        "official_observation_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("observation_key", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(24, 6), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("information_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("observation_key", "revision_number"),
    )
    op.create_index(
        "ix_official_revisions_available",
        "official_observation_revisions",
        ["information_available_at"],
    )

    op.create_table(
        "official_data_release_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("release_run_id", sa.String(length=120), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_count", sa.Integer(), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("new_revision_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("no_persist_live", sa.Boolean(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("release_run_id"),
    )

    op.create_table(
        "regulatory_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.String(length=120), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("document_type", sa.String(length=120), nullable=False),
        sa.Column("agencies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cfr_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rin", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("html_url", sa.Text(), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("information_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index(
        "ix_regulatory_documents_publication",
        "regulatory_documents",
        ["publication_date"],
    )

    op.create_table(
        "series_asset_associations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("association_id", sa.String(length=120), nullable=False),
        sa.Column("profile_id", sa.String(length=160), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("relationship_type", sa.String(length=120), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("association_id"),
    )
    op.create_index("ix_series_asset_profile", "series_asset_associations", ["profile_id"])
    op.create_index("ix_series_asset_asset", "series_asset_associations", ["asset_id"])

    op.create_table(
        "official_release_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("profile_id", sa.String(length=160), nullable=True),
        sa.Column("document_id", sa.String(length=120), nullable=True),
        sa.Column("event_family", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("information_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_official_release_events_source", "official_release_events", ["source_id"])
    op.create_index(
        "ix_official_release_events_available",
        "official_release_events",
        ["information_available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_official_release_events_available", table_name="official_release_events")
    op.drop_index("ix_official_release_events_source", table_name="official_release_events")
    op.drop_table("official_release_events")
    op.drop_index("ix_series_asset_asset", table_name="series_asset_associations")
    op.drop_index("ix_series_asset_profile", table_name="series_asset_associations")
    op.drop_table("series_asset_associations")
    op.drop_index("ix_regulatory_documents_publication", table_name="regulatory_documents")
    op.drop_table("regulatory_documents")
    op.drop_table("official_data_release_runs")
    op.drop_index(
        "ix_official_revisions_available",
        table_name="official_observation_revisions",
    )
    op.drop_table("official_observation_revisions")
    op.drop_index("ix_official_observations_dataset", table_name="official_observations")
    op.drop_index(
        "ix_official_observations_profile_period",
        table_name="official_observations",
    )
    op.drop_table("official_observations")
    op.drop_index("ix_official_series_source_dataset", table_name="official_series_profiles")
    op.drop_table("official_series_profiles")
    op.drop_table("official_datasets")
