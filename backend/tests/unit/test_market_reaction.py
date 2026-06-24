from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from finnews.application.services.cross_asset import canonical_json, sha256_text
from finnews.application.services.market_reaction import (
    CONTRACT_NAME,
    MARKET_STATES,
    SUPPORTED_SCENARIOS,
    MarketReactionError,
    build_market_reaction_demo,
    compare_scenarios,
    market_data_contract_example_rows,
    market_reaction_overview,
    market_reaction_static_payload,
    scenario_summary,
    validate_market_bar_file,
)
from finnews.application.services.market_reaction_release_audit import (
    build_m3c_point_in_time_audit,
    build_m3c_release_ledger,
    build_m3c_scenario_audit,
    write_m3c_release_audit_reports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_market_bar_contract_accepts_csv_and_jsonl_deterministically(tmp_path: Path) -> None:
    rows = market_data_contract_example_rows()
    csv_path = tmp_path / "bars.csv"
    jsonl_path = tmp_path / "bars.jsonl"
    _write_csv(csv_path, rows)
    _write_jsonl(jsonl_path, rows)

    csv_result = validate_market_bar_file(csv_path)
    jsonl_result = validate_market_bar_file(jsonl_path)

    assert csv_result["valid"] is True
    assert jsonl_result["valid"] is True
    assert csv_result["contract_name"] == CONTRACT_NAME
    assert csv_result["row_count"] == 2
    assert csv_result["deterministic_hash"] == jsonl_result["deterministic_hash"]
    assert csv_result["live_fetch_metadata"] is False
    assert csv_result["credentials_present"] is False


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("future_return", "0.1", "forbidden fields"),
        ("account_id", "abc", "forbidden fields"),
        ("order_type", "market", "forbidden fields"),
        ("buy", "true", "forbidden fields"),
        ("bar_start_at", "2026-01-02T00:00:00", "timezone-aware"),
        ("timezone", "America/New_York", "only UTC"),
        ("high", "1.0", "high must be"),
        ("volume", "-1", "non-negative"),
        ("schema_version", "wrong", "unsupported schema_version"),
    ],
)
def test_market_bar_contract_rejects_invalid_rows(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    rows = market_data_contract_example_rows()
    rows[0][field] = value
    path = tmp_path / f"{field}.jsonl"
    _write_jsonl(path, rows)

    with pytest.raises(MarketReactionError, match=message):
        validate_market_bar_file(path)


def test_market_bar_contract_rejects_duplicates_and_non_monotonic_order(tmp_path: Path) -> None:
    duplicate_rows = market_data_contract_example_rows()
    duplicate_rows[1]["bar_id"] = duplicate_rows[0]["bar_id"]
    duplicate_path = tmp_path / "duplicate.jsonl"
    _write_jsonl(duplicate_path, duplicate_rows)
    with pytest.raises(MarketReactionError, match="duplicate bar business key"):
        validate_market_bar_file(duplicate_path)

    reversed_path = tmp_path / "reversed.jsonl"
    _write_jsonl(reversed_path, list(reversed(market_data_contract_example_rows())))
    with pytest.raises(MarketReactionError, match="monotonic"):
        validate_market_bar_file(reversed_path)


def test_synthetic_market_reaction_dataset_counts_and_hashes_are_stable() -> None:
    dataset = build_market_reaction_demo()
    overview = market_reaction_overview(dataset)

    assert overview["scenario_ids"] == SUPPORTED_SCENARIOS
    assert overview["scenario_count"] == 3
    assert overview["asset_count_per_scenario"] == 24
    assert overview["session_count_per_scenario"] == 90
    assert overview["bar_count_per_scenario"] == 2160
    assert overview["total_bar_count"] == 6480
    assert overview["study_count"] == 645
    assert overview["label_count"] == 645
    assert overview["metric_row_count"] == 132
    assert overview["market_state_distribution"] == {state: 1296 for state in MARKET_STATES}
    assert dataset.leakage_audit["diagnostics"]
    assert {item["status"] for item in dataset.leakage_audit["diagnostics"]} == {"PASS"}
    assert dataset.leakage_audit["label_hash"] == sha256_text(canonical_json(dataset.labels))


def test_scenario_summaries_and_comparison_separate_null_planted_and_regime() -> None:
    null_summary = scenario_summary("synthetic-null-reaction-v1")
    planted_summary = scenario_summary("synthetic-planted-reaction-v1")
    regime_summary = scenario_summary("synthetic-regime-shift-v1")
    comparison = compare_scenarios("synthetic-null-reaction-v1", "synthetic-planted-reaction-v1")

    assert null_summary["bar_count"] == 2160
    assert planted_summary["label_count"] == 215
    assert regime_summary["market_state_distribution"] == {state: 432 for state in MARKET_STATES}
    assert comparison["left_bar_count"] == comparison["right_bar_count"] == 2160
    assert comparison["one_week_consistency_delta"] != 0


def test_market_reaction_static_payload_contains_full_and_sample_sets() -> None:
    payload = market_reaction_static_payload()

    assert payload["market-reaction-overview"]["no_live_market_data"] is True
    assert len(payload["market-reaction-labels"]) == 645
    assert len(payload["market-reaction-labels-sample"]) == 500
    assert "market-data-bars" not in payload
    assert len(payload["market-data-bars-sample"]) == 500
    rendered = json.dumps(payload).lower()
    assert "account_id" not in rendered
    assert "order_type" not in rendered


def test_m3c_release_audit_reports_are_deterministic() -> None:
    ledger = build_m3c_release_ledger(REPO_ROOT)
    scenario = build_m3c_scenario_audit()
    point_in_time = build_m3c_point_in_time_audit()

    assert ledger["status"] == "PASS"
    assert ledger["contract"]["name"] == "finnews-market-bars-v1"
    assert ledger["bar_accounting"]["total_bars"] == 6480
    assert ledger["static_export"]["full_bar_static_exported"] is False
    assert scenario["byte_identical_rebuild"] is True
    assert scenario["total_bar_count"] == 6480
    assert point_in_time["status"] == "PASS"
    assert point_in_time["boundary_results"]["current_clock_mutation"] == "PASS"

    first = write_m3c_release_audit_reports(REPO_ROOT)
    second = write_m3c_release_audit_reports(REPO_ROOT)

    assert first["status"] == "PASS"
    assert first["byte_identical_rebuild"] == second["byte_identical_rebuild"]
    assert first["report_hashes"] == second["report_hashes"]
