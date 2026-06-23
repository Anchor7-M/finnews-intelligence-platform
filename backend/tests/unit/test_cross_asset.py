from __future__ import annotations

import json
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
from finnews.domain.enums import AssetClass, CrossAssetEventFamily


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


def test_signal_output_must_stay_under_ignored_local_root(tmp_path: Path) -> None:
    with pytest.raises(CrossAssetError, match="signal exports must be under"):
        write_signal_package(tmp_path / "signals")


def test_trading_surface_audit_has_no_disallowed_execution_surface() -> None:
    result = trading_surface_audit(Path("."))

    assert result["valid"] is True
    assert result["mt5_import_present"] is False
    assert result["terminal_contact_present"] is False
    assert result["order_route_present"] is False
