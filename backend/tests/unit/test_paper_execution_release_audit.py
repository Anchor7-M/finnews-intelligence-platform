from __future__ import annotations

import json
from pathlib import Path

from finnews.application.services.paper_execution import (
    PAPER_FORBIDDEN_FIELDS,
    build_paper_execution_demo,
    paper_order_example,
    validate_paper_order_intent,
)
from finnews.application.services.paper_execution_release_audit import (
    EXPECTED_SUMMARY,
    PROMPT_FORBIDDEN_FIELDS,
    build_contract_audit,
    build_execution_surface_audit,
    build_fill_accounting_audit,
    build_m4b0_release_reports,
    build_manual_approval_audit,
    build_postgres_audit,
    build_release_ledger,
    build_risk_gate_audit,
    build_scenario_audit,
    write_m4b0_release_audit_reports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_m4b0_release_reports_are_deterministic_and_match_expected_counts(
    tmp_path: Path,
) -> None:
    first = write_m4b0_release_audit_reports(REPO_ROOT)
    second = write_m4b0_release_audit_reports(REPO_ROOT)

    assert first["status"] == "PASS"
    assert first["hashes"] == second["hashes"]
    assert all(first["byte_identical_rebuild"].values())
    ledger = json.loads(
        (REPO_ROOT / "reports/paper-execution/m4b0-release-ledger.json").read_text(encoding="utf-8")
    )
    assert (
        ledger["counts"]["signal_candidates_considered"]
        == EXPECTED_SUMMARY["signal_candidates_considered"]
    )
    assert ledger["counts"]["paper_order_count"] == EXPECTED_SUMMARY["paper_order_count"]
    assert ledger["counts"]["paper_fill_count"] == EXPECTED_SUMMARY["paper_fill_count"]
    assert ledger["counts"]["filled_count"] == EXPECTED_SUMMARY["filled_count"]
    assert ledger["portfolio"]["average_final_nav"] == EXPECTED_SUMMARY["average_final_nav"]

    left = build_m4b0_release_reports(REPO_ROOT)
    right = build_m4b0_release_reports(REPO_ROOT)
    assert json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)
    assert (tmp_path / "unused").exists() is False


def test_contract_audit_rejects_prompt_forbidden_fields() -> None:
    assert set(PROMPT_FORBIDDEN_FIELDS).issubset(PAPER_FORBIDDEN_FIELDS)
    audit = build_contract_audit(REPO_ROOT)

    assert audit["status"] == "PASS"
    assert audit["example_valid"]["valid"] is True
    assert audit["unknown_field_rejected"] is True
    assert audit["expired_order_rejected"] is True
    assert audit["synthetic_data_required"] is True
    assert audit["not_investment_advice_required"] is True
    assert all(not row["valid"] for row in audit["forbidden_field_results"])

    example = paper_order_example()
    missing = {key: value for key, value in example.items() if key != "synthetic_data"}
    result = validate_paper_order_intent(missing)
    assert result["valid"] is False
    assert "missing fields" in " ".join(result["errors"])


def test_release_audit_subreports_pass_and_remain_paper_only() -> None:
    dataset = build_paper_execution_demo()
    reports = [
        build_release_ledger(REPO_ROOT, dataset),
        build_risk_gate_audit(dataset),
        build_manual_approval_audit(dataset),
        build_fill_accounting_audit(dataset),
        build_scenario_audit(dataset),
        build_postgres_audit(),
        build_execution_surface_audit(REPO_ROOT),
    ]

    assert all(report["status"] == "PASS" for report in reports)
    manual = build_manual_approval_audit(dataset)
    assert manual["state_counts"] == {"approved": 17, "pending_review": 10, "rejected": 3}
    fill = build_fill_accounting_audit(dataset)
    assert fill["hand_calculations"]["one_fill"]["commission_expected"] == "1.250000"
    scenario = build_scenario_audit(dataset)
    assert [row["filled"] for row in scenario["scenarios"]] == [1, 4, 3]
