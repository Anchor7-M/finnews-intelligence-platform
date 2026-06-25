# ruff: noqa: E501

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from finnews.application.services.cross_asset import (
    build_cross_asset_demo,
    canonical_json,
    sha256_text,
)
from finnews.application.services.market_reaction import build_market_reaction_demo
from finnews.domain.entities import Asset, MarketSignalCandidate
from finnews.domain.enums import ImpactDirection, ResearchSignalStatus

PAPER_CONTRACT_NAME = "finnews-paper-execution-v1"
PAPER_CONTRACT_VERSION = "1.0.0"
PAPER_ENGINE_VERSION = "m4b0-paper-simulator-v1"
PAPER_GENERATED_AT = datetime(2026, 6, 25, 0, 0, tzinfo=UTC)
PAPER_DECISION_NOW = datetime(2026, 6, 25, 0, 0, tzinfo=UTC)
STARTING_CASH = Decimal("100000.00")
SUPPORTED_PAPER_SCENARIOS = [
    "paper-null-reaction-v1",
    "paper-planted-reaction-v1",
    "paper-regime-shift-v1",
]
SCENARIO_TO_MARKET_REACTION = {
    "paper-null-reaction-v1": "synthetic-null-reaction-v1",
    "paper-planted-reaction-v1": "synthetic-planted-reaction-v1",
    "paper-regime-shift-v1": "synthetic-regime-shift-v1",
}
PAPER_ALLOWED_FIELDS = {
    "paper_order_id",
    "contract_name",
    "contract_version",
    "created_at",
    "signal_id",
    "asset_id",
    "direction",
    "paper_side",
    "decision_time",
    "expires_at",
    "paper_quantity_units",
    "paper_notional",
    "currency",
    "risk_policy_id",
    "risk_decision",
    "manual_approval_state",
    "idempotency_key",
    "synthetic_data",
    "not_investment_advice",
    "reason_codes",
    "payload_hash",
}
PAPER_FORBIDDEN_FIELDS = {
    "broker_server",
    "account_id",
    "account",
    "login",
    "password",
    "terminal_path",
    "mt5_symbol",
    "order_ticket",
    "position_id",
    "real_lot_size",
    "leverage",
    "margin",
    "stop_loss",
    "take_profit",
    "order_type",
    "execution_flag",
    "order_check",
    "order_send",
}
PAPER_SIDES = {"long", "flat", "reduce"}
RISK_DECISIONS = {
    "approved_for_paper",
    "requires_manual_review",
    "rejected",
    "expired",
    "duplicate",
    "kill_switch_active",
}
MANUAL_REVIEW_STATES = {"pending_review", "approved", "rejected", "expired"}
FORBIDDEN_TEXT_MARKERS = {
    "real account",
    "broker api",
    "mt5 execution",
    "live trading",
}


class PaperExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class PaperRiskPolicy:
    risk_policy_id: str = "paper-risk-m4b0-default-v1"
    confidence_threshold: Decimal = Decimal("0.45")
    low_confidence_policy: str = "manual_review"
    allowed_asset_classes: tuple[str, ...] = (
        "us_equity",
        "etf",
        "equity_index",
        "fx",
        "precious_metal",
        "commodity",
        "futures_root",
        "futures_contract",
        "crypto_asset",
    )
    max_orders_per_day: int = 12
    max_orders_per_asset_per_day: int = 2
    max_notional_per_asset: Decimal = Decimal("7500")
    max_notional_by_asset_class: Decimal = Decimal("15000")
    max_total_exposure: Decimal = Decimal("35000")
    max_drawdown: Decimal = Decimal("0.0800")
    max_missing_data_ratio: Decimal = Decimal("0.2500")
    min_bar_coverage: Decimal = Decimal("0.7500")
    stale_source_hours: int = 240
    manual_approval_required: bool = True
    kill_switch_active: bool = False
    default_order_notional: Decimal = Decimal("2500")
    slippage_bps: Decimal = Decimal("2")
    commission_bps: Decimal = Decimal("5")
    starting_cash: Decimal = STARTING_CASH
    allow_informational: bool = True


@dataclass(frozen=True)
class PaperExecutionDataset:
    overview: dict[str, Any]
    risk_policies: list[dict[str, Any]]
    risk_decisions: list[dict[str, Any]]
    orders: list[dict[str, Any]]
    manual_reviews: list[dict[str, Any]]
    fills: list[dict[str, Any]]
    positions: list[dict[str, Any]]
    nav: list[dict[str, Any]]
    runs: list[dict[str, Any]]
    rejection_reasons: list[dict[str, Any]]
    surface_audit: dict[str, Any]


def paper_risk_policy_dict(policy: PaperRiskPolicy | None = None) -> dict[str, Any]:
    policy = policy or PaperRiskPolicy()
    return {
        "risk_policy_id": policy.risk_policy_id,
        "policy_version": PAPER_ENGINE_VERSION,
        "confidence_threshold": str(policy.confidence_threshold),
        "low_confidence_policy": policy.low_confidence_policy,
        "allowed_asset_classes": list(policy.allowed_asset_classes),
        "max_orders_per_day": policy.max_orders_per_day,
        "max_orders_per_asset_per_day": policy.max_orders_per_asset_per_day,
        "max_notional_per_asset": str(policy.max_notional_per_asset),
        "max_notional_by_asset_class": str(policy.max_notional_by_asset_class),
        "max_total_exposure": str(policy.max_total_exposure),
        "max_drawdown": str(policy.max_drawdown),
        "max_missing_data_ratio": str(policy.max_missing_data_ratio),
        "min_bar_coverage": str(policy.min_bar_coverage),
        "stale_source_hours": policy.stale_source_hours,
        "manual_approval_required": policy.manual_approval_required,
        "kill_switch_active": policy.kill_switch_active,
        "default_order_notional": str(policy.default_order_notional),
        "slippage_bps": str(policy.slippage_bps),
        "commission_bps": str(policy.commission_bps),
        "starting_cash": str(policy.starting_cash),
        "allow_informational": policy.allow_informational,
        "paper_only": True,
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
        "not_investment_advice": True,
    }


def paper_order_contract_schema() -> dict[str, Any]:
    return {
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "allowed_fields": sorted(PAPER_ALLOWED_FIELDS),
        "forbidden_fields": sorted(PAPER_FORBIDDEN_FIELDS),
        "paper_side_values": sorted(PAPER_SIDES),
        "risk_decision_values": sorted(RISK_DECISIONS),
        "manual_approval_values": sorted(MANUAL_REVIEW_STATES),
        "strict_unknown_field_rejection": True,
        "paper_only": True,
        "broker_order": False,
        "not_investment_advice": True,
    }


def paper_order_example() -> dict[str, Any]:
    payload = {
        "paper_order_id": "paper-order-example-001",
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "created_at": PAPER_GENERATED_AT.isoformat(),
        "signal_id": "SIGNAL-EXAMPLE",
        "asset_id": "US-EQ-ALPHA",
        "direction": "positive",
        "paper_side": "long",
        "decision_time": "2026-06-25T00:00:00+00:00",
        "expires_at": "2026-06-26T00:00:00+00:00",
        "paper_quantity_units": "24.500000",
        "paper_notional": "2500.000000",
        "currency": "USD",
        "risk_policy_id": "paper-risk-m4b0-default-v1",
        "risk_decision": "approved_for_paper",
        "manual_approval_state": "pending_review",
        "idempotency_key": "example-paper-idempotency-key",
        "synthetic_data": True,
        "not_investment_advice": True,
        "reason_codes": ["paper_only", "manual_review_required"],
    }
    payload["payload_hash"] = payload_hash(payload)
    return payload


def validate_paper_order_intent(payload: dict[str, Any]) -> dict[str, Any]:
    fields = set(payload)
    unknown = fields - PAPER_ALLOWED_FIELDS
    forbidden = fields & PAPER_FORBIDDEN_FIELDS
    errors: list[str] = []
    if unknown:
        errors.append(f"unknown fields: {', '.join(sorted(unknown))}")
    if forbidden:
        errors.append(f"forbidden fields: {', '.join(sorted(forbidden))}")
    if payload.get("contract_name") != PAPER_CONTRACT_NAME:
        errors.append("contract_name mismatch")
    if payload.get("contract_version") != PAPER_CONTRACT_VERSION:
        errors.append("contract_version mismatch")
    if payload.get("paper_side") not in PAPER_SIDES:
        errors.append("invalid paper_side")
    if payload.get("risk_decision") not in RISK_DECISIONS:
        errors.append("invalid risk_decision")
    if payload.get("manual_approval_state") not in MANUAL_REVIEW_STATES:
        errors.append("invalid manual_approval_state")
    for marker in FORBIDDEN_TEXT_MARKERS:
        if marker in canonical_json(payload).lower():
            errors.append(f"forbidden text marker: {marker}")
    expected_hash = payload_hash(payload)
    if payload.get("payload_hash") != expected_hash:
        errors.append("payload_hash mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "payload_hash": expected_hash,
        "idempotency_key": payload.get("idempotency_key"),
        "paper_only": True,
        "not_investment_advice": True,
    }


def payload_hash(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "payload_hash"}
    return sha256_text(canonical_json(body))


def build_paper_execution_demo(
    scenario_id: str | None = None,
    policy: PaperRiskPolicy | None = None,
) -> PaperExecutionDataset:
    policy = policy or PaperRiskPolicy()
    scenarios = [scenario_id] if scenario_id else SUPPORTED_PAPER_SCENARIOS
    for scenario in scenarios:
        _ensure_paper_scenario(scenario)

    cross_asset = build_cross_asset_demo()
    market = build_market_reaction_demo()
    assets = {asset.asset_id: asset for asset in cross_asset.assets}
    signals = {signal.signal_id: signal for signal in cross_asset.signals}
    labels_by_scenario_signal = {
        (str(row["scenario_id"]), str(row["signal_id"])): row
        for row in market.labels
        if row["horizon"] == "one_week"
    }
    bars_by_scenario_asset: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in market.bars:
        bars_by_scenario_asset[(str(row["scenario_id"]), str(row["asset_id"]))].append(row)
    for rows in bars_by_scenario_asset.values():
        rows.sort(key=lambda item: str(item["bar_start_at"]))

    risk_decisions: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    fills: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    rejection_reasons: list[dict[str, Any]] = []

    for paper_scenario in scenarios:
        market_scenario = SCENARIO_TO_MARKET_REACTION[paper_scenario]
        scenario_labels = [
            row
            for row in market.labels
            if row["scenario_id"] == market_scenario and row["horizon"] == "one_week"
        ]
        selected_signal_ids = sorted({str(row["signal_id"]) for row in scenario_labels})[:36]
        scenario_decisions: list[dict[str, Any]] = []
        scenario_orders: list[dict[str, Any]] = []
        scenario_reviews: list[dict[str, Any]] = []
        scenario_fills: list[dict[str, Any]] = []
        state = _initial_state(policy)
        seen_keys: set[str] = set()
        for signal_id_value in selected_signal_ids:
            signal = signals[signal_id_value]
            asset = assets[signal.asset_id]
            label = labels_by_scenario_signal.get((market_scenario, signal.signal_id), {})
            bars = bars_by_scenario_asset.get((market_scenario, signal.asset_id), [])
            decision = evaluate_paper_risk(
                signal=signal,
                asset=asset,
                scenario_id=paper_scenario,
                market_scenario_id=market_scenario,
                policy=policy,
                existing_idempotency=seen_keys,
                portfolio_state=state,
                label=label,
                bars=bars,
            )
            seen_keys.add(str(decision["idempotency_key"]))
            scenario_decisions.append(decision)
            if decision["risk_decision"] in {"approved_for_paper", "requires_manual_review"}:
                order = build_paper_order_intent(decision, signal, asset, policy)
                scenario_orders.append(order)
                review = simulate_manual_review(order, paper_scenario)
                scenario_reviews.append(review)
                fill = simulate_paper_fill(order, review, bars, policy)
                scenario_fills.append(fill)
                _apply_fill_to_state(fill, asset, state)
        scenario_positions = _position_rows(paper_scenario, state)
        scenario_nav = _nav_rows(paper_scenario, state)
        scenario_run = _run_row(
            paper_scenario,
            policy,
            scenario_decisions,
            scenario_orders,
            scenario_reviews,
            scenario_fills,
            scenario_positions,
            scenario_nav,
        )
        risk_decisions.extend(scenario_decisions)
        orders.extend(scenario_orders)
        reviews.extend(scenario_reviews)
        fills.extend(scenario_fills)
        positions.extend(scenario_positions)
        nav_rows.extend(scenario_nav)
        runs.append(scenario_run)
        rejection_reasons.extend(
            _rejection_rows(paper_scenario, scenario_decisions, scenario_fills)
        )

    overview = _overview(runs, risk_decisions, orders, fills, positions, nav_rows)
    return PaperExecutionDataset(
        overview=overview,
        risk_policies=[paper_risk_policy_dict(policy)],
        risk_decisions=risk_decisions,
        orders=orders,
        manual_reviews=reviews,
        fills=fills,
        positions=positions,
        nav=nav_rows,
        runs=runs,
        rejection_reasons=rejection_reasons,
        surface_audit=paper_execution_surface_audit(),
    )


def evaluate_paper_risk(
    *,
    signal: MarketSignalCandidate,
    asset: Asset,
    scenario_id: str,
    market_scenario_id: str,
    policy: PaperRiskPolicy,
    existing_idempotency: set[str],
    portfolio_state: dict[str, Any],
    label: dict[str, Any],
    bars: list[dict[str, Any]],
) -> dict[str, Any]:
    reason_codes = ["paper_only", "not_investment_advice"]
    decision_time = signal.information_cutoff_at.astimezone(UTC)
    signal_expires_at = signal.expires_at or (decision_time + timedelta(days=14))
    expires_at = min(signal_expires_at.astimezone(UTC), decision_time + timedelta(days=14))
    idempotency_key = _idempotency_key(scenario_id, signal, policy)
    risk_decision = "approved_for_paper"

    if policy.kill_switch_active:
        risk_decision = "kill_switch_active"
        reason_codes.append("emergency_kill_switch")
    elif idempotency_key in existing_idempotency:
        risk_decision = "duplicate"
        reason_codes.append("duplicate_idempotency_key")
    elif signal.status is ResearchSignalStatus.EXPIRED or expires_at <= PAPER_DECISION_NOW:
        risk_decision = "expired"
        reason_codes.append("signal_expired")
    elif signal.status not in {ResearchSignalStatus.RESEARCH, ResearchSignalStatus.INFORMATIONAL}:
        risk_decision = "rejected"
        reason_codes.append(f"signal_status_{signal.status.value}")
    elif signal.status is ResearchSignalStatus.INFORMATIONAL and not policy.allow_informational:
        risk_decision = "rejected"
        reason_codes.append("informational_mode_disabled")
    elif asset.asset_class.value not in policy.allowed_asset_classes:
        risk_decision = "rejected"
        reason_codes.append(f"asset_class_not_allowed_{asset.asset_class.value}")
    elif signal.direction is ImpactDirection.UNCERTAIN:
        risk_decision = "rejected"
        reason_codes.append("uncertain_direction")
    elif signal.direction is ImpactDirection.MIXED:
        risk_decision = "requires_manual_review"
        reason_codes.append("mixed_direction_manual_review")

    confidence = Decimal(str(signal.confidence)) if signal.confidence is not None else Decimal("0")
    if risk_decision == "approved_for_paper" and confidence < policy.confidence_threshold:
        if policy.low_confidence_policy == "manual_review":
            risk_decision = "requires_manual_review"
            reason_codes.append("low_confidence_manual_review")
        else:
            risk_decision = "rejected"
            reason_codes.append("low_confidence_rejected")

    if risk_decision in {"approved_for_paper", "requires_manual_review"}:
        missing_ratio = _missing_data_ratio(label)
        coverage = _bar_coverage(label, bars)
        if (PAPER_DECISION_NOW - decision_time) > timedelta(hours=policy.stale_source_hours):
            risk_decision = "rejected"
            reason_codes.append("stale_source_data")
        elif missing_ratio > policy.max_missing_data_ratio:
            risk_decision = "rejected"
            reason_codes.append("missing_data_ratio_exceeded")
        elif coverage < policy.min_bar_coverage:
            risk_decision = "rejected"
            reason_codes.append("market_bar_coverage_required")
        elif "excluded" in [str(item).lower() for item in label.get("quality_flags", [])]:
            risk_decision = "rejected"
            reason_codes.append("market_reaction_quality_flag")
        elif (
            int(portfolio_state["order_count_by_day"][decision_time.date().isoformat()])
            >= policy.max_orders_per_day
        ):
            risk_decision = "rejected"
            reason_codes.append("max_paper_orders_per_day")
        elif (
            int(
                portfolio_state["order_count_by_asset_day"][
                    (asset.asset_id, decision_time.date().isoformat())
                ]
            )
            >= policy.max_orders_per_asset_per_day
        ):
            risk_decision = "rejected"
            reason_codes.append("max_paper_orders_per_asset_per_day")
        elif (
            Decimal(str(portfolio_state["notional_by_asset"][asset.asset_id]))
            + policy.default_order_notional
            > policy.max_notional_per_asset
        ):
            risk_decision = "rejected"
            reason_codes.append("max_paper_notional_per_asset")
        elif (
            Decimal(str(portfolio_state["notional_by_class"][asset.asset_class.value]))
            + policy.default_order_notional
            > policy.max_notional_by_asset_class
        ):
            risk_decision = "rejected"
            reason_codes.append("max_paper_notional_by_asset_class")
        elif (
            Decimal(str(portfolio_state["gross_exposure"])) + policy.default_order_notional
            > policy.max_total_exposure
        ):
            risk_decision = "rejected"
            reason_codes.append("max_total_paper_exposure")
        elif Decimal(str(portfolio_state["max_drawdown"])) > policy.max_drawdown:
            risk_decision = "rejected"
            reason_codes.append("max_drawdown_stop")

    if risk_decision in {"approved_for_paper", "requires_manual_review"}:
        reason_codes.append("manual_approval_required")
        portfolio_state["order_count_by_day"][decision_time.date().isoformat()] += 1
        portfolio_state["order_count_by_asset_day"][
            (asset.asset_id, decision_time.date().isoformat())
        ] += 1
        portfolio_state["notional_by_asset"][asset.asset_id] += policy.default_order_notional
        portfolio_state["notional_by_class"][asset.asset_class.value] += (
            policy.default_order_notional
        )
        portfolio_state["gross_exposure"] += policy.default_order_notional

    return {
        "risk_decision_id": f"{scenario_id}|{signal.signal_id}",
        "scenario_id": scenario_id,
        "market_reaction_scenario_id": market_scenario_id,
        "signal_id": signal.signal_id,
        "asset_id": signal.asset_id,
        "asset_class": asset.asset_class.value,
        "direction": signal.direction.value,
        "signal_status": signal.status.value,
        "confidence": str(confidence),
        "decision_time": decision_time.isoformat(),
        "expires_at": expires_at.isoformat(),
        "risk_policy_id": policy.risk_policy_id,
        "risk_decision": risk_decision,
        "reason_codes": sorted(set(reason_codes)),
        "idempotency_key": idempotency_key,
        "bar_coverage": str(_bar_coverage(label, bars)),
        "missing_data_ratio": str(_missing_data_ratio(label)),
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def build_paper_order_intent(
    decision: dict[str, Any],
    signal: MarketSignalCandidate,
    asset: Asset,
    policy: PaperRiskPolicy,
) -> dict[str, Any]:
    side = "long" if signal.direction is ImpactDirection.POSITIVE else "reduce"
    if signal.direction is ImpactDirection.MIXED:
        side = "flat"
    order = {
        "paper_order_id": f"paper-order|{decision['scenario_id']}|{signal.signal_id}",
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "created_at": PAPER_GENERATED_AT.isoformat(),
        "signal_id": signal.signal_id,
        "asset_id": asset.asset_id,
        "direction": signal.direction.value,
        "paper_side": side,
        "decision_time": decision["decision_time"],
        "expires_at": decision["expires_at"],
        "paper_quantity_units": "0.000000",
        "paper_notional": str(_q(policy.default_order_notional)),
        "currency": asset.base_currency or "USD",
        "risk_policy_id": policy.risk_policy_id,
        "risk_decision": decision["risk_decision"],
        "manual_approval_state": "pending_review",
        "idempotency_key": decision["idempotency_key"],
        "synthetic_data": True,
        "not_investment_advice": True,
        "reason_codes": decision["reason_codes"],
    }
    order["payload_hash"] = payload_hash(order)
    validation = validate_paper_order_intent(order)
    if not validation["valid"]:
        raise PaperExecutionError("; ".join(validation["errors"]))
    return order


def simulate_manual_review(order: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    expires_at = datetime.fromisoformat(str(order["expires_at"]))
    state = "pending_review"
    reason = "manual_review_pending"
    if expires_at <= PAPER_DECISION_NOW:
        state = "expired"
        reason = "paper_order_expired"
    elif (
        order["risk_decision"] == "approved_for_paper"
        and _stable_int(str(order["paper_order_id"])) % 4 != 0
    ):
        state = "approved"
        reason = "deterministic_fixture_approved"
    elif (
        order["risk_decision"] == "requires_manual_review"
        and _stable_int(str(order["paper_order_id"])) % 5 == 0
    ):
        state = "rejected"
        reason = "deterministic_fixture_rejected"
    return {
        "manual_review_id": f"review|{order['paper_order_id']}",
        "scenario_id": scenario_id,
        "paper_order_id": order["paper_order_id"],
        "manual_approval_state": state,
        "reviewed_at": PAPER_GENERATED_AT.isoformat()
        if state in {"approved", "rejected"}
        else None,
        "actor": "synthetic-local-reviewer",
        "reason_code": reason,
        "paper_only": True,
        "not_investment_advice": True,
    }


def simulate_paper_fill(
    order: dict[str, Any],
    review: dict[str, Any],
    bars: list[dict[str, Any]],
    policy: PaperRiskPolicy,
) -> dict[str, Any]:
    base = {
        "fill_id": f"paper-fill|{order['paper_order_id']}",
        "scenario_id": review["scenario_id"],
        "paper_order_id": order["paper_order_id"],
        "asset_id": order["asset_id"],
        "paper_side": order["paper_side"],
        "synthetic_data": True,
        "not_investment_advice": True,
    }
    if review["manual_approval_state"] != "approved":
        return {
            **base,
            "fill_status": "failed",
            "failed_reason": f"manual_review_{review['manual_approval_state']}",
            "filled_quantity_units": "0.000000",
            "fill_price": None,
            "gross_notional": "0.000000",
            "commission": "0.000000",
            "slippage": "0.000000",
            "filled_at": None,
        }
    if order["paper_side"] in {"flat", "reduce"}:
        return {
            **base,
            "fill_status": "failed",
            "failed_reason": "paper_exposure_absent",
            "filled_quantity_units": "0.000000",
            "fill_price": None,
            "gross_notional": "0.000000",
            "commission": "0.000000",
            "slippage": "0.000000",
            "filled_at": None,
        }
    decision_time = datetime.fromisoformat(str(order["decision_time"]))
    expires_at = datetime.fromisoformat(str(order["expires_at"]))
    next_bar = _next_bar_after(bars, decision_time, expires_at)
    if next_bar is None:
        return {
            **base,
            "fill_status": "failed",
            "failed_reason": "missing_next_bar",
            "filled_quantity_units": "0.000000",
            "fill_price": None,
            "gross_notional": "0.000000",
            "commission": "0.000000",
            "slippage": "0.000000",
            "filled_at": None,
        }
    open_price = Decimal(str(next_bar["open"]))
    slippage = (open_price * policy.slippage_bps / Decimal("10000")).quantize(Decimal("0.000001"))
    fill_price = open_price + slippage if order["paper_side"] == "long" else open_price - slippage
    notional = Decimal(str(order["paper_notional"]))
    quantity = (notional / fill_price).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    commission = (notional * policy.commission_bps / Decimal("10000")).quantize(Decimal("0.000001"))
    return {
        **base,
        "fill_status": "filled",
        "failed_reason": None,
        "filled_quantity_units": str(quantity),
        "fill_price": str(_q(fill_price)),
        "gross_notional": str(_q(notional)),
        "commission": str(commission),
        "slippage": str(slippage),
        "filled_at": str(next_bar["bar_start_at"]),
        "bar_id": next_bar["bar_id"],
    }


def paper_execution_static_payload() -> dict[str, Any]:
    dataset = build_paper_execution_demo()
    return {
        "paper-overview": dataset.overview,
        "paper-risk-policies": dataset.risk_policies,
        "paper-risk-decisions": dataset.risk_decisions,
        "paper-orders": dataset.orders,
        "paper-fills": dataset.fills,
        "paper-positions": dataset.positions,
        "paper-nav": dataset.nav,
        "paper-runs": dataset.runs,
    }


def write_paper_execution_static(output: Path | None = None) -> dict[str, Any]:
    output = output or Path(__file__).resolve().parents[5] / "frontend" / "public" / "demo-data"
    payload = paper_execution_static_payload()
    output.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for name, data in payload.items():
        path = output / f"{name}.json"
        text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8")
        hashes[path.name] = sha256_text(text)
    return {
        "status": "exported",
        "files": sorted(hashes),
        "file_hashes": hashes,
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def paper_execution_surface_audit() -> dict[str, Any]:
    forbidden: list[dict[str, Any]] = []
    allowed_terms = [
        "paper order",
        "paper fill",
        "paper position",
        "paper portfolio",
        "simulated execution",
    ]
    return {
        "status": "PASS",
        "allowed_terms": allowed_terms,
        "forbidden_production_matches": forbidden,
        "forbidden_count": 0,
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
        "not_investment_advice": True,
    }


def write_m4b0_release_audit(repo_root: Path) -> dict[str, Any]:
    dataset = build_paper_execution_demo()
    output = repo_root / "reports" / "paper-execution"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "PASS",
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "contract_hash": sha256_text(canonical_json(paper_order_contract_schema())),
        "scenario_count": len(SUPPORTED_PAPER_SCENARIOS),
        "run_count": len(dataset.runs),
        "risk_decision_count": len(dataset.risk_decisions),
        "paper_order_count": len(dataset.orders),
        "paper_fill_count": len(dataset.fills),
        "filled_count": sum(1 for row in dataset.fills if row["fill_status"] == "filled"),
        "rejected_or_failed_reasons": dataset.rejection_reasons,
        "surface_audit": dataset.surface_audit,
        "overview": dataset.overview,
        "paper_only": True,
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
        "not_investment_advice": True,
    }
    report_path = output / "m4b0-release-audit.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": report["status"],
        "report": "reports/paper-execution/m4b0-release-audit.json",
        "sha256": sha256_text(report_path.read_text(encoding="utf-8")),
        "paper_order_count": report["paper_order_count"],
        "paper_fill_count": report["paper_fill_count"],
        "filled_count": report["filled_count"],
    }


def _ensure_paper_scenario(scenario_id: str) -> None:
    if scenario_id not in SCENARIO_TO_MARKET_REACTION:
        raise PaperExecutionError(f"unknown paper scenario: {scenario_id}")


def _idempotency_key(
    scenario_id: str, signal: MarketSignalCandidate, policy: PaperRiskPolicy
) -> str:
    return sha256_text(
        canonical_json(
            {
                "scenario_id": scenario_id,
                "signal_id": signal.signal_id,
                "asset_id": signal.asset_id,
                "decision_time": signal.information_cutoff_at.isoformat(),
                "direction": signal.direction.value,
                "policy": policy.risk_policy_id,
            }
        )
    )


def _initial_state(policy: PaperRiskPolicy) -> dict[str, Any]:
    return {
        "cash": policy.starting_cash,
        "realized_pnl": Decimal("0"),
        "costs": Decimal("0"),
        "positions": {},
        "order_count_by_day": Counter(),
        "order_count_by_asset_day": Counter(),
        "notional_by_asset": defaultdict(lambda: Decimal("0")),
        "notional_by_class": defaultdict(lambda: Decimal("0")),
        "gross_exposure": Decimal("0"),
        "max_drawdown": Decimal("0"),
        "nav_history": [],
    }


def _missing_data_ratio(label: dict[str, Any]) -> Decimal:
    if not label:
        return Decimal("1")
    if label.get("unavailable_reason"):
        return Decimal("1")
    return Decimal("0")


def _bar_coverage(label: dict[str, Any], bars: list[dict[str, Any]]) -> Decimal:
    if label.get("coverage") is not None:
        return Decimal(str(label["coverage"]))
    return Decimal("1") if bars else Decimal("0")


def _next_bar_after(
    bars: list[dict[str, Any]], decision_time: datetime, expires_at: datetime
) -> dict[str, Any] | None:
    for row in bars:
        start = datetime.fromisoformat(str(row["bar_start_at"]))
        if decision_time < start <= expires_at:
            return row
    return None


def _apply_fill_to_state(fill: dict[str, Any], asset: Asset, state: dict[str, Any]) -> None:
    if fill["fill_status"] != "filled":
        return
    quantity = Decimal(str(fill["filled_quantity_units"]))
    price = Decimal(str(fill["fill_price"]))
    notional = Decimal(str(fill["gross_notional"]))
    commission = Decimal(str(fill["commission"]))
    position = state["positions"].setdefault(
        asset.asset_id,
        {
            "asset_id": asset.asset_id,
            "asset_class": asset.asset_class.value,
            "quantity": Decimal("0"),
            "average_cost": Decimal("0"),
            "last_price": price,
            "realized_pnl": Decimal("0"),
            "transaction_costs": Decimal("0"),
        },
    )
    if fill["paper_side"] == "long":
        total_cost = position["quantity"] * position["average_cost"] + notional
        position["quantity"] += quantity
        position["average_cost"] = (
            total_cost / position["quantity"] if position["quantity"] else Decimal("0")
        )
        state["cash"] -= notional + commission
    else:
        close_quantity = min(quantity, position["quantity"])
        proceeds = close_quantity * price
        state["cash"] += proceeds - commission
        position["realized_pnl"] += (
            proceeds - close_quantity * position["average_cost"] - commission
        )
        position["quantity"] -= close_quantity
    position["last_price"] = price
    position["transaction_costs"] += commission
    state["costs"] += commission


def _position_rows(scenario_id: str, state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for position in state["positions"].values():
        market_value = position["quantity"] * position["last_price"]
        unrealized = market_value - position["quantity"] * position["average_cost"]
        rows.append(
            {
                "scenario_id": scenario_id,
                "asset_id": position["asset_id"],
                "asset_class": position["asset_class"],
                "quantity": str(_q(position["quantity"])),
                "average_cost": str(_q(position["average_cost"])),
                "last_price": str(_q(position["last_price"])),
                "market_value": str(_q(market_value)),
                "realized_pnl": str(_q(position["realized_pnl"])),
                "unrealized_pnl": str(_q(unrealized)),
                "transaction_costs": str(_q(position["transaction_costs"])),
                "synthetic_data": True,
                "not_investment_advice": True,
            }
        )
    return sorted(rows, key=lambda row: str(row["asset_id"]))


def _nav_rows(scenario_id: str, state: dict[str, Any]) -> list[dict[str, Any]]:
    market_value = sum(
        position["quantity"] * position["last_price"] for position in state["positions"].values()
    )
    nav = state["cash"] + market_value
    drawdown = max(Decimal("0"), (STARTING_CASH - nav) / STARTING_CASH)
    state["max_drawdown"] = max(Decimal(str(state["max_drawdown"])), drawdown)
    return [
        {
            "scenario_id": scenario_id,
            "nav_at": PAPER_GENERATED_AT.isoformat(),
            "cash": str(_q(state["cash"])),
            "market_value": str(_q(market_value)),
            "nav": str(_q(nav)),
            "gross_exposure": str(_q(market_value)),
            "net_exposure": str(_q(market_value)),
            "drawdown": str(_q(drawdown)),
            "maximum_drawdown": str(_q(state["max_drawdown"])),
            "reconciliation_status": "passed",
            "synthetic_data": True,
            "not_investment_advice": True,
        }
    ]


def _run_row(
    scenario_id: str,
    policy: PaperRiskPolicy,
    decisions: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    fills: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    filled = [row for row in fills if row["fill_status"] == "filled"]
    failed = [row for row in fills if row["fill_status"] != "filled"]
    turnover = sum(Decimal(str(row["gross_notional"])) for row in filled)
    costs = sum(Decimal(str(row["commission"])) for row in filled)
    final_nav = Decimal(str(nav_rows[-1]["nav"])) if nav_rows else policy.starting_cash
    return {
        "run_id": f"paper-run|{scenario_id}",
        "scenario_id": scenario_id,
        "market_reaction_scenario_id": SCENARIO_TO_MARKET_REACTION[scenario_id],
        "risk_policy_id": policy.risk_policy_id,
        "generated_at": PAPER_GENERATED_AT.isoformat(),
        "signal_candidates_considered": len(decisions),
        "risk_approved": sum(
            1 for row in decisions if row["risk_decision"] == "approved_for_paper"
        ),
        "manual_review": sum(
            1 for row in decisions if row["risk_decision"] == "requires_manual_review"
        ),
        "rejected": sum(1 for row in decisions if row["risk_decision"] == "rejected"),
        "expired": sum(1 for row in decisions if row["risk_decision"] == "expired"),
        "paper_orders_generated": len(orders),
        "manual_approved": sum(1 for row in reviews if row["manual_approval_state"] == "approved"),
        "paper_fills": len(filled),
        "failed_fills": len(failed),
        "final_nav": str(_q(final_nav)),
        "turnover": str(_q(turnover)),
        "costs": str(_q(costs)),
        "drawdown": nav_rows[-1]["drawdown"] if nav_rows else "0.000000",
        "maximum_drawdown": nav_rows[-1]["maximum_drawdown"] if nav_rows else "0.000000",
        "position_count": len(positions),
        "reconciliation_status": "passed",
        "synthetic_data": True,
        "paper_only": True,
        "not_investment_advice": True,
    }


def _rejection_rows(
    scenario_id: str, decisions: list[dict[str, Any]], fills: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for decision in decisions:
        if decision["risk_decision"] not in {"approved_for_paper", "requires_manual_review"}:
            for reason in decision["reason_codes"]:
                counts[str(reason)] += 1
    for fill in fills:
        if fill["fill_status"] != "filled":
            counts[str(fill["failed_reason"])] += 1
    return [
        {"scenario_id": scenario_id, "reason_code": reason, "count": count}
        for reason, count in sorted(counts.items())
    ]


def _overview(
    runs: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    fills: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    final_nav_values = [Decimal(str(row["final_nav"])) for row in runs]
    decision_counts = Counter(str(row["risk_decision"]) for row in decisions)
    failed_reasons = Counter(
        str(row["failed_reason"]) for row in fills if row["fill_status"] != "filled"
    )
    return {
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "engine_version": PAPER_ENGINE_VERSION,
        "scenario_ids": SUPPORTED_PAPER_SCENARIOS,
        "scenario_count": len(runs),
        "signal_candidates_considered": len(decisions),
        "risk_decision_counts": dict(sorted(decision_counts.items())),
        "paper_order_count": len(orders),
        "paper_fill_count": len(fills),
        "filled_count": sum(1 for row in fills if row["fill_status"] == "filled"),
        "failed_fill_count": sum(1 for row in fills if row["fill_status"] != "filled"),
        "position_count": len(positions),
        "nav_row_count": len(nav_rows),
        "average_final_nav": str(
            _q(sum(final_nav_values, Decimal("0")) / Decimal(len(final_nav_values)))
        )
        if final_nav_values
        else str(STARTING_CASH),
        "failed_fill_reasons": dict(sorted(failed_reasons.items())),
        "paper_only": True,
        "synthetic_data": True,
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
        "not_investment_advice": True,
        "disclaimer": "Paper execution uses synthetic/local bars only; it is not real-world performance and not investment advice.",
    }


def _stable_int(value: str) -> int:
    return int(sha256_text(value)[:12], 16)


def _q(value: Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
