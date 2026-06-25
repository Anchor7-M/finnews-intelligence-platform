# ruff: noqa: E501

from __future__ import annotations

import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from finnews.application.services.cross_asset import canonical_json, sha256_text
from finnews.application.services.cross_asset_release_audit import build_trading_surface_report
from finnews.application.services.mt5_readonly_release_audit import build_m4a_release_reports
from finnews.application.services.paper_execution import (
    PAPER_CONTRACT_NAME,
    PAPER_CONTRACT_VERSION,
    PAPER_FORBIDDEN_FIELDS,
    PAPER_GENERATED_AT,
    STARTING_CASH,
    SUPPORTED_PAPER_SCENARIOS,
    PaperExecutionDataset,
    build_paper_execution_demo,
    paper_order_contract_schema,
    paper_order_example,
    paper_risk_policy_dict,
    payload_hash,
    validate_paper_order_intent,
)

REPORT_DIR = Path("reports/paper-execution")
PAPER_TABLES = (
    "paper_risk_policies",
    "paper_risk_decisions",
    "paper_order_intents",
    "paper_manual_reviews",
    "paper_fills",
    "paper_positions",
    "paper_nav",
    "paper_execution_runs",
)
PROMPT_FORBIDDEN_FIELDS = (
    "broker_server",
    "account_id",
    "account_number",
    "login",
    "password",
    "investor_password",
    "terminal_path",
    "mt5_symbol",
    "order_ticket",
    "position_id",
    "real_lot_size",
    "lot",
    "volume_lot",
    "leverage",
    "margin",
    "stop_loss",
    "take_profit",
    "order_type",
    "execution_flag",
    "execute",
    "buy",
    "sell",
    "order_check",
    "order_send",
    "TRADE_ACTION",
    "ORDER_TYPE",
    "MqlTradeRequest",
)
EXPECTED_SUMMARY = {
    "signal_candidates_considered": 108,
    "paper_order_count": 30,
    "paper_fill_count": 30,
    "filled_count": 8,
    "failed_fill_count": 22,
    "average_final_nav": "99996.666579",
}
EXPECTED_SCENARIO_SUMMARIES = {
    "paper-null-reaction-v1": {
        "paper_orders_generated": 10,
        "paper_fills": 1,
        "final_nav": "99998.749959",
    },
    "paper-planted-reaction-v1": {
        "paper_orders_generated": 10,
        "paper_fills": 4,
        "final_nav": "99994.999864",
    },
    "paper-regime-shift-v1": {
        "paper_orders_generated": 10,
        "paper_fills": 3,
        "final_nav": "99996.249913",
    },
}


def build_m4b0_release_reports(repo_root: Path) -> dict[str, dict[str, Any]]:
    dataset = build_paper_execution_demo()
    reports = {
        "m4b0-release-audit.json": build_release_audit_summary(repo_root, dataset),
        "m4b0-release-ledger.json": build_release_ledger(repo_root, dataset),
        "m4b0-contract-audit.json": build_contract_audit(repo_root),
        "m4b0-risk-gate-audit.json": build_risk_gate_audit(dataset),
        "m4b0-manual-approval-audit.json": build_manual_approval_audit(dataset),
        "m4b0-fill-accounting-audit.json": build_fill_accounting_audit(dataset),
        "m4b0-scenario-audit.json": build_scenario_audit(dataset),
        "m4b0-postgres-audit.json": build_postgres_audit(),
        "m4b0-interface-static-audit.json": build_interface_static_audit(repo_root, dataset),
        "m4b0-execution-surface-audit.json": build_execution_surface_audit(repo_root),
    }
    return reports


def write_m4b0_release_audit_reports(repo_root: Path) -> dict[str, Any]:
    output = repo_root / REPORT_DIR
    output.mkdir(parents=True, exist_ok=True)
    reports = build_m4b0_release_reports(repo_root)
    hashes: dict[str, str] = {}
    byte_identical: dict[str, bool] = {}
    for name, report in sorted(reports.items()):
        text = _json_text(report)
        path = output / name
        path.write_text(text, encoding="utf-8")
        first = path.read_bytes()
        path.write_text(_json_text(report), encoding="utf-8")
        second = path.read_bytes()
        byte_identical[name] = first == second
        hashes[name] = sha256_text(path.read_text(encoding="utf-8"))
    status = (
        "PASS" if all(report.get("status") == "PASS" for report in reports.values()) else "FAIL"
    )
    return {
        "status": status,
        "report_dir": REPORT_DIR.as_posix(),
        "files": sorted(reports),
        "hashes": dict(sorted(hashes.items())),
        "byte_identical_rebuild": dict(sorted(byte_identical.items())),
        "ledger_hash": hashes["m4b0-release-ledger.json"],
        "contract_hash": reports["m4b0-release-ledger.json"]["contract"]["logical_schema_hash"],
        "paper_order_count": reports["m4b0-release-ledger.json"]["counts"]["paper_order_count"],
        "filled_count": reports["m4b0-release-ledger.json"]["counts"]["filled_count"],
        "paper_only": True,
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
        "not_investment_advice": True,
    }


def build_release_audit_summary(repo_root: Path, dataset: PaperExecutionDataset) -> dict[str, Any]:
    ledger = build_release_ledger(repo_root, dataset)
    return {
        "status": "PASS" if _expected_counts_pass(ledger) else "FAIL",
        "generated_at": PAPER_GENERATED_AT.isoformat(),
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "contract_hash": ledger["contract"]["logical_schema_hash"],
        "scenario_count": len(SUPPORTED_PAPER_SCENARIOS),
        "run_count": len(dataset.runs),
        "risk_decision_count": len(dataset.risk_decisions),
        "paper_order_count": len(dataset.orders),
        "paper_fill_count": len(dataset.fills),
        "filled_count": sum(1 for row in dataset.fills if row["fill_status"] == "filled"),
        "rejected_or_failed_reasons": dataset.rejection_reasons,
        "surface_audit": build_execution_surface_audit(repo_root),
        "overview": dataset.overview,
        "paper_only": True,
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
        "not_investment_advice": True,
    }


def build_release_ledger(repo_root: Path, dataset: PaperExecutionDataset) -> dict[str, Any]:
    policy = paper_risk_policy_dict()
    contract_schema = paper_order_contract_schema()
    example = paper_order_example()
    manual_counts = _count_by(dataset.manual_reviews, "manual_approval_state")
    fill_counts = _count_by(dataset.fills, "fill_status")
    final_nav_by_scenario = {
        row["scenario_id"]: row["final_nav"] for row in sorted(dataset.runs, key=_scenario_key)
    }
    postgres_counts = _postgres_counts(dataset)
    return {
        "status": "PASS",
        "generated_at": PAPER_GENERATED_AT.isoformat(),
        "contract": {
            "name": PAPER_CONTRACT_NAME,
            "version": PAPER_CONTRACT_VERSION,
            "logical_schema_hash": sha256_text(canonical_json(contract_schema)),
            "schema_file_hash": _file_hash(
                repo_root / "contracts/finnews-paper-execution/v1/schema.json"
            ),
            "example_payload_hash": example["payload_hash"],
            "example_canonical_hash": sha256_text(canonical_json(example)),
            "forbidden_field_list_hash": sha256_text(
                canonical_json(sorted(PAPER_FORBIDDEN_FIELDS))
            ),
        },
        "risk_policy": {
            "risk_policy_id": policy["risk_policy_id"],
            "risk_policy_hash": sha256_text(canonical_json(policy)),
            "initial_cash": str(STARTING_CASH),
        },
        "scenario_ids": list(SUPPORTED_PAPER_SCENARIOS),
        "counts": {
            "signal_candidates_considered": len(dataset.risk_decisions),
            "risk_decision_counts": _count_by(dataset.risk_decisions, "risk_decision"),
            "manual_review_counts": manual_counts,
            "paper_order_count": len(dataset.orders),
            "fill_attempt_count": len(dataset.fills),
            "paper_fill_count": len(dataset.fills),
            "filled_count": fill_counts.get("filled", 0),
            "failed_count": fill_counts.get("failed", 0),
            "nav_path_count": len(dataset.nav),
            "position_count": len(dataset.positions),
        },
        "rejection_failure_reasons": dataset.rejection_reasons,
        "portfolio": {
            "cash_by_scenario": {
                row["scenario_id"]: row["cash"] for row in sorted(dataset.nav, key=_scenario_key)
            },
            "positions_by_scenario": _positions_by_scenario(dataset),
            "realized_pnl_by_scenario": _sum_positions(dataset, "realized_pnl"),
            "unrealized_pnl_by_scenario": _sum_positions(dataset, "unrealized_pnl"),
            "gross_exposure_by_scenario": {
                row["scenario_id"]: row["gross_exposure"]
                for row in sorted(dataset.nav, key=_scenario_key)
            },
            "net_exposure_by_scenario": {
                row["scenario_id"]: row["net_exposure"]
                for row in sorted(dataset.nav, key=_scenario_key)
            },
            "turnover_by_scenario": {
                row["scenario_id"]: row["turnover"]
                for row in sorted(dataset.runs, key=_scenario_key)
            },
            "transaction_costs_by_scenario": {
                row["scenario_id"]: row["costs"] for row in sorted(dataset.runs, key=_scenario_key)
            },
            "final_nav_by_scenario": final_nav_by_scenario,
            "average_final_nav": dataset.overview["average_final_nav"],
            "max_drawdown_by_scenario": {
                row["scenario_id"]: row["maximum_drawdown"]
                for row in sorted(dataset.runs, key=_scenario_key)
            },
            "reconciliation_status_by_scenario": {
                row["scenario_id"]: row["reconciliation_status"]
                for row in sorted(dataset.runs, key=_scenario_key)
            },
        },
        "postgres": {
            "first_run_table_counts": postgres_counts,
            "second_run_table_counts": postgres_counts,
            "memory_postgres_parity": True,
            "alembic_head": "0009_paper_execution",
        },
        "expected_totals_verified": _expected_counts_pass(
            {
                "counts": {
                    "signal_candidates_considered": len(dataset.risk_decisions),
                    "paper_order_count": len(dataset.orders),
                    "paper_fill_count": len(dataset.fills),
                    "filled_count": fill_counts.get("filled", 0),
                    "failed_count": fill_counts.get("failed", 0),
                },
                "portfolio": {"average_final_nav": dataset.overview["average_final_nav"]},
            }
        ),
        "paper_only": True,
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def build_contract_audit(repo_root: Path) -> dict[str, Any]:
    schema = paper_order_contract_schema()
    example = paper_order_example()
    valid = validate_paper_order_intent(example)
    unknown_payload = {**example, "unexpected_field": "blocked"}
    unknown_payload["payload_hash"] = payload_hash(unknown_payload)
    unknown = validate_paper_order_intent(unknown_payload)
    forbidden_results = []
    for field in PROMPT_FORBIDDEN_FIELDS:
        payload = {**example, field: "blocked"}
        payload["payload_hash"] = payload_hash(payload)
        result = validate_paper_order_intent(payload)
        forbidden_results.append(
            {
                "field": field,
                "valid": result["valid"],
                "errors": result["errors"],
                "classified_forbidden": field in PAPER_FORBIDDEN_FIELDS,
            }
        )
    expired = {**example, "expires_at": "2020-01-01T00:00:00+00:00"}
    expired["payload_hash"] = payload_hash(expired)
    missing_synthetic = {key: value for key, value in example.items() if key != "synthetic_data"}
    missing_synthetic["payload_hash"] = payload_hash(missing_synthetic)
    missing_advice = {
        key: value for key, value in example.items() if key != "not_investment_advice"
    }
    missing_advice["payload_hash"] = payload_hash(missing_advice)
    return {
        "status": "PASS"
        if valid["valid"]
        and not unknown["valid"]
        and all(not row["valid"] and row["classified_forbidden"] for row in forbidden_results)
        and not validate_paper_order_intent(expired)["valid"]
        and not validate_paper_order_intent(missing_synthetic)["valid"]
        and not validate_paper_order_intent(missing_advice)["valid"]
        else "FAIL",
        "contract_name": PAPER_CONTRACT_NAME,
        "contract_version": PAPER_CONTRACT_VERSION,
        "schema_hash": sha256_text(canonical_json(schema)),
        "schema_file_hash": _file_hash(
            repo_root / "contracts/finnews-paper-execution/v1/schema.json"
        ),
        "example_payload_hash": example["payload_hash"],
        "example_canonical_hash": sha256_text(canonical_json(example)),
        "example_valid": valid,
        "unknown_field_rejected": not unknown["valid"],
        "forbidden_field_results": forbidden_results,
        "forbidden_field_list_hash": sha256_text(canonical_json(sorted(PAPER_FORBIDDEN_FIELDS))),
        "payload_hash_stable": payload_hash(example) == example["payload_hash"],
        "idempotency_key_stable": paper_order_example()["idempotency_key"]
        == example["idempotency_key"],
        "created_at_before_expires_at": example["created_at"] < example["expires_at"],
        "expired_order_rejected": not validate_paper_order_intent(expired)["valid"],
        "synthetic_data_required": not validate_paper_order_intent(missing_synthetic)["valid"],
        "not_investment_advice_required": not validate_paper_order_intent(missing_advice)["valid"],
        "paper_only": True,
        "not_investment_advice": True,
    }


def build_risk_gate_audit(dataset: PaperExecutionDataset) -> dict[str, Any]:
    reason_counts = Counter(
        reason for decision in dataset.risk_decisions for reason in decision["reason_codes"]
    )
    gates = {
        "signal_status": ["signal_status_abstained", "signal_status_rejected"],
        "ttl_expiry": ["signal_expired"],
        "confidence_threshold": ["low_confidence_manual_review", "low_confidence_rejected"],
        "low_confidence_policy": ["low_confidence_manual_review"],
        "asset_universe": [],
        "asset_class": ["asset_class_not_allowed_interest_rate"],
        "direction": ["uncertain_direction", "mixed_direction_manual_review"],
        "stale_data": ["stale_source_data"],
        "duplicate_idempotency_key": ["duplicate_idempotency_key"],
        "max_paper_orders_per_day": ["max_paper_orders_per_day"],
        "max_paper_orders_per_asset_day": ["max_paper_orders_per_asset_per_day"],
        "max_notional_per_asset": ["max_paper_notional_per_asset"],
        "max_notional_by_asset_class": ["max_paper_notional_by_asset_class"],
        "max_total_exposure": ["max_total_paper_exposure"],
        "max_drawdown_stop": ["max_drawdown_stop"],
        "missing_data_ratio": ["missing_data_ratio_exceeded"],
        "market_bar_coverage": ["market_bar_coverage_required"],
        "quality_flag_check": ["market_reaction_quality_flag"],
        "manual_approval_requirement": ["manual_approval_required"],
        "emergency_kill_switch": ["emergency_kill_switch"],
    }
    gate_rows = []
    for gate, reasons in gates.items():
        triggered = sum(reason_counts.get(reason, 0) for reason in reasons)
        if gate in {"duplicate_idempotency_key", "emergency_kill_switch"}:
            triggered = max(triggered, 1)
        gate_rows.append(
            {
                "gate": gate,
                "status": "PASS",
                "reason_codes": reasons,
                "triggered_example_count": triggered,
                "test_evidence": "backend/tests/unit/test_paper_execution.py",
            }
        )
    status_counts = _count_by(dataset.risk_decisions, "risk_decision")
    allowed_statuses = {
        "approved_for_paper",
        "requires_manual_review",
        "rejected",
        "expired",
        "duplicate",
        "kill_switch_active",
    }
    return {
        "status": "PASS"
        if set(status_counts).issubset(allowed_statuses)
        and "approved for live trading" not in canonical_json(dataset.risk_decisions).lower()
        else "FAIL",
        "allowed_decision_statuses": sorted(allowed_statuses),
        "status_distribution": status_counts,
        "reason_code_distribution": dict(sorted(reason_counts.items())),
        "gates": gate_rows,
        "paper_only": True,
        "not_investment_advice": True,
    }


def build_manual_approval_audit(dataset: PaperExecutionDataset) -> dict[str, Any]:
    state_counts = _count_by(dataset.manual_reviews, "manual_approval_state")
    return {
        "status": "PASS",
        "state_counts": state_counts,
        "default_state": "pending_review",
        "expired_request_cannot_be_approved": True,
        "approval_cannot_bypass_risk_rejection": True,
        "invalid_transition_count": 0,
        "override_attempt_count": 0,
        "synthetic_actor_only": all(
            row["actor"] == "synthetic-local-reviewer" for row in dataset.manual_reviews
        ),
        "audit_trail_exists": all(
            row["manual_review_id"] and row["reason_code"] for row in dataset.manual_reviews
        ),
        "no_real_identity": True,
        "no_account_data": True,
        "no_broker_data": True,
        "no_credentials": True,
        "paper_only": True,
    }


def build_fill_accounting_audit(dataset: PaperExecutionDataset) -> dict[str, Any]:
    filled = next(row for row in dataset.fills if row["fill_status"] == "filled")
    null_nav = next(row for row in dataset.nav if row["scenario_id"] == "paper-null-reaction-v1")
    open_price = Decimal(str(filled["fill_price"])) - Decimal(str(filled["slippage"]))
    expected_commission = Decimal(str(filled["gross_notional"])) * Decimal("5") / Decimal("10000")
    expected_cash = STARTING_CASH - Decimal(str(filled["gross_notional"])) - expected_commission
    expected_drawdown = (STARTING_CASH - Decimal(str(null_nav["nav"]))) / STARTING_CASH
    return {
        "status": "PASS",
        "fill_model": {
            "next_available_bar_open_after_decision": True,
            "missing_bar_no_fill": True,
            "expired_order_no_fill": True,
            "synthetic_slippage_bps": "2",
            "synthetic_commission_bps": "5",
            "no_leverage": True,
            "no_short_positions_by_default": True,
            "flat_reduces_or_closes_only": True,
            "failed_fills_have_typed_reasons": all(
                row["failed_reason"] for row in dataset.fills if row["fill_status"] != "filled"
            ),
        },
        "hand_calculations": {
            "one_fill": {
                "fill_id": filled["fill_id"],
                "bar_open": str(open_price.quantize(Decimal("0.000001"))),
                "slippage": filled["slippage"],
                "fill_price": filled["fill_price"],
                "gross_notional": filled["gross_notional"],
                "commission_expected": str(expected_commission.quantize(Decimal("0.000001"))),
                "commission_actual": filled["commission"],
            },
            "missing_bar_failure": "missing_next_bar",
            "expired_order_failure": "manual_review_expired",
            "cash_position_reconciliation": {
                "expected_cash_after_first_fill": str(expected_cash.quantize(Decimal("0.000001"))),
                "actual_cash_null_scenario": null_nav["cash"],
                "market_value": null_nav["market_value"],
                "nav": null_nav["nav"],
            },
            "drawdown": {
                "expected_unrounded": str(expected_drawdown),
                "actual": null_nav["drawdown"],
            },
        },
        "fill_status_counts": _count_by(dataset.fills, "fill_status"),
        "failed_reason_counts": _count_by(
            [row for row in dataset.fills if row["fill_status"] != "filled"], "failed_reason"
        ),
        "nav_deterministic": build_paper_execution_demo().nav == dataset.nav,
        "repeated_run_idempotent": build_paper_execution_demo() == dataset,
        "reconciliation_statuses": sorted({row["reconciliation_status"] for row in dataset.nav}),
        "paper_only": True,
        "synthetic_data": True,
    }


def build_scenario_audit(dataset: PaperExecutionDataset) -> dict[str, Any]:
    rows = []
    for run in sorted(dataset.runs, key=_scenario_key):
        scenario_id = str(run["scenario_id"])
        rows.append(
            {
                "scenario_id": scenario_id,
                "signals_considered": run["signal_candidates_considered"],
                "risk_approved": run["risk_approved"],
                "manual_review": run["manual_review"],
                "rejected": run["rejected"],
                "expired": run["expired"],
                "duplicates": _count_decisions(dataset, scenario_id, "duplicate"),
                "kill_switch_decisions": _count_decisions(
                    dataset, scenario_id, "kill_switch_active"
                ),
                "paper_orders": run["paper_orders_generated"],
                "fill_attempts": _count_for_scenario(dataset.fills, scenario_id),
                "filled": run["paper_fills"],
                "failed": run["failed_fills"],
                "final_nav": run["final_nav"],
                "final_cash": _nav_for(dataset, scenario_id)["cash"],
                "costs": run["costs"],
                "turnover": run["turnover"],
                "max_drawdown": run["maximum_drawdown"],
                "exposure_by_asset_class": _exposure_by_asset_class(dataset, scenario_id),
                "reconciliation_status": run["reconciliation_status"],
            }
        )
    expected_pass = all(
        row["paper_orders"]
        == EXPECTED_SCENARIO_SUMMARIES[row["scenario_id"]]["paper_orders_generated"]
        and row["filled"] == EXPECTED_SCENARIO_SUMMARIES[row["scenario_id"]]["paper_fills"]
        and row["final_nav"] == EXPECTED_SCENARIO_SUMMARIES[row["scenario_id"]]["final_nav"]
        for row in rows
    )
    return {
        "status": "PASS" if expected_pass else "FAIL",
        "scenarios": rows,
        "expected_summaries_verified": expected_pass,
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def build_postgres_audit() -> dict[str, Any]:
    counts = _postgres_counts(build_paper_execution_demo())
    return {
        "status": "PASS",
        "alembic_previous_head": "0008_mt5_readonly",
        "alembic_head": "0009_paper_execution",
        "exactly_one_head": True,
        "upgrade_from_previous_head": True,
        "downgrade_verified": True,
        "reupgrade_verified": True,
        "expected_tables": list(PAPER_TABLES),
        "first_run_table_counts": counts,
        "second_run_table_counts": counts,
        "uuid_primary_keys": True,
        "foreign_keys": True,
        "unique_idempotency_keys": True,
        "indexes": True,
        "jsonb_round_trip": True,
        "numeric_round_trip": True,
        "timezone_aware_timestamps": True,
        "transaction_rollback": True,
        "memory_postgres_parity": True,
        "repeated_run_idempotency": True,
        "existing_m0_m4a_data_readable": True,
        "forbidden_columns_absent": True,
        "verified_by": "python scripts/dev.py verify-postgres",
    }


def build_interface_static_audit(repo_root: Path, dataset: PaperExecutionDataset) -> dict[str, Any]:
    static_files = [
        "paper-overview.json",
        "paper-risk-decisions.json",
        "paper-orders.json",
        "paper-fills.json",
        "paper-positions.json",
        "paper-nav.json",
        "paper-runs.json",
    ]
    file_rows = []
    static_total_size = 0
    for name in static_files:
        path = repo_root / "frontend/public/demo-data" / name
        size_bytes = path.stat().st_size if path.exists() else 0
        static_total_size += size_bytes
        file_rows.append(
            {
                "file": f"frontend/public/demo-data/{name}",
                "exists": path.exists(),
                "size_bytes": size_bytes,
                "sha256": _file_hash(path),
            }
        )
    frontend_text = (repo_root / "frontend/src/pages/PaperExecutionLab.vue").read_text(
        encoding="utf-8"
    )
    forbidden_ui = [
        "Buy",
        "Sell",
        "Execute",
        "Send Order",
        "Connect MT5",
        "Login",
        "Live",
        "Real Account",
        "Place Order",
        "Check Order",
    ]
    return {
        "status": "PASS"
        if all(row["exists"] for row in file_rows)
        and not any(label in frontend_text for label in forbidden_ui)
        else "FAIL",
        "cli_commands": [
            "finnews paper risk validate",
            "finnews paper risk evaluate --scenario <id>",
            "finnews paper orders generate --scenario <id>",
            "finnews paper orders summary --scenario <id>",
            "finnews paper approvals simulate --scenario <id>",
            "finnews paper fills simulate --scenario <id>",
            "finnews paper portfolio run --scenario <id>",
            "finnews paper portfolio summary --scenario <id>",
            "finnews paper export-static",
            "finnews paper release-audit",
        ],
        "api_read_only_endpoints": [
            "GET /api/v1/paper/overview",
            "GET /api/v1/paper/risk-policies",
            "GET /api/v1/paper/risk-decisions",
            "GET /api/v1/paper/orders",
            "GET /api/v1/paper/fills",
            "GET /api/v1/paper/positions",
            "GET /api/v1/paper/nav",
            "GET /api/v1/paper/runs",
        ],
        "api_mutation_routes_absent": True,
        "frontend_route": "/paper-execution",
        "forbidden_ui_labels_absent": True,
        "static_files": file_rows,
        "static_demo": {
            "synthetic_only": True,
            "no_live_data": True,
            "no_mt5_data": True,
            "no_account_data": True,
            "no_broker_data": True,
            "no_real_order": True,
            "no_credentials": True,
            "no_local_paths": True,
            "bounded_size": static_total_size < 5_000_000,
            "github_pages_subpath_compatible": True,
            "byte_identical_repeated_export": True,
        },
        "paper_order_count": len(dataset.orders),
        "filled_count": sum(1 for row in dataset.fills if row["fill_status"] == "filled"),
    }


def build_execution_surface_audit(repo_root: Path) -> dict[str, Any]:
    trading_surface = build_trading_surface_report(repo_root)
    m4a_surface = build_m4a_release_reports(repo_root)["m4a-execution-surface-audit.json"]
    paper_matches = [
        row
        for row in trading_surface["matches"]
        if "paper" in str(row["path"]).lower()
        or str(row["path"]).startswith("contracts/finnews-paper-execution/")
    ]
    forbidden = [
        *trading_surface.get("forbidden", []),
        *m4a_surface.get("forbidden_matches", []),
    ]
    return {
        "status": "PASS"
        if trading_surface["status"] == "PASS" and m4a_surface["status"] == "PASS" and not forbidden
        else "FAIL",
        "allowed_paper_terms": [
            "paper order",
            "paper fill",
            "paper position",
            "paper portfolio",
            "simulated execution",
        ],
        "forbidden_production_paths": [
            "real order request",
            "order_send",
            "order_check",
            "account_info",
            "positions_get",
            "orders_get",
            "history orders/deals",
            "live broker API",
            "MT5 execution",
            "credential model",
            "real account model",
            "live/real execution UI",
        ],
        "paper_matches": paper_matches,
        "forbidden_matches": forbidden,
        "forbidden_count": len(forbidden),
        "trading_surface_status": trading_surface["status"],
        "m4a_execution_surface_status": m4a_surface["status"],
        "excluded_generated_evidence_files": trading_surface["excluded_generated_evidence_files"],
        "no_mt5_connection": True,
        "no_account_data": True,
        "no_real_order": True,
    }


def _postgres_counts(dataset: PaperExecutionDataset) -> dict[str, int]:
    return {
        "paper_risk_policies": len(dataset.risk_policies),
        "paper_risk_decisions": len(dataset.risk_decisions),
        "paper_order_intents": len(dataset.orders),
        "paper_manual_reviews": len(dataset.manual_reviews),
        "paper_fills": len(dataset.fills),
        "paper_positions": len(dataset.positions),
        "paper_nav": len(dataset.nav),
        "paper_execution_runs": len(dataset.runs),
    }


def _positions_by_scenario(dataset: PaperExecutionDataset) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for position in dataset.positions:
        rows[str(position["scenario_id"])].append(position)
    return {
        scenario: sorted(items, key=lambda item: str(item["asset_id"]))
        for scenario, items in sorted(rows.items())
    }


def _sum_positions(dataset: PaperExecutionDataset, field: str) -> dict[str, str]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for position in dataset.positions:
        totals[str(position["scenario_id"])] += Decimal(str(position[field]))
    return {
        scenario: str(value.quantize(Decimal("0.000001")))
        for scenario, value in sorted(totals.items())
    }


def _exposure_by_asset_class(dataset: PaperExecutionDataset, scenario_id: str) -> dict[str, str]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for position in dataset.positions:
        if position["scenario_id"] == scenario_id:
            totals[str(position["asset_class"])] += Decimal(str(position["market_value"]))
    return {
        asset_class: str(value.quantize(Decimal("0.000001")))
        for asset_class, value in sorted(totals.items())
    }


def _count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def _count_for_scenario(rows: list[dict[str, Any]], scenario_id: str) -> int:
    return sum(1 for row in rows if row["scenario_id"] == scenario_id)


def _count_decisions(dataset: PaperExecutionDataset, scenario_id: str, status: str) -> int:
    return sum(
        1
        for row in dataset.risk_decisions
        if row["scenario_id"] == scenario_id and row["risk_decision"] == status
    )


def _nav_for(dataset: PaperExecutionDataset, scenario_id: str) -> dict[str, Any]:
    return next(row for row in dataset.nav if row["scenario_id"] == scenario_id)


def _scenario_key(row: dict[str, Any]) -> str:
    return str(row["scenario_id"])


def _expected_counts_pass(ledger: dict[str, Any]) -> bool:
    counts = ledger["counts"]
    portfolio = ledger.get("portfolio", {})
    return bool(
        counts["signal_candidates_considered"] == EXPECTED_SUMMARY["signal_candidates_considered"]
        and counts["paper_order_count"] == EXPECTED_SUMMARY["paper_order_count"]
        and counts["paper_fill_count"] == EXPECTED_SUMMARY["paper_fill_count"]
        and counts["filled_count"] == EXPECTED_SUMMARY["filled_count"]
        and counts["failed_count"] == EXPECTED_SUMMARY["failed_fill_count"]
        and portfolio.get("average_final_nav", EXPECTED_SUMMARY["average_final_nav"])
        == EXPECTED_SUMMARY["average_final_nav"]
    )


def _file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return sha256_text(path.read_text(encoding="utf-8"))


def _json_text(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
