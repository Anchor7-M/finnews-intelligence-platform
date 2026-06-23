"""cross asset signal foundation

Revision ID: 0005_cross_asset_signal
Revises: 0004_research_export_metadata
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_cross_asset_signal"
down_revision: str | None = "0004_research_export_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("asset_class", sa.String(length=60), nullable=False),
        sa.Column("canonical_symbol", sa.String(length=80), nullable=True),
        sa.Column("home_venue", sa.String(length=80), nullable=True),
        sa.Column("country_region", sa.String(length=80), nullable=False),
        sa.Column("base_currency", sa.String(length=16), nullable=True),
        sa.Column("quote_currency", sa.String(length=16), nullable=True),
        sa.Column("parent_asset_id", sa.String(length=120), nullable=True),
        sa.Column("expiry", sa.Date(), nullable=True),
        sa.Column("contract_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("asset_id"),
    )
    op.create_index("ix_assets_class_region", "assets", ["asset_class", "country_region"])
    op.create_index("ix_assets_status", "assets", ["status"])

    op.create_table(
        "asset_symbol_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("symbol", sa.String(length=240), nullable=False),
        sa.Column("normalized_symbol", sa.String(length=240), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.UniqueConstraint("asset_id", "namespace", "symbol", "provider", "provider_version"),
    )
    op.create_index(
        "ix_asset_alias_namespace_symbol",
        "asset_symbol_aliases",
        ["namespace", "normalized_symbol", "active"],
    )

    op.create_table(
        "asset_provider_symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("symbol", sa.String(length=240), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("asset_id", "namespace", "provider", "symbol"),
    )
    op.create_index(
        "ix_provider_symbols_lookup",
        "asset_provider_symbols",
        ["namespace", "provider", "symbol", "active"],
    )

    op.create_table(
        "broker_symbol_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("broker_profile_id", sa.String(length=120), nullable=False),
        sa.Column("mt5_symbol", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("local_note", sa.Text(), nullable=True),
        sa.UniqueConstraint("broker_profile_id", "mt5_symbol", "enabled"),
    )
    op.create_index("ix_broker_symbol_mappings_asset", "broker_symbol_mappings", ["asset_id"])

    op.create_table(
        "asset_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("relationship_id", sa.String(length=120), nullable=False),
        sa.Column("source_asset_id", sa.String(length=120), nullable=False),
        sa.Column("target_asset_id", sa.String(length=120), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("direction", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("relationship_id"),
    )
    op.create_index("ix_asset_relationships_source", "asset_relationships", ["source_asset_id"])
    op.create_index("ix_asset_relationships_target", "asset_relationships", ["target_asset_id"])

    op.create_table(
        "cross_asset_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("event_family", sa.String(length=100), nullable=False),
        sa.Column("event_subtype", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("information_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("affected_region", sa.String(length=80), nullable=False),
        sa.Column("relevant_currency", sa.String(length=16), nullable=True),
        sa.Column("source_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("uncertainty_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("duplicate_of_event_id", sa.String(length=120), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ix_cross_asset_events_family_time",
        "cross_asset_events",
        ["event_family", "information_available_at"],
    )

    op.create_table(
        "asset_impact_hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("impact_id", sa.String(length=120), nullable=False),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("direction", sa.String(length=40), nullable=False),
        sa.Column("impact_strength", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("horizon", sa.String(length=40), nullable=False),
        sa.Column("evidence_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("information_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("rejection_reason", sa.String(length=160), nullable=True),
        sa.Column("uncertainty_reason", sa.String(length=160), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("impact_id"),
    )
    op.create_index(
        "ix_asset_impacts_asset_event",
        "asset_impact_hypotheses",
        ["asset_id", "event_id"],
    )
    op.create_index(
        "ix_asset_impacts_direction_horizon",
        "asset_impact_hypotheses",
        ["direction", "horizon"],
    )

    op.create_table(
        "market_signal_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("signal_id", sa.String(length=120), nullable=False),
        sa.Column("impact_id", sa.String(length=120), nullable=False),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("direction", sa.String(length=40), nullable=False),
        sa.Column("horizon", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("information_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("evidence_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("signal_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_market_signals_asset_status",
        "market_signal_candidates",
        ["asset_id", "status"],
    )
    op.create_index(
        "ix_market_signals_horizon_direction",
        "market_signal_candidates",
        ["horizon", "direction"],
    )

    op.create_table(
        "signal_publication_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(length=120), nullable=False),
        sa.Column("contract_name", sa.String(length=120), nullable=False),
        sa.Column("contract_version", sa.String(length=40), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("file_hashes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("signal_publication_runs")
    op.drop_index("ix_market_signals_horizon_direction", table_name="market_signal_candidates")
    op.drop_index("ix_market_signals_asset_status", table_name="market_signal_candidates")
    op.drop_table("market_signal_candidates")
    op.drop_index("ix_asset_impacts_direction_horizon", table_name="asset_impact_hypotheses")
    op.drop_index("ix_asset_impacts_asset_event", table_name="asset_impact_hypotheses")
    op.drop_table("asset_impact_hypotheses")
    op.drop_index("ix_cross_asset_events_family_time", table_name="cross_asset_events")
    op.drop_table("cross_asset_events")
    op.drop_index("ix_asset_relationships_target", table_name="asset_relationships")
    op.drop_index("ix_asset_relationships_source", table_name="asset_relationships")
    op.drop_table("asset_relationships")
    op.drop_index("ix_broker_symbol_mappings_asset", table_name="broker_symbol_mappings")
    op.drop_table("broker_symbol_mappings")
    op.drop_index("ix_provider_symbols_lookup", table_name="asset_provider_symbols")
    op.drop_table("asset_provider_symbols")
    op.drop_index("ix_asset_alias_namespace_symbol", table_name="asset_symbol_aliases")
    op.drop_table("asset_symbol_aliases")
    op.drop_index("ix_assets_status", table_name="assets")
    op.drop_index("ix_assets_class_region", table_name="assets")
    op.drop_table("assets")
