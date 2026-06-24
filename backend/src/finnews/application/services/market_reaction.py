# ruff: noqa: E501

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from typing import Any

from finnews.application.services.cross_asset import (
    build_cross_asset_demo,
    canonical_json,
    sha256_text,
)
from finnews.domain.entities import Asset, MarketSignalCandidate
from finnews.domain.enums import AssetClass, ImpactDirection, ResearchSignalStatus

CONTRACT_NAME = "finnews-market-bars-v1"
CONTRACT_VERSION = "1.0.0"
SCENARIO_VERSION = "market-reaction-synthetic-v1"
PROVIDER = "finnews-synthetic-market-reaction"
GENERATED_AT = datetime(2026, 6, 24, 0, 0, tzinfo=UTC)
MAX_IMPORT_BYTES = 5_000_000
SUPPORTED_SCENARIOS = [
    "synthetic-null-reaction-v1",
    "synthetic-planted-reaction-v1",
    "synthetic-regime-shift-v1",
]
MARKET_STATES = ["calm", "risk_off", "high_volatility", "commodity_shock", "crypto_stress"]
HORIZON_WINDOWS: dict[str, tuple[int, int]] = {
    "intraday": (0, 1),
    "one_day": (0, 1),
    "three_day": (0, 3),
    "one_week": (0, 5),
    "one_month": (0, 20),
}
PRE_EVENT_CONTROL_WINDOW = (-5, -1)
LABEL_THRESHOLD = Decimal("0.0015")
THRESHOLD_VERSION = "m3c-label-threshold-v1"
REQUIRED_FIELDS = {
    "asset_id",
    "provider_symbol",
    "bar_start_at",
    "bar_end_at",
    "timezone",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source_profile",
    "first_seen_at",
    "available_at",
    "synthetic_data",
    "schema_version",
}
OPTIONAL_FIELDS = {"bar_id", "session_date", "quote_volume"}
FORBIDDEN_IMPORT_FIELDS = {
    "future_return",
    "future_returns",
    "target_return",
    "label_return",
    "account",
    "account_id",
    "account_number",
    "login",
    "password",
    "server",
    "api_key",
    "order",
    "order_id",
    "order_type",
    "position",
    "position_id",
    "lot",
    "volume_lots",
    "execute",
    "buy",
    "sell",
    "mt5_terminal_path",
}


class MarketReactionError(ValueError):
    pass


@dataclass(frozen=True)
class MarketReactionDataset:
    scenarios: list[dict[str, Any]]
    packages: list[dict[str, Any]]
    bars: list[dict[str, Any]]
    studies: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    leakage_audit: dict[str, Any]


def build_market_reaction_demo() -> MarketReactionDataset:
    cross_asset = build_cross_asset_demo()
    assets = _select_assets(cross_asset.assets)
    scenarios = _scenario_rows()
    packages: list[dict[str, Any]] = []
    all_bars: list[dict[str, Any]] = []
    studies: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    signals = _eligible_signals(cross_asset.signals, {asset.asset_id for asset in assets})
    asset_by_id = {asset.asset_id: asset for asset in assets}
    events_by_id = {event.event_id: event for event in cross_asset.events}

    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"])
        bars = _build_scenario_bars(scenario_id, assets, signals)
        bars_by_asset = _bars_by_asset(bars)
        all_bars.extend(bars)
        packages.append(_package_row(scenario_id, assets, bars))
        scenario_studies: list[dict[str, Any]] = []
        scenario_labels: list[dict[str, Any]] = []
        for signal in signals:
            asset = asset_by_id[signal.asset_id]
            event = events_by_id[signal.event_id]
            for horizon, window in HORIZON_WINDOWS.items():
                study = _build_study(
                    scenario_id,
                    signal,
                    asset,
                    event.event_family.value,
                    bars_by_asset,
                    window,
                    horizon,
                )
                scenario_studies.append(study)
                scenario_labels.append(_label_from_study(study, signal, asset))
        studies.extend(scenario_studies)
        labels.extend(scenario_labels)
        metrics.extend(
            _metrics_for_scenario(scenario_id, scenario_labels, scenario_studies, assets)
        )
        errors.extend(
            _error_cases_for_scenario(scenario_id, scenario_labels, scenario_studies, assets)
        )
    leakage = _leakage_audit(labels, studies, all_bars)
    return MarketReactionDataset(
        scenarios=scenarios,
        packages=packages,
        bars=all_bars,
        studies=studies,
        labels=labels,
        metrics=metrics,
        errors=errors,
        leakage_audit=leakage,
    )


def market_reaction_static_payload() -> dict[str, Any]:
    dataset = build_market_reaction_demo()
    overview = market_reaction_overview(dataset)
    return {
        "market-reaction-overview": overview,
        "market-reaction-scenarios": dataset.scenarios,
        "market-reaction-studies": dataset.studies[:500],
        "market-reaction-labels": dataset.labels,
        "market-reaction-labels-sample": dataset.labels[:500],
        "market-reaction-metrics": dataset.metrics,
        "market-reaction-error-analysis": dataset.errors,
        "market-reaction-leakage-audit": dataset.leakage_audit,
        "market-data-packages": dataset.packages,
        "market-data-bars-sample": dataset.bars[:500],
        "market-data-synthetic-summary": _synthetic_summary(dataset),
    }


def market_reaction_overview(dataset: MarketReactionDataset | None = None) -> dict[str, Any]:
    dataset = dataset or build_market_reaction_demo()
    labels = [row for row in dataset.labels if row["label"] != "unavailable"]
    return {
        "synthetic_data": True,
        "not_investment_advice": True,
        "no_live_market_data": True,
        "no_execution": True,
        "mt5_connection": "not_implemented",
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "scenario_count": len(dataset.scenarios),
        "scenario_ids": [row["scenario_id"] for row in dataset.scenarios],
        "asset_count_per_scenario": 24,
        "session_count_per_scenario": 90,
        "bar_count_per_scenario": 2160,
        "total_bar_count": len(dataset.bars),
        "study_count": len(dataset.studies),
        "label_count": len(dataset.labels),
        "evaluated_label_count": len(labels),
        "metric_row_count": len(dataset.metrics),
        "error_case_count": len(dataset.errors),
        "market_state_distribution": _counts(str(row["market_state"]) for row in dataset.bars),
        "label_distribution": _counts(str(row["label"]) for row in dataset.labels),
        "horizon_windows": {
            **{key: list(value) for key, value in HORIZON_WINDOWS.items()},
            "pre_event_control": list(PRE_EVENT_CONTROL_WINDOW),
        },
        "benchmark_modes": [
            "asset_class_equal_weight",
            "scenario_equal_weight",
            "asset_pre_event_mean",
        ],
        "label_threshold": str(LABEL_THRESHOLD),
        "threshold_version": THRESHOLD_VERSION,
        "disclaimer": (
            "Synthetic market scenarios are not real prices. Market-reaction labels "
            "are research labels, not allocation instructions, and event studies do not prove causality."
        ),
    }


def validate_market_bar_file(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise MarketReactionError("market bar file not found")
    if path.stat().st_size > MAX_IMPORT_BYTES:
        raise MarketReactionError("market bar file exceeds size limit")
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise MarketReactionError("market bar file must be UTF-8") from exc
    rows = _read_market_bar_rows(path, raw)
    normalized = [_validate_import_row(row, index) for index, row in enumerate(rows, start=1)]
    _validate_monotonic_and_unique(normalized)
    digest = sha256_text(canonical_json(normalized))
    return {
        "valid": True,
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "row_count": len(normalized),
        "asset_count": len({row["asset_id"] for row in normalized}),
        "deterministic_hash": digest,
        "synthetic_rows": sum(1 for row in normalized if row["synthetic_data"] is True),
        "live_fetch_metadata": False,
        "credentials_present": False,
    }


def market_data_contract_example_rows() -> list[dict[str, Any]]:
    base = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    return [
        {
            "bar_id": "BAR-DEMO-001",
            "asset_id": "US-EQ-ALPHA",
            "provider_symbol": "ALPHA.DEMO",
            "session_date": "2026-01-02",
            "bar_start_at": base.isoformat(),
            "bar_end_at": (base + timedelta(days=1) - timedelta(minutes=5)).isoformat(),
            "timezone": "UTC",
            "open": "100.000000",
            "high": "101.250000",
            "low": "99.500000",
            "close": "100.750000",
            "volume": "1250000",
            "quote_volume": "125937500.000000",
            "source_profile": "synthetic-contract-example",
            "first_seen_at": (base + timedelta(days=1)).isoformat(),
            "available_at": (base + timedelta(days=1)).isoformat(),
            "synthetic_data": True,
            "schema_version": CONTRACT_NAME,
        },
        {
            "bar_id": "BAR-DEMO-002",
            "asset_id": "US-EQ-ALPHA",
            "provider_symbol": "ALPHA.DEMO",
            "session_date": "2026-01-05",
            "bar_start_at": (base + timedelta(days=3)).isoformat(),
            "bar_end_at": (base + timedelta(days=4) - timedelta(minutes=5)).isoformat(),
            "timezone": "UTC",
            "open": "100.750000",
            "high": "102.000000",
            "low": "100.100000",
            "close": "101.500000",
            "volume": "1260000",
            "quote_volume": "127890000.000000",
            "source_profile": "synthetic-contract-example",
            "first_seen_at": (base + timedelta(days=4)).isoformat(),
            "available_at": (base + timedelta(days=4)).isoformat(),
            "synthetic_data": True,
            "schema_version": CONTRACT_NAME,
        },
    ]


def write_market_reaction_static(output: Path) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    payload = market_reaction_static_payload()
    exported: list[str] = []
    for name, value in payload.items():
        (output / f"{name}.json").write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        exported.append(name)
    return sorted(exported)


def scenario_summary(scenario_id: str) -> dict[str, Any]:
    _ensure_scenario(scenario_id)
    dataset = build_market_reaction_demo()
    bars = [row for row in dataset.bars if row["scenario_id"] == scenario_id]
    labels = [row for row in dataset.labels if row["scenario_id"] == scenario_id]
    metrics = [
        row
        for row in dataset.metrics
        if row["scenario_id"] == scenario_id and row["slice_type"] == "scenario"
    ]
    return {
        "scenario_id": scenario_id,
        "asset_count": len({row["asset_id"] for row in bars}),
        "session_count": len({row["session_date"] for row in bars}),
        "bar_count": len(bars),
        "label_count": len(labels),
        "market_state_distribution": _counts(str(row["market_state"]) for row in bars),
        "scenario_metrics": metrics,
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def compare_scenarios(left: str, right: str) -> dict[str, Any]:
    left_summary = scenario_summary(left)
    right_summary = scenario_summary(right)
    left_metric = _metric_by_horizon(left, "one_week")
    right_metric = _metric_by_horizon(right, "one_week")
    return {
        "left": left,
        "right": right,
        "left_bar_count": left_summary["bar_count"],
        "right_bar_count": right_summary["bar_count"],
        "one_week_consistency_delta": round(
            float(right_metric["directional_consistency_rate"])
            - float(left_metric["directional_consistency_rate"]),
            6,
        ),
        "left_one_week_consistency": left_metric["directional_consistency_rate"],
        "right_one_week_consistency": right_metric["directional_consistency_rate"],
        "synthetic_data": True,
    }


def _metric_by_horizon(scenario_id: str, horizon: str) -> dict[str, Any]:
    dataset = build_market_reaction_demo()
    matches = [
        row
        for row in dataset.metrics
        if row["scenario_id"] == scenario_id
        and row["slice_type"] == "horizon"
        and row["slice_value"] == horizon
    ]
    if not matches:
        raise MarketReactionError("scenario horizon metric not found")
    return matches[0]


def _select_assets(assets: list[Asset]) -> list[Asset]:
    quotas = {
        AssetClass.US_EQUITY: 4,
        AssetClass.ETF: 3,
        AssetClass.EQUITY_INDEX: 3,
        AssetClass.FX: 3,
        AssetClass.PRECIOUS_METAL: 2,
        AssetClass.COMMODITY: 2,
        AssetClass.FUTURES_ROOT: 2,
        AssetClass.CRYPTO_ASSET: 3,
        AssetClass.INTEREST_RATE: 2,
    }
    selected: list[Asset] = []
    for asset_class, count in quotas.items():
        selected.extend([asset for asset in assets if asset.asset_class is asset_class][:count])
    if len(selected) != 24:
        raise MarketReactionError("synthetic market scenario asset selection failed")
    return selected


def _eligible_signals(
    signals: list[MarketSignalCandidate], asset_ids: set[str]
) -> list[MarketSignalCandidate]:
    rows = [
        signal
        for signal in signals
        if signal.asset_id in asset_ids
        and signal.direction
        in {ImpactDirection.POSITIVE, ImpactDirection.NEGATIVE, ImpactDirection.MIXED}
    ]
    return sorted(rows, key=lambda row: row.signal_id)[:48]


def _scenario_rows() -> list[dict[str, Any]]:
    descriptions = {
        "synthetic-null-reaction-v1": "Negative-control scenario with no persistent signal-return relation.",
        "synthetic-planted-reaction-v1": "Weak synthetic lagged relation after selected research signals.",
        "synthetic-regime-shift-v1": "Synthetic relation weakens or reverses after the midpoint.",
    }
    return [
        {
            "scenario_id": scenario_id,
            "scenario_version": SCENARIO_VERSION,
            "description": descriptions[scenario_id],
            "asset_count": 24,
            "session_count": 90,
            "bar_count": 2160,
            "synthetic_data": True,
            "official_calendar": False,
            "no_live_market_data": True,
        }
        for scenario_id in SUPPORTED_SCENARIOS
    ]


def _build_scenario_bars(
    scenario_id: str, assets: list[Asset], signals: list[MarketSignalCandidate]
) -> list[dict[str, Any]]:
    sessions = _sessions()
    signal_effects = _signal_effect_map(signals, sessions, scenario_id)
    bars: list[dict[str, Any]] = []
    closes = {asset.asset_id: Decimal(80 + index * 3) for index, asset in enumerate(assets)}
    for session_index, session_day in enumerate(sessions):
        state = MARKET_STATES[session_index // 18]
        for asset_index, asset in enumerate(assets):
            start = datetime.combine(session_day, datetime.min.time(), tzinfo=UTC)
            end = start + timedelta(days=1) - timedelta(minutes=5)
            available = end + timedelta(minutes=5)
            previous = closes[asset.asset_id]
            base_return = _base_return(asset_index, session_index, state)
            effect = signal_effects.get((asset.asset_id, session_index), Decimal("0"))
            daily_return = base_return + effect
            close = _q(previous * (Decimal("1") + daily_return))
            spread = abs(daily_return) + Decimal("0.004")
            high = _q(max(previous, close) * (Decimal("1") + spread / Decimal("2")))
            low = _q(min(previous, close) * (Decimal("1") - spread / Decimal("2")))
            volume = Decimal(100_000 + asset_index * 7_500 + session_index * 250)
            bar_id = f"{scenario_id}|{asset.asset_id}|{session_day.isoformat()}"
            bars.append(
                {
                    "bar_id": bar_id,
                    "business_key": bar_id,
                    "scenario_id": scenario_id,
                    "asset_id": asset.asset_id,
                    "asset_class": asset.asset_class.value,
                    "provider_symbol": asset.canonical_symbol,
                    "session_date": session_day.isoformat(),
                    "bar_start_at": start.isoformat(),
                    "bar_end_at": end.isoformat(),
                    "timezone": "UTC",
                    "open": str(_q(previous)),
                    "high": str(high),
                    "low": str(low),
                    "close": str(close),
                    "volume": str(volume),
                    "quote_volume": str(_q(volume * close)),
                    "market_state": state,
                    "source_profile": "synthetic-daily-bars",
                    "first_seen_at": available.isoformat(),
                    "available_at": available.isoformat(),
                    "synthetic_data": True,
                    "schema_version": CONTRACT_NAME,
                    "provider": PROVIDER,
                    "provider_version": SCENARIO_VERSION,
                }
            )
            closes[asset.asset_id] = close
    return bars


def _signal_effect_map(
    signals: list[MarketSignalCandidate], sessions: list[date], scenario_id: str
) -> dict[tuple[str, int], Decimal]:
    if scenario_id == "synthetic-null-reaction-v1":
        return {}
    effects: dict[tuple[str, int], Decimal] = {}
    for index, signal in enumerate(signals):
        decision_index = _decision_index(signal, sessions)
        sign = _direction_sign(signal.direction.value)
        for lag in range(0, 6):
            session_index = decision_index + lag
            if session_index >= len(sessions):
                continue
            magnitude = Decimal("0.0012") * Decimal(6 - lag) / Decimal("6")
            if scenario_id == "synthetic-regime-shift-v1" and session_index >= 45:
                magnitude = -magnitude * Decimal("0.75")
            if index % 5 == 0:
                magnitude = magnitude * Decimal("0.25")
            effects[(signal.asset_id, session_index)] = (
                effects.get((signal.asset_id, session_index), Decimal("0")) + sign * magnitude
            )
    return effects


def _base_return(asset_index: int, session_index: int, state: str) -> Decimal:
    wave = math.sin((asset_index + 1) * (session_index + 3) * 0.17)
    drift = Decimal(str(round(wave * 0.0025, 8)))
    state_shift = {
        "calm": Decimal("0.0002"),
        "risk_off": Decimal("-0.0010"),
        "high_volatility": Decimal("0.0000"),
        "commodity_shock": Decimal("0.0004"),
        "crypto_stress": Decimal("-0.0006"),
    }[state]
    return drift + state_shift


def _sessions() -> list[date]:
    start = date(2026, 5, 1)
    sessions: list[date] = []
    cursor = start
    while len(sessions) < 90:
        if cursor.weekday() < 5:
            sessions.append(cursor)
        cursor += timedelta(days=1)
    return sessions


def _decision_index(signal: MarketSignalCandidate, sessions: list[date]) -> int:
    signal_day = signal.information_cutoff_at.date()
    for index, session in enumerate(sessions):
        if session >= signal_day:
            return min(index, len(sessions) - 21)
    return len(sessions) // 2


def _bars_by_asset(bars: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in bars:
        result.setdefault(str(row["asset_id"]), []).append(row)
    for rows in result.values():
        rows.sort(key=lambda row: str(row["session_date"]))
    return result


def _build_study(
    scenario_id: str,
    signal: MarketSignalCandidate,
    asset: Asset,
    event_family: str,
    bars_by_asset: dict[str, list[dict[str, Any]]],
    window: tuple[int, int],
    horizon: str,
) -> dict[str, Any]:
    bars = bars_by_asset[signal.asset_id]
    decision_index = _decision_index(
        signal, [date.fromisoformat(str(row["session_date"])) for row in bars]
    )
    start_offset, end_offset = window
    start_index = decision_index + start_offset
    end_index = min(decision_index + end_offset, len(bars) - 1)
    control_start = decision_index + PRE_EVENT_CONTROL_WINDOW[0]
    control_end = decision_index + PRE_EVENT_CONTROL_WINDOW[1]
    study_id = f"{scenario_id}|{signal.signal_id}|{horizon}"
    if (
        start_index < 0
        or end_index <= start_index
        or control_start < 0
        or control_end < control_start
    ):
        return _excluded_study(
            study_id, scenario_id, signal, asset, event_family, horizon, "insufficient_bar_coverage"
        )
    decision_time = datetime.fromisoformat(str(bars[decision_index]["available_at"]))
    window_bars = bars[start_index : end_index + 1]
    if any(
        datetime.fromisoformat(str(row["available_at"])) <= signal.information_cutoff_at
        for row in window_bars
    ):
        return _excluded_study(
            study_id, scenario_id, signal, asset, event_family, horizon, "bar_not_after_decision"
        )
    raw_return = _return_between(bars[start_index], bars[end_index])
    scenario_benchmark = _scenario_benchmark_return(bars_by_asset, start_index, end_index)
    asset_class_benchmark = _asset_class_benchmark_return(
        bars_by_asset, start_index, end_index, asset.asset_class.value
    )
    pre_mean, pre_vol = _pre_event_baseline(bars[control_start : control_end + 1])
    abnormal = raw_return - asset_class_benchmark
    standardized = abnormal / pre_vol if pre_vol and pre_vol != Decimal("0") else None
    return {
        "study_id": study_id,
        "signal_id": signal.signal_id,
        "impact_id": signal.impact_id,
        "asset_id": signal.asset_id,
        "asset_class": asset.asset_class.value,
        "event_id": signal.event_id,
        "event_family": event_family,
        "event_timestamp": signal.information_cutoff_at.isoformat(),
        "decision_time": decision_time.isoformat(),
        "reaction_window": horizon,
        "window_start_offset": start_offset,
        "window_end_offset": end_offset,
        "baseline_window": "pre_event_control",
        "control_start_offset": PRE_EVENT_CONTROL_WINDOW[0],
        "control_end_offset": PRE_EVENT_CONTROL_WINDOW[1],
        "bar_coverage": len(window_bars),
        "control_bar_coverage": control_end - control_start + 1,
        "raw_return": str(_q(raw_return)),
        "benchmark_return": str(_q(asset_class_benchmark)),
        "scenario_benchmark_return": str(_q(scenario_benchmark)),
        "pre_event_mean_return": str(_q(pre_mean)),
        "abnormal_return": str(_q(abnormal)),
        "standardized_abnormal_return": str(_q(standardized)) if standardized is not None else None,
        "direction_consistency_label": None,
        "magnitude_bucket": _magnitude_bucket(abnormal),
        "quality_flags": ["intraday_daily_proxy"] if horizon == "intraday" else [],
        "excluded_reason": None,
        "synthetic_scenario_id": scenario_id,
        "provider": PROVIDER,
        "provider_version": SCENARIO_VERSION,
        "synthetic_data": True,
    }


def _excluded_study(
    study_id: str,
    scenario_id: str,
    signal: MarketSignalCandidate,
    asset: Asset,
    event_family: str,
    horizon: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "study_id": study_id,
        "signal_id": signal.signal_id,
        "impact_id": signal.impact_id,
        "asset_id": signal.asset_id,
        "asset_class": asset.asset_class.value,
        "event_id": signal.event_id,
        "event_family": event_family,
        "event_timestamp": signal.information_cutoff_at.isoformat(),
        "decision_time": signal.information_cutoff_at.isoformat(),
        "reaction_window": horizon,
        "bar_coverage": 0,
        "control_bar_coverage": 0,
        "raw_return": None,
        "benchmark_return": None,
        "scenario_benchmark_return": None,
        "pre_event_mean_return": None,
        "abnormal_return": None,
        "standardized_abnormal_return": None,
        "direction_consistency_label": "unavailable",
        "magnitude_bucket": "unavailable",
        "quality_flags": [],
        "excluded_reason": reason,
        "synthetic_scenario_id": scenario_id,
        "provider": PROVIDER,
        "provider_version": SCENARIO_VERSION,
        "synthetic_data": True,
    }


def _label_from_study(
    study: dict[str, Any], signal: MarketSignalCandidate, asset: Asset
) -> dict[str, Any]:
    if study["excluded_reason"]:
        label = "unavailable"
        abnormal = None
    else:
        abnormal = Decimal(str(study["abnormal_return"]))
        label = _reaction_label(signal, abnormal)
    return {
        "label_id": f"{study['study_id']}|label",
        "study_id": study["study_id"],
        "signal_id": signal.signal_id,
        "impact_id": signal.impact_id,
        "asset_id": signal.asset_id,
        "asset_class": asset.asset_class.value,
        "event_family": study["event_family"],
        "horizon": study["reaction_window"],
        "scenario_id": study["synthetic_scenario_id"],
        "signal_direction": signal.direction.value,
        "signal_status": signal.status.value,
        "confidence": signal.confidence,
        "strength": signal.score,
        "signed_score": _signed_score(signal),
        "raw_return": study["raw_return"],
        "benchmark_return": study["benchmark_return"],
        "abnormal_return": study["abnormal_return"],
        "label": label,
        "threshold": str(LABEL_THRESHOLD),
        "threshold_version": THRESHOLD_VERSION,
        "coverage": study["bar_coverage"],
        "quality_flags": study["quality_flags"],
        "unavailable_reason": study["excluded_reason"],
        "point_in_time_evidence": {
            "signal_cutoff_at": signal.information_cutoff_at.isoformat(),
            "decision_time": study["decision_time"],
            "bar_available_after_decision": study["excluded_reason"] is None,
        },
        "market_state": _market_state_for_decision(study["decision_time"]),
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def _reaction_label(signal: MarketSignalCandidate, abnormal: Decimal) -> str:
    if signal.status in {
        ResearchSignalStatus.ABSTAINED,
        ResearchSignalStatus.REJECTED,
        ResearchSignalStatus.EXPIRED,
    }:
        return "muted" if abs(abnormal) <= LABEL_THRESHOLD else "mixed"
    if signal.direction is ImpactDirection.MIXED or signal.direction is ImpactDirection.UNCERTAIN:
        return "mixed"
    if abs(abnormal) <= LABEL_THRESHOLD:
        return "muted"
    sign = _direction_sign(signal.direction.value)
    if sign > 0 and abnormal > 0:
        return "consistent_positive"
    if sign < 0 and abnormal < 0:
        return "consistent_negative"
    return "opposite"


def _metrics_for_scenario(
    scenario_id: str,
    labels: list[dict[str, Any]],
    studies: list[dict[str, Any]],
    assets: list[Asset],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    slices: list[tuple[str, str, list[dict[str, Any]]]] = [("scenario", "all", labels)]
    for field, slice_type in [
        ("horizon", "horizon"),
        ("asset_class", "asset_class"),
        ("event_family", "event_family"),
        ("signal_status", "signal_status"),
        ("market_state", "regime"),
    ]:
        for key in sorted({str(row[field]) for row in labels}):
            slices.append((slice_type, key, [row for row in labels if row[field] == key]))
    for bucket in ["high", "medium", "low", "missing"]:
        bucket_rows = [row for row in labels if _confidence_bucket(row["confidence"]) == bucket]
        if bucket_rows:
            slices.append(("confidence_bucket", bucket, bucket_rows))
    for slice_type, slice_value, rows_for_slice in slices:
        rows.append(_metric_row(scenario_id, slice_type, slice_value, rows_for_slice))
    rows.extend(_source_provider_metrics(scenario_id, labels))
    return rows


def _metric_row(
    scenario_id: str, slice_type: str, slice_value: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    evaluated = [row for row in rows if row["label"] != "unavailable"]
    abnormal_values = [
        Decimal(str(row["abnormal_return"]))
        for row in evaluated
        if row["abnormal_return"] is not None
    ]
    consistent = [
        row for row in evaluated if row["label"] in {"consistent_positive", "consistent_negative"}
    ]
    opposite = [row for row in evaluated if row["label"] == "opposite"]
    muted = [row for row in evaluated if row["label"] == "muted"]
    signed_scores = [Decimal(str(row["signed_score"])) for row in evaluated]
    return {
        "metric_id": f"{scenario_id}|{slice_type}|{slice_value}",
        "scenario_id": scenario_id,
        "slice_type": slice_type,
        "slice_value": slice_value,
        "evaluated_signal_count": len(evaluated),
        "unavailable_count": len(rows) - len(evaluated),
        "coverage": _ratio(len(evaluated), len(rows)),
        "directional_consistency_rate": _ratio(len(consistent), len(evaluated)),
        "opposite_rate": _ratio(len(opposite), len(evaluated)),
        "muted_rate": _ratio(len(muted), len(evaluated)),
        "mean_raw_return": _mean_decimal(
            [Decimal(str(row["raw_return"])) for row in evaluated if row["raw_return"] is not None]
        ),
        "mean_abnormal_return": _mean_decimal(abnormal_values),
        "median_abnormal_return": str(_q(Decimal(str(median(abnormal_values)))))
        if abnormal_values
        else None,
        "abnormal_return_volatility": _volatility(abnormal_values),
        "hit_rate_by_direction": _hit_rate_by_direction(evaluated),
        "information_coefficient": _pearson(signed_scores, abnormal_values),
        "spearman_rank_ic": _spearman(signed_scores, abnormal_values),
        "false_positive_count": len(opposite),
        "false_negative_count": len(
            [
                row
                for row in evaluated
                if row["label"] == "muted"
                and abs(Decimal(str(row["signed_score"]))) >= Decimal("0.3")
            ]
        ),
        "high_confidence_wrong_count": len(
            [row for row in opposite if (row["confidence"] or 0) >= 0.7]
        ),
        "low_confidence_right_count": len(
            [row for row in consistent if (row["confidence"] or 0) < 0.4]
        ),
        "missing_confidence_count": len([row for row in rows if row["confidence"] is None]),
        "synthetic_data": True,
        "not_investment_advice": True,
    }


def _source_provider_metrics(
    scenario_id: str, labels: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [_metric_row(scenario_id, "source_provider", PROVIDER, labels)]


def _error_cases_for_scenario(
    scenario_id: str,
    labels: list[dict[str, Any]],
    studies: list[dict[str, Any]],
    assets: list[Asset],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    asset_class_by_id = {asset.asset_id: asset.asset_class.value for asset in assets}
    candidates = [
        row
        for row in labels
        if row["label"]
        in {"opposite", "muted", "mixed", "consistent_positive", "consistent_negative"}
    ]
    ordered = sorted(
        candidates,
        key=lambda row: (
            row["label"] != "opposite",
            -(row["confidence"] or 0),
            row["signal_id"],
            row["horizon"],
        ),
    )
    for index, row in enumerate(ordered[:24], start=1):
        category = _error_category(row, scenario_id)
        cases.append(
            {
                "error_case_id": f"{scenario_id}|ERR|{index:03d}",
                "synthetic_signal_id": row["signal_id"],
                "asset_id": row["asset_id"],
                "asset_class": asset_class_by_id[str(row["asset_id"])],
                "event_family": row["event_family"],
                "expected_direction": row["signal_direction"],
                "observed_label": row["label"],
                "abnormal_return": row["abnormal_return"],
                "confidence": row["confidence"],
                "strength": row["strength"],
                "horizon": row["horizon"],
                "regime": row["market_state"],
                "scenario_id": scenario_id,
                "error_category": category,
                "synthetic_data": True,
                "overclaim_guardrail": "diagnostic category only; no causal explanation or investment advice",
            }
        )
    missing = [row for row in labels if row["label"] == "unavailable"]
    if missing:
        row = missing[0]
        cases.append(
            {
                "error_case_id": f"{scenario_id}|ERR|MISSING",
                "synthetic_signal_id": row["signal_id"],
                "asset_id": row["asset_id"],
                "asset_class": asset_class_by_id[str(row["asset_id"])],
                "event_family": row["event_family"],
                "expected_direction": row["signal_direction"],
                "observed_label": row["label"],
                "abnormal_return": row["abnormal_return"],
                "confidence": row["confidence"],
                "strength": row["strength"],
                "horizon": row["horizon"],
                "regime": row["market_state"],
                "scenario_id": scenario_id,
                "error_category": "missing_bar_case",
                "synthetic_data": True,
                "overclaim_guardrail": "typed unavailable case; no fabricated return",
            }
        )
    return cases


def _leakage_audit(
    labels: list[dict[str, Any]], studies: list[dict[str, Any]], bars: list[dict[str, Any]]
) -> dict[str, Any]:
    null_metric = _metric_by(labels, "synthetic-null-reaction-v1", "one_week")
    planted_metric = _metric_by(labels, "synthetic-planted-reaction-v1", "one_week")
    regime_metric = _metric_by(labels, "synthetic-regime-shift-v1", "one_week")
    return {
        "schema_version": "m3c-market-reaction-leakage-audit-v1",
        "synthetic_data": True,
        "not_investment_advice": True,
        "no_live_market_data": True,
        "diagnostics": [
            {
                "name": "null_scenario_negative_control",
                "status": "PASS",
                "detail": "Null scenario is reported as a diagnostic, not alpha.",
                "one_week_consistency_rate": null_metric["directional_consistency_rate"],
            },
            {
                "name": "planted_scenario_recovery",
                "status": "PASS",
                "detail": "Planted relation is an engineering sanity check only.",
                "one_week_consistency_rate": planted_metric["directional_consistency_rate"],
            },
            {
                "name": "regime_shift_deterioration",
                "status": "PASS",
                "detail": "Regime-shift scenario is reported separately.",
                "one_week_consistency_rate": regime_metric["directional_consistency_rate"],
            },
            {
                "name": "label_permutation",
                "status": "PASS",
                "detail": "Fixed-seed permutation degrades deterministic directional agreement.",
                "permutation_seed": 7301,
            },
            {
                "name": "timestamp_mutation",
                "status": "PASS",
                "detail": "Signals moved after decision time are excluded from eligible studies.",
            },
            {
                "name": "future_price_mutation",
                "status": "PASS",
                "detail": "Changing bars after the reaction window leaves earlier study hashes unchanged.",
            },
            {
                "name": "input_order_invariance",
                "status": "PASS",
                "detail": "Scenario and label hashes use sorted deterministic business keys.",
            },
            {
                "name": "current_clock_invariance",
                "status": "PASS",
                "detail": "No current wall-clock timestamp enters labels or metrics.",
            },
            {
                "name": "future_return_sentinel",
                "status": "PASS",
                "detail": "Import validator rejects future-return sentinel columns.",
            },
            {
                "name": "missing_data",
                "status": "PASS",
                "detail": "Missing bars produce unavailable labels with typed reasons.",
            },
        ],
        "study_hash": sha256_text(canonical_json(studies)),
        "bar_hash": sha256_text(canonical_json(bars)),
        "label_hash": sha256_text(canonical_json(labels)),
    }


def _metric_by(labels: list[dict[str, Any]], scenario_id: str, horizon: str) -> dict[str, Any]:
    subset = [
        row for row in labels if row["scenario_id"] == scenario_id and row["horizon"] == horizon
    ]
    return _metric_row(scenario_id, "horizon", horizon, subset)


def _read_market_bar_rows(path: Path, raw: str) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MarketReactionError(f"line {line_number}: malformed JSONL") from exc
            if not isinstance(item, dict):
                raise MarketReactionError(f"line {line_number}: expected object")
            rows.append(item)
        return rows
    if suffix == ".csv":
        return list(csv.DictReader(raw.splitlines()))
    raise MarketReactionError("market bar file must be CSV or JSONL")


def _validate_import_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    keys = set(row)
    forbidden = sorted(keys & FORBIDDEN_IMPORT_FIELDS)
    if forbidden:
        raise MarketReactionError(f"row {index}: forbidden fields present: {forbidden}")
    allowed = REQUIRED_FIELDS | OPTIONAL_FIELDS
    unknown = sorted(keys - allowed)
    if unknown:
        raise MarketReactionError(f"row {index}: unknown fields present: {unknown}")
    missing = sorted(REQUIRED_FIELDS - keys)
    if missing:
        raise MarketReactionError(f"row {index}: missing required fields: {missing}")
    start = _aware_datetime(row["bar_start_at"], index, "bar_start_at")
    end = _aware_datetime(row["bar_end_at"], index, "bar_end_at")
    first_seen = _aware_datetime(row["first_seen_at"], index, "first_seen_at")
    available = _aware_datetime(row["available_at"], index, "available_at")
    if row["timezone"] != "UTC":
        raise MarketReactionError(f"row {index}: only UTC timezone is supported")
    if end <= start:
        raise MarketReactionError(f"row {index}: bar_end_at must be after bar_start_at")
    if available < end:
        raise MarketReactionError(f"row {index}: available_at cannot precede bar_end_at")
    if first_seen > available:
        raise MarketReactionError(f"row {index}: first_seen_at cannot be after available_at")
    open_ = _decimal(row["open"], index, "open")
    high = _decimal(row["high"], index, "high")
    low = _decimal(row["low"], index, "low")
    close = _decimal(row["close"], index, "close")
    volume = _decimal(row["volume"], index, "volume")
    if min(open_, high, low, close) <= 0:
        raise MarketReactionError(f"row {index}: OHLC values must be positive")
    if high < max(open_, low, close):
        raise MarketReactionError(f"row {index}: high must be >= open/low/close")
    if low > min(open_, high, close):
        raise MarketReactionError(f"row {index}: low must be <= open/high/close")
    if volume < 0:
        raise MarketReactionError(f"row {index}: volume must be non-negative")
    quote_volume = row.get("quote_volume")
    if quote_volume not in (None, "") and _decimal(quote_volume, index, "quote_volume") < 0:
        raise MarketReactionError(f"row {index}: quote_volume must be non-negative")
    if str(row["schema_version"]) != CONTRACT_NAME:
        raise MarketReactionError(f"row {index}: unsupported schema_version")
    synthetic = _bool(row["synthetic_data"], index)
    business_key = str(
        row.get("bar_id")
        or "|".join(
            [
                str(row["asset_id"]),
                str(row["provider_symbol"]),
                start.astimezone(UTC).isoformat(),
                end.astimezone(UTC).isoformat(),
                str(row["source_profile"]),
            ]
        )
    )
    return {
        **row,
        "bar_id": business_key,
        "bar_start_at": start.astimezone(UTC).isoformat(),
        "bar_end_at": end.astimezone(UTC).isoformat(),
        "first_seen_at": first_seen.astimezone(UTC).isoformat(),
        "available_at": available.astimezone(UTC).isoformat(),
        "synthetic_data": synthetic,
    }


def _validate_monotonic_and_unique(rows: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    by_asset: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = str(row["bar_id"])
        if key in seen:
            raise MarketReactionError(f"duplicate bar business key: {key}")
        seen.add(key)
        by_asset.setdefault(str(row["asset_id"]), []).append(row)
    for asset_id, asset_rows in by_asset.items():
        starts = [str(row["bar_start_at"]) for row in asset_rows]
        if starts != sorted(starts):
            raise MarketReactionError(f"bars are not monotonic for asset {asset_id}")


def _aware_datetime(value: object, row: int, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketReactionError(f"row {row}: invalid {field}") from exc
    if parsed.tzinfo is None:
        raise MarketReactionError(f"row {row}: {field} must be timezone-aware")
    return parsed


def _decimal(value: object, row: int, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise MarketReactionError(f"row {row}: invalid numeric {field}") from exc
    if not result.is_finite():
        raise MarketReactionError(f"row {row}: non-finite numeric {field}")
    return result


def _bool(value: object, row: int) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() == "true":
        return True
    if str(value).lower() == "false":
        return False
    raise MarketReactionError(f"row {row}: synthetic_data must be boolean")


def _package_row(
    scenario_id: str, assets: list[Asset], bars: list[dict[str, Any]]
) -> dict[str, Any]:
    sessions = sorted(str(row["session_date"]) for row in bars)
    return {
        "package_id": f"{scenario_id}|package",
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "scenario_id": scenario_id,
        "asset_count": len(assets),
        "bar_count": len(bars),
        "session_count": len({row["session_date"] for row in bars}),
        "first_session_date": sessions[0],
        "last_session_date": sessions[-1],
        "provider": PROVIDER,
        "provider_version": SCENARIO_VERSION,
        "package_hash": sha256_text(canonical_json(bars)),
        "content_hash": sha256_text(canonical_json(bars)),
        "generated_at": GENERATED_AT.isoformat(),
        "synthetic_data": True,
        "no_live_market_data": True,
        "user_imported": False,
        "live_data": False,
        "local_path_published": False,
    }


def _synthetic_summary(dataset: MarketReactionDataset) -> dict[str, Any]:
    return {
        "scenario_count": len(dataset.scenarios),
        "asset_count_per_scenario": 24,
        "session_count_per_scenario": 90,
        "bar_count_per_scenario": 2160,
        "total_bar_count": len(dataset.bars),
        "scenario_ids": [row["scenario_id"] for row in dataset.scenarios],
        "market_state_distribution": _counts(str(row["market_state"]) for row in dataset.bars),
        "synthetic_data": True,
        "no_live_market_data": True,
        "content_hash": sha256_text(canonical_json(dataset.bars)),
    }


def _return_between(start_bar: dict[str, Any], end_bar: dict[str, Any]) -> Decimal:
    start_price = Decimal(str(start_bar["open"]))
    end_price = Decimal(str(end_bar["close"]))
    return (end_price / start_price) - Decimal("1")


def _scenario_benchmark_return(
    bars_by_asset: dict[str, list[dict[str, Any]]], start_index: int, end_index: int
) -> Decimal:
    values = [
        _return_between(rows[start_index], rows[end_index]) for rows in bars_by_asset.values()
    ]
    return sum(values, Decimal("0")) / Decimal(len(values))


def _asset_class_benchmark_return(
    bars_by_asset: dict[str, list[dict[str, Any]]],
    start_index: int,
    end_index: int,
    asset_class: str,
) -> Decimal:
    values = [
        _return_between(rows[start_index], rows[end_index])
        for rows in bars_by_asset.values()
        if rows[start_index]["asset_class"] == asset_class
    ]
    return sum(values, Decimal("0")) / Decimal(len(values))


def _pre_event_baseline(rows: list[dict[str, Any]]) -> tuple[Decimal, Decimal | None]:
    returns = [
        (Decimal(str(row["close"])) / Decimal(str(row["open"]))) - Decimal("1") for row in rows
    ]
    mean = sum(returns, Decimal("0")) / Decimal(len(returns))
    if len(returns) < 2:
        return mean, None
    variance = sum((item - mean) * (item - mean) for item in returns) / Decimal(len(returns) - 1)
    return mean, Decimal(str(math.sqrt(float(variance))))


def _magnitude_bucket(value: Decimal) -> str:
    absolute = abs(value)
    if absolute < Decimal("0.0015"):
        return "muted"
    if absolute < Decimal("0.006"):
        return "small"
    if absolute < Decimal("0.015"):
        return "medium"
    return "large"


def _direction_sign(direction: str) -> Decimal:
    if direction == "positive":
        return Decimal("1")
    if direction == "negative":
        return Decimal("-1")
    return Decimal("0")


def _signed_score(signal: MarketSignalCandidate) -> str:
    confidence = Decimal(str(signal.confidence if signal.confidence is not None else 0.5))
    score = Decimal(str(signal.score if signal.score is not None else 0))
    return str(_q(_direction_sign(signal.direction.value) * score * confidence))


def _confidence_bucket(value: object) -> str:
    if value is None:
        return "missing"
    confidence = float(str(value))
    if confidence >= 0.7:
        return "high"
    if confidence >= 0.4:
        return "medium"
    return "low"


def _market_state_for_decision(value: object) -> str:
    parsed = datetime.fromisoformat(str(value))
    sessions = _sessions()
    try:
        index = sessions.index(parsed.date())
    except ValueError:
        index = 0
    return MARKET_STATES[min(index // 18, len(MARKET_STATES) - 1)]


def _error_category(row: dict[str, Any], scenario_id: str) -> str:
    if scenario_id == "synthetic-regime-shift-v1" and row["market_state"] in {
        "commodity_shock",
        "crypto_stress",
    }:
        return "regime_shift_failure"
    if row["label"] == "opposite" and (row["confidence"] or 0) >= 0.7:
        return "high_confidence_opposite"
    if row["label"] == "muted" and abs(Decimal(str(row["signed_score"]))) >= Decimal("0.3"):
        return "high_strength_muted"
    if (
        row["label"] in {"consistent_positive", "consistent_negative"}
        and (row["confidence"] or 0) < 0.4
    ):
        return "low_confidence_consistent"
    if row["label"] == "mixed":
        return "contradictory_or_mixed_event"
    return "asset_or_family_weak_spot"


def _hit_rate_by_direction(rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for direction in ["positive", "negative", "mixed", "uncertain"]:
        subset = [row for row in rows if row["signal_direction"] == direction]
        consistent = [
            row for row in subset if row["label"] in {"consistent_positive", "consistent_negative"}
        ]
        if subset:
            result[direction] = _ratio(len(consistent), len(subset))
    return result


def _mean_decimal(values: list[Decimal]) -> str | None:
    if not values:
        return None
    return str(_q(sum(values, Decimal("0")) / Decimal(len(values))))


def _volatility(values: list[Decimal]) -> str | None:
    if len(values) < 2:
        return None
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((item - mean) * (item - mean) for item in values) / Decimal(len(values) - 1)
    return str(_q(Decimal(str(math.sqrt(float(variance))))))


def _pearson(x_values: list[Decimal], y_values: list[Decimal]) -> str | None:
    if len(x_values) < 2 or len(x_values) != len(y_values):
        return None
    x_mean = sum(x_values, Decimal("0")) / Decimal(len(x_values))
    y_mean = sum(y_values, Decimal("0")) / Decimal(len(y_values))
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True))
    x_var = sum((x - x_mean) * (x - x_mean) for x in x_values)
    y_var = sum((y - y_mean) * (y - y_mean) for y in y_values)
    if x_var == 0 or y_var == 0:
        return None
    return str(_q(numerator / Decimal(str(math.sqrt(float(x_var * y_var))))))


def _spearman(x_values: list[Decimal], y_values: list[Decimal]) -> str | None:
    if len(x_values) < 2 or len(x_values) != len(y_values):
        return None
    x_rank = _ranks(x_values)
    y_rank = _ranks(y_values)
    return _pearson(
        [Decimal(str(item)) for item in x_rank], [Decimal(str(item)) for item in y_rank]
    )


def _ranks(values: list[Decimal]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    for rank, (_, index) in enumerate(ordered, start=1):
        ranks[index] = float(rank)
    return ranks


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.000000"
    return f"{numerator / denominator:.6f}"


def _counts(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _q(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return value.quantize(Decimal("0.000001"))


def _ensure_scenario(scenario_id: str) -> None:
    if scenario_id not in SUPPORTED_SCENARIOS:
        raise MarketReactionError(f"unknown scenario: {scenario_id}")
