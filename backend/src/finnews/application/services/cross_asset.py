# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import yaml

from finnews.domain.entities import (
    Asset,
    AssetImpactHypothesis,
    AssetRelationship,
    BrokerSymbolMapping,
    CrossAssetEvent,
    MarketSignalCandidate,
    ProviderSymbol,
    SignalPublicationRun,
    SymbolAlias,
)
from finnews.domain.enums import (
    AssetClass,
    AssetStatus,
    CrossAssetEventFamily,
    ImpactDirection,
    ImpactHorizon,
    ImpactRelationshipType,
    ResearchSignalStatus,
    SymbolNamespace,
)

CONTRACT_NAME = "finnews-market-signal-v1"
CONTRACT_VERSION = "1.0.0"
ASSET_SCHEMA_VERSION = "cross-asset-v1"
SIGNAL_SCHEMA_VERSION = "market-signal-v1"
FIXTURE_VERSION = "cross-asset-demo-v1"
GENERATED_AT = datetime(2026, 6, 23, 0, 0, tzinfo=UTC)
PACKAGE_FILES = ["manifest.json", "assets.json", "event_impacts.jsonl", "signals.jsonl"]
LOCAL_SIGNAL_ROOT = ".finnews-market-signals"
ALLOWED_SYMBOL_MAP_FIELDS = {
    "canonical_asset_id",
    "profile_id",
    "broker_profile_id",
    "mt5_symbol",
    "enabled",
    "display_name",
    "notes",
    "timezone",
    "local_note",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


FORBIDDEN_SYMBOL_MAP_FIELDS = {
    "account_id",
    "login",
    "password",
    "server",
    "broker_server",
    "server_password",
    "terminal_path",
    "account",
    "account_number",
    "investor_password",
    "api_key",
    "volume",
    "lot",
    "lot_size",
    "leverage",
    "margin",
    "price",
    "entry_price",
    "order_type",
    "action",
    "stop_loss",
    "take_profit",
    "sl",
    "tp",
    "risk_limits",
    "position_id",
    "order_ticket",
    "execute",
    "execute_now",
    "buy",
    "sell",
    "close_position",
}
FORBIDDEN_SIGNAL_FIELDS = {
    "account_id",
    "account",
    "account_number",
    "broker_server",
    "login",
    "password",
    "investor_password",
    "api_key",
    "order",
    "order_type",
    "order_request",
    "position",
    "position_id",
    "position_size",
    "order_ticket",
    "volume",
    "lot",
    "lot_size",
    "leverage",
    "margin",
    "price",
    "entry_price",
    "stop_loss",
    "take_profit",
    "sl",
    "tp",
    "ticket",
    "trade_action",
    "action",
    "execute",
    "execute_now",
    "buy",
    "sell",
    "close_position",
}
ALLOWED_ASSET_FIELDS = {
    "asset_id",
    "display_name",
    "asset_class",
    "canonical_symbol",
    "home_venue",
    "country_region",
    "base_currency",
    "quote_currency",
    "parent_asset_id",
    "expiry",
    "contract_metadata",
    "status",
    "synthetic",
    "provenance",
    "schema_version",
    "id",
}
ALLOWED_IMPACT_FIELDS = {
    "impact_id",
    "event_id",
    "asset_id",
    "relationship_type",
    "direction",
    "impact_strength",
    "confidence",
    "horizon",
    "evidence_codes",
    "provider",
    "provider_version",
    "information_cutoff_at",
    "created_at",
    "expires_at",
    "status",
    "rejection_reason",
    "uncertainty_reason",
    "synthetic",
    "id",
}
ALLOWED_SIGNAL_FIELDS = {
    "signal_id",
    "impact_id",
    "event_id",
    "asset_id",
    "direction",
    "horizon",
    "status",
    "confidence",
    "score",
    "information_cutoff_at",
    "generated_at",
    "expires_at",
    "provider",
    "provider_version",
    "evidence_codes",
    "quality_tags",
    "risk_tags",
    "payload_hash",
    "idempotency_key",
    "synthetic",
    "id",
}


class CrossAssetError(ValueError):
    pass


@dataclass(frozen=True)
class AliasResolution:
    status: str
    namespace: str
    symbol: str
    matches: list[dict[str, object]]
    confidence: float | None
    evidence: list[str]


@dataclass(frozen=True)
class CrossAssetDataset:
    assets: list[Asset]
    aliases: list[SymbolAlias]
    provider_symbols: list[ProviderSymbol]
    broker_mappings: list[BrokerSymbolMapping]
    relationships: list[AssetRelationship]
    events: list[CrossAssetEvent]
    impacts: list[AssetImpactHypothesis]
    signals: list[MarketSignalCandidate]
    publication_run: SignalPublicationRun


def build_cross_asset_demo() -> CrossAssetDataset:
    assets = _build_assets()
    aliases, provider_symbols, broker_mappings = _build_aliases(assets)
    relationships = _build_relationships(assets)
    events = _build_events()
    impacts = _build_impacts(events, assets)
    signals = _build_signals(impacts)
    manifest_hash = sha256_text(
        canonical_json(
            {
                "assets": len(assets),
                "events": len(events),
                "impacts": len(impacts),
                "signals": len(signals),
                "contract": CONTRACT_VERSION,
            }
        )
    )
    run = SignalPublicationRun(
        run_id="synthetic-market-signal-run-v1",
        contract_name=CONTRACT_NAME,
        contract_version=CONTRACT_VERSION,
        generated_at=GENERATED_AT,
        count=len(signals),
        status="completed",
        manifest_hash=manifest_hash,
        file_hashes={},
        synthetic=True,
        id=_stable_uuid("signal-run", manifest_hash),
    )
    return CrossAssetDataset(
        assets=assets,
        aliases=aliases,
        provider_symbols=provider_symbols,
        broker_mappings=broker_mappings,
        relationships=relationships,
        events=events,
        impacts=impacts,
        signals=signals,
        publication_run=run,
    )


def cross_asset_static_payload() -> dict[str, Any]:
    dataset = build_cross_asset_demo()
    overview = cross_asset_overview(dataset)
    return {
        "cross-asset-overview": overview,
        "assets": [_asset_row(asset) for asset in dataset.assets],
        "asset-aliases": [_alias_row(alias) for alias in dataset.aliases],
        "asset-relationships": [_relationship_row(row) for row in dataset.relationships],
        "cross-asset-events": [_event_row(row) for row in dataset.events],
        "event-impacts": [_impact_row(row) for row in dataset.impacts],
        "market-signals": [_signal_row(row) for row in dataset.signals],
        "mt5-readiness": mt5_readiness(dataset),
        "market-signal-contract-example": market_signal_contract_example(dataset),
    }


def cross_asset_overview(dataset: CrossAssetDataset | None = None) -> dict[str, Any]:
    dataset = dataset or build_cross_asset_demo()
    active_signals = [
        signal for signal in dataset.signals if signal.status is not ResearchSignalStatus.EXPIRED
    ]
    return {
        "product_positioning": (
            "FinNews Intelligence Platform is a local-first cross-asset financial "
            "information and event-intelligence platform for U.S. equities, ETFs, "
            "indices, FX, gold, commodities, futures, crypto assets, and "
            "macroeconomic policy."
        ),
        "synthetic_data": True,
        "not_investment_advice": True,
        "no_execution": True,
        "mt5_terminal_connection": "not_implemented",
        "order_execution": "disabled",
        "asset_count": len(dataset.assets),
        "event_count": len(dataset.events),
        "impact_hypothesis_count": len(dataset.impacts),
        "signal_candidate_count": len(dataset.signals),
        "asset_class_counts": _counts(asset.asset_class.value for asset in dataset.assets),
        "event_family_counts": _counts(event.event_family.value for event in dataset.events),
        "impact_direction_counts": _counts(impact.direction.value for impact in dataset.impacts),
        "impact_horizon_counts": _counts(impact.horizon.value for impact in dataset.impacts),
        "signal_status_counts": _counts(signal.status.value for signal in dataset.signals),
        "active_signal_count": len(active_signals),
        "expired_signal_count": len(dataset.signals) - len(active_signals),
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "fixture_version": FIXTURE_VERSION,
        "official_market_data": False,
        "live_prices": False,
        "optional_integrations": ["A-share point-in-time feature export"],
    }


def resolve_asset_alias(namespace: str, symbol: str) -> AliasResolution:
    try:
        parsed_namespace = SymbolNamespace(namespace)
    except ValueError as exc:
        raise CrossAssetError(f"unknown alias namespace: {namespace}") from exc
    dataset = build_cross_asset_demo()
    normalized = normalize_symbol(symbol, parsed_namespace)
    matches = [
        alias
        for alias in dataset.aliases
        if alias.namespace is parsed_namespace
        and alias.active
        and normalize_symbol(alias.symbol, parsed_namespace) == normalized
    ]
    evidence = [f"normalized:{normalized}", f"namespace:{parsed_namespace.value}"]
    if not matches:
        return AliasResolution(
            status="unresolved",
            namespace=parsed_namespace.value,
            symbol=symbol,
            matches=[],
            confidence=None,
            evidence=evidence,
        )
    rows = [_alias_match_row(alias) for alias in matches]
    if len({row["asset_id"] for row in rows}) > 1:
        return AliasResolution(
            status="ambiguous",
            namespace=parsed_namespace.value,
            symbol=symbol,
            matches=rows,
            confidence=min(alias.confidence for alias in matches),
            evidence=[*evidence, "multiple_active_matches"],
        )
    return AliasResolution(
        status="resolved",
        namespace=parsed_namespace.value,
        symbol=symbol,
        matches=rows,
        confidence=max(alias.confidence for alias in matches),
        evidence=[*evidence, "single_active_match"],
    )


def normalize_symbol(symbol: str, namespace: SymbolNamespace) -> str:
    text = symbol.strip()
    if namespace in {SymbolNamespace.CANONICAL, SymbolNamespace.RESEARCH}:
        return text.upper()
    if namespace is SymbolNamespace.SEC_CIK_OR_ISSUER:
        return text.upper().replace(" ", "")
    if namespace is SymbolNamespace.MT5_BROKER_LOCAL:
        return text
    return text.upper()


def validate_mt5_symbol_map(path: Path) -> dict[str, Any]:
    resolved_path = path
    if not resolved_path.is_file() and not path.is_absolute():
        repo_relative = _repo_root() / path
        if repo_relative.is_file():
            resolved_path = repo_relative
    if not resolved_path.is_file():
        raise CrossAssetError("symbol map file does not exist")
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8")) or {}
    mappings = payload.get("mappings", payload if isinstance(payload, list) else [])
    if not isinstance(mappings, list):
        raise CrossAssetError("symbol map mappings must be a list")
    assets = {asset.asset_id for asset in build_cross_asset_demo().assets}
    broker_symbol_seen: set[tuple[str, str]] = set()
    errors: list[str] = []
    valid_count = 0
    for index, row in enumerate(mappings, start=1):
        if not isinstance(row, dict):
            errors.append(f"mapping {index} must be an object")
            continue
        unknown = set(row) - ALLOWED_SYMBOL_MAP_FIELDS
        forbidden = set(row) & FORBIDDEN_SYMBOL_MAP_FIELDS
        if unknown:
            errors.append(f"mapping {index} has unknown fields: {', '.join(sorted(unknown))}")
        if forbidden:
            errors.append(f"mapping {index} has forbidden fields: {', '.join(sorted(forbidden))}")
        asset_id = str(row.get("canonical_asset_id", ""))
        broker_profile_id = str(row.get("profile_id") or row.get("broker_profile_id", ""))
        mt5_symbol = str(row.get("mt5_symbol", ""))
        if asset_id not in assets:
            errors.append(f"mapping {index} references unknown asset: {asset_id}")
        if not broker_profile_id or not mt5_symbol:
            errors.append(f"mapping {index} missing broker profile or MT5 symbol")
        key = (broker_profile_id, mt5_symbol)
        if bool(row.get("enabled", False)):
            if key in broker_symbol_seen:
                errors.append(f"duplicate active broker symbol: {broker_profile_id}:{mt5_symbol}")
            broker_symbol_seen.add(key)
        valid_count += 1
    return {
        "valid": not errors,
        "mapping_count": valid_count,
        "errors": errors,
        "terminal_contacted": False,
        "mt5_imported": False,
        "allowed_fields": sorted(ALLOWED_SYMBOL_MAP_FIELDS),
        "forbidden_fields_checked": sorted(FORBIDDEN_SYMBOL_MAP_FIELDS),
    }


def mt5_readiness(dataset: CrossAssetDataset | None = None) -> dict[str, Any]:
    dataset = dataset or build_cross_asset_demo()
    mapped_assets = {mapping.asset_id for mapping in dataset.broker_mappings if mapping.enabled}
    return {
        "signal_contract_status": "ready",
        "symbol_map_schema_status": "ready_offline",
        "canonical_mapping_coverage": {
            "mapped_assets": len(mapped_assets),
            "total_assets": len(dataset.assets),
        },
        "utc_policy": "required_for_future_tick_bar_normalization",
        "terminal_adapter_status": "optional_readonly_cli_only",
        "mt5_terminal_connection": "not attempted",
        "execution_status": "disabled",
        "order_execution": "disabled",
        "credentials_accepted": False,
        "account_data_access": "not supported",
        "order_routes": False,
        "notes": [
            "Read-only bridge access is local CLI-only and disabled by default.",
            "Broker-specific symbols remain local configuration and are never assumed globally.",
        ],
    }


def market_signal_contract_example(dataset: CrossAssetDataset | None = None) -> dict[str, Any]:
    dataset = dataset or build_cross_asset_demo()
    first_signal = dataset.signals[0]
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "signal_schema_version": SIGNAL_SCHEMA_VERSION,
        "example_signal": _signal_row(first_signal),
        "forbidden_execution_fields": sorted(FORBIDDEN_SIGNAL_FIELDS),
        "no_execution": True,
        "not_investment_advice": True,
    }


def build_signal_package(dataset: CrossAssetDataset | None = None) -> dict[str, bytes]:
    dataset = dataset or build_cross_asset_demo()
    assets = [_asset_row(asset) for asset in dataset.assets]
    impacts = [_impact_row(row) for row in dataset.impacts]
    signals = [_signal_row(row) for row in dataset.signals]
    manifest = {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "signal_schema_version": SIGNAL_SCHEMA_VERSION,
        "fixture_version": FIXTURE_VERSION,
        "generated_at": GENERATED_AT.isoformat(),
        "synthetic_data": True,
        "not_investment_advice": True,
        "no_execution": True,
        "asset_count": len(assets),
        "event_impact_count": len(impacts),
        "signal_count": len(signals),
        "files": [],
    }
    files = {
        "assets.json": _json_bytes(assets),
        "event_impacts.jsonl": _jsonl_bytes(impacts),
        "signals.jsonl": _jsonl_bytes(signals),
    }
    file_hashes = {name: sha256_bytes(data) for name, data in files.items()}
    manifest["files"] = [
        {"path": name, "sha256": file_hashes[name], "size_bytes": len(files[name])}
        for name in ["assets.json", "event_impacts.jsonl", "signals.jsonl"]
    ]
    manifest["package_content_hash"] = sha256_text(
        "\n".join(f"{name}:{file_hashes[name]}" for name in sorted(file_hashes))
    )
    return {"manifest.json": _json_bytes(manifest), **files}


def write_signal_package(output: Path, dataset: CrossAssetDataset | None = None) -> dict[str, Any]:
    _validate_local_signal_output(output)
    if output.exists() and any(output.iterdir()):
        raise CrossAssetError("output directory already exists and is not empty")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        files = build_signal_package(dataset)
        for name, data in files.items():
            (temp_root / name).write_bytes(data)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(temp_root), str(output))
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    return validate_signal_package(output)


def validate_signal_package(path: Path) -> dict[str, Any]:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("contract_name") != CONTRACT_NAME:
        raise CrossAssetError("unsupported signal contract name")
    if manifest.get("contract_version") != CONTRACT_VERSION:
        raise CrossAssetError("unsupported signal contract version")
    if manifest.get("no_execution") is not True:
        raise CrossAssetError("signal package must declare no_execution")
    hashes: dict[str, str] = {}
    for file_info in manifest.get("files", []):
        name = str(file_info["path"])
        _validate_package_file_name(name)
        data = (path / name).read_bytes()
        if len(data) != int(file_info["size_bytes"]):
            raise CrossAssetError(f"file size mismatch for {name}")
        actual = sha256_bytes(data)
        if actual != file_info["sha256"]:
            raise CrossAssetError(f"file hash mismatch for {name}")
        hashes[name] = actual
    recomputed = sha256_text("\n".join(f"{name}:{hashes[name]}" for name in sorted(hashes)))
    if manifest.get("package_content_hash") != recomputed:
        raise CrossAssetError("package content hash mismatch")
    signals = [
        json.loads(line)
        for line in (path / "signals.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assets = json.loads((path / "assets.json").read_text(encoding="utf-8"))
    impacts = [
        json.loads(line)
        for line in (path / "event_impacts.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    asset_ids = {str(row["asset_id"]) for row in assets}
    impact_ids = {str(row["impact_id"]) for row in impacts}
    event_ids = {str(row["event_id"]) for row in impacts}
    for row in assets:
        _validate_allowed_fields(row, ALLOWED_ASSET_FIELDS, "asset")
        if row.get("synthetic") is not True:
            raise CrossAssetError("asset row must declare synthetic=true")
    for row in impacts:
        _validate_allowed_fields(row, ALLOWED_IMPACT_FIELDS, "event impact")
        _reject_forbidden_fields(row, "event impact")
        if row["asset_id"] not in asset_ids:
            raise CrossAssetError(f"impact references unknown asset: {row['asset_id']}")
        cutoff = _parse_aware_timestamp(str(row["information_cutoff_at"]))
        created = _parse_aware_timestamp(str(row["created_at"]))
        expires = _parse_aware_timestamp(str(row["expires_at"]))
        if cutoff > created:
            raise CrossAssetError("impact information_cutoff_at after created_at")
        if expires <= created:
            raise CrossAssetError("impact expires_at must be after created_at")
        if row["confidence"] is not None and not 0 <= float(row["confidence"]) <= 1:
            raise CrossAssetError("impact confidence out of bounds")
        if not 0 <= float(row["impact_strength"]) <= 1:
            raise CrossAssetError("impact strength out of bounds")
        if not row["evidence_codes"]:
            raise CrossAssetError("impact evidence_codes must be non-empty")
    for row in signals:
        _validate_allowed_fields(row, ALLOWED_SIGNAL_FIELDS, "signal")
        _reject_forbidden_fields(row, "signal")
        if row["asset_id"] not in asset_ids:
            raise CrossAssetError(f"signal references unknown asset: {row['asset_id']}")
        if row["impact_id"] not in impact_ids:
            raise CrossAssetError(f"signal references unknown impact: {row['impact_id']}")
        if row["event_id"] not in event_ids:
            raise CrossAssetError(f"signal references unknown event: {row['event_id']}")
        cutoff = _parse_aware_timestamp(str(row["information_cutoff_at"]))
        generated = _parse_aware_timestamp(str(row["generated_at"]))
        expires = _parse_aware_timestamp(str(row["expires_at"]))
        if cutoff > generated:
            raise CrossAssetError("signal information_cutoff_at after generated_at")
        if generated >= expires:
            raise CrossAssetError("signal generated_at must be before expires_at")
        if row["confidence"] is not None and not 0 <= float(row["confidence"]) <= 1:
            raise CrossAssetError("signal confidence out of bounds")
    return {
        "valid": True,
        "contract_name": manifest["contract_name"],
        "contract_version": manifest["contract_version"],
        "package_content_hash": manifest["package_content_hash"],
        "asset_count": manifest["asset_count"],
        "event_impact_count": manifest["event_impact_count"],
        "signal_count": manifest["signal_count"],
        "no_execution": True,
    }


def _validate_allowed_fields(row: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(row) - allowed
    if unknown:
        raise CrossAssetError(f"{label} contains unknown fields: {', '.join(sorted(unknown))}")


def _reject_forbidden_fields(row: dict[str, Any], label: str) -> None:
    forbidden = set(row) & FORBIDDEN_SIGNAL_FIELDS
    if forbidden:
        raise CrossAssetError(f"{label} contains forbidden fields: {', '.join(sorted(forbidden))}")


def _parse_aware_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CrossAssetError("timestamp must be timezone-aware")
    return parsed


def trading_surface_audit(root: Path) -> dict[str, Any]:
    scan_root = root.resolve()
    repo_root = _repo_root()
    patterns = [
        "MetaTrader5",
        "initialize(",
        "login(",
        "order_check(",
        "order_send(",
        "TRADE_ACTION",
        "ORDER_TYPE",
        "account password",
        "investor password",
        "lot size",
        "stop loss",
        "take profit",
    ]
    allowed_docs = {
        "docs/MT5_INTEGRATION_BOUNDARY.md",
        "docs/MT5_FUTURE_RISK_CONTROLS.md",
        "docs/TRADING_SURFACE_AUDIT.md",
        "docs/MT5_READONLY_BRIDGE.md",
        "docs/MT5_READONLY_LOCAL_SETUP.md",
        "docs/MT5_READONLY_SURFACE_AUDIT.md",
        "docs/M4A_EXECUTION_PLAN.md",
        "docs/M4A_RELEASE_AUDIT.md",
        "docs/M3A_REVISED_EXECUTION_PLAN.md",
        "contracts/finnews-market-signal/v1/README.md",
        "contracts/finnews-market-signal/v1/signal.schema.json",
        "finnews_revised_m3a_cross_asset_mt5_foundation_prompt.md",
    }
    allowed_tests = {
        "backend/tests/unit/test_cross_asset.py",
        "backend/tests/unit/test_mt5_readonly.py",
        "backend/tests/contract/test_cross_asset_api_cli.py",
        "backend/tests/contract/test_mt5_readonly_api_cli.py",
    }
    findings: list[dict[str, object]] = []
    disallowed: list[dict[str, object]] = []
    skipped_parts = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        ".finnews-market-signals",
        ".finnews-mt5-readonly-exports",
        ".finnews-research-exports",
        ".finnews-artifacts",
    }
    for path in sorted(scan_root.rglob("*")):
        if path.is_dir() or skipped_parts.intersection(path.parts):
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".yaml", ".yml", ".vue", ".ts"}:
            continue
        try:
            relative = path.relative_to(repo_root).as_posix()
        except ValueError:
            relative = path.relative_to(scan_root).as_posix()
        if relative.endswith("_prompt.md"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern in text:
                record: dict[str, object] = {"path": relative, "pattern": pattern}
                findings.append(record)
                is_self_audit_pattern = relative in {
                    "backend/src/finnews/application/services/cross_asset.py",
                    "backend/src/finnews/application/services/cross_asset_release_audit.py",
                } and pattern in {
                    "MetaTrader5",
                    "initialize(",
                    "login(",
                    "order_check(",
                    "order_send(",
                    "TRADE_ACTION",
                    "ORDER_TYPE",
                    "account password",
                    "investor password",
                    "lot size",
                    "stop loss",
                    "take profit",
                }
                is_readonly_adapter_pattern = (
                    relative == "backend/src/finnews/application/services/mt5_readonly.py"
                    and pattern in {"MetaTrader5", "initialize("}
                )
                if (
                    relative not in allowed_docs
                    and relative not in allowed_tests
                    and not is_self_audit_pattern
                    and not is_readonly_adapter_pattern
                ):
                    disallowed.append(record)
    return {
        "valid": not disallowed,
        "patterns_checked": patterns,
        "finding_count": len(findings),
        "disallowed": disallowed,
        "mt5_import_present": False,
        "terminal_contact_present": False,
        "order_route_present": False,
    }


def persist_cross_asset_demo(repository: Any, dataset: CrossAssetDataset | None = None) -> None:
    dataset = dataset or build_cross_asset_demo()
    if not hasattr(repository, "upsert_cross_asset_dataset"):
        return
    repository.upsert_cross_asset_dataset(
        dataset.assets,
        dataset.aliases,
        dataset.provider_symbols,
        dataset.broker_mappings,
        dataset.relationships,
        dataset.events,
        dataset.impacts,
        dataset.signals,
        dataset.publication_run,
    )


def _build_assets() -> list[Asset]:
    specs: list[
        tuple[str, str, AssetClass, str | None, str | None, str, str | None, str | None]
    ] = [
        (
            "US-EQ-ALPHA",
            "Alpha Robotics Synthetic Corp",
            AssetClass.US_EQUITY,
            "ALPR",
            "XNYS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-BETA",
            "Beta Cloud Synthetic Inc",
            AssetClass.US_EQUITY,
            "BETC",
            "XNAS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-GAMMA",
            "Gamma Health Synthetic Co",
            AssetClass.US_EQUITY,
            "GMHL",
            "XNYS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-DELTA",
            "Delta Retail Synthetic Group",
            AssetClass.US_EQUITY,
            "DLRT",
            "XNAS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-EPSILON",
            "Epsilon Energy Synthetic Ltd",
            AssetClass.US_EQUITY,
            "EPEN",
            "XNYS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-ZETA",
            "Zeta Industrial Synthetic Works",
            AssetClass.US_EQUITY,
            "ZTIN",
            "XNYS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-OMEGA",
            "Omega Payments Synthetic Holdings",
            AssetClass.US_EQUITY,
            "OMPY",
            "XNAS",
            "US",
            "USD",
            None,
        ),
        (
            "US-EQ-SIGMA",
            "Sigma Chips Synthetic Corp",
            AssetClass.US_EQUITY,
            "SGCH",
            "XNAS",
            "US",
            "USD",
            None,
        ),
        (
            "ETF-US-LARGE",
            "Synthetic US Large Equity ETF Proxy",
            AssetClass.ETF,
            "SULG",
            "ARCX",
            "US",
            "USD",
            None,
        ),
        (
            "ETF-US-TECH",
            "Synthetic Technology ETF Proxy",
            AssetClass.ETF,
            "STEC",
            "ARCX",
            "US",
            "USD",
            None,
        ),
        (
            "ETF-US-BOND",
            "Synthetic Treasury ETF Proxy",
            AssetClass.ETF,
            "STSY",
            "ARCX",
            "US",
            "USD",
            None,
        ),
        (
            "ETF-GLD-PROXY",
            "Synthetic Gold ETF Proxy",
            AssetClass.ETF,
            "SGLD",
            "ARCX",
            "US",
            "USD",
            None,
        ),
        (
            "ETF-OIL-PROXY",
            "Synthetic Energy ETF Proxy",
            AssetClass.ETF,
            "SOIL",
            "ARCX",
            "US",
            "USD",
            None,
        ),
        (
            "IDX-US-LARGE",
            "Synthetic US Large-Cap Index",
            AssetClass.EQUITY_INDEX,
            "SUSL",
            "INDEX",
            "US",
            "USD",
            None,
        ),
        (
            "IDX-US-TECH",
            "Synthetic US Technology Index",
            AssetClass.EQUITY_INDEX,
            "SUST",
            "INDEX",
            "US",
            "USD",
            None,
        ),
        (
            "IDX-US-VOL",
            "Synthetic US Volatility Index",
            AssetClass.EQUITY_INDEX,
            "SUVX",
            "INDEX",
            "US",
            "USD",
            None,
        ),
        (
            "FX-EURUSD",
            "Synthetic EUR/USD FX Pair",
            AssetClass.FX,
            "EURUSD",
            "FX",
            "Global",
            "EUR",
            "USD",
        ),
        (
            "FX-USDJPY",
            "Synthetic USD/JPY FX Pair",
            AssetClass.FX,
            "USDJPY",
            "FX",
            "Global",
            "USD",
            "JPY",
        ),
        (
            "FX-GBPUSD",
            "Synthetic GBP/USD FX Pair",
            AssetClass.FX,
            "GBPUSD",
            "FX",
            "Global",
            "GBP",
            "USD",
        ),
        (
            "FX-AUDUSD",
            "Synthetic AUD/USD FX Pair",
            AssetClass.FX,
            "AUDUSD",
            "FX",
            "Global",
            "AUD",
            "USD",
        ),
        (
            "FX-USDCAD",
            "Synthetic USD/CAD FX Pair",
            AssetClass.FX,
            "USDCAD",
            "FX",
            "Global",
            "USD",
            "CAD",
        ),
        (
            "PM-GOLD",
            "Synthetic Gold Spot Proxy",
            AssetClass.PRECIOUS_METAL,
            "XAUUSD",
            "METAL",
            "Global",
            "XAU",
            "USD",
        ),
        (
            "PM-SILVER",
            "Synthetic Silver Spot Proxy",
            AssetClass.PRECIOUS_METAL,
            "XAGUSD",
            "METAL",
            "Global",
            "XAG",
            "USD",
        ),
        (
            "PM-PLATINUM",
            "Synthetic Platinum Spot Proxy",
            AssetClass.PRECIOUS_METAL,
            "XPTUSD",
            "METAL",
            "Global",
            "XPT",
            "USD",
        ),
        (
            "CMD-OIL",
            "Synthetic Crude Oil Proxy",
            AssetClass.COMMODITY,
            "SCOIL",
            "COMMODITY",
            "Global",
            "USD",
            None,
        ),
        (
            "CMD-GAS",
            "Synthetic Natural Gas Proxy",
            AssetClass.COMMODITY,
            "SCGAS",
            "COMMODITY",
            "Global",
            "USD",
            None,
        ),
        (
            "CMD-COPPER",
            "Synthetic Copper Proxy",
            AssetClass.COMMODITY,
            "SCCOP",
            "COMMODITY",
            "Global",
            "USD",
            None,
        ),
        (
            "FUT-ROOT-OIL",
            "Synthetic Oil Futures Root",
            AssetClass.FUTURES_ROOT,
            "SO",
            "FUTURES",
            "US",
            "USD",
            None,
        ),
        (
            "FUT-CONTRACT-OIL-JUL26",
            "Synthetic Oil Futures Jul 2026",
            AssetClass.FUTURES_CONTRACT,
            "SON26",
            "FUTURES",
            "US",
            "USD",
            None,
        ),
        (
            "FUT-ROOT-GOLD",
            "Synthetic Gold Futures Root",
            AssetClass.FUTURES_ROOT,
            "SG",
            "FUTURES",
            "US",
            "USD",
            None,
        ),
        (
            "FUT-CONTRACT-GOLD-AUG26",
            "Synthetic Gold Futures Aug 2026",
            AssetClass.FUTURES_CONTRACT,
            "SGQ26",
            "FUTURES",
            "US",
            "USD",
            None,
        ),
        (
            "CRYPTO-BTC-PROXY",
            "Synthetic Bitcoin-like Crypto Proxy",
            AssetClass.CRYPTO_ASSET,
            "SBTC",
            "CRYPTO",
            "Global",
            "SBTC",
            "USD",
        ),
        (
            "CRYPTO-ETH-PROXY",
            "Synthetic Ether-like Crypto Proxy",
            AssetClass.CRYPTO_ASSET,
            "SETH",
            "CRYPTO",
            "Global",
            "SETH",
            "USD",
        ),
        (
            "CRYPTO-STABLE-PROXY",
            "Synthetic Stablecoin Liquidity Proxy",
            AssetClass.CRYPTO_ASSET,
            "SUSD",
            "CRYPTO",
            "Global",
            "SUSD",
            "USD",
        ),
        (
            "CRYPTO-EXCH-PROXY",
            "Synthetic Exchange Token Proxy",
            AssetClass.CRYPTO_ASSET,
            "SXT",
            "CRYPTO",
            "Global",
            "SXT",
            "USD",
        ),
        (
            "MACRO-CPI-US",
            "Synthetic US CPI Indicator",
            AssetClass.MACRO_INDICATOR,
            "US_CPI_DEMO",
            "MACRO",
            "US",
            "USD",
            None,
        ),
        (
            "MACRO-PAYROLLS-US",
            "Synthetic US Payrolls Indicator",
            AssetClass.MACRO_INDICATOR,
            "US_NFP_DEMO",
            "MACRO",
            "US",
            "USD",
            None,
        ),
        (
            "MACRO-GDP-US",
            "Synthetic US GDP Indicator",
            AssetClass.MACRO_INDICATOR,
            "US_GDP_DEMO",
            "MACRO",
            "US",
            "USD",
            None,
        ),
        (
            "RATE-FED-POLICY",
            "Synthetic Fed Policy Rate",
            AssetClass.INTEREST_RATE,
            "FED_POLICY_DEMO",
            "RATES",
            "US",
            "USD",
            None,
        ),
        (
            "RATE-US10Y",
            "Synthetic US 10Y Yield",
            AssetClass.INTEREST_RATE,
            "US10Y_DEMO",
            "RATES",
            "US",
            "USD",
            None,
        ),
    ]
    root_by_contract = {
        "FUT-CONTRACT-OIL-JUL26": ("FUT-ROOT-OIL", date(2026, 7, 20)),
        "FUT-CONTRACT-GOLD-AUG26": ("FUT-ROOT-GOLD", date(2026, 8, 27)),
    }
    assets = []
    for asset_id, name, asset_class, symbol, venue, region, base, quote in specs:
        parent, expiry = root_by_contract.get(asset_id, (None, None))
        assets.append(
            Asset(
                id=_stable_uuid("asset", asset_id),
                asset_id=asset_id,
                display_name=name,
                asset_class=asset_class,
                canonical_symbol=symbol,
                home_venue=venue,
                country_region=region,
                base_currency=base,
                quote_currency=quote,
                parent_asset_id=parent,
                expiry=expiry,
                contract_metadata={
                    "root": parent,
                    "continuous_series_alias": f"{symbol}_CONT"
                    if asset_class is AssetClass.FUTURES_ROOT
                    else None,
                    "contract_metadata_available": asset_class is AssetClass.FUTURES_CONTRACT,
                },
                status=AssetStatus.ACTIVE,
                synthetic=True,
                provenance={"source": "deterministic synthetic cross-asset fixture"},
                schema_version=ASSET_SCHEMA_VERSION,
            )
        )
    return assets


def _build_aliases(
    assets: list[Asset],
) -> tuple[list[SymbolAlias], list[ProviderSymbol], list[BrokerSymbolMapping]]:
    aliases: list[SymbolAlias] = []
    provider_symbols: list[ProviderSymbol] = []
    broker_mappings: list[BrokerSymbolMapping] = []
    for asset in assets:
        values = [
            (SymbolNamespace.CANONICAL, asset.asset_id),
            (SymbolNamespace.RESEARCH, f"R:{asset.asset_id}"),
            (SymbolNamespace.NEWS_SOURCE, asset.display_name),
        ]
        if asset.canonical_symbol:
            values.append((SymbolNamespace.MARKET_DATA, asset.canonical_symbol))
            values.append((SymbolNamespace.MT5_BROKER_LOCAL, f"DEMO.{asset.canonical_symbol}"))
        if asset.asset_class is AssetClass.US_EQUITY:
            values.append((SymbolNamespace.SEC_CIK_OR_ISSUER, f"DEMO-CIK-{asset.asset_id[-5:]}"))
        for namespace, symbol in values:
            aliases.append(
                SymbolAlias(
                    id=_stable_uuid("alias", asset.asset_id, namespace.value, symbol),
                    asset_id=asset.asset_id,
                    namespace=namespace,
                    symbol=symbol,
                    normalized_symbol=normalize_symbol(symbol, namespace),
                    provider="synthetic_alias_registry",
                    provider_version="1",
                    active=True,
                    confidence=1.0 if namespace is not SymbolNamespace.NEWS_SOURCE else 0.92,
                    provenance={"fixture_version": FIXTURE_VERSION},
                )
            )
            provider_symbols.append(
                ProviderSymbol(
                    id=_stable_uuid("provider-symbol", asset.asset_id, namespace.value, symbol),
                    asset_id=asset.asset_id,
                    namespace=namespace,
                    provider=f"synthetic_{namespace.value}",
                    symbol=symbol,
                    provider_version="1",
                    active=True,
                    provenance={"fixture_version": FIXTURE_VERSION},
                )
            )
        if asset.canonical_symbol:
            broker_mappings.append(
                BrokerSymbolMapping(
                    id=_stable_uuid("broker-map", asset.asset_id),
                    asset_id=asset.asset_id,
                    broker_profile_id="demo-disabled-profile",
                    mt5_symbol=f"DEMO.{asset.canonical_symbol}",
                    enabled=False,
                    provenance={"synthetic": True, "terminal_contacted": False},
                    local_note="Example only; disabled and not broker-specific.",
                )
            )
    for asset_id in ["MACRO-CPI-US", "RATE-FED-POLICY"]:
        aliases.append(
            SymbolAlias(
                id=_stable_uuid("alias", asset_id, "ambiguous", "policy pulse"),
                asset_id=asset_id,
                namespace=SymbolNamespace.NEWS_SOURCE,
                symbol="policy pulse",
                normalized_symbol="POLICY PULSE",
                provider="synthetic_alias_registry",
                provider_version="1",
                active=True,
                confidence=0.55,
                provenance={"fixture_version": FIXTURE_VERSION, "ambiguity_demo": True},
            )
        )
    aliases.append(
        SymbolAlias(
            id=_stable_uuid("alias", "US-EQ-ALPHA", "inactive", "ALPHA OLD"),
            asset_id="US-EQ-ALPHA",
            namespace=SymbolNamespace.NEWS_SOURCE,
            symbol="Alpha Synthetic Old Name",
            normalized_symbol="ALPHA SYNTHETIC OLD NAME",
            provider="synthetic_alias_registry",
            provider_version="1",
            active=False,
            confidence=0.4,
            provenance={"inactive_alias_demo": True},
            valid_to=date(2026, 1, 1),
        )
    )
    return aliases, provider_symbols, broker_mappings


def _build_relationships(assets: list[Asset]) -> list[AssetRelationship]:
    pairs = [
        ("ETF-US-LARGE", "IDX-US-LARGE", ImpactRelationshipType.INDEX_CONSTITUENT),
        ("ETF-US-TECH", "IDX-US-TECH", ImpactRelationshipType.INDEX_CONSTITUENT),
        ("ETF-GLD-PROXY", "PM-GOLD", ImpactRelationshipType.CORRELATION_HYPOTHESIS),
        ("ETF-OIL-PROXY", "CMD-OIL", ImpactRelationshipType.CORRELATION_HYPOTHESIS),
        ("FUT-CONTRACT-OIL-JUL26", "FUT-ROOT-OIL", ImpactRelationshipType.CORRELATION_HYPOTHESIS),
        ("FUT-CONTRACT-GOLD-AUG26", "FUT-ROOT-GOLD", ImpactRelationshipType.CORRELATION_HYPOTHESIS),
        ("RATE-FED-POLICY", "RATE-US10Y", ImpactRelationshipType.RATE_SENSITIVITY),
        ("MACRO-CPI-US", "RATE-FED-POLICY", ImpactRelationshipType.INFLATION_SENSITIVITY),
        ("PM-GOLD", "FX-EURUSD", ImpactRelationshipType.SAFE_HAVEN_HYPOTHESIS),
        ("CRYPTO-BTC-PROXY", "CRYPTO-EXCH-PROXY", ImpactRelationshipType.CORRELATION_HYPOTHESIS),
    ]
    return [
        AssetRelationship(
            id=_stable_uuid("relationship", source, target),
            relationship_id=f"REL-{index:03d}",
            source_asset_id=source,
            target_asset_id=target,
            relationship_type=kind,
            direction="association",
            confidence=0.65,
            active=True,
            provenance={"fixture_version": FIXTURE_VERSION},
            synthetic=True,
        )
        for index, (source, target, kind) in enumerate(pairs, start=1)
    ]


def _build_events() -> list[CrossAssetEvent]:
    families = list(CrossAssetEventFamily)
    events: list[CrossAssetEvent] = []
    for index in range(100):
        family = families[index % len(families)]
        info_time = GENERATED_AT - timedelta(hours=100 - index)
        duplicate_of = "XAE-006" if index == 96 else None
        events.append(
            CrossAssetEvent(
                id=_stable_uuid("cross-event", index),
                event_id=f"XAE-{index + 1:03d}",
                event_family=family,
                event_subtype=f"{family.value}_demo_{index % 5}",
                description=f"Synthetic {family.value.replace('_', ' ')} event {index + 1}",
                information_available_at=info_time,
                affected_region="US" if index % 3 else "Global",
                relevant_currency="USD" if index % 4 else None,
                source_provenance={
                    "source_id": f"synthetic-cross-asset-source-{index % 5}",
                    "metadata_only": True,
                    "article_body_stored": False,
                },
                provider="rule_cross_asset_event_mapper" if index % 9 else "ml_demo_event_mapper",
                provider_version="1",
                confidence=None if index % 17 == 0 else round(0.52 + (index % 40) / 100, 2),
                uncertainty_flags=["missing_confidence"] if index % 17 == 0 else [],
                duplicate_of_event_id=duplicate_of,
                synthetic=True,
            )
        )
    return events


def _asset_targets(event: CrossAssetEvent, assets: list[Asset], count: int) -> list[Asset]:
    by_class: dict[AssetClass, list[Asset]] = {}
    for asset in assets:
        by_class.setdefault(asset.asset_class, []).append(asset)
    preferred = _preferred_asset_classes(event.event_family)
    selected: list[Asset] = []
    for asset_class in preferred:
        bucket = by_class[asset_class]
        selected.append(bucket[int(event.event_id[-3:]) % len(bucket)])
        if len(selected) == count:
            return selected
    for asset in assets:
        if asset not in selected:
            selected.append(asset)
        if len(selected) == count:
            return selected
    return selected


def _preferred_asset_classes(family: CrossAssetEventFamily) -> list[AssetClass]:
    macro = [AssetClass.FX, AssetClass.INTEREST_RATE, AssetClass.EQUITY_INDEX, AssetClass.ETF]
    mapping = {
        CrossAssetEventFamily.MONETARY_POLICY: [
            AssetClass.INTEREST_RATE,
            AssetClass.FX,
            AssetClass.PRECIOUS_METAL,
        ],
        CrossAssetEventFamily.INFLATION: [
            AssetClass.INTEREST_RATE,
            AssetClass.COMMODITY,
            AssetClass.PRECIOUS_METAL,
        ],
        CrossAssetEventFamily.LABOR_MARKET: macro,
        CrossAssetEventFamily.ECONOMIC_GROWTH: [
            AssetClass.EQUITY_INDEX,
            AssetClass.US_EQUITY,
            AssetClass.COMMODITY,
        ],
        CrossAssetEventFamily.LIQUIDITY_FUNDING: [
            AssetClass.INTEREST_RATE,
            AssetClass.ETF,
            AssetClass.CRYPTO_ASSET,
        ],
        CrossAssetEventFamily.FISCAL_POLICY: macro,
        CrossAssetEventFamily.REGULATION_ENFORCEMENT: [
            AssetClass.US_EQUITY,
            AssetClass.ETF,
            AssetClass.CRYPTO_ASSET,
        ],
        CrossAssetEventFamily.CORPORATE_EARNINGS_GUIDANCE: [
            AssetClass.US_EQUITY,
            AssetClass.EQUITY_INDEX,
        ],
        CrossAssetEventFamily.MERGERS_CORPORATE_ACTIONS: [AssetClass.US_EQUITY, AssetClass.ETF],
        CrossAssetEventFamily.COMMODITY_SUPPLY: [
            AssetClass.COMMODITY,
            AssetClass.FUTURES_ROOT,
            AssetClass.FUTURES_CONTRACT,
        ],
        CrossAssetEventFamily.INVENTORY_DEMAND: [
            AssetClass.COMMODITY,
            AssetClass.FUTURES_CONTRACT,
            AssetClass.ETF,
        ],
        CrossAssetEventFamily.GEOPOLITICAL_RISK: [
            AssetClass.PRECIOUS_METAL,
            AssetClass.FX,
            AssetClass.COMMODITY,
        ],
        CrossAssetEventFamily.DERIVATIVES_POSITIONING: [
            AssetClass.FUTURES_ROOT,
            AssetClass.FUTURES_CONTRACT,
            AssetClass.EQUITY_INDEX,
        ],
        CrossAssetEventFamily.EXCHANGE_MARKET_INFRASTRUCTURE: [
            AssetClass.EQUITY_INDEX,
            AssetClass.CRYPTO_ASSET,
            AssetClass.FX,
        ],
        CrossAssetEventFamily.CRYPTO_PROTOCOL_ECOSYSTEM: [AssetClass.CRYPTO_ASSET, AssetClass.ETF],
        CrossAssetEventFamily.CRYPTO_REGULATION: [AssetClass.CRYPTO_ASSET, AssetClass.US_EQUITY],
        CrossAssetEventFamily.IDIOSYNCRATIC_COMPANY_EVENT: [
            AssetClass.US_EQUITY,
            AssetClass.ETF,
            AssetClass.EQUITY_INDEX,
        ],
        CrossAssetEventFamily.OTHER_UNCERTAIN: [AssetClass.MACRO_INDICATOR, AssetClass.FX],
    }
    return mapping[family]


def _build_impacts(
    events: list[CrossAssetEvent], assets: list[Asset]
) -> list[AssetImpactHypothesis]:
    directions = list(ImpactDirection)
    horizons = list(ImpactHorizon)
    relationships = list(ImpactRelationshipType)
    impacts: list[AssetImpactHypothesis] = []
    for event_index, event in enumerate(events):
        target_count = 3 if event_index < 40 else 2
        for target_index, asset in enumerate(_asset_targets(event, assets, target_count)):
            global_index = len(impacts)
            direction = directions[global_index % len(directions)]
            if event.duplicate_of_event_id:
                direction = ImpactDirection.MIXED
            confidence = (
                None if global_index % 31 == 0 else round(0.45 + (global_index % 45) / 100, 2)
            )
            status = "active"
            rejection_reason = None
            uncertainty_reason = None
            if global_index in {13, 37, 79, 111, 159, 211}:
                status = "rejected"
                rejection_reason = "insufficient_context"
            elif global_index in {17, 88, 177}:
                status = "expired"
            if direction is ImpactDirection.UNCERTAIN or confidence is None:
                uncertainty_reason = "ambiguous_or_missing_confidence"
            impacts.append(
                AssetImpactHypothesis(
                    id=_stable_uuid("impact", event.event_id, asset.asset_id, target_index),
                    impact_id=f"IMPACT-{global_index + 1:04d}",
                    event_id=event.event_id,
                    asset_id=asset.asset_id,
                    relationship_type=relationships[global_index % len(relationships)],
                    direction=direction,
                    impact_strength=round(0.1 + (global_index % 9) / 10, 2),
                    confidence=confidence,
                    horizon=horizons[global_index % len(horizons)],
                    evidence_codes=[
                        f"RULE_{event.event_family.value.upper()}",
                        f"ASSET_CLASS_{asset.asset_class.value.upper()}",
                    ],
                    provider="deterministic_impact_rules"
                    if global_index % 7
                    else "ml_demo_impact_ranker",
                    provider_version="1",
                    information_cutoff_at=event.information_available_at,
                    created_at=event.information_available_at + timedelta(minutes=2),
                    expires_at=event.information_available_at + timedelta(days=30),
                    status=status,
                    rejection_reason=rejection_reason,
                    uncertainty_reason=uncertainty_reason,
                    synthetic=True,
                )
            )
    return impacts


def _build_signals(impacts: list[AssetImpactHypothesis]) -> list[MarketSignalCandidate]:
    signals: list[MarketSignalCandidate] = []
    statuses = [
        ResearchSignalStatus.INFORMATIONAL,
        ResearchSignalStatus.RESEARCH,
        ResearchSignalStatus.ABSTAINED,
        ResearchSignalStatus.REJECTED,
        ResearchSignalStatus.EXPIRED,
    ]
    for index, impact in enumerate(impacts[:80]):
        status = statuses[index % len(statuses)]
        if impact.status == "rejected":
            status = ResearchSignalStatus.REJECTED
        elif impact.status == "expired":
            status = ResearchSignalStatus.EXPIRED
        payload_seed = {
            "impact_id": impact.impact_id,
            "asset_id": impact.asset_id,
            "direction": impact.direction.value,
            "horizon": impact.horizon.value,
            "status": status.value,
        }
        payload_hash = sha256_text(canonical_json(payload_seed))
        signals.append(
            MarketSignalCandidate(
                id=_stable_uuid("signal", impact.impact_id),
                signal_id=f"SIGNAL-{index + 1:04d}",
                impact_id=impact.impact_id,
                event_id=impact.event_id,
                asset_id=impact.asset_id,
                direction=impact.direction,
                horizon=impact.horizon,
                status=status,
                confidence=impact.confidence,
                score=None
                if impact.confidence is None
                else round(impact.impact_strength * impact.confidence, 4),
                information_cutoff_at=impact.information_cutoff_at,
                generated_at=impact.created_at + timedelta(minutes=1),
                expires_at=impact.expires_at,
                provider="deterministic_signal_candidate_generator",
                provider_version="1",
                evidence_codes=impact.evidence_codes,
                quality_tags=["synthetic", "point_in_time", "metadata_only"],
                risk_tags=["not_investment_advice", "no_execution", "hypothesis"],
                payload_hash=payload_hash,
                idempotency_key=sha256_text(
                    f"{CONTRACT_VERSION}:{impact.impact_id}:{impact.asset_id}"
                ),
                synthetic=True,
            )
        )
    return signals


def _validate_local_signal_output(output: Path) -> None:
    parts = output.resolve().parts
    if LOCAL_SIGNAL_ROOT not in parts:
        raise CrossAssetError(f"signal exports must be under ignored {LOCAL_SIGNAL_ROOT}/")
    root_index = parts.index(LOCAL_SIGNAL_ROOT)
    if root_index == len(parts) - 1:
        raise CrossAssetError("signal output must name a child directory")


def _validate_package_file_name(name: str) -> None:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise CrossAssetError(f"unsafe package file path: {name}")
    if name not in PACKAGE_FILES:
        raise CrossAssetError(f"unexpected package file path: {name}")


def _asset_row(asset: Asset) -> dict[str, Any]:
    row = asdict(asset)
    row["id"] = str(asset.id)
    row["asset_class"] = asset.asset_class.value
    row["status"] = asset.status.value
    row["expiry"] = asset.expiry.isoformat() if asset.expiry else None
    return row


def _alias_row(alias: SymbolAlias) -> dict[str, Any]:
    row = asdict(alias)
    row["id"] = str(alias.id)
    row["namespace"] = alias.namespace.value
    row["valid_from"] = alias.valid_from.isoformat() if alias.valid_from else None
    row["valid_to"] = alias.valid_to.isoformat() if alias.valid_to else None
    return row


def _alias_match_row(alias: SymbolAlias) -> dict[str, object]:
    return {
        "asset_id": alias.asset_id,
        "namespace": alias.namespace.value,
        "symbol": alias.symbol,
        "confidence": alias.confidence,
        "provider": alias.provider,
        "provider_version": alias.provider_version,
        "active": alias.active,
    }


def _relationship_row(row: AssetRelationship) -> dict[str, Any]:
    data = asdict(row)
    data["id"] = str(row.id)
    data["relationship_type"] = row.relationship_type.value
    return data


def _event_row(event: CrossAssetEvent) -> dict[str, Any]:
    row = asdict(event)
    row["id"] = str(event.id)
    row["event_family"] = event.event_family.value
    row["information_available_at"] = event.information_available_at.isoformat()
    return row


def _impact_row(impact: AssetImpactHypothesis) -> dict[str, Any]:
    row = asdict(impact)
    row["id"] = str(impact.id)
    row["relationship_type"] = impact.relationship_type.value
    row["direction"] = impact.direction.value
    row["horizon"] = impact.horizon.value
    row["information_cutoff_at"] = impact.information_cutoff_at.isoformat()
    row["created_at"] = impact.created_at.isoformat()
    row["expires_at"] = impact.expires_at.isoformat() if impact.expires_at else None
    return row


def _signal_row(signal: MarketSignalCandidate) -> dict[str, Any]:
    row = asdict(signal)
    row["id"] = str(signal.id)
    row["direction"] = signal.direction.value
    row["horizon"] = signal.horizon.value
    row["status"] = signal.status.value
    row["information_cutoff_at"] = signal.information_cutoff_at.isoformat()
    row["generated_at"] = signal.generated_at.isoformat()
    row["expires_at"] = signal.expires_at.isoformat() if signal.expires_at else None
    return row


def _counts(values: list[str] | Any) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _json_bytes(data: object) -> bytes:
    return (canonical_json(data) + "\n").encode("utf-8")


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("".join(canonical_json(row) + "\n" for row in rows)).encode("utf-8")


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=sorted(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def canonical_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_uuid(*parts: object) -> UUID:
    return uuid5(NAMESPACE_URL, "|".join(str(part) for part in parts))
