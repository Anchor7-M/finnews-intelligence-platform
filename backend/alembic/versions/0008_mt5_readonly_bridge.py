"""mt5 readonly bridge metadata

Revision ID: 0008_mt5_readonly
Revises: 0007_market_reaction
Create Date: 2026-06-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_mt5_readonly"
down_revision: str | None = "0007_market_reaction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mt5_readonly_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("profile_id"),
    )

    op.create_table(
        "mt5_readonly_symbol_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", sa.String(length=120), nullable=False),
        sa.Column("canonical_asset_id", sa.String(length=120), nullable=False),
        sa.Column("mt5_symbol", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=True),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("profile_id", "canonical_asset_id", "mt5_symbol"),
    )
    op.create_index(
        "ix_mt5_readonly_symbol_mappings_asset",
        "mt5_readonly_symbol_mappings",
        ["canonical_asset_id"],
    )

    op.create_table(
        "mt5_readonly_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("profile_id", sa.String(length=120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("terminal_access_status", sa.String(length=80), nullable=False),
        sa.Column("mapped_asset_count", sa.Integer(), nullable=False),
        sa.Column("exported_bar_count", sa.Integer(), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_mt5_readonly_runs_profile", "mt5_readonly_runs", ["profile_id"])

    op.create_table(
        "mt5_bar_export_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("manifest_id", sa.String(length=180), nullable=False),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("contract_name", sa.String(length=120), nullable=False),
        sa.Column("contract_version", sa.String(length=40), nullable=False),
        sa.Column("timeframe", sa.String(length=20), nullable=False),
        sa.Column("asset_count", sa.Integer(), nullable=False),
        sa.Column("bar_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("logical_output_ref", sa.String(length=240), nullable=True),
        sa.Column("safe_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("manifest_id"),
    )
    op.create_index("ix_mt5_bar_export_manifests_run", "mt5_bar_export_manifests", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_mt5_bar_export_manifests_run", table_name="mt5_bar_export_manifests")
    op.drop_table("mt5_bar_export_manifests")
    op.drop_index("ix_mt5_readonly_runs_profile", table_name="mt5_readonly_runs")
    op.drop_table("mt5_readonly_runs")
    op.drop_index(
        "ix_mt5_readonly_symbol_mappings_asset",
        table_name="mt5_readonly_symbol_mappings",
    )
    op.drop_table("mt5_readonly_symbol_mappings")
    op.drop_table("mt5_readonly_profiles")
