from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from finnews.application.services.cross_asset import build_cross_asset_demo
from finnews.application.services.market_reaction import build_market_reaction_demo
from finnews.application.services.paper_execution import (
    PAPER_CONTRACT_NAME,
    PaperRiskPolicy,
    build_paper_execution_demo,
    evaluate_paper_risk,
    paper_execution_surface_audit,
    paper_order_example,
    simulate_manual_review,
    simulate_paper_fill,
    validate_paper_order_intent,
    write_m4b0_release_audit,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_paper_order_contract_accepts_example_and_rejects_unknown_forbidden_fields() -> None:
    example = paper_order_example()
    valid = validate_paper_order_intent(example)
    assert valid["valid"] is True
    assert example["contract_name"] == PAPER_CONTRACT_NAME

    unknown = {**example, "broker_server": "demo", "surprise": True}
    unknown["payload_hash"] = "0" * 64
    result = validate_paper_order_intent(unknown)
    assert result["valid"] is False
    assert "forbidden fields" in " ".join(result["errors"])
    assert "unknown fields" in " ".join(result["errors"])


def test_risk_gates_kill_switch_duplicate_expired_and_low_confidence() -> None:
    cross = build_cross_asset_demo()
    signal = next(item for item in cross.signals if item.status.value == "research")
    asset = next(item for item in cross.assets if item.asset_id == signal.asset_id)
    market = build_market_reaction_demo()
    label = next(
        row
        for row in market.labels
        if row["signal_id"] == signal.signal_id
        and row["scenario_id"] == "synthetic-planted-reaction-v1"
        and row["horizon"] == "one_week"
    )
    bars = [
        row
        for row in market.bars
        if row["scenario_id"] == "synthetic-planted-reaction-v1"
        and row["asset_id"] == signal.asset_id
    ]
    policy = PaperRiskPolicy()
    state = {
        "order_count_by_day": {},
        "order_count_by_asset_day": {},
        "notional_by_asset": {asset.asset_id: Decimal("0")},
        "notional_by_class": {asset.asset_class.value: Decimal("0")},
        "gross_exposure": Decimal("0"),
        "max_drawdown": Decimal("0"),
    }
    from collections import Counter, defaultdict

    state["order_count_by_day"] = Counter()
    state["order_count_by_asset_day"] = Counter()
    state["notional_by_asset"] = defaultdict(lambda: Decimal("0"))
    state["notional_by_class"] = defaultdict(lambda: Decimal("0"))

    decision = evaluate_paper_risk(
        signal=signal,
        asset=asset,
        scenario_id="paper-planted-reaction-v1",
        market_scenario_id="synthetic-planted-reaction-v1",
        policy=policy,
        existing_idempotency=set(),
        portfolio_state=state,
        label=label,
        bars=bars,
    )
    assert decision["risk_decision"] in {"approved_for_paper", "requires_manual_review"}

    duplicate = evaluate_paper_risk(
        signal=signal,
        asset=asset,
        scenario_id="paper-planted-reaction-v1",
        market_scenario_id="synthetic-planted-reaction-v1",
        policy=policy,
        existing_idempotency={decision["idempotency_key"]},
        portfolio_state=state,
        label=label,
        bars=bars,
    )
    assert duplicate["risk_decision"] == "duplicate"

    killed = evaluate_paper_risk(
        signal=signal,
        asset=asset,
        scenario_id="paper-planted-reaction-v1",
        market_scenario_id="synthetic-planted-reaction-v1",
        policy=PaperRiskPolicy(kill_switch_active=True),
        existing_idempotency=set(),
        portfolio_state=state,
        label=label,
        bars=bars,
    )
    assert killed["risk_decision"] == "kill_switch_active"


def test_manual_approval_and_fill_rules_do_not_bypass_risk() -> None:
    dataset = build_paper_execution_demo("paper-planted-reaction-v1")
    order = dataset.orders[0]
    pending = {
        "scenario_id": "paper-planted-reaction-v1",
        "manual_approval_state": "pending_review",
    }
    assert simulate_paper_fill(order, pending, [], PaperRiskPolicy())["fill_status"] == "failed"

    expired = {**order, "expires_at": (datetime(2020, 1, 1, tzinfo=UTC)).isoformat()}
    review = simulate_manual_review(expired, "paper-planted-reaction-v1")
    assert review["manual_approval_state"] == "expired"

    approved_fill = next(fill for fill in dataset.fills if fill["fill_status"] == "filled")
    assert approved_fill["fill_price"] is not None
    assert Decimal(approved_fill["commission"]) > 0


def test_three_scenarios_are_deterministic_and_reconcile() -> None:
    first = build_paper_execution_demo()
    second = build_paper_execution_demo()
    assert first == second
    assert first.overview["scenario_count"] == 3
    assert first.overview["paper_order_count"] == 30
    assert first.overview["filled_count"] == 8
    assert {row["reconciliation_status"] for row in first.nav} == {"passed"}
    assert all(row["synthetic_data"] for row in first.runs)
    assert "manual_review_pending_review" in first.overview["failed_fill_reasons"]


def test_policy_limits_reject_missing_data_drawdown_and_order_caps() -> None:
    dataset = build_paper_execution_demo("paper-planted-reaction-v1")
    assert any(row["risk_decision"] == "rejected" for row in dataset.risk_decisions)

    cross = build_cross_asset_demo()
    signal = next(item for item in cross.signals if item.status.value == "research")
    asset = next(item for item in cross.assets if item.asset_id == signal.asset_id)
    from collections import Counter, defaultdict

    state = {
        "order_count_by_day": Counter(),
        "order_count_by_asset_day": Counter(),
        "notional_by_asset": defaultdict(lambda: Decimal("0")),
        "notional_by_class": defaultdict(lambda: Decimal("0")),
        "gross_exposure": Decimal("0"),
        "max_drawdown": Decimal("0.2"),
    }
    decision = evaluate_paper_risk(
        signal=signal,
        asset=asset,
        scenario_id="paper-planted-reaction-v1",
        market_scenario_id="synthetic-planted-reaction-v1",
        policy=PaperRiskPolicy(),
        existing_idempotency=set(),
        portfolio_state=state,
        label={},
        bars=[],
    )
    assert decision["risk_decision"] == "rejected"

    cap_state = {
        "order_count_by_day": Counter({"2026-06-18": 1}),
        "order_count_by_asset_day": Counter(),
        "notional_by_asset": defaultdict(lambda: Decimal("0")),
        "notional_by_class": defaultdict(lambda: Decimal("0")),
        "gross_exposure": Decimal("0"),
        "max_drawdown": Decimal("0"),
    }
    capped = evaluate_paper_risk(
        signal=signal,
        asset=asset,
        scenario_id="paper-planted-reaction-v1",
        market_scenario_id="synthetic-planted-reaction-v1",
        policy=PaperRiskPolicy(max_orders_per_day=1),
        existing_idempotency=set(),
        portfolio_state=cap_state,
        label={"coverage": "1"},
        bars=[{"bar_start_at": "2026-06-19T00:00:00+00:00"}],
    )
    assert "max_paper_orders_per_day" in capped["reason_codes"]


def test_release_and_surface_audits_are_safe() -> None:
    surface = paper_execution_surface_audit()
    assert surface["status"] == "PASS"
    assert surface["forbidden_count"] == 0
    report = write_m4b0_release_audit(REPO_ROOT)
    assert report["status"] == "PASS"
    assert report["paper_order_count"] == 30
    assert report["filled_count"] == 8
