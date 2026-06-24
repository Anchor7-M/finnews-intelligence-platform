from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from finnews.application.services.market_reaction import validate_market_bar_file
from finnews.application.services.mt5_readonly import (
    FIXED_TEST_EXPORT_TIME,
    Mt5RateBar,
    OptionalMetaTrader5ReadOnlyAdapter,
    evaluate_mt5_readonly_gates,
    export_mt5_bars_readonly,
    mt5_readonly_readiness,
    mt5_readonly_symbol_map_schema,
    validate_mt5_readonly_symbol_map,
)
from finnews.application.services.mt5_readonly_release_audit import (
    build_m4a_release_reports,
    write_m4a_release_audit_reports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class FakeReadOnlyBridge:
    def __init__(self, bars: list[Mt5RateBar] | None = None, init_ready: bool = True) -> None:
        self.bars = bars or [
            Mt5RateBar(
                time=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                tick_volume=Decimal("1234"),
            )
        ]
        self.init_ready = init_ready
        self.shutdown_called = False

    def package_status(self) -> dict[str, object]:
        return {"package_available": True, "status": "fake_available"}

    def initialize_readonly(self) -> dict[str, object]:
        return {
            "terminal_access_status": "read_only_ready"
            if self.init_ready
            else "terminal_unavailable"
        }

    def shutdown(self) -> None:
        self.shutdown_called = True

    def terminal_snapshot(self) -> dict[str, object]:
        return {"terminal_access_status": "read_only_ready", "build": 1}

    def symbol_snapshot(self, symbols: list[str]) -> list[dict[str, object]]:
        return [{"symbol": symbol, "digits": 5, "visible": True} for symbol in symbols]

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Mt5RateBar]:
        assert symbol == "DEMO.EURUSD"
        assert timeframe == "D1"
        assert start.tzinfo is not None
        assert end.tzinfo is not None
        return self.bars


def _symbol_map(path: Path, extra: str = "") -> Path:
    path.write_text(
        f"""
mappings:
  - profile_id: demo
    canonical_asset_id: FX-EURUSD
    mt5_symbol: DEMO.EURUSD
    enabled: true
    display_name: Synthetic EURUSD
    notes: Local test mapping
    timezone: UTC
{extra}
""",
        encoding="utf-8",
    )
    return path


def test_symbol_map_schema_and_validation_accept_safe_fields(tmp_path: Path) -> None:
    path = _symbol_map(tmp_path / "map.yaml")
    schema = mt5_readonly_symbol_map_schema()
    result = validate_mt5_readonly_symbol_map(path)

    assert schema["credentials_allowed"] is False
    assert schema["order_fields_allowed"] is False
    assert result["valid"] is True
    assert result["enabled_mapping_count"] == 1
    assert result["mapped_asset_count"] == 1
    assert result["terminal_contacted"] is False
    assert result["mt5_imported"] is False


def test_symbol_map_rejects_forbidden_unknown_duplicate_and_unsupported(tmp_path: Path) -> None:
    path = _symbol_map(
        tmp_path / "map.yaml",
        """
  - profile_id: demo
    canonical_asset_id: FX-EURUSD
    mt5_symbol: DEMO.EURUSD
    enabled: true
  - profile_id: demo
    canonical_asset_id: MACRO-CPI-US
    mt5_symbol: DEMO.CPI
    enabled: true
    password: no
  - profile_id: demo
    canonical_asset_id: UNKNOWN
    mt5_symbol: DEMO.UNKNOWN
    enabled: true
    surprise: no
""",
    )
    result = validate_mt5_readonly_symbol_map(path)
    errors = " ".join(result["errors"])

    assert result["valid"] is False
    assert "duplicate active symbol" in errors
    assert "unsupported asset class" in errors
    assert "forbidden fields" in errors
    assert "unknown fields" in errors
    assert "unknown asset" in errors


def test_gates_block_without_allow_flag_confirm_valid_map_and_safe_output(tmp_path: Path) -> None:
    path = _symbol_map(tmp_path / "map.yaml")
    result = evaluate_mt5_readonly_gates(
        symbol_map_path=path,
        output=tmp_path / "outside",
        start=datetime(2026, 6, 1, tzinfo=UTC),
        end=datetime(2026, 6, 2, tzinfo=UTC),
        timeframe="D1",
        confirm_local_terminal=False,
        env={},
        repo_root=REPO_ROOT,
    )

    assert result["allowed"] is False
    assert "allow_env_missing" in result["failures"]
    assert "confirm_local_terminal_missing" in result["failures"]
    assert "output_outside_ignored_root" in result["failures"]
    assert result["terminal_contacted"] is False


def test_gates_reject_naive_non_utc_ci_and_excessive_ranges(tmp_path: Path) -> None:
    path = _symbol_map(tmp_path / "map.yaml")
    output = REPO_ROOT / ".finnews-mt5-readonly-exports" / "test"
    result = evaluate_mt5_readonly_gates(
        symbol_map_path=path,
        output=output,
        start=datetime(2026, 1, 1),
        end=datetime(2026, 2, 15),
        timeframe="M1",
        confirm_local_terminal=True,
        env={"FINNEWS_ALLOW_LOCAL_MT5_READONLY": "1", "CI": "true"},
        repo_root=REPO_ROOT,
    )

    assert "ci_environment_blocked" in result["failures"]
    assert "naive_datetime" in result["failures"]


def test_fake_adapter_exports_market_bar_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _symbol_map(tmp_path / "map.yaml")
    output = REPO_ROOT / ".finnews-mt5-readonly-exports" / "pytest-export"
    monkeypatch.setenv("FINNEWS_ALLOW_LOCAL_MT5_READONLY", "1")
    bridge = FakeReadOnlyBridge()

    result = export_mt5_bars_readonly(
        symbol_map_path=path,
        timeframe="D1",
        start=datetime(2026, 6, 1, tzinfo=UTC),
        end=datetime(2026, 6, 2, tzinfo=UTC),
        output=output,
        confirm_local_terminal=True,
        bridge=bridge,
        repo_root=REPO_ROOT,
        export_time=FIXED_TEST_EXPORT_TIME,
    )

    assert result["status"] == "exported"
    assert result["bar_count"] == 1
    assert bridge.shutdown_called is True
    validation = validate_market_bar_file(output / "bars.jsonl")
    assert validation["valid"] is True
    assert validation["row_count"] == 1
    manifest = (output / "manifest.json").read_text(encoding="utf-8").lower()
    for forbidden in ["account_id", "password", "order_send", "positions_get"]:
        assert forbidden not in manifest


def test_fake_adapter_rejects_duplicate_and_invalid_bars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _symbol_map(tmp_path / "map.yaml")
    output = REPO_ROOT / ".finnews-mt5-readonly-exports" / "pytest-bad-export"
    monkeypatch.setenv("FINNEWS_ALLOW_LOCAL_MT5_READONLY", "1")
    duplicate_bar = Mt5RateBar(
        time=datetime(2026, 6, 1, tzinfo=UTC),
        open=Decimal("1"),
        high=Decimal("1"),
        low=Decimal("1"),
        close=Decimal("1"),
        tick_volume=Decimal("1"),
    )
    result = export_mt5_bars_readonly(
        symbol_map_path=path,
        timeframe="D1",
        start=datetime(2026, 6, 1, tzinfo=UTC),
        end=datetime(2026, 6, 2, tzinfo=UTC),
        output=output,
        confirm_local_terminal=True,
        bridge=FakeReadOnlyBridge([duplicate_bar, duplicate_bar]),
        repo_root=REPO_ROOT,
    )

    assert result["status"] == "invalid_bars"


def test_optional_adapter_missing_package_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_import(name: str) -> object:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("importlib.import_module", missing_import)
    adapter = OptionalMetaTrader5ReadOnlyAdapter()

    assert adapter.package_status()["status"] == "not_installed"


def test_default_public_readiness_never_exposes_terminal_details() -> None:
    readiness = mt5_readonly_readiness()

    assert readiness["mt5_terminal_connection"] == "not attempted"
    assert readiness["order_execution"] == "disabled"
    assert readiness["account_access"] == "not_supported"
    assert readiness["public_api_trigger"] == "disabled"


def test_mt5_metadata_migration_has_no_forbidden_columns() -> None:
    migration = (REPO_ROOT / "backend/alembic/versions/0008_mt5_readonly_bridge.py").read_text(
        encoding="utf-8"
    )
    forbidden_columns = [
        '"password"',
        '"login"',
        '"account"',
        '"order"',
        '"position"',
        '"stop_loss"',
        '"take_profit"',
        '"margin_required"',
    ]

    assert all(column not in migration for column in forbidden_columns)


def test_m4a_release_audit_reports_are_deterministic_and_safe(tmp_path: Path) -> None:
    first = build_m4a_release_reports(REPO_ROOT)
    second = build_m4a_release_reports(REPO_ROOT)

    assert first == second
    ledger = first["m4a-release-ledger.json"]
    assert ledger["default_public_readiness"] == {
        "MT5 terminal connection": "not attempted",
        "Order execution": "disabled",
        "Account access": "not supported",
    }
    assert ledger["no_credential_storage"] is True
    assert ledger["no_account_access"] is True
    assert ledger["no_order_execution"] is True
    assert first["m4a-execution-surface-audit.json"]["status"] == "PASS"
    rendered = json.dumps(first, sort_keys=True).lower()
    for forbidden in ["c:\\", "/users/", "broker.example", "real_terminal", "live_bar_row"]:
        assert forbidden not in rendered

    result = write_m4a_release_audit_reports(REPO_ROOT)
    left = (REPO_ROOT / "reports/mt5-readonly/m4a-release-ledger.json").read_bytes()
    result_again = write_m4a_release_audit_reports(REPO_ROOT)
    right = (REPO_ROOT / "reports/mt5-readonly/m4a-release-ledger.json").read_bytes()
    assert result["status"] == "PASS"
    assert result_again["status"] == "PASS"
    assert left == right
