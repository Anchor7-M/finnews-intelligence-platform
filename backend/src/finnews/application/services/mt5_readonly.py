from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

import yaml

from finnews.application.services.cross_asset import build_cross_asset_demo, sha256_bytes
from finnews.application.services.market_reaction import (
    CONTRACT_NAME as MARKET_BARS_CONTRACT_NAME,
)

LOCAL_EXPORT_ROOT = ".finnews-mt5-readonly-exports"
READONLY_ALLOW_ENV = "FINNEWS_ALLOW_LOCAL_MT5_READONLY"
READONLY_ADAPTER_VERSION = "mt5-readonly-bridge-v1"
SUPPORTED_TIMEFRAMES = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}
MAX_BARS_PER_SYMBOL = 10_000
MAX_SYMBOLS = 40
MAX_INTRADAY_DAYS = 30
MAX_DAILY_DAYS = 365 * 5 + 2
EXPORT_LATENCY = timedelta(minutes=5)
FIXED_TEST_EXPORT_TIME = datetime(2026, 6, 1, 0, 1, tzinfo=UTC)

ALLOWED_SYMBOL_MAP_FIELDS = {
    "profile_id",
    "canonical_asset_id",
    "mt5_symbol",
    "enabled",
    "display_name",
    "notes",
    "timezone",
}
LEGACY_SYMBOL_MAP_ALIASES = {"broker_profile_id": "profile_id", "local_note": "notes"}
FORBIDDEN_SYMBOL_MAP_FIELDS = {
    "account_id",
    "account",
    "account_number",
    "login",
    "password",
    "investor_password",
    "server",
    "broker_server",
    "server_password",
    "broker_password",
    "terminal_path",
    "api_key",
    "token",
    "secret",
    "volume",
    "lot",
    "order_type",
    "action",
    "price",
    "entry_price",
    "stop_loss",
    "sl",
    "take_profit",
    "tp",
    "margin",
    "margin_required",
    "risk_limit",
    "trade_mode",
    "trade_mode_override",
    "execute",
    "execute_now",
    "buy",
    "sell",
    "close_position",
}
SECRET_VALUE_MARKERS = ("password", "secret", "token", "api_key", "login=", "server=")
MT5_EXPORT_ASSET_CLASSES = {
    "us_equity",
    "etf",
    "equity_index",
    "fx",
    "precious_metal",
    "commodity",
    "futures_root",
    "futures_contract",
    "crypto_asset",
}


class Mt5ReadOnlyError(Exception):
    pass


class Mt5AdapterUnavailable(Mt5ReadOnlyError):
    pass


class Mt5ReadOnlyPolicyViolation(Mt5ReadOnlyError):
    pass


@dataclass(frozen=True)
class Mt5SymbolMapEntry:
    profile_id: str
    canonical_asset_id: str
    mt5_symbol: str
    enabled: bool
    display_name: str | None = None
    notes: str | None = None
    timezone: str | None = None


@dataclass(frozen=True)
class Mt5RateBar:
    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    tick_volume: Decimal
    spread: Decimal | None = None
    real_volume: Decimal | None = None


class Mt5ReadOnlyBridge(Protocol):
    def package_status(self) -> dict[str, Any]: ...

    def initialize_readonly(self) -> dict[str, Any]: ...

    def shutdown(self) -> None: ...

    def terminal_snapshot(self) -> dict[str, Any]: ...

    def symbol_snapshot(self, symbols: list[str]) -> list[dict[str, Any]]: ...

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Mt5RateBar]: ...


class DisabledMt5ReadOnlyBridge:
    requires_terminal_access = False

    def package_status(self) -> dict[str, Any]:
        return {"package_available": False, "status": "not_checked"}

    def initialize_readonly(self) -> dict[str, Any]:
        return {"terminal_access_status": "blocked_by_gate"}

    def shutdown(self) -> None:
        return None

    def terminal_snapshot(self) -> dict[str, Any]:
        return {"terminal_access_status": "not_attempted"}

    def symbol_snapshot(self, symbols: list[str]) -> list[dict[str, Any]]:
        return [
            {"symbol": symbol, "selected": False, "visible": False, "metadata_status": "not_read"}
            for symbol in symbols
        ]

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Mt5RateBar]:
        raise Mt5AdapterUnavailable("read-only bridge is disabled")


class OptionalMetaTrader5ReadOnlyAdapter:
    requires_terminal_access = True

    def __init__(self) -> None:
        self._module: Any | None = None

    def package_status(self) -> dict[str, Any]:
        try:
            module = self._load_module()
        except Mt5AdapterUnavailable:
            return {"package_available": False, "status": "not_installed"}
        version = getattr(module, "version", lambda: None)()
        return {
            "package_available": True,
            "status": "available",
            "package_version": _safe_version(version),
        }

    def initialize_readonly(self) -> dict[str, Any]:
        module = self._load_module()
        initialized = bool(module.initialize())
        if not initialized:
            return {
                "terminal_access_status": "terminal_unavailable",
                "last_error": _sanitize_error(getattr(module, "last_error", lambda: None)()),
            }
        return {"terminal_access_status": "read_only_ready"}

    def shutdown(self) -> None:
        if self._module is not None:
            getattr(self._module, "shutdown", lambda: None)()

    def terminal_snapshot(self) -> dict[str, Any]:
        module = self._load_module()
        info = getattr(module, "terminal_info", lambda: None)()
        return _terminal_info_to_safe_dict(info)

    def symbol_snapshot(self, symbols: list[str]) -> list[dict[str, Any]]:
        module = self._load_module()
        rows = []
        for symbol in symbols:
            info = module.symbol_info(symbol)
            rows.append(_symbol_info_to_safe_dict(symbol, info))
        return rows

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Mt5RateBar]:
        module = self._load_module()
        timeframe_value = getattr(module, f"TIMEFRAME_{timeframe}")
        raw_rows = module.copy_rates_range(symbol, timeframe_value, start, end)
        if raw_rows is None:
            return []
        return [_rate_bar_from_raw(row) for row in raw_rows]

    def _load_module(self) -> Any:
        if self._module is None:
            try:
                self._module = importlib.import_module("MetaTrader5")
            except ModuleNotFoundError as exc:
                raise Mt5AdapterUnavailable("MetaTrader5 package is not installed") from exc
        return self._module


def mt5_readonly_overview() -> dict[str, Any]:
    return {
        "feature_status": "implemented_optional_local_cli_only",
        "bridge_purpose": (
            "read-only terminal readiness, symbol metadata, and historical bar export"
        ),
        "package_required_for_ci": False,
        "terminal_connection": "not attempted",
        "order_execution": "disabled",
        "account_access": "not supported",
        "public_api_trigger": "disabled",
        "local_cli_only": True,
        "not_investment_advice": True,
        "deferred": ["M4B demo execution", "M4C live execution review"],
    }


def mt5_readonly_readiness(
    *,
    bridge: Mt5ReadOnlyBridge | None = None,
    symbol_map_path: Path | None = None,
) -> dict[str, Any]:
    bridge = bridge or DisabledMt5ReadOnlyBridge()
    symbol_map_result = (
        validate_mt5_readonly_symbol_map(symbol_map_path)
        if symbol_map_path is not None
        else {
            "valid": False,
            "mapping_count": 0,
            "enabled_mapping_count": 0,
            "mapped_asset_count": 0,
            "unmapped_asset_count": len(build_cross_asset_demo().assets),
            "duplicate_symbol_count": 0,
            "errors": ["symbol map not supplied"],
            "terminal_contacted": False,
        }
    )
    package = bridge.package_status()
    return {
        "bridge_feature_status": "available_optional_local_cli_only",
        "package_available": bool(package.get("package_available", False)),
        "package_status": package.get("status", "not_checked"),
        "terminal_access_status": "not_attempted",
        "local_symbol_map_status": "valid" if symbol_map_result["valid"] else "not_supplied",
        "mapped_asset_count": symbol_map_result["mapped_asset_count"],
        "unmapped_asset_count": symbol_map_result["unmapped_asset_count"],
        "duplicate_symbol_count": symbol_map_result["duplicate_symbol_count"],
        "last_local_readonly_run": None,
        "execution_status": "disabled",
        "order_support": "not_implemented",
        "account_access": "not_supported",
        "public_api_trigger": "disabled",
        "mt5_terminal_connection": "not attempted",
        "order_execution": "disabled",
        "not_investment_advice": True,
    }


def mt5_readonly_symbol_map_schema() -> dict[str, Any]:
    return {
        "schema_version": "mt5-readonly-symbol-map-v1",
        "allowed_fields": sorted(ALLOWED_SYMBOL_MAP_FIELDS),
        "legacy_aliases": LEGACY_SYMBOL_MAP_ALIASES,
        "forbidden_fields": sorted(FORBIDDEN_SYMBOL_MAP_FIELDS),
        "ignored_local_path": "config/integrations/mt5-symbol-map.local.yaml",
        "tracked_example_path": "config/integrations/mt5-symbol-map.example.yaml",
        "terminal_contacted_by_validation": False,
        "credentials_allowed": False,
        "order_fields_allowed": False,
    }


def mt5_readonly_runs_static() -> list[dict[str, Any]]:
    return [
        {
            "run_id": "synthetic-m4a-readonly-run",
            "status": "not_run_static_demo",
            "terminal_access_status": "not_attempted",
            "mapped_asset_count": 0,
            "exported_bar_count": 0,
            "synthetic": True,
            "no_terminal_metadata": True,
            "not_investment_advice": True,
        }
    ]


def mt5_readonly_static_payload() -> dict[str, Any]:
    return {
        "mt5-readonly-overview": mt5_readonly_overview(),
        "mt5-readonly-readiness": mt5_readonly_readiness(),
        "mt5-readonly-symbol-map-schema": mt5_readonly_symbol_map_schema(),
        "mt5-readonly-runs": mt5_readonly_runs_static(),
    }


def validate_mt5_readonly_symbol_map(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise Mt5ReadOnlyPolicyViolation("symbol map file not found")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mappings = raw.get("mappings")
    if not isinstance(mappings, list):
        raise Mt5ReadOnlyPolicyViolation("symbol map mappings must be a list")
    assets = {asset.asset_id: asset for asset in build_cross_asset_demo().assets}
    errors: list[str] = []
    entries: list[Mt5SymbolMapEntry] = []
    active_symbol_seen: set[tuple[str, str]] = set()
    active_asset_by_symbol: dict[tuple[str, str], str] = {}
    enabled_count = 0
    for index, raw_row in enumerate(mappings, start=1):
        if not isinstance(raw_row, dict):
            errors.append(f"mapping {index} must be an object")
            continue
        row = _normalize_symbol_map_row(raw_row)
        unknown = set(row) - ALLOWED_SYMBOL_MAP_FIELDS
        forbidden = set(row) & FORBIDDEN_SYMBOL_MAP_FIELDS
        if unknown:
            errors.append(f"mapping {index} has unknown fields: {', '.join(sorted(unknown))}")
        if forbidden:
            errors.append(f"mapping {index} has forbidden fields: {', '.join(sorted(forbidden))}")
        _scan_secret_like_values(row, errors, index)
        asset_id = str(row.get("canonical_asset_id", ""))
        profile_id = str(row.get("profile_id", ""))
        mt5_symbol = str(row.get("mt5_symbol", ""))
        enabled = bool(row.get("enabled", False))
        asset = assets.get(asset_id)
        if asset is None:
            errors.append(f"mapping {index} references unknown asset: {asset_id}")
        elif asset.asset_class.value not in MT5_EXPORT_ASSET_CLASSES:
            errors.append(
                f"mapping {index} references unsupported asset class: {asset.asset_class.value}"
            )
        if not profile_id or not mt5_symbol:
            errors.append(f"mapping {index} missing profile_id or mt5_symbol")
        if enabled:
            enabled_count += 1
            key = (profile_id, mt5_symbol)
            if key in active_symbol_seen:
                errors.append(f"duplicate active symbol: {profile_id}:{mt5_symbol}")
            active_symbol_seen.add(key)
            previous_asset = active_asset_by_symbol.get(key)
            if previous_asset is not None and previous_asset != asset_id:
                errors.append(f"active symbol maps to multiple assets: {profile_id}:{mt5_symbol}")
            active_asset_by_symbol[key] = asset_id
        entries.append(
            Mt5SymbolMapEntry(
                profile_id=profile_id,
                canonical_asset_id=asset_id,
                mt5_symbol=mt5_symbol,
                enabled=enabled,
                display_name=_optional_str(row.get("display_name")),
                notes=_optional_str(row.get("notes")),
                timezone=_optional_str(row.get("timezone")),
            )
        )
    mapped_assets = {entry.canonical_asset_id for entry in entries if entry.enabled}
    return {
        "valid": not errors,
        "mapping_count": len(entries),
        "enabled_mapping_count": enabled_count,
        "mapped_asset_count": len(mapped_assets),
        "unmapped_asset_count": len(assets) - len(mapped_assets),
        "duplicate_symbol_count": max(0, enabled_count - len(active_symbol_seen)),
        "errors": errors,
        "terminal_contacted": False,
        "mt5_imported": False,
        "allowed_fields": sorted(ALLOWED_SYMBOL_MAP_FIELDS),
        "forbidden_fields_checked": sorted(FORBIDDEN_SYMBOL_MAP_FIELDS),
        "entries": entries,
    }


def evaluate_mt5_readonly_gates(
    *,
    symbol_map_path: Path | None,
    output: Path | None,
    start: datetime | None,
    end: datetime | None,
    timeframe: str,
    confirm_local_terminal: bool,
    requires_terminal_access: bool = True,
    env: dict[str, str] | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    gate_env = dict(os.environ if env is None else env)
    repo_root = (repo_root or Path.cwd()).resolve()
    failures: list[str] = []
    if gate_env.get(READONLY_ALLOW_ENV) != "1":
        failures.append("allow_env_missing")
    if not confirm_local_terminal:
        failures.append("confirm_local_terminal_missing")
    if requires_terminal_access and gate_env.get("CI", "").lower() in {"1", "true", "yes"}:
        failures.append("ci_environment_blocked")
    if symbol_map_path is None:
        failures.append("symbol_map_missing")
    if output is None:
        failures.append("output_missing")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        failures.append("unsupported_timeframe")
    if start is None or end is None:
        failures.append("datetime_range_missing")
    else:
        if start.tzinfo is None or end.tzinfo is None:
            failures.append("naive_datetime")
        elif start.utcoffset() != timedelta(0) or end.utcoffset() != timedelta(0):
            failures.append("non_utc_datetime")
        elif start >= end:
            failures.append("invalid_datetime_range")
        else:
            days = (end - start).total_seconds() / 86400
            if timeframe == "D1" and days > MAX_DAILY_DAYS:
                failures.append("daily_range_too_large")
            if timeframe != "D1" and days > MAX_INTRADAY_DAYS:
                failures.append("intraday_range_too_large")
    if output is not None and not _under_local_export_root(output, repo_root):
        failures.append("output_outside_ignored_root")
    secret_keys = [
        key
        for key in gate_env
        if key.upper().startswith("FINNEWS_MT5_")
        and any(marker in key.lower() for marker in SECRET_VALUE_MARKERS)
    ]
    if secret_keys:
        failures.append("credential_environment_present")
    symbol_map_result: dict[str, Any] | None = None
    if symbol_map_path is not None and symbol_map_path.exists():
        try:
            symbol_map_result = validate_mt5_readonly_symbol_map(symbol_map_path)
        except Mt5ReadOnlyPolicyViolation as exc:
            failures.append(f"symbol_map_invalid:{exc}")
        else:
            if not symbol_map_result["valid"]:
                failures.append("symbol_map_invalid")
            if symbol_map_result["enabled_mapping_count"] > MAX_SYMBOLS:
                failures.append("too_many_symbols")
    return {
        "allowed": not failures,
        "terminal_access_status": "not_attempted" if not failures else "blocked_by_gate",
        "failures": failures,
        "symbol_map": _public_symbol_map_result(symbol_map_result),
        "terminal_contacted": False,
        "operation": "read_only_export",
        "requires_terminal_access": requires_terminal_access,
        "ci_gate_scope": "real_terminal_access",
    }


def export_mt5_bars_readonly(
    *,
    symbol_map_path: Path,
    timeframe: str,
    start: datetime,
    end: datetime,
    output: Path,
    confirm_local_terminal: bool,
    bridge: Mt5ReadOnlyBridge | None = None,
    repo_root: Path | None = None,
    export_time: datetime | None = None,
) -> dict[str, Any]:
    repo_root = (repo_root or Path.cwd()).resolve()
    output = _repo_relative_path(output, repo_root)
    bridge = bridge or OptionalMetaTrader5ReadOnlyAdapter()
    requires_terminal_access = _bridge_requires_terminal_access(bridge)
    gate = evaluate_mt5_readonly_gates(
        symbol_map_path=symbol_map_path,
        output=output,
        start=start,
        end=end,
        timeframe=timeframe,
        confirm_local_terminal=confirm_local_terminal,
        requires_terminal_access=requires_terminal_access,
        repo_root=repo_root,
    )
    if not gate["allowed"]:
        return {"status": "blocked_by_gate", **gate}
    symbol_map_result = validate_mt5_readonly_symbol_map(symbol_map_path)
    entries = [
        entry
        for entry in symbol_map_result["entries"]
        if isinstance(entry, Mt5SymbolMapEntry) and entry.enabled
    ]
    init = bridge.initialize_readonly()
    if init.get("terminal_access_status") != "read_only_ready":
        return {"status": "terminal_unavailable", **init}
    try:
        rows: list[dict[str, Any]] = []
        symbols: list[str] = []
        first_seen = export_time or datetime.now(UTC)
        for entry in entries:
            symbols.append(entry.mt5_symbol)
            bars = bridge.copy_rates_range(entry.mt5_symbol, timeframe, start, end)
            if len(bars) > MAX_BARS_PER_SYMBOL:
                return {"status": "blocked_by_gate", "failures": ["too_many_bars"]}
            seen_times: set[datetime] = set()
            for bar in bars:
                if bar.time in seen_times:
                    return {"status": "invalid_bars", "error": "duplicate timestamps"}
                seen_times.add(bar.time)
                rows.append(_bar_contract_row(entry, timeframe, bar, first_seen))
        _write_export_package(output, rows, symbol_map_result, timeframe, start, end, symbols)
        manifest_path = output / "manifest.json"
        return {
            "status": "exported",
            "contract_name": MARKET_BARS_CONTRACT_NAME,
            "timeframe": timeframe,
            "mapped_symbol_count": len(entries),
            "bar_count": len(rows),
            "output": _safe_relative_output(output, repo_root),
            "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
            "terminal_contacted": True,
            "account_access": "not_supported",
            "order_execution": "disabled",
            "not_investment_advice": True,
        }
    finally:
        bridge.shutdown()


def _bar_contract_row(
    entry: Mt5SymbolMapEntry,
    timeframe: str,
    bar: Mt5RateBar,
    first_seen: datetime,
) -> dict[str, Any]:
    start = bar.time.astimezone(UTC)
    end = start + timedelta(seconds=SUPPORTED_TIMEFRAMES[timeframe])
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        raise Mt5ReadOnlyPolicyViolation("invalid OHLC values")
    if bar.high < max(bar.open, bar.low, bar.close) or bar.low > min(bar.open, bar.high, bar.close):
        raise Mt5ReadOnlyPolicyViolation("invalid OHLC ordering")
    if bar.tick_volume < 0:
        raise Mt5ReadOnlyPolicyViolation("negative historical bar volume")
    return {
        "bar_id": (
            f"mt5-readonly|{entry.profile_id}|{entry.canonical_asset_id}|"
            f"{timeframe}|{start.isoformat()}"
        ),
        "asset_id": entry.canonical_asset_id,
        "provider_symbol": entry.mt5_symbol,
        "session_date": start.date().isoformat(),
        "bar_start_at": start.isoformat(),
        "bar_end_at": end.isoformat(),
        "timezone": "UTC",
        "open": str(_q(bar.open)),
        "high": str(_q(bar.high)),
        "low": str(_q(bar.low)),
        "close": str(_q(bar.close)),
        "volume": str(_q(bar.tick_volume)),
        "quote_volume": None,
        "source_profile": f"mt5-readonly:{entry.profile_id}",
        "first_seen_at": first_seen.astimezone(UTC).isoformat(),
        "available_at": (end + EXPORT_LATENCY).isoformat(),
        "synthetic_data": False,
        "schema_version": MARKET_BARS_CONTRACT_NAME,
    }


def _write_export_package(
    output: Path,
    rows: list[dict[str, Any]],
    symbol_map_result: dict[str, Any],
    timeframe: str,
    start: datetime,
    end: datetime,
    symbols: list[str],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    bars_path = output / "bars.jsonl"
    bars_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "contract_name": MARKET_BARS_CONTRACT_NAME,
        "adapter_version": READONLY_ADAPTER_VERSION,
        "timeframe": timeframe,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "bar_count": len(rows),
        "mapped_asset_count": symbol_map_result["mapped_asset_count"],
        "symbols": symbols,
        "bars_sha256": sha256_bytes(bars_path.read_bytes()),
        "account_access": "not_supported",
        "order_execution": "disabled",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _normalize_symbol_map_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for old, new in LEGACY_SYMBOL_MAP_ALIASES.items():
        if old in normalized and new not in normalized:
            normalized[new] = normalized.pop(old)
    return normalized


def _scan_secret_like_values(row: dict[str, Any], errors: list[str], index: int) -> None:
    for field, value in row.items():
        text = str(value).lower()
        if field in {"notes", "display_name"} and any(
            marker in text for marker in SECRET_VALUE_MARKERS
        ):
            errors.append(f"mapping {index} contains secret-like value in {field}")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _public_symbol_map_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {key: value for key, value in result.items() if key != "entries"}


def _under_local_export_root(path: Path, repo_root: Path) -> bool:
    resolved = _repo_relative_path(path, repo_root).resolve()
    root = (repo_root / LOCAL_EXPORT_ROOT).resolve()
    return resolved == root or root in resolved.parents


def _repo_relative_path(path: Path, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _bridge_requires_terminal_access(bridge: Mt5ReadOnlyBridge) -> bool:
    return bool(getattr(bridge, "requires_terminal_access", True))


def _safe_relative_output(path: Path, repo_root: Path) -> str:
    try:
        return (
            _repo_relative_path(path, repo_root)
            .resolve()
            .relative_to(repo_root.resolve())
            .as_posix()
        )
    except ValueError:
        return "<outside-repository>"


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise Mt5ReadOnlyPolicyViolation("datetime must be timezone-aware")
    if parsed.utcoffset() != timedelta(0):
        raise Mt5ReadOnlyPolicyViolation("datetime must be UTC")
    return parsed.astimezone(UTC)


def parse_cli_utc_datetime(value: str) -> datetime:
    return _parse_timestamp(value)


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def _safe_version(version: object) -> str | None:
    if version is None:
        return None
    if isinstance(version, (tuple, list)):
        return ".".join(str(part) for part in version)
    return str(version)


def _sanitize_error(error: object) -> str | None:
    if error is None:
        return None
    text = str(error)
    for marker in SECRET_VALUE_MARKERS:
        text = text.replace(marker, "<redacted>")
    return text[:160]


def _terminal_info_to_safe_dict(info: object) -> dict[str, Any]:
    if info is None:
        return {"terminal_access_status": "terminal_unavailable"}
    data = _object_to_dict(info)
    return {
        "terminal_access_status": "read_only_ready",
        "build": data.get("build"),
        "version": data.get("version"),
        "connected": data.get("connected"),
    }


def _symbol_info_to_safe_dict(symbol: str, info: object) -> dict[str, Any]:
    data = _object_to_dict(info)
    return {
        "symbol": symbol,
        "selected": bool(data.get("select", data.get("selected", False))),
        "visible": bool(data.get("visible", False)),
        "digits": data.get("digits"),
        "point": data.get("point"),
        "currency_base": data.get("currency_base"),
        "currency_profit": data.get("currency_profit"),
        "currency_margin": data.get("currency_margin"),
    }


def _object_to_dict(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {
        name: getattr(value, name)
        for name in dir(value)
        if not name.startswith("_") and not callable(getattr(value, name))
    }


def _rate_bar_from_raw(row: object) -> Mt5RateBar:
    data = _object_to_dict(row)
    timestamp = data["time"]
    if isinstance(timestamp, datetime):
        dt = timestamp.astimezone(UTC)
    else:
        dt = datetime.fromtimestamp(int(timestamp), UTC)
    return Mt5RateBar(
        time=dt,
        open=Decimal(str(data["open"])),
        high=Decimal(str(data["high"])),
        low=Decimal(str(data["low"])),
        close=Decimal(str(data["close"])),
        tick_volume=Decimal(str(data.get("tick_volume", data.get("volume", 0)))),
        spread=Decimal(str(data["spread"])) if data.get("spread") is not None else None,
        real_volume=Decimal(str(data["real_volume"]))
        if data.get("real_volume") is not None
        else None,
    )
