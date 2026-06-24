from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from finnews.application.services.cross_asset import (
    CONTRACT_NAME,
    CONTRACT_VERSION,
    CrossAssetError,
    build_cross_asset_demo,
    resolve_asset_alias,
    trading_surface_audit,
    validate_mt5_symbol_map,
    validate_signal_package,
    write_signal_package,
)
from finnews.application.services.cross_asset_release_audit import (
    EXCLUDED_GENERATED_EVIDENCE_FILES,
    GENERATED_M3C_MARKET_REACTION_EVIDENCE_FILES,
    GENERATED_TRADING_SURFACE_AUDIT_OUTPUT_PATH,
    _pattern_count,
    build_lifecycle_audit_report,
    build_release_ledger,
    build_trading_surface_report,
    write_revised_m3a_release_reports,
)
from finnews.domain.enums import AssetClass, CrossAssetEventFamily

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_cross_asset_fixture_exact_counts_and_class_coverage() -> None:
    dataset = build_cross_asset_demo()
    counts: dict[str, int] = {}
    for asset in dataset.assets:
        counts[asset.asset_class.value] = counts.get(asset.asset_class.value, 0) + 1

    assert len(dataset.assets) == 40
    assert counts == {
        "us_equity": 8,
        "etf": 5,
        "equity_index": 3,
        "fx": 5,
        "precious_metal": 3,
        "commodity": 3,
        "futures_root": 2,
        "futures_contract": 2,
        "crypto_asset": 4,
        "macro_indicator": 3,
        "interest_rate": 2,
    }
    assert {asset.asset_class for asset in dataset.assets} == set(AssetClass)
    assert len({asset.asset_id for asset in dataset.assets}) == 40
    assert all(asset.synthetic for asset in dataset.assets)
    assert len(dataset.events) == 100
    assert {event.event_family for event in dataset.events} == set(CrossAssetEventFamily)
    assert len(dataset.impacts) == 240
    assert len(dataset.signals) == 80


def test_alias_resolution_reports_resolved_ambiguous_and_unresolved() -> None:
    resolved = resolve_asset_alias("canonical", "US-EQ-ALPHA")
    ambiguous = resolve_asset_alias("news_source", "policy pulse")
    unresolved = resolve_asset_alias("market_data", "MISSING")

    assert resolved.status == "resolved"
    assert resolved.matches[0]["asset_id"] == "US-EQ-ALPHA"
    assert ambiguous.status == "ambiguous"
    assert len(ambiguous.matches) == 2
    assert unresolved.status == "unresolved"


def test_futures_contracts_have_root_relationship_metadata() -> None:
    dataset = build_cross_asset_demo()
    contracts = [
        asset for asset in dataset.assets if asset.asset_class is AssetClass.FUTURES_CONTRACT
    ]

    assert {asset.parent_asset_id for asset in contracts} == {"FUT-ROOT-OIL", "FUT-ROOT-GOLD"}
    assert all(asset.expiry is not None for asset in contracts)
    assert all(
        asset.contract_metadata["contract_metadata_available"] is True for asset in contracts
    )


def test_mt5_symbol_map_validation_rejects_duplicate_unknown_and_execution_fields(
    tmp_path: Path,
) -> None:
    valid_path = Path("config/integrations/mt5-symbol-map.example.yaml")
    assert validate_mt5_symbol_map(valid_path)["valid"] is True

    invalid = tmp_path / "mt5-symbol-map.local.yaml"
    invalid.write_text(
        """
mappings:
  - canonical_asset_id: FX-EURUSD
    broker_profile_id: demo
    mt5_symbol: DEMO.EURUSD
    enabled: true
    volume: 1
  - canonical_asset_id: UNKNOWN
    broker_profile_id: demo
    mt5_symbol: DEMO.EURUSD
    enabled: true
        """,
        encoding="utf-8",
    )

    result = validate_mt5_symbol_map(invalid)

    assert result["valid"] is False
    assert "volume" in " ".join(result["errors"])
    assert "UNKNOWN" in " ".join(result["errors"])
    assert "duplicate active broker symbol" in " ".join(result["errors"])
    assert result["terminal_contacted"] is False


def test_mt5_symbol_map_validation_rejects_each_forbidden_category(tmp_path: Path) -> None:
    forbidden_fields = [
        "account_id",
        "account_number",
        "broker_server",
        "login",
        "password",
        "investor_password",
        "terminal_path",
        "order_type",
        "action",
        "volume",
        "lot",
        "leverage",
        "margin",
        "price",
        "entry_price",
        "stop_loss",
        "sl",
        "take_profit",
        "tp",
        "position_id",
        "order_ticket",
        "execute",
        "execute_now",
        "buy",
        "sell",
        "close_position",
    ]
    for field in forbidden_fields:
        path = tmp_path / f"{field}.yaml"
        path.write_text(
            f"""
mappings:
  - canonical_asset_id: FX-EURUSD
    broker_profile_id: demo
    mt5_symbol: DEMO.EURUSD
    enabled: true
    {field}: forbidden
            """,
            encoding="utf-8",
        )
        result = validate_mt5_symbol_map(path)
        assert result["valid"] is False
        assert field in " ".join(result["errors"])
        assert result["terminal_contacted"] is False


def test_signal_package_is_deterministic_and_rejects_forbidden_fields(tmp_path: Path) -> None:
    left = tmp_path / ".finnews-market-signals" / "left"
    right = tmp_path / ".finnews-market-signals" / "right"

    left_result = write_signal_package(left)
    right_result = write_signal_package(right)

    assert left_result["valid"] is True
    assert left_result["package_content_hash"] == right_result["package_content_hash"]
    assert left_result["contract_name"] == CONTRACT_NAME
    assert left_result["contract_version"] == CONTRACT_VERSION
    assert left_result["asset_count"] == 40
    assert left_result["event_impact_count"] == 240
    assert left_result["signal_count"] == 80

    rows = (left / "signals.jsonl").read_text(encoding="utf-8").splitlines()
    tampered = json.loads(rows[0])
    tampered["order_type"] = "BUY"
    rows[0] = json.dumps(tampered, sort_keys=True)
    (left / "signals.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(CrossAssetError, match="file (hash|size) mismatch"):
        validate_signal_package(left)


def test_signal_package_can_use_existing_empty_output_directory(tmp_path: Path) -> None:
    output = tmp_path / ".finnews-market-signals" / "empty-target"
    output.mkdir(parents=True)

    result = write_signal_package(output)

    assert result["valid"] is True
    assert (output / "manifest.json").exists()


def test_signal_package_strict_contract_rejects_unknown_and_execution_fields(
    tmp_path: Path,
) -> None:
    forbidden_fields = [
        "account_id",
        "account_number",
        "broker_server",
        "login",
        "password",
        "investor_password",
        "order_type",
        "action",
        "volume",
        "lot",
        "leverage",
        "entry_price",
        "price",
        "stop_loss",
        "sl",
        "take_profit",
        "tp",
        "margin",
        "position_id",
        "order_ticket",
        "execute",
        "execute_now",
        "buy",
        "sell",
        "close_position",
    ]
    for field in forbidden_fields:
        output = tmp_path / ".finnews-market-signals" / field
        write_signal_package(output)
        rows = (output / "signals.jsonl").read_text(encoding="utf-8").splitlines()
        tampered = json.loads(rows[0])
        tampered[field] = "forbidden"
        rows[0] = json.dumps(tampered, sort_keys=True)
        _rewrite_signal_rows_with_valid_manifest(output, rows)
        with pytest.raises(CrossAssetError, match="unknown fields|forbidden fields"):
            validate_signal_package(output)

    output = tmp_path / ".finnews-market-signals" / "unknown"
    write_signal_package(output)
    rows = (output / "signals.jsonl").read_text(encoding="utf-8").splitlines()
    tampered = json.loads(rows[0])
    tampered["unexpected_field"] = "x"
    rows[0] = json.dumps(tampered, sort_keys=True)
    _rewrite_signal_rows_with_valid_manifest(output, rows)
    with pytest.raises(CrossAssetError, match="unknown fields"):
        validate_signal_package(output)


def test_signal_lifecycle_rejects_invalid_timestamp_boundaries(tmp_path: Path) -> None:
    output = tmp_path / ".finnews-market-signals" / "lifecycle"
    write_signal_package(output)
    rows = (output / "signals.jsonl").read_text(encoding="utf-8").splitlines()
    tampered = json.loads(rows[0])
    tampered["expires_at"] = tampered["generated_at"]
    rows[0] = json.dumps(tampered, sort_keys=True)
    _rewrite_signal_rows_with_valid_manifest(output, rows)
    with pytest.raises(CrossAssetError, match="generated_at must be before expires_at"):
        validate_signal_package(output)


def test_signal_output_must_stay_under_ignored_local_root(tmp_path: Path) -> None:
    with pytest.raises(CrossAssetError, match="signal exports must be under"):
        write_signal_package(tmp_path / "signals")


def test_trading_surface_audit_has_no_disallowed_execution_surface() -> None:
    result = trading_surface_audit(Path("."))

    assert result["valid"] is True
    assert result["mt5_import_present"] is False
    assert result["terminal_contact_present"] is False
    assert result["order_route_present"] is False


def test_release_ledger_and_audit_reports_are_deterministic(tmp_path: Path) -> None:
    first = build_release_ledger(REPO_ROOT)
    second = build_release_ledger(REPO_ROOT)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["asset_ledger"]["total"] == 40
    assert first["alias_ledger"]["total"] == 211
    assert first["event_ledger"]["total"] == 100
    assert first["impact_ledger"]["total"] == 240
    assert first["signal_ledger"]["total"] == 80
    assert first["alias_ledger"]["active_alias_uniqueness_violations"] == 0

    report = write_revised_m3a_release_reports(REPO_ROOT, output_root=tmp_path)
    left = (tmp_path / "reports" / "cross-asset" / "revised-m3a-release-ledger.json").read_bytes()
    report_again = write_revised_m3a_release_reports(REPO_ROOT, output_root=tmp_path)
    right = (tmp_path / "reports" / "cross-asset" / "revised-m3a-release-ledger.json").read_bytes()
    assert left == right
    assert report["ledger_sha256"] == report_again["ledger_sha256"]


def test_lifecycle_and_trading_surface_release_reports() -> None:
    lifecycle = build_lifecycle_audit_report(REPO_ROOT)
    assert lifecycle["package_byte_identical_rebuild"] is True
    assert lifecycle["cutoff_lte_generated"] is True
    assert lifecycle["generated_before_expiry"] is True
    assert lifecycle["logical_rebuild_idempotency_same"] is True

    surface = build_trading_surface_report(REPO_ROOT)
    assert surface["status"] == "PASS"
    assert surface["forbidden_count"] == 0
    assert surface["mt5_dependency_present"] is False
    assert GENERATED_TRADING_SURFACE_AUDIT_OUTPUT_PATH in set(
        surface["excluded_generated_evidence_files"]
    )
    assert set(surface["excluded_generated_evidence_files"]) == set(
        EXCLUDED_GENERATED_EVIDENCE_FILES
    )
    assert set(GENERATED_M3C_MARKET_REACTION_EVIDENCE_FILES).issubset(
        set(surface["excluded_generated_evidence_files"])
    )
    assert all((REPO_ROOT / path).exists() for path in GENERATED_M3C_MARKET_REACTION_EVIDENCE_FILES)
    for row in [*surface["matches"], *surface["forbidden"]]:
        assert row["path"] not in EXCLUDED_GENERATED_EVIDENCE_FILES
    assert not any(row["path"].startswith("reports/market-reaction/") for row in surface["matches"])


def test_trading_surface_report_still_classifies_docs_tests_and_forbidden_source(
    tmp_path: Path,
) -> None:
    surface = build_trading_surface_report(REPO_ROOT)
    classifications = {(row["path"], row["classification"]) for row in surface["matches"]}
    assert (
        "docs/TRADING_SURFACE_AUDIT.md",
        "permitted architecture documentation",
    ) in classifications
    assert (
        "backend/tests/unit/test_cross_asset.py",
        "permitted test fixture proving rejection",
    ) in classifications

    repo = tmp_path / "repo"
    production_file = repo / "backend" / "src" / "finnews" / "interfaces" / "api" / "trading.py"
    production_file.parent.mkdir(parents=True)
    production_file.write_text(
        "def unsafe_route():\n    order_send({'symbol': 'DEMO'})\n",
        encoding="utf-8",
    )
    report_file = repo / "reports" / "market-reaction" / "m3c-release-ledger.json"
    report_file.parent.mkdir(parents=True)
    report_file.write_text(
        '{"pattern": "order_send(", "volume": 1, "buy": true, "sell": true}',
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

    forbidden_surface = build_trading_surface_report(repo)

    assert forbidden_surface["status"] == "FAIL"
    assert forbidden_surface["forbidden_count"] == 1
    assert forbidden_surface["forbidden"][0] == {
        "path": "backend/src/finnews/interfaces/api/trading.py",
        "pattern": "order_send(",
        "count": 1,
        "classification": "forbidden executable production path",
    }
    assert not any(
        row["path"] == "reports/market-reaction/m3c-release-ledger.json"
        for row in [*forbidden_surface["matches"], *forbidden_surface["forbidden"]]
    )


def test_trading_surface_report_allows_market_data_volume_not_order_calls(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    market_reaction = (
        repo / "backend" / "src" / "finnews" / "application" / "services" / "market_reaction.py"
    )
    market_reaction.parent.mkdir(parents=True)
    market_reaction.write_text("def bar_schema():\n    volume = 100\n    return volume\n")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

    allowed_surface = build_trading_surface_report(repo)

    assert allowed_surface["status"] == "PASS"
    assert allowed_surface["forbidden_count"] == 0
    assert {
        "path": "backend/src/finnews/application/services/market_reaction.py",
        "pattern": "volume",
        "count": 2,
        "classification": "permitted market-data bar volume field",
    } in allowed_surface["matches"]

    release_audit = (
        repo
        / "backend"
        / "src"
        / "finnews"
        / "application"
        / "services"
        / "market_reaction_release_audit.py"
    )
    release_audit.write_text("def check_bar(row):\n    return row['volume'] >= 0\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

    release_audit_surface = build_trading_surface_report(repo)

    assert release_audit_surface["status"] == "PASS"
    assert {
        "path": "backend/src/finnews/application/services/market_reaction_release_audit.py",
        "pattern": "volume",
        "count": 1,
        "classification": "permitted market-data bar volume field",
    } in release_audit_surface["matches"]

    market_reaction.write_text(
        "def unsafe_route():\n    volume = 100\n    order_send({'symbol': 'DEMO'})\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

    forbidden_surface = build_trading_surface_report(repo)

    assert forbidden_surface["status"] == "FAIL"
    assert forbidden_surface["forbidden"][0]["pattern"] == "order_send("


def test_trading_surface_token_patterns_do_not_match_substrings() -> None:
    assert _pattern_count("disabled pilot source", "lot") == 0
    assert _pattern_count("lot = 0.1", "lot") == 1


def test_trading_surface_report_generation_is_byte_identical(tmp_path: Path) -> None:
    write_revised_m3a_release_reports(REPO_ROOT, output_root=tmp_path)
    left = (
        tmp_path / "reports" / "cross-asset" / "revised-m3a-trading-surface-audit.json"
    ).read_bytes()
    write_revised_m3a_release_reports(REPO_ROOT, output_root=tmp_path)
    right = (
        tmp_path / "reports" / "cross-asset" / "revised-m3a-trading-surface-audit.json"
    ).read_bytes()
    assert left == right


def _rewrite_signal_rows_with_valid_manifest(output: Path, rows: list[str]) -> None:
    from finnews.application.services.cross_asset import sha256_bytes, sha256_text

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = ("\n".join(rows) + "\n").encode()
    (output / "signals.jsonl").write_bytes(data)
    hashes: dict[str, str] = {}
    for file_info in manifest["files"]:
        name = file_info["path"]
        if name == "signals.jsonl":
            file_info["size_bytes"] = len(data)
            file_info["sha256"] = sha256_bytes(data)
        hashes[name] = file_info["sha256"]
    manifest["package_content_hash"] = sha256_text(
        "\n".join(f"{name}:{hashes[name]}" for name in sorted(hashes))
    )
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
