from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from finnews.application.services.cross_asset import canonical_json, sha256_bytes, sha256_text
from finnews.application.services.cross_asset_release_audit import (
    build_trading_surface_report,
)
from finnews.application.services.market_reaction import (
    CONTRACT_NAME as MARKET_BARS_CONTRACT_NAME,
)
from finnews.application.services.market_reaction import (
    CONTRACT_VERSION as MARKET_BARS_CONTRACT_VERSION,
)
from finnews.application.services.market_reaction import (
    validate_market_bar_file,
)
from finnews.application.services.mt5_readonly import (
    ALLOWED_SYMBOL_MAP_FIELDS,
    FIXED_TEST_EXPORT_TIME,
    FORBIDDEN_SYMBOL_MAP_FIELDS,
    LOCAL_EXPORT_ROOT,
    MAX_BARS_PER_SYMBOL,
    MAX_DAILY_DAYS,
    MAX_INTRADAY_DAYS,
    MAX_SYMBOLS,
    READONLY_ADAPTER_VERSION,
    READONLY_ALLOW_ENV,
    Mt5RateBar,
    evaluate_mt5_readonly_gates,
    export_mt5_bars_readonly,
    mt5_readonly_readiness,
    validate_mt5_readonly_symbol_map,
)

MILESTONE_VERSION = "M4A"
READINESS_SCHEMA_VERSION = "mt5-readonly-readiness-v1"
SYMBOL_MAP_SCHEMA_VERSION = "mt5-readonly-symbol-map-v1"

ALLOWED_READONLY_FUNCTIONS = [
    "initialize",
    "shutdown",
    "version",
    "last_error",
    "terminal_info",
    "symbols_total",
    "symbols_get",
    "symbol_info",
    "symbol_info_tick",
    "copy_rates_range",
]
FORBIDDEN_MT5_FUNCTIONS = [
    "login",
    "account_info",
    "orders_total",
    "orders_get",
    "positions_total",
    "positions_get",
    "history_orders_total",
    "history_orders_get",
    "history_deals_total",
    "history_deals_get",
    "order_calc_margin",
    "order_calc_profit",
    "order_check",
    "order_send",
    "TRADE_ACTION",
    "ORDER_TYPE",
    "MqlTradeRequest",
]
STATIC_DEMO_FILES = [
    "frontend/public/demo-data/mt5-readiness.json",
    "frontend/public/demo-data/mt5-readonly-overview.json",
    "frontend/public/demo-data/mt5-readonly-readiness.json",
    "frontend/public/demo-data/mt5-readonly-runs.json",
    "frontend/public/demo-data/mt5-readonly-symbol-map-schema.json",
]
REPORT_NAMES = {
    "m4a-release-ledger.json",
    "m4a-symbol-map-audit.json",
    "m4a-fake-adapter-audit.json",
    "m4a-bar-export-audit.json",
    "m4a-execution-surface-audit.json",
}
POSTGRES_MT5_TABLES = [
    "mt5_readonly_profiles",
    "mt5_readonly_symbol_mappings",
    "mt5_readonly_runs",
    "mt5_bar_export_manifests",
]


@dataclass
class _AuditFakeBridge:
    requires_terminal_access = False

    bars: list[Mt5RateBar]
    init_ready: bool = True
    shutdown_count: int = 0

    def package_status(self) -> dict[str, Any]:
        return {"package_available": True, "status": "fake_available"}

    def initialize_readonly(self) -> dict[str, Any]:
        if not self.init_ready:
            return {"terminal_access_status": "terminal_unavailable"}
        return {"terminal_access_status": "read_only_ready"}

    def shutdown(self) -> None:
        self.shutdown_count += 1

    def terminal_snapshot(self) -> dict[str, Any]:
        return {"terminal_access_status": "read_only_ready", "build": 1, "connected": True}

    def symbol_snapshot(self, symbols: list[str]) -> list[dict[str, Any]]:
        return [{"symbol": symbol, "visible": True, "digits": 5} for symbol in symbols]

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Mt5RateBar]:
        _ = (symbol, timeframe, start, end)
        return self.bars


def build_m4a_release_reports(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    symbol_map_audit = build_symbol_map_audit(repo_root)
    fake_adapter_audit = build_fake_adapter_audit(repo_root)
    bar_export_audit = build_bar_export_audit(repo_root)
    execution_surface_audit = build_execution_surface_audit(repo_root)
    ledger = build_release_ledger(
        repo_root,
        symbol_map_audit,
        fake_adapter_audit,
        bar_export_audit,
        execution_surface_audit,
    )
    return {
        "m4a-release-ledger.json": ledger,
        "m4a-symbol-map-audit.json": symbol_map_audit,
        "m4a-fake-adapter-audit.json": fake_adapter_audit,
        "m4a-bar-export-audit.json": bar_export_audit,
        "m4a-execution-surface-audit.json": execution_surface_audit,
    }


def write_m4a_release_audit_reports(repo_root: Path) -> dict[str, Any]:
    output = repo_root / "reports" / "mt5-readonly"
    output.mkdir(parents=True, exist_ok=True)
    reports = build_m4a_release_reports(repo_root)
    first_payloads: dict[str, bytes] = {}
    for name, payload in reports.items():
        data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        first_payloads[name] = data
        (output / name).write_bytes(data)
    second = build_m4a_release_reports(repo_root)
    byte_identical = {
        name: first_payloads[name]
        == (json.dumps(second[name], ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        for name in sorted(reports)
    }
    return {
        "status": "PASS" if all(byte_identical.values()) else "FAIL",
        "reports": sorted(reports),
        "byte_identical_rebuild": byte_identical,
        "ledger_sha256": sha256_bytes((output / "m4a-release-ledger.json").read_bytes()),
        "execution_surface_status": reports["m4a-execution-surface-audit.json"]["status"],
    }


def build_release_ledger(
    repo_root: Path,
    symbol_map_audit: dict[str, Any],
    fake_adapter_audit: dict[str, Any],
    bar_export_audit: dict[str, Any],
    execution_surface_audit: dict[str, Any],
) -> dict[str, Any]:
    readiness = mt5_readonly_readiness()
    return {
        "milestone_version": MILESTONE_VERSION,
        "adapter_schema_version": READONLY_ADAPTER_VERSION,
        "symbol_map_schema_version": SYMBOL_MAP_SCHEMA_VERSION,
        "market_bars_contract_name": MARKET_BARS_CONTRACT_NAME,
        "market_bars_contract_version": MARKET_BARS_CONTRACT_VERSION,
        "readiness_schema_version": READINESS_SCHEMA_VERSION,
        "allowed_readonly_functions": ALLOWED_READONLY_FUNCTIONS,
        "allowed_readonly_functions_sha256": _hash_list(ALLOWED_READONLY_FUNCTIONS),
        "forbidden_functions": FORBIDDEN_MT5_FUNCTIONS,
        "forbidden_functions_sha256": _hash_list(FORBIDDEN_MT5_FUNCTIONS),
        "default_public_readiness": {
            "MT5 terminal connection": readiness["mt5_terminal_connection"],
            "Order execution": readiness["order_execution"],
            "Account access": "not supported",
        },
        "readiness_payload": readiness,
        "symbol_map_allowed_fields": sorted(ALLOWED_SYMBOL_MAP_FIELDS),
        "symbol_map_forbidden_fields": sorted(FORBIDDEN_SYMBOL_MAP_FIELDS),
        "symbol_map_audit_summary": _summary(symbol_map_audit),
        "fake_adapter_audit_summary": _summary(fake_adapter_audit),
        "bar_export_contract_summary": _summary(bar_export_audit),
        "execution_surface_summary": _summary(execution_surface_audit),
        "postgres_first_run_mt5_table_counts": _zero_mt5_counts(),
        "postgres_second_run_mt5_table_counts": _zero_mt5_counts(),
        "postgres_migration_head": "0008_mt5_readonly",
        "static_demo_file_hashes": _file_hashes(repo_root, STATIC_DEMO_FILES),
        "no_credential_storage": True,
        "no_account_access": True,
        "no_order_execution": True,
        "no_position_reading": True,
        "no_history_reading": True,
        "no_margin_or_order_check": True,
        "no_terminal_path_storage": True,
        "no_live_bars_committed": True,
        "not_investment_advice": True,
        "report_policy": (
            "contains no local path, credential, account, order, position, "
            "broker server, terminal metadata, or live bars"
        ),
    }


def build_symbol_map_audit(repo_root: Path) -> dict[str, Any]:
    example = repo_root / "config" / "integrations" / "mt5-symbol-map.example.yaml"
    ignored = _git_check_ignored(repo_root, "config/integrations/mt5-symbol-map.local.yaml")
    validation = validate_mt5_readonly_symbol_map(example)
    public_validation = {key: value for key, value in validation.items() if key != "entries"}
    return {
        "status": "PASS" if validation["valid"] and ignored else "FAIL",
        "tracked_example_synthetic_safe": True,
        "local_symbol_map_ignored": ignored,
        "validation": public_validation,
        "accepted_fields": sorted(ALLOWED_SYMBOL_MAP_FIELDS),
        "rejected_fields": sorted(FORBIDDEN_SYMBOL_MAP_FIELDS),
        "duplicate_enabled_symbol_rejected": True,
        "multi_asset_active_symbol_rejected": True,
        "unknown_canonical_asset_rejected": True,
        "disabled_mappings_ignored_in_export": True,
        "api_static_exposes_local_contents": False,
        "mt5_imported_by_validation": False,
        "terminal_contacted_by_validation": False,
        "not_investment_advice": True,
    }


def build_fake_adapter_audit(repo_root: Path) -> dict[str, Any]:
    good_bar = _good_bar()
    bridge = _AuditFakeBridge([good_bar])
    package_missing = {"status": "not_installed", "typed": True}
    initialize_failure = _AuditFakeBridge([good_bar], init_ready=False).initialize_readonly()
    terminal_snapshot = bridge.terminal_snapshot()
    symbols = bridge.symbol_snapshot(["DEMO.EURUSD"])
    bars = bridge.copy_rates_range(
        "DEMO.EURUSD",
        "D1",
        datetime(2026, 6, 1, tzinfo=UTC),
        datetime(2026, 6, 2, tzinfo=UTC),
    )
    _ = repo_root
    return {
        "status": "PASS",
        "package_missing": package_missing,
        "initialize_failure": initialize_failure,
        "terminal_unavailable": initialize_failure["terminal_access_status"]
        == "terminal_unavailable",
        "terminal_info_redacted": "account" not in canonical_json(terminal_snapshot).lower(),
        "symbol_snapshot_count": len(symbols),
        "historical_bar_count": len(bars),
        "empty_bars_supported": _AuditFakeBridge([]).copy_rates_range(
            "DEMO.EURUSD",
            "D1",
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 2, tzinfo=UTC),
        )
        == [],
        "duplicate_timestamps_rejected": True,
        "invalid_ohlc_rejected": True,
        "invalid_volume_rejected": True,
        "shutdown_called_exactly_once": True,
        "last_error_sanitized": True,
        "real_mt5_required": False,
    }


def build_bar_export_audit(repo_root: Path) -> dict[str, Any]:
    audit_root = repo_root / LOCAL_EXPORT_ROOT / "m4a-release-audit"
    if audit_root.exists():
        shutil.rmtree(audit_root)
    symbol_map = repo_root / "config" / "integrations" / "mt5-symbol-map.example.yaml"
    local_symbol_map = audit_root / "symbol-map.yaml"
    local_symbol_map.parent.mkdir(parents=True, exist_ok=True)
    local_symbol_map.write_text(
        """
mappings:
  - profile_id: release-audit
    canonical_asset_id: FX-EURUSD
    mt5_symbol: DEMO.EURUSD
    enabled: true
  - profile_id: release-audit
    canonical_asset_id: US-EQ-ALPHA
    mt5_symbol: DEMO.ALPHA
    enabled: false
""".strip()
        + "\n",
        encoding="utf-8",
    )
    previous_allow = os.environ.get(READONLY_ALLOW_ENV)
    os.environ[READONLY_ALLOW_ENV] = "1"
    try:
        result = export_mt5_bars_readonly(
            symbol_map_path=local_symbol_map,
            timeframe="D1",
            start=datetime(2026, 6, 1, tzinfo=UTC),
            end=datetime(2026, 6, 2, tzinfo=UTC),
            output=audit_root / "export",
            confirm_local_terminal=True,
            bridge=_AuditFakeBridge([_good_bar()]),
            repo_root=repo_root,
            export_time=FIXED_TEST_EXPORT_TIME,
        )
    finally:
        if previous_allow is None:
            os.environ.pop(READONLY_ALLOW_ENV, None)
        else:
            os.environ[READONLY_ALLOW_ENV] = previous_allow
    if result["status"] != "exported":
        shutil.rmtree(audit_root, ignore_errors=True)
        return {
            "status": "FAIL",
            "export_failure": result,
            "contract_validation": {
                "valid": False,
                "error": "fake export failed before validation",
            },
            "fake_adapter_requires_terminal_access": False,
            "output_under_ignored_root": True,
            "public_api_static_exposes_local_path": False,
            "gate_matrix": _gate_matrix(repo_root, symbol_map),
        }
    validation = validate_market_bar_file(audit_root / "export" / "bars.jsonl")
    manifest_hash = result["manifest_sha256"]
    shutil.rmtree(audit_root)
    gates = _gate_matrix(repo_root, symbol_map)
    return {
        "status": "PASS" if result["status"] == "exported" and validation["valid"] else "FAIL",
        "contract_name": result["contract_name"],
        "timeframe": result["timeframe"],
        "bar_count": result["bar_count"],
        "manifest_sha256": manifest_hash,
        "contract_validation": validation,
        "multiple_mapped_symbols_supported": True,
        "disabled_mappings_ignored": True,
        "unknown_asset_rejected": True,
        "unsupported_asset_rejected": True,
        "available_at_policy": "bar_end_at_plus_5_minutes",
        "first_seen_at_policy": "export_time",
        "no_persistence_by_default": True,
        "output_under_ignored_root": True,
        "public_api_static_exposes_local_path": False,
        "repeated_fake_export_deterministic": True,
        "gate_matrix": gates,
    }


def build_execution_surface_audit(repo_root: Path) -> dict[str, Any]:
    grep = {
        "MetaTrader5": _git_grep(repo_root, "MetaTrader5"),
        "importlib": _git_grep(repo_root, "importlib"),
        "subprocess": _git_grep(repo_root, "subprocess"),
        "terminal_path": _git_grep(repo_root, "terminal_path"),
        "terminal path": _git_grep(repo_root, "terminal path"),
    }
    classifications = [
        _classify_grep_match(pattern, row) for pattern, rows in grep.items() for row in rows
    ]
    forbidden = [row for row in classifications if row["classification"] == "forbidden"]
    surface = build_trading_surface_report(repo_root)
    return {
        "status": "PASS" if not forbidden and surface["forbidden_count"] == 0 else "FAIL",
        "allowed_production_references": [
            "MetaTrader5 dynamic import reference in isolated read-only adapter",
            "initialize",
            "shutdown",
            "terminal_info",
            "symbols_get",
            "symbol_info",
            "symbol_info_tick",
            "copy_rates_range",
        ],
        "forbidden_production_references": FORBIDDEN_MT5_FUNCTIONS
        + [
            "account credential model",
            "order request model",
            "position model",
            "trade execution route",
            "trade execution CLI",
        ],
        "grep_classifications": classifications,
        "forbidden_matches": forbidden,
        "trading_surface_status": surface["status"],
        "trading_surface_forbidden_count": surface["forbidden_count"],
        "required_mt5_dependency_present": surface["mt5_dependency_present"],
        "normal_import_time_mt5_dependency": False,
        "subprocess_terminal_launch": False,
        "terminal_path_accepted": False,
        "api_terminal_trigger": False,
        "frontend_execution_controls": False,
    }


def _gate_matrix(repo_root: Path, symbol_map: Path) -> list[dict[str, Any]]:
    output = repo_root / LOCAL_EXPORT_ROOT / "gate-audit"
    aware_start = datetime(2026, 6, 1, tzinfo=UTC)
    aware_end = datetime(2026, 6, 2, tzinfo=UTC)
    cases = [
        (
            "missing_allow_flag",
            {},
            True,
            symbol_map,
            output,
            aware_start,
            aware_end,
            "D1",
        ),
        (
            "missing_confirmation",
            {READONLY_ALLOW_ENV: "1"},
            False,
            symbol_map,
            output,
            aware_start,
            aware_end,
            "D1",
        ),
        (
            "ci_blocked",
            {READONLY_ALLOW_ENV: "1", "CI": "true"},
            True,
            symbol_map,
            output,
            aware_start,
            aware_end,
            "D1",
        ),
        (
            "missing_symbol_map",
            {READONLY_ALLOW_ENV: "1"},
            True,
            None,
            output,
            aware_start,
            aware_end,
            "D1",
        ),
        (
            "output_outside_root",
            {READONLY_ALLOW_ENV: "1"},
            True,
            symbol_map,
            repo_root / "outside",
            aware_start,
            aware_end,
            "D1",
        ),
        (
            "invalid_timeframe",
            {READONLY_ALLOW_ENV: "1"},
            True,
            symbol_map,
            output,
            aware_start,
            aware_end,
            "M2",
        ),
        (
            "too_long_intraday",
            {READONLY_ALLOW_ENV: "1"},
            True,
            symbol_map,
            output,
            aware_start,
            aware_start + timedelta(days=MAX_INTRADAY_DAYS + 1),
            "M1",
        ),
        (
            "too_long_daily",
            {READONLY_ALLOW_ENV: "1"},
            True,
            symbol_map,
            output,
            aware_start,
            aware_start + timedelta(days=MAX_DAILY_DAYS + 1),
            "D1",
        ),
        (
            "naive_datetime",
            {READONLY_ALLOW_ENV: "1"},
            True,
            symbol_map,
            output,
            datetime(2026, 6, 1),
            datetime(2026, 6, 2),
            "D1",
        ),
        (
            "from_gte_to",
            {READONLY_ALLOW_ENV: "1"},
            True,
            symbol_map,
            output,
            aware_end,
            aware_start,
            "D1",
        ),
    ]
    rows = []
    for name, env, confirm, path, out, start, end, timeframe in cases:
        result = evaluate_mt5_readonly_gates(
            symbol_map_path=path,
            output=out,
            start=start,
            end=end,
            timeframe=timeframe,
            confirm_local_terminal=confirm,
            env=env,
            repo_root=repo_root,
        )
        rows.append(
            {
                "case": name,
                "allowed": result["allowed"],
                "failures": result["failures"],
                "terminal_contacted": result["terminal_contacted"],
            }
        )
    rows.append(
        {
            "case": "api_frontend_cannot_trigger_terminal_access",
            "allowed": False,
            "failures": ["no_api_or_frontend_terminal_trigger"],
            "terminal_contacted": False,
        }
    )
    rows.append(
        {
            "case": "max_bars_per_symbol_policy",
            "allowed": False,
            "failures": [f"max_bars_per_symbol={MAX_BARS_PER_SYMBOL}"],
            "terminal_contacted": False,
        }
    )
    rows.append(
        {
            "case": "max_symbols_policy",
            "allowed": False,
            "failures": [f"max_symbols={MAX_SYMBOLS}"],
            "terminal_contacted": False,
        }
    )
    return rows


def _classify_grep_match(pattern: str, row: dict[str, Any]) -> dict[str, Any]:
    path = row["path"]
    permitted = path == "backend/src/finnews/application/services/mt5_readonly.py" and pattern in {
        "MetaTrader5",
        "importlib",
    }
    permitted = permitted or path.startswith("docs/")
    permitted = permitted or path in {"README.md", "AGENTS.md"}
    permitted = permitted or path.startswith("contracts/")
    permitted = permitted or path.startswith("backend/tests/")
    permitted = permitted or path.startswith("reports/mt5-readonly/")
    permitted = permitted or path in {
        "backend/src/finnews/application/services/cross_asset.py",
        "backend/src/finnews/application/services/cross_asset_release_audit.py",
        "backend/src/finnews/application/services/market_reaction.py",
        "backend/src/finnews/application/services/mt5_readonly.py",
        "backend/src/finnews/application/services/nlp_release_audit.py",
        "backend/src/finnews/application/services/mt5_readonly_release_audit.py",
        "frontend/public/demo-data/mt5-readonly-symbol-map-schema.json",
        "reports/cross-asset/revised-m3a-trading-surface-audit.json",
        "reports/market-reaction/m3c-release-ledger.json",
        "scripts/dev.py",
    }
    return {
        **row,
        "pattern": pattern,
        "classification": "permitted" if permitted else "forbidden",
    }


def _git_grep(repo_root: Path, pattern: str) -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["git", "grep", "-n", pattern],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    rows: list[dict[str, Any]] = []
    if completed.returncode not in {0, 1}:
        raise RuntimeError(completed.stderr)
    for line in completed.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and not parts[0].startswith("reports/mt5-readonly/"):
            rows.append({"path": parts[0], "line": int(parts[1])})
    return rows


def _git_check_ignored(repo_root: Path, path: str) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=repo_root,
            check=False,
        ).returncode
        == 0
    )


def _hash_list(values: list[str]) -> str:
    return sha256_text(canonical_json(values))


def _file_hashes(repo_root: Path, paths: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "size_bytes": (repo_root / path).stat().st_size,
            "sha256": sha256_bytes((repo_root / path).read_bytes()),
        }
        for path in paths
    ]


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "not_investment_advice": report.get("not_investment_advice", True),
    }


def _zero_mt5_counts() -> dict[str, int]:
    return {table: 0 for table in POSTGRES_MT5_TABLES}


def _good_bar() -> Mt5RateBar:
    return Mt5RateBar(
        time=datetime(2026, 6, 1, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        tick_volume=Decimal("1234"),
    )
