"""nlp model registry metadata

Revision ID: 0003_nlp_model_registry
Revises: 0002_source_fetch_state
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_nlp_model_registry"
down_revision: str | None = "0002_source_fetch_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nlp_model_registry",
        sa.Column("model_id", sa.String(length=160), primary_key=True),
        sa.Column("task", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model_kind", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("dataset_version", sa.String(length=40), nullable=False),
        sa.Column("dataset_sha256", sa.String(length=64), nullable=False),
        sa.Column("split_hashes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("label_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calibration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("config_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("artifact_size_bytes >= 0", name="ck_nlp_model_artifact_size"),
    )
    op.create_index(
        "ix_nlp_model_registry_task_status",
        "nlp_model_registry",
        ["task", "status"],
    )
    op.create_index(
        "ix_nlp_model_registry_dataset",
        "nlp_model_registry",
        ["dataset_id", "dataset_version"],
    )
    op.create_table(
        "nlp_evaluation_runs",
        sa.Column("evaluation_id", sa.String(length=180), primary_key=True),
        sa.Column("model_id", sa.String(length=160), nullable=False),
        sa.Column("task", sa.String(length=40), nullable=False),
        sa.Column("dataset_id", sa.String(length=160), nullable=False),
        sa.Column("dataset_version", sa.String(length=40), nullable=False),
        sa.Column("dataset_sha256", sa.String(length=64), nullable=False),
        sa.Column("split_name", sa.String(length=40), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("slice_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calibration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selection_procedure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["nlp_model_registry.model_id"]),
    )
    op.create_index(
        "ix_nlp_evaluation_runs_task_split",
        "nlp_evaluation_runs",
        ["task", "split_name"],
    )
    op.create_index("ix_nlp_evaluation_runs_model", "nlp_evaluation_runs", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_nlp_evaluation_runs_model", table_name="nlp_evaluation_runs")
    op.drop_index("ix_nlp_evaluation_runs_task_split", table_name="nlp_evaluation_runs")
    op.drop_table("nlp_evaluation_runs")
    op.drop_index("ix_nlp_model_registry_dataset", table_name="nlp_model_registry")
    op.drop_index("ix_nlp_model_registry_task_status", table_name="nlp_model_registry")
    op.drop_table("nlp_model_registry")
