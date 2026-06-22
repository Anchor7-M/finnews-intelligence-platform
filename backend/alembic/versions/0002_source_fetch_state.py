"""source fetch state and attempts

Revision ID: 0002_source_fetch_state
Revises: 0001_initial_schema
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_source_fetch_state"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_definitions",
        sa.Column("source_id", sa.String(length=120), primary_key=True),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("approved_hostnames", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("import_format", sa.String(length=40), nullable=True),
        sa.Column("terms_url", sa.Text(), nullable=True),
        sa.Column("documentation_url", sa.Text(), nullable=True),
        sa.Column("reviewed_date", sa.String(length=40), nullable=True),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("content_storage_policy", sa.String(length=64), nullable=False),
        sa.Column("provenance_required", sa.Boolean(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("connect_timeout_seconds", sa.Float(), nullable=False),
        sa.Column("read_timeout_seconds", sa.Float(), nullable=False),
        sa.Column("max_response_bytes", sa.Integer(), nullable=False),
        sa.Column("retry_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("cursor_strategy", sa.String(length=80), nullable=True),
        sa.Column("field_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_agent", sa.String(length=240), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("risk_classification", sa.String(length=40), nullable=False),
        sa.Column("adapter_version", sa.String(length=40), nullable=False),
    )
    op.create_table(
        "source_fetch_states",
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_response_hash", sa.String(length=64), nullable=True),
        sa.Column("last_response_byte_count", sa.Integer(), nullable=False),
        sa.Column("last_item_count", sa.Integer(), nullable=False),
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error_category", sa.String(length=80), nullable=False),
        sa.Column("last_error_summary", sa.String(length=240), nullable=False),
        sa.Column("health_status", sa.String(length=40), nullable=False),
        sa.Column("adapter_version", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_definitions.source_id"]),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_index("ix_source_fetch_states_health", "source_fetch_states", ["health_status"])
    op.create_index(
        "ix_source_fetch_states_next_allowed",
        "source_fetch_states",
        ["next_allowed_at"],
    )
    op.create_table(
        "source_fetch_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("response_byte_count", sa.Integer(), nullable=False),
        sa.Column("response_hash", sa.String(length=64), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(length=80), nullable=False),
        sa.Column("error_summary", sa.String(length=240), nullable=False),
        sa.Column("etag_present", sa.Boolean(), nullable=False),
        sa.Column("last_modified_present", sa.Boolean(), nullable=False),
        sa.Column("cursor_before", sa.Text(), nullable=True),
        sa.Column("cursor_after", sa.Text(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_definitions.source_id"]),
    )
    op.create_index(
        "ix_source_fetch_attempts_source_started",
        "source_fetch_attempts",
        ["source_id", "started_at"],
    )
    op.create_index("ix_source_fetch_attempts_outcome", "source_fetch_attempts", ["outcome"])


def downgrade() -> None:
    op.drop_index("ix_source_fetch_attempts_outcome", table_name="source_fetch_attempts")
    op.drop_index("ix_source_fetch_attempts_source_started", table_name="source_fetch_attempts")
    op.drop_table("source_fetch_attempts")
    op.drop_index("ix_source_fetch_states_next_allowed", table_name="source_fetch_states")
    op.drop_index("ix_source_fetch_states_health", table_name="source_fetch_states")
    op.drop_table("source_fetch_states")
    op.drop_table("source_definitions")
