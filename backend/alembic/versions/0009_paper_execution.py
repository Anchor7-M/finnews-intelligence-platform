"""paper execution simulator metadata

Revision ID: 0009_paper_execution
Revises: 0008_mt5_readonly
Create Date: 2026-06-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_paper_execution"
down_revision: str | None = "0008_mt5_readonly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_risk_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("risk_policy_id", sa.String(length=160), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("risk_policy_id", name="uq_paper_risk_policies_risk_policy_id"),
    )

    op.create_table(
        "paper_execution_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(length=180), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("risk_policy_id", sa.String(length=160), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["risk_policy_id"],
            ["paper_risk_policies.risk_policy_id"],
            name="fk_paper_execution_runs_risk_policy_id",
        ),
        sa.UniqueConstraint("run_id", name="uq_paper_execution_runs_run_id"),
    )
    op.create_index("ix_paper_execution_runs_scenario", "paper_execution_runs", ["scenario_id"])

    op.create_table(
        "paper_risk_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("risk_decision_id", sa.String(length=220), nullable=False),
        sa.Column("run_id", sa.String(length=180), nullable=False),
        sa.Column("signal_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("risk_policy_id", sa.String(length=160), nullable=False),
        sa.Column("risk_decision", sa.String(length=60), nullable=False),
        sa.Column("decision_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["paper_execution_runs.run_id"],
            name="fk_paper_risk_decisions_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["risk_policy_id"],
            ["paper_risk_policies.risk_policy_id"],
            name="fk_paper_risk_decisions_risk_policy_id",
        ),
        sa.UniqueConstraint("risk_decision_id", name="uq_paper_risk_decisions_risk_decision_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_paper_risk_decisions_idempotency_key"),
    )
    op.create_index("ix_paper_risk_decisions_asset", "paper_risk_decisions", ["asset_id"])

    op.create_table(
        "paper_order_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_order_id", sa.String(length=220), nullable=False),
        sa.Column("risk_decision_id", sa.String(length=220), nullable=False),
        sa.Column("contract_name", sa.String(length=120), nullable=False),
        sa.Column("contract_version", sa.String(length=40), nullable=False),
        sa.Column("signal_id", sa.String(length=120), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("paper_side", sa.String(length=20), nullable=False),
        sa.Column("decision_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paper_quantity_units", sa.Numeric(24, 8), nullable=False),
        sa.Column("paper_notional", sa.Numeric(24, 8), nullable=False),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("manual_approval_state", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["risk_decision_id"],
            ["paper_risk_decisions.risk_decision_id"],
            name="fk_paper_order_intents_risk_decision_id",
        ),
        sa.UniqueConstraint("paper_order_id", name="uq_paper_order_intents_paper_order_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_paper_order_intents_idempotency_key"),
    )
    op.create_index("ix_paper_order_intents_asset", "paper_order_intents", ["asset_id"])

    op.create_table(
        "paper_manual_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("manual_review_id", sa.String(length=240), nullable=False),
        sa.Column("paper_order_id", sa.String(length=220), nullable=False),
        sa.Column("manual_approval_state", sa.String(length=40), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synthetic_actor", sa.String(length=120), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("audit_trail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["paper_order_id"],
            ["paper_order_intents.paper_order_id"],
            name="fk_paper_manual_reviews_paper_order_id",
        ),
        sa.UniqueConstraint("manual_review_id", name="uq_paper_manual_reviews_manual_review_id"),
    )

    op.create_table(
        "paper_fills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fill_id", sa.String(length=240), nullable=False),
        sa.Column("paper_order_id", sa.String(length=220), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("fill_status", sa.String(length=40), nullable=False),
        sa.Column("failed_reason", sa.String(length=120), nullable=True),
        sa.Column("filled_quantity_units", sa.Numeric(24, 8), nullable=False),
        sa.Column("fill_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("gross_notional", sa.Numeric(24, 8), nullable=False),
        sa.Column("commission", sa.Numeric(24, 8), nullable=False),
        sa.Column("slippage", sa.Numeric(24, 8), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["paper_order_id"],
            ["paper_order_intents.paper_order_id"],
            name="fk_paper_fills_paper_order_id",
        ),
        sa.UniqueConstraint("fill_id", name="uq_paper_fills_fill_id"),
    )
    op.create_index("ix_paper_fills_order", "paper_fills", ["paper_order_id"])

    op.create_table(
        "paper_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(length=180), nullable=False),
        sa.Column("asset_id", sa.String(length=120), nullable=False),
        sa.Column("asset_class", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("average_cost", sa.Numeric(24, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(24, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(24, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(24, 8), nullable=False),
        sa.Column("transaction_costs", sa.Numeric(24, 8), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["paper_execution_runs.run_id"],
            name="fk_paper_positions_run_id",
        ),
        sa.UniqueConstraint("run_id", "asset_id", name="uq_paper_positions_run_id_asset_id"),
    )

    op.create_table(
        "paper_nav",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(length=180), nullable=False),
        sa.Column("nav_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash", sa.Numeric(24, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(24, 8), nullable=False),
        sa.Column("nav", sa.Numeric(24, 8), nullable=False),
        sa.Column("gross_exposure", sa.Numeric(24, 8), nullable=False),
        sa.Column("net_exposure", sa.Numeric(24, 8), nullable=False),
        sa.Column("drawdown", sa.Numeric(18, 8), nullable=False),
        sa.Column("maximum_drawdown", sa.Numeric(18, 8), nullable=False),
        sa.Column("reconciliation_status", sa.String(length=40), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["paper_execution_runs.run_id"],
            name="fk_paper_nav_run_id",
        ),
    )
    op.create_index("ix_paper_nav_run", "paper_nav", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_paper_nav_run", table_name="paper_nav")
    op.drop_table("paper_nav")
    op.drop_table("paper_positions")
    op.drop_index("ix_paper_fills_order", table_name="paper_fills")
    op.drop_table("paper_fills")
    op.drop_table("paper_manual_reviews")
    op.drop_index("ix_paper_order_intents_asset", table_name="paper_order_intents")
    op.drop_table("paper_order_intents")
    op.drop_index("ix_paper_risk_decisions_asset", table_name="paper_risk_decisions")
    op.drop_table("paper_risk_decisions")
    op.drop_index("ix_paper_execution_runs_scenario", table_name="paper_execution_runs")
    op.drop_table("paper_execution_runs")
    op.drop_table("paper_risk_policies")
