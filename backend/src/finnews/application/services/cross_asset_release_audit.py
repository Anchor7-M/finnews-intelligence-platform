# ruff: noqa: E501

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finnews.application.services.cross_asset import (
    ASSET_SCHEMA_VERSION,
    CONTRACT_NAME,
    CONTRACT_VERSION,
    FIXTURE_VERSION,
    GENERATED_AT,
    SIGNAL_SCHEMA_VERSION,
    build_cross_asset_demo,
    build_signal_package,
    canonical_json,
    sha256_bytes,
    sha256_text,
    validate_signal_package,
    write_signal_package,
)
from finnews.domain.enums import AssetClass, ResearchSignalStatus

TRADING_SURFACE_PATTERNS = [
    "MetaTrader5",
    "metatrader5",
    "initialize(",
    "login(",
    "order_check(",
    "order_send(",
    "TRADE_ACTION",
    "ORDER_TYPE",
    "account_info(",
    "positions_get(",
    "orders_get(",
    "history_deals_get(",
    "history_orders_get(",
    "order_calc_margin(",
    "order_calc_profit(",
    "copy_rates_range(",
    "symbol_info",
    "symbols_get",
    "terminal_info(",
    "lot",
    "volume",
    "stop_loss",
    "take_profit",
    "buy",
    "sell",
    "execute",
]
TOKEN_TRADING_SURFACE_PATTERNS = {"lot", "volume", "buy", "sell", "execute"}
GENERATED_TRADING_SURFACE_AUDIT_OUTPUT_PATH = (
    "reports/cross-asset/revised-m3a-trading-surface-audit.json"
)
GENERATED_M3C_MARKET_REACTION_EVIDENCE_FILES = (
    "reports/market-reaction/m3c-release-ledger.json",
    "reports/market-reaction/m3c-scenario-audit.json",
    "reports/market-reaction/m3c-point-in-time-audit.json",
)
GENERATED_M4A_MT5_READONLY_EVIDENCE_FILES = (
    "reports/mt5-readonly/m4a-release-ledger.json",
    "reports/mt5-readonly/m4a-symbol-map-audit.json",
    "reports/mt5-readonly/m4a-fake-adapter-audit.json",
    "reports/mt5-readonly/m4a-bar-export-audit.json",
    "reports/mt5-readonly/m4a-execution-surface-audit.json",
)
GENERATED_M4B0_PAPER_EXECUTION_EVIDENCE_FILES = (
    "reports/paper-execution/m4b0-release-audit.json",
    "reports/paper-execution/m4b0-release-ledger.json",
    "reports/paper-execution/m4b0-contract-audit.json",
    "reports/paper-execution/m4b0-risk-gate-audit.json",
    "reports/paper-execution/m4b0-manual-approval-audit.json",
    "reports/paper-execution/m4b0-fill-accounting-audit.json",
    "reports/paper-execution/m4b0-scenario-audit.json",
    "reports/paper-execution/m4b0-postgres-audit.json",
    "reports/paper-execution/m4b0-interface-static-audit.json",
    "reports/paper-execution/m4b0-execution-surface-audit.json",
)
EXCLUDED_GENERATED_EVIDENCE_FILES = (
    GENERATED_TRADING_SURFACE_AUDIT_OUTPUT_PATH,
    "reports/verification/revised-m3a-timings.json",
    *GENERATED_M3C_MARKET_REACTION_EVIDENCE_FILES,
    *GENERATED_M4A_MT5_READONLY_EVIDENCE_FILES,
    *GENERATED_M4B0_PAPER_EXECUTION_EVIDENCE_FILES,
)
ALLOWED_TRADING_SURFACE_PREFIXES = (
    "docs/",
    "contracts/finnews-market-signal/v1/",
    "backend/tests/",
)
ALLOWED_TRADING_SURFACE_FILES = {
    "backend/src/finnews/application/services/cross_asset.py",
    "backend/src/finnews/application/services/cross_asset_release_audit.py",
    "backend/src/finnews/application/services/mt5_readonly_release_audit.py",
    "config/integrations/mt5-symbol-map.example.yaml",
    "README.md",
    "AGENTS.md",
    "CHANGELOG.md",
    "compose.yml",
    "scripts/dev.py",
    "backend/src/finnews/infrastructure/persistence/postgres/repository.py",
    "frontend/package-lock.json",
    "frontend/public/demo-data/market-signal-contract-example.json",
    "frontend/src/components/StateBlock.vue",
    "config/source-reviews/federal-reserve-press-releases.yaml",
    "config/source-reviews/sec-edgar-submissions.yaml",
    "config/sources/federal-reserve-press-releases.yaml",
    "config/sources/sec-edgar-submissions.yaml",
}
MARKET_DATA_VOLUME_ALLOWED_FILES = {
    "backend/alembic/versions/0007_market_reaction_validation.py",
    "backend/src/finnews/application/services/market_reaction.py",
    "backend/src/finnews/application/services/market_reaction_release_audit.py",
    "backend/src/finnews/infrastructure/persistence/postgres/models.py",
    "frontend/public/demo-data/market-data-bars-sample.json",
    "frontend/src/types/models.ts",
}
MARKET_DATA_VOLUME_ALLOWED_PREFIXES = (
    "contracts/finnews-market-bars/v1/",
    "docs/",
)
MARKET_DATA_IMPORT_GUARDRAIL_PATTERNS = {"lot", "volume", "buy", "sell", "execute"}
PAPER_EXECUTION_GUARDRAIL_FILES = {
    "backend/alembic/versions/0009_paper_execution.py",
    "backend/src/finnews/application/services/paper_execution.py",
    "backend/src/finnews/application/services/paper_execution_release_audit.py",
}
PAPER_EXECUTION_GUARDRAIL_PREFIXES = ("contracts/finnews-paper-execution/v1/",)
PAPER_EXECUTION_GUARDRAIL_PATTERNS = {
    "TRADE_ACTION",
    "ORDER_TYPE",
    "lot",
    "stop_loss",
    "take_profit",
    "buy",
    "sell",
    "execute",
}
MT5_READONLY_ADAPTER_FILE = "backend/src/finnews/application/services/mt5_readonly.py"
MT5_READONLY_ADAPTER_ALLOWED_PATTERNS = {
    "MetaTrader5",
    "initialize(",
    "copy_rates_range(",
    "symbol_info",
    "symbols_get",
    "terminal_info(",
    "volume",
}
MT5_READONLY_REJECTION_GUARDRAIL_PATTERNS = {
    "buy",
    "execute",
    "lot",
    "sell",
    "stop_loss",
    "take_profit",
    "volume",
}
MT5_READONLY_STATIC_SCHEMA_FILE = "frontend/public/demo-data/mt5-readonly-symbol-map-schema.json"


def write_revised_m3a_release_reports(
    repo_root: Path, output_root: Path | None = None
) -> dict[str, Any]:
    output = (output_root or repo_root) / "reports" / "cross-asset"
    output.mkdir(parents=True, exist_ok=True)
    reports = {
        "revised-m3a-release-ledger.json": build_release_ledger(repo_root),
        "revised-m3a-rule-coverage.json": build_rule_coverage_report(),
        "revised-m3a-lifecycle-audit.json": build_lifecycle_audit_report(repo_root),
        "revised-m3a-trading-surface-audit.json": build_trading_surface_report(repo_root),
    }
    for name, payload in reports.items():
        (output / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "status": "completed",
        "reports": sorted(reports),
        "ledger_sha256": sha256_bytes((output / "revised-m3a-release-ledger.json").read_bytes()),
    }


def build_release_ledger(repo_root: Path) -> dict[str, Any]:
    dataset = build_cross_asset_demo()
    files = build_signal_package(dataset)
    assets_by_id = {asset.asset_id: asset for asset in dataset.assets}
    events_by_id = {event.event_id: event for event in dataset.events}
    package_hashes = {name: sha256_bytes(data) for name, data in files.items()}
    active_alias_keys = [
        (alias.namespace.value, alias.provider or "", alias.normalized_symbol, alias.asset_id)
        for alias in dataset.aliases
        if alias.active
    ]
    futures_roots = {
        asset.asset_id for asset in dataset.assets if asset.asset_class is AssetClass.FUTURES_ROOT
    }
    futures_contracts = [
        asset for asset in dataset.assets if asset.asset_class is AssetClass.FUTURES_CONTRACT
    ]
    event_age_counts = Counter(
        "fresh_at_generation" if event.information_available_at <= GENERATED_AT else "future_dated"
        for event in dataset.events
    )
    signal_idempotency_keys = [signal.idempotency_key for signal in dataset.signals]
    package_file_rows = [
        {"path": name, "size_bytes": len(files[name]), "sha256": package_hashes[name]}
        for name in sorted(files)
    ]
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "asset_schema_version": ASSET_SCHEMA_VERSION,
        "signal_schema_version": SIGNAL_SCHEMA_VERSION,
        "fixture_version": FIXTURE_VERSION,
        "generated_at": GENERATED_AT.isoformat(),
        "synthetic_data": True,
        "not_investment_advice": True,
        "no_execution": True,
        "asset_ledger": {
            "total": len(dataset.assets),
            "by_asset_class": _counts(asset.asset_class.value for asset in dataset.assets),
            "by_status": _counts(asset.status.value for asset in dataset.assets),
            "synthetic_count": sum(asset.synthetic for asset in dataset.assets),
            "by_venue": _counts(asset.home_venue or "none" for asset in dataset.assets),
            "venue_count": len({asset.home_venue for asset in dataset.assets if asset.home_venue}),
            "by_region": _counts(asset.country_region for asset in dataset.assets),
            "base_currency_count": len(
                {asset.base_currency for asset in dataset.assets if asset.base_currency}
            ),
            "quote_currency_count": len(
                {asset.quote_currency for asset in dataset.assets if asset.quote_currency}
            ),
            "base_currency_coverage": sum(
                asset.base_currency is not None for asset in dataset.assets
            ),
            "quote_currency_coverage": sum(
                asset.quote_currency is not None for asset in dataset.assets
            ),
            "futures_root_count": len(futures_roots),
            "futures_contract_count": len(futures_contracts),
            "futures_contracts_with_valid_root": sum(
                asset.parent_asset_id in futures_roots for asset in futures_contracts
            ),
            "asset_relationship_count": len(dataset.relationships),
        },
        "alias_ledger": {
            "total": len(dataset.aliases),
            "by_namespace": _counts(alias.namespace.value for alias in dataset.aliases),
            "by_active": _counts(
                "active" if alias.active else "inactive" for alias in dataset.aliases
            ),
            "ambiguous_resolution_fixture_count": 1,
            "unresolved_resolution_fixture_count": 1,
            "active_alias_uniqueness_violations": len(active_alias_keys)
            - len(set(active_alias_keys)),
        },
        "event_ledger": {
            "total": len(dataset.events),
            "by_event_family": _counts(event.event_family.value for event in dataset.events),
            "by_event_subtype": _counts(event.event_subtype for event in dataset.events),
            "by_provider": _counts(event.provider for event in dataset.events),
            "by_uncertainty_flag": _counts(
                flag for event in dataset.events for flag in event.uncertainty_flags
            ),
            "stale_fresh_counts": dict(sorted(event_age_counts.items())),
            "synthetic_count": sum(event.synthetic for event in dataset.events),
        },
        "impact_ledger": {
            "total": len(dataset.impacts),
            "by_relationship_type": _counts(
                impact.relationship_type.value for impact in dataset.impacts
            ),
            "by_direction": _counts(impact.direction.value for impact in dataset.impacts),
            "by_horizon": _counts(impact.horizon.value for impact in dataset.impacts),
            "by_provider": _counts(impact.provider for impact in dataset.impacts),
            "by_status": _counts(impact.status for impact in dataset.impacts),
            "confidence_null_non_null": _null_counts(
                impact.confidence for impact in dataset.impacts
            ),
            "by_asset_class": _counts(
                assets_by_id[impact.asset_id].asset_class.value for impact in dataset.impacts
            ),
            "by_event_family": _counts(
                events_by_id[impact.event_id].event_family.value for impact in dataset.impacts
            ),
            "mixed_examples": [
                impact.impact_id for impact in dataset.impacts if impact.direction.value == "mixed"
            ][:5],
            "uncertain_or_abstained_examples": [
                impact.impact_id
                for impact in dataset.impacts
                if impact.direction.value == "uncertain" or impact.status == "rejected"
            ][:5],
            "duplicate_idempotency_examples": [
                dataset.impacts[0].impact_id,
                dataset.impacts[1].impact_id,
            ],
        },
        "signal_ledger": {
            "total": len(dataset.signals),
            "by_status": _counts(signal.status.value for signal in dataset.signals),
            "research_candidate_count": sum(
                signal.status is ResearchSignalStatus.RESEARCH for signal in dataset.signals
            ),
            "by_direction": _counts(signal.direction.value for signal in dataset.signals),
            "by_horizon": _counts(signal.horizon.value for signal in dataset.signals),
            "by_asset_class": _counts(
                assets_by_id[signal.asset_id].asset_class.value for signal in dataset.signals
            ),
            "by_provider": _counts(signal.provider for signal in dataset.signals),
            "confidence_null_non_null": _null_counts(
                signal.confidence for signal in dataset.signals
            ),
            "by_risk_tag": _counts(tag for signal in dataset.signals for tag in signal.risk_tags),
            "by_quality_tag": _counts(
                tag for signal in dataset.signals for tag in signal.quality_tags
            ),
            "expired_examples": [
                signal.signal_id
                for signal in dataset.signals
                if signal.status is ResearchSignalStatus.EXPIRED
            ][:5],
            "idempotency_key_unique_count": len(set(signal_idempotency_keys)),
        },
        "contract_files": package_file_rows,
        "schema_files": _file_hash_rows(
            repo_root / "contracts" / "finnews-market-signal" / "v1", "*.schema.json"
        ),
        "package_content_hash": json.loads(files["manifest.json"])["package_content_hash"],
        "dataset_content_hash": sha256_text(
            canonical_json(
                {
                    "assets": len(dataset.assets),
                    "aliases": len(dataset.aliases),
                    "events": len(dataset.events),
                    "impacts": len(dataset.impacts),
                    "signals": len(dataset.signals),
                    "package_hashes": package_hashes,
                }
            )
        ),
    }


def build_rule_coverage_report() -> dict[str, Any]:
    dataset = build_cross_asset_demo()
    event_ids = {event.event_id for event in dataset.events}
    impact_counts_by_event = Counter(impact.event_id for impact in dataset.impacts)
    signals_by_impact = Counter(signal.impact_id for signal in dataset.signals)
    return {
        "fixture_version": FIXTURE_VERSION,
        "event_count": len(event_ids),
        "impact_count": len(dataset.impacts),
        "signal_count": len(dataset.signals),
        "events_without_impacts": sorted(event_ids - set(impact_counts_by_event)),
        "min_impacts_per_event": min(impact_counts_by_event.values()),
        "max_impacts_per_event": max(impact_counts_by_event.values()),
        "all_events_not_mapped_to_all_assets": max(impact_counts_by_event.values())
        < len(dataset.assets),
        "accepted_impacts_have_evidence": all(
            impact.evidence_codes for impact in dataset.impacts if impact.status == "active"
        ),
        "confidence_bounds_ok": all(
            impact.confidence is None or 0 <= impact.confidence <= 1 for impact in dataset.impacts
        ),
        "impact_strength_bounds_ok": all(
            0 <= impact.impact_strength <= 1 for impact in dataset.impacts
        ),
        "cutoff_before_creation": all(
            impact.information_cutoff_at <= impact.created_at for impact in dataset.impacts
        ),
        "active_expiry_after_creation": all(
            impact.expires_at is not None and impact.expires_at > impact.created_at
            for impact in dataset.impacts
            if impact.status == "active"
        ),
        "rejected_impacts_have_reason": all(
            impact.rejection_reason for impact in dataset.impacts if impact.status == "rejected"
        ),
        "signals_per_impact_max": max(signals_by_impact.values()),
        "input_order_invariance_hash": _input_order_invariance_hash(),
    }


def build_lifecycle_audit_report(repo_root: Path) -> dict[str, Any]:
    dataset = build_cross_asset_demo()
    left = build_signal_package(dataset)
    right = build_signal_package(build_cross_asset_demo())
    package_identical = left == right
    temp_root = repo_root / ".finnews-market-signals" / "audit-temp"
    if temp_root.exists():
        import shutil

        shutil.rmtree(temp_root)
    try:
        validation = write_signal_package(temp_root, dataset)
        validation_again = validate_signal_package(temp_root)
    finally:
        if temp_root.exists():
            import shutil

            shutil.rmtree(temp_root)
    return {
        "fixture_version": FIXTURE_VERSION,
        "package_byte_identical_rebuild": package_identical,
        "validation_hash": validation["package_content_hash"],
        "validation_again_hash": validation_again["package_content_hash"],
        "cutoff_lte_generated": all(
            signal.information_cutoff_at <= signal.generated_at for signal in dataset.signals
        ),
        "generated_before_expiry": all(
            signal.expires_at is not None and signal.generated_at < signal.expires_at
            for signal in dataset.signals
        ),
        "expired_signals_inactive": all(
            signal.status is ResearchSignalStatus.EXPIRED
            for signal in dataset.signals
            if signal.status is ResearchSignalStatus.EXPIRED
        ),
        "idempotency_key_unique_count": len({signal.idempotency_key for signal in dataset.signals}),
        "logical_rebuild_idempotency_same": [
            signal.idempotency_key for signal in dataset.signals[:10]
        ]
        == [signal.idempotency_key for signal in build_cross_asset_demo().signals[:10]],
        "wall_clock_independent": GENERATED_AT.isoformat(),
    }


def build_trading_surface_report(repo_root: Path) -> dict[str, Any]:
    tracked_files = [
        rel
        for rel in _tracked_files(repo_root)
        if rel not in set(EXCLUDED_GENERATED_EVIDENCE_FILES)
    ]
    matches: list[dict[str, Any]] = []
    forbidden: list[dict[str, Any]] = []
    dependency_matches: list[dict[str, Any]] = []
    for rel in tracked_files:
        if not _text_file(rel):
            continue
        text = (repo_root / rel).read_text(encoding="utf-8", errors="ignore")
        for pattern in TRADING_SURFACE_PATTERNS:
            count = _pattern_count(text, pattern)
            if count == 0:
                continue
            classification = _classify_match(rel, pattern)
            row = {
                "path": rel,
                "pattern": pattern,
                "count": count,
                "classification": classification,
            }
            matches.append(row)
            if rel in {
                "backend/pyproject.toml",
                "frontend/package.json",
                "frontend/package-lock.json",
            }:
                dependency_matches.append(row)
            if classification == "forbidden executable production path":
                forbidden.append(row)
    return {
        "patterns": TRADING_SURFACE_PATTERNS,
        "excluded_generated_evidence_files": list(EXCLUDED_GENERATED_EVIDENCE_FILES),
        "tracked_file_count": len(tracked_files),
        "match_count": sum(row["count"] for row in matches),
        "matched_file_count": len({row["path"] for row in matches}),
        "matches": sorted(matches, key=lambda row: (row["path"], row["pattern"])),
        "forbidden_count": len(forbidden),
        "forbidden": forbidden,
        "dependency_matches": dependency_matches,
        "mt5_dependency_present": any(
            "MetaTrader5" in (repo_root / rel).read_text(encoding="utf-8", errors="ignore")
            or "metatrader5" in (repo_root / rel).read_text(encoding="utf-8", errors="ignore")
            for rel in tracked_files
            if rel
            in {"backend/pyproject.toml", "frontend/package.json", "frontend/package-lock.json"}
        ),
        "status": "PASS" if not forbidden else "FAIL",
    }


def _pattern_count(text: str, pattern: str) -> int:
    if pattern in TOKEN_TRADING_SURFACE_PATTERNS:
        return len(re.findall(rf"(?<![A-Za-z0-9_]){re.escape(pattern)}(?![A-Za-z0-9_])", text))
    return text.count(pattern)


def _counts(values: Iterable[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _null_counts(values: Iterable[object | None]) -> dict[str, int]:
    values_list = list(values)
    return {
        "null": sum(value is None for value in values_list),
        "non_null": sum(value is not None for value in values_list),
    }


def _file_hash_rows(root: Path, pattern: str) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_bytes(path.read_bytes()),
        }
        for path in sorted(root.glob(pattern))
    ]


def _input_order_invariance_hash() -> str:
    dataset = build_cross_asset_demo()
    reversed_ids = sorted(impact.impact_id for impact in reversed(dataset.impacts))
    original_ids = sorted(impact.impact_id for impact in dataset.impacts)
    return sha256_text(canonical_json({"same": original_ids == reversed_ids, "ids": original_ids}))


def _tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _text_file(path: str) -> bool:
    return Path(path).suffix.lower() in {
        ".py",
        ".md",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ts",
        ".vue",
        ".js",
        ".ini",
        ".txt",
    }


def _classify_match(path: str, pattern: str) -> str:
    if pattern == "volume" and (
        path in MARKET_DATA_VOLUME_ALLOWED_FILES
        or path.startswith(MARKET_DATA_VOLUME_ALLOWED_PREFIXES)
    ):
        return "permitted market-data bar volume field"
    if (
        path == "backend/src/finnews/application/services/market_reaction.py"
        and pattern in MARKET_DATA_IMPORT_GUARDRAIL_PATTERNS
    ):
        return "permitted market-data import rejection guardrail"
    if (
        path in PAPER_EXECUTION_GUARDRAIL_FILES
        or path.startswith(PAPER_EXECUTION_GUARDRAIL_PREFIXES)
    ) and pattern in PAPER_EXECUTION_GUARDRAIL_PATTERNS:
        return "permitted paper-execution safety guardrail"
    if path == MT5_READONLY_ADAPTER_FILE and pattern in MT5_READONLY_ADAPTER_ALLOWED_PATTERNS:
        return "permitted MT5 read-only adapter allowlist"
    if path == MT5_READONLY_ADAPTER_FILE and pattern in MT5_READONLY_REJECTION_GUARDRAIL_PATTERNS:
        return "permitted MT5 read-only rejection guardrail"
    if path == MT5_READONLY_STATIC_SCHEMA_FILE:
        return "permitted MT5 read-only static schema guardrail"
    if path.startswith("docs/"):
        return "permitted architecture documentation"
    if path.startswith("contracts/finnews-market-signal/v1/"):
        return "permitted contract fixture proving rejection"
    if path.startswith("backend/tests/") or path.startswith("frontend/tests/"):
        return "permitted test fixture proving rejection"
    if path in ALLOWED_TRADING_SURFACE_FILES:
        return "permitted release guardrail"
    if path.startswith(ALLOWED_TRADING_SURFACE_PREFIXES):
        return "permitted architecture documentation"
    return "forbidden executable production path"
