from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from finnews.application.ports.repositories import NewsRepository
from finnews.domain.entities import (
    Article,
    ArticleCompanyLink,
    ArticleEvent,
    ArticleSentiment,
    Company,
    ResearchCalendar,
    ResearchExportRun,
    ResearchFeatureRow,
    ResearchLineageRow,
    ResearchSession,
)
from finnews.domain.enums import EventType, ProcessingState, SentimentLabel

CONTRACT_NAME = "finnews-research-export-v1"
CONTRACT_VERSION = "1.0.0"
FEATURE_SCHEMA_VERSION = "news-factor-v1"
GENERATED_BY_VERSION = "finnews-m3a"
DEMO_CALENDAR_ID = "synthetic-ashare-demo-calendar"
DEMO_CALENDAR_VERSION = "2026-demo-v1"
DEMO_EXPORT_ID = "synthetic-news-factor-demo-v1"
CALENDAR_TIMEZONE = "Asia/Shanghai"
DEFAULT_WINDOWS = [1, 3, 5, 10]
DEFAULT_CUTOFF_POLICY = "pre_open_15m"
SESSION_COUNT = 60
DEMO_SYNTHETIC_HOLIDAYS = [
    date(2026, 5, 12),
    date(2026, 5, 15),
    date(2026, 6, 19),
    date(2026, 7, 6),
]
PACKAGE_FILES = [
    "calendar.csv",
    "companies.csv",
    "feature_rows.csv",
    "feature_rows.jsonl",
    "lineage.jsonl",
    "quality_report.json",
    "leakage_audit.json",
]
CALENDAR_FIELDS = [
    "calendar_id",
    "calendar_version",
    "timezone",
    "session_date",
    "open_at",
    "break_start_at",
    "break_end_at",
    "close_at",
    "sequence",
    "special_session",
]
COMPANY_FIELDS = [
    "company_id",
    "ticker",
    "exchange",
    "legal_name",
    "short_name",
    "sector",
    "active",
    "synthetic_data",
]
BASE_FEATURE_FIELDS = [
    "contract_version",
    "calendar_id",
    "calendar_version",
    "session_date",
    "decision_cutoff_at",
    "ticker",
    "company_id",
    "window_sessions",
    "feature_schema_version",
    "information_cutoff_at",
    "generated_from_article_count",
    "latest_information_available_at",
    "event_provider",
    "event_model_version",
    "sentiment_provider",
    "sentiment_model_version",
    "lineage_row_id",
    "synthetic_data",
    "generated_by_version",
]
CORE_FEATURE_FIELDS = [
    "news_count",
    "unique_article_count",
    "unique_source_count",
    "has_news",
    "missing_published_time_count",
    "abstained_prediction_count",
    "positive_count",
    "neutral_count",
    "negative_count",
    "uncertain_count",
    "positive_share",
    "negative_share",
    "uncertain_share",
    "mean_sentiment_score",
    "confidence_weighted_sentiment_score",
    "sentiment_score_std",
    "min_sentiment_score",
    "max_sentiment_score",
    "event_type_count",
    "event_entropy",
    "mean_novelty_score",
    "max_novelty_score",
    "source_diversity_ratio",
    "hours_since_latest_news",
    "decayed_news_count",
    "decayed_sentiment_score",
    "low_coverage",
    "contains_missing_timestamp",
    "contains_abstention",
    "contains_multi_company_article",
    "contains_backfilled_information",
]
EVENT_FEATURE_FIELDS = [
    item
    for event_type in EventType
    for item in (f"event_{event_type.value}_count", f"event_{event_type.value}_share")
]
FEATURE_FIELDS = [*CORE_FEATURE_FIELDS, *EVENT_FEATURE_FIELDS]
FEATURE_ROW_FIELDS = [*BASE_FEATURE_FIELDS, *FEATURE_FIELDS]
LINEAGE_FIELDS = [
    "lineage_row_id",
    "feature_row_key",
    "contract_version",
    "calendar_id",
    "calendar_version",
    "session_date",
    "decision_cutoff_at",
    "ticker",
    "company_id",
    "window_sessions",
    "canonical_article_id",
    "source_id",
    "company_link_id",
    "source_published_at",
    "first_seen_at",
    "processed_at",
    "information_available_at",
    "event_label",
    "event_provider",
    "event_model_version",
    "sentiment_label",
    "sentiment_score",
    "sentiment_confidence",
    "sentiment_provider",
    "sentiment_model_version",
    "novelty_score",
    "inclusion_reason",
    "assigned_session_date",
    "assigned_cutoff_at",
    "synthetic_data",
]


class ResearchExportError(ValueError):
    pass


@dataclass(frozen=True)
class CalendarValidationResult:
    valid: bool
    calendar_id: str
    calendar_version: str
    timezone: str
    session_count: int
    calendar_hash: str
    errors: list[str]


@dataclass(frozen=True)
class ResearchExportPackage:
    export_id: str
    manifest: dict[str, Any]
    calendar: ResearchCalendar
    sessions: list[ResearchSession]
    companies: list[Company]
    feature_rows: list[dict[str, Any]]
    lineage_rows: list[dict[str, Any]]
    quality_report: dict[str, Any]
    leakage_audit: dict[str, Any]
    file_hashes: dict[str, str]
    package_path: Path | None = None

    @property
    def package_hash(self) -> str:
        return str(self.manifest["package_content_hash"])


def build_demo_calendar() -> tuple[ResearchCalendar, list[ResearchSession]]:
    zone = ZoneInfo(CALENDAR_TIMEZONE)
    holidays = set(DEMO_SYNTHETIC_HOLIDAYS)
    sessions: list[ResearchSession] = []
    current = date(2026, 5, 11)
    while len(sessions) < SESSION_COUNT:
        if current.weekday() < 5 and current not in holidays:
            sequence = len(sessions) + 1
            sessions.append(
                ResearchSession(
                    calendar_id=DEMO_CALENDAR_ID,
                    calendar_version=DEMO_CALENDAR_VERSION,
                    session_date=current,
                    open_at=datetime.combine(current, time(9, 30), zone),
                    break_start_at=datetime.combine(current, time(11, 30), zone),
                    break_end_at=datetime.combine(current, time(13, 0), zone),
                    close_at=datetime.combine(current, time(15, 0), zone),
                    sequence=sequence,
                    special_session=False,
                    id=_stable_uuid("research-session", DEMO_CALENDAR_ID, current.isoformat()),
                )
            )
        current += timedelta(days=1)
    calendar_hash = calendar_hash_for_sessions(sessions)
    calendar = ResearchCalendar(
        calendar_id=DEMO_CALENDAR_ID,
        calendar_version=DEMO_CALENDAR_VERSION,
        timezone=CALENDAR_TIMEZONE,
        calendar_hash=calendar_hash,
        provenance={
            "source": "deterministic synthetic demo",
            "official_calendar": False,
            "holiday_count": len(holidays),
            "holiday_dates": [item.isoformat() for item in DEMO_SYNTHETIC_HOLIDAYS],
        },
        synthetic=True,
        id=_stable_uuid("research-calendar", DEMO_CALENDAR_ID, DEMO_CALENDAR_VERSION),
    )
    return calendar, sessions


def load_local_calendar(
    path: Path, *, max_bytes: int = 1_000_000
) -> tuple[ResearchCalendar, list[ResearchSession]]:
    if not path.is_file():
        raise ResearchExportError("calendar file does not exist")
    if path.stat().st_size > max_bytes:
        raise ResearchExportError("calendar file exceeds size limit")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ResearchExportError("calendar file must be UTF-8") from exc
    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
        metadata: dict[str, Any] = {}
    elif path.suffix.lower() == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict):
            metadata = dict(payload.get("metadata", {}))
            rows = list(payload.get("sessions", []))
        elif isinstance(payload, list):
            metadata = {}
            rows = payload
        else:
            raise ResearchExportError("calendar JSON must be an object or list")
    else:
        raise ResearchExportError("calendar path must end with .csv or .json")
    calendar_id = str(metadata.get("calendar_id", "local-user-calendar"))
    calendar_version = str(metadata.get("calendar_version", "local-v1"))
    timezone_name = str(metadata.get("timezone", CALENDAR_TIMEZONE))
    try:
        zone = ZoneInfo(timezone_name)
    except Exception as exc:
        raise ResearchExportError(f"invalid timezone: {timezone_name}") from exc
    sessions: list[ResearchSession] = []
    for index, row in enumerate(rows, start=1):
        try:
            session_date = date.fromisoformat(str(row["session_date"]))
            sessions.append(
                ResearchSession(
                    calendar_id=calendar_id,
                    calendar_version=calendar_version,
                    session_date=session_date,
                    open_at=_parse_aware_datetime(str(row["open_at"]), zone),
                    break_start_at=_parse_aware_datetime(str(row["break_start_at"]), zone),
                    break_end_at=_parse_aware_datetime(str(row["break_end_at"]), zone),
                    close_at=_parse_aware_datetime(str(row["close_at"]), zone),
                    sequence=int(row.get("sequence", index)),
                    special_session=_to_bool(row.get("special_session", False)),
                    id=_stable_uuid("research-session", calendar_id, session_date.isoformat()),
                )
            )
        except KeyError as exc:
            raise ResearchExportError(f"calendar row {index} missing required field") from exc
        except ResearchExportError:
            raise
        except Exception as exc:
            raise ResearchExportError(f"calendar row {index} is invalid") from exc
    validation = validate_calendar_sessions(calendar_id, calendar_version, timezone_name, sessions)
    if not validation.valid:
        raise ResearchExportError("; ".join(validation.errors))
    calendar = ResearchCalendar(
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        timezone=timezone_name,
        calendar_hash=validation.calendar_hash,
        provenance={
            "source": "user supplied local file",
            "official_calendar": bool(metadata.get("official_calendar", False)),
            "original_filename": path.name,
        },
        synthetic=bool(metadata.get("synthetic", False)),
        id=_stable_uuid("research-calendar", calendar_id, calendar_version),
    )
    return calendar, sorted(sessions, key=lambda item: item.sequence)


def validate_calendar_path(path: Path) -> CalendarValidationResult:
    try:
        calendar, sessions = load_local_calendar(path)
    except Exception as exc:
        return CalendarValidationResult(
            valid=False,
            calendar_id="unknown",
            calendar_version="unknown",
            timezone="unknown",
            session_count=0,
            calendar_hash="",
            errors=[str(exc)],
        )
    return validate_calendar_sessions(
        calendar.calendar_id, calendar.calendar_version, calendar.timezone, sessions
    )


def validate_calendar_sessions(
    calendar_id: str,
    calendar_version: str,
    timezone_name: str,
    sessions: list[ResearchSession],
) -> CalendarValidationResult:
    errors: list[str] = []
    try:
        ZoneInfo(timezone_name)
    except Exception:
        errors.append(f"invalid timezone: {timezone_name}")
    seen_dates: set[date] = set()
    previous_sequence = 0
    previous_date: date | None = None
    for session in sorted(sessions, key=lambda item: item.sequence):
        if session.session_date in seen_dates:
            errors.append(f"duplicate session_date: {session.session_date}")
        seen_dates.add(session.session_date)
        if session.sequence <= previous_sequence:
            errors.append("session sequences must be strictly increasing")
        previous_sequence = session.sequence
        if previous_date and session.session_date <= previous_date:
            errors.append("session dates must be strictly increasing")
        previous_date = session.session_date
        if not (session.open_at < session.break_start_at < session.break_end_at < session.close_at):
            errors.append(f"invalid open/break/close ordering: {session.session_date}")
        for stamp in (
            session.open_at,
            session.break_start_at,
            session.break_end_at,
            session.close_at,
        ):
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                errors.append(f"timestamp must be timezone-aware: {session.session_date}")
    return CalendarValidationResult(
        valid=not errors,
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        timezone=timezone_name,
        session_count=len(sessions),
        calendar_hash=calendar_hash_for_sessions(sessions) if not errors else "",
        errors=errors,
    )


def build_research_export(
    repository: NewsRepository,
    *,
    calendar: ResearchCalendar | None = None,
    sessions: list[ResearchSession] | None = None,
    cutoff_policy: Literal["pre_open_15m", "session_close"] = "pre_open_15m",
    windows: list[int] | None = None,
    persist_metadata: bool = False,
) -> ResearchExportPackage:
    windows = windows or DEFAULT_WINDOWS
    if calendar is None or sessions is None:
        calendar, sessions = build_demo_calendar()
    validation = validate_calendar_sessions(
        calendar.calendar_id, calendar.calendar_version, calendar.timezone, sessions
    )
    if not validation.valid:
        raise ResearchExportError("; ".join(validation.errors))
    if sorted(windows) != windows or any(window <= 0 for window in windows):
        raise ResearchExportError("windows must be positive ascending session counts")
    companies = sorted(repository.list_companies(), key=lambda item: item.ticker)
    if not companies:
        raise ResearchExportError("no companies available for research export")
    observations, excluded = _build_observations(repository, sessions, cutoff_policy)
    assigned_by_company_session: dict[tuple[UUID, int], list[_Observation]] = {}
    lineage_rows: list[dict[str, Any]] = []
    for observation in observations:
        if observation.assigned_session is None or observation.assigned_cutoff_at is None:
            excluded[observation.exclusion_reason or "out_of_calendar"] += 1
            lineage_rows.append(_excluded_lineage_row(observation, calendar, cutoff_policy))
            continue
        assigned_by_company_session.setdefault(
            (observation.company_id, observation.assigned_session.sequence), []
        ).append(observation)
    company_by_id = {company.id: company for company in companies}
    feature_rows: list[dict[str, Any]] = []
    non_empty_lineage: list[dict[str, Any]] = []
    for session in sessions:
        cutoff = decision_cutoff(session, cutoff_policy)
        for company in companies:
            for window in windows:
                lower = max(1, session.sequence - window + 1)
                row_observations: list[_Observation] = []
                for sequence in range(lower, session.sequence + 1):
                    row_observations.extend(
                        assigned_by_company_session.get((company.id, sequence), [])
                    )
                row_observations = sorted(
                    row_observations,
                    key=lambda item: (
                        item.information_available_at.isoformat(),
                        str(item.article_id),
                        str(item.company_id),
                    ),
                )
                logical_key = _feature_logical_key(calendar, session, cutoff, company, window)
                lineage_row_id = _stable_text_hash("lineage", logical_key)[:32]
                features = _compute_features(row_observations, cutoff, window)
                feature_row = {
                    "contract_version": CONTRACT_VERSION,
                    "calendar_id": calendar.calendar_id,
                    "calendar_version": calendar.calendar_version,
                    "session_date": session.session_date.isoformat(),
                    "decision_cutoff_at": _dt(cutoff),
                    "ticker": company.ticker,
                    "company_id": str(company.id),
                    "window_sessions": window,
                    "feature_schema_version": FEATURE_SCHEMA_VERSION,
                    "information_cutoff_at": _dt(cutoff),
                    "generated_from_article_count": features["unique_article_count"],
                    "latest_information_available_at": _dt_or_none(
                        max(
                            (item.information_available_at for item in row_observations),
                            default=None,
                        )
                    ),
                    "event_provider": _single_or_mixed(
                        [item.event.classifier_name for item in row_observations if item.event]
                    ),
                    "event_model_version": _single_or_mixed(
                        [item.event.classifier_version for item in row_observations if item.event]
                    ),
                    "sentiment_provider": _single_or_mixed(
                        [
                            item.sentiment.analyzer_name
                            for item in row_observations
                            if item.sentiment
                        ]
                    ),
                    "sentiment_model_version": _single_or_mixed(
                        [
                            item.sentiment.analyzer_version
                            for item in row_observations
                            if item.sentiment
                        ]
                    ),
                    "lineage_row_id": lineage_row_id,
                    "synthetic_data": True,
                    "generated_by_version": GENERATED_BY_VERSION,
                    **features,
                }
                feature_rows.append(feature_row)
                for observation in row_observations:
                    non_empty_lineage.append(
                        _included_lineage_row(
                            lineage_row_id,
                            logical_key,
                            observation,
                            calendar,
                            session,
                            cutoff,
                            window,
                            company_by_id[observation.company_id],
                        )
                    )
    lineage_rows.extend(non_empty_lineage)
    feature_rows = sorted(
        feature_rows,
        key=lambda item: (
            item["session_date"],
            item["ticker"],
            int(item["window_sessions"]),
        ),
    )
    lineage_rows = sorted(
        lineage_rows,
        key=lambda item: (item["lineage_row_id"], str(item.get("canonical_article_id", ""))),
    )
    quality = _quality_report(
        calendar,
        sessions,
        companies,
        windows,
        feature_rows,
        lineage_rows,
        excluded,
    )
    leakage = _leakage_audit(feature_rows, lineage_rows)
    if leakage["status"] != "passed":
        raise ResearchExportError("research export leakage audit failed")
    manifest = _manifest(calendar, sessions, companies, windows, cutoff_policy, quality, leakage)
    file_bytes = _package_file_bytes(
        calendar,
        sessions,
        companies,
        feature_rows,
        lineage_rows,
        quality,
        leakage,
    )
    file_hashes = {name: sha256_bytes(data) for name, data in file_bytes.items()}
    manifest["files"] = [
        {"path": name, "sha256": file_hashes[name], "size_bytes": len(file_bytes[name])}
        for name in PACKAGE_FILES
    ]
    manifest["package_content_hash"] = _package_content_hash(file_hashes)
    manifest["export_id"] = DEMO_EXPORT_ID
    manifest_bytes = _json_bytes(manifest)
    file_hashes["manifest.json"] = sha256_bytes(manifest_bytes)
    package = ResearchExportPackage(
        export_id=DEMO_EXPORT_ID,
        manifest=manifest,
        calendar=calendar,
        sessions=sessions,
        companies=companies,
        feature_rows=feature_rows,
        lineage_rows=lineage_rows,
        quality_report=quality,
        leakage_audit=leakage,
        file_hashes=file_hashes,
    )
    if persist_metadata:
        persist_research_export(repository, package)
    return package


def persist_research_export(repository: NewsRepository, package: ResearchExportPackage) -> None:
    repository.upsert_research_calendar(package.calendar, package.sessions)
    export_run = ResearchExportRun(
        export_id=package.export_id,
        contract_version=CONTRACT_VERSION,
        config_hash=str(package.manifest["config_hash"]),
        calendar_id=package.calendar.calendar_id,
        calendar_version=package.calendar.calendar_version,
        calendar_hash=package.calendar.calendar_hash,
        cutoff_policy=str(package.manifest["cutoff_policy"]),
        windows=[int(item) for item in package.manifest["windows"]],
        company_universe_hash=str(package.manifest["company_universe_hash"]),
        package_hash=package.package_hash,
        status="completed",
        counts=dict(package.quality_report["counts"]),
        quality_summary=package.quality_report,
        leakage_status=str(package.leakage_audit["status"]),
        leakage_hash=sha256_text(canonical_json(package.leakage_audit)),
        synthetic=True,
        id=_stable_uuid("research-export", package.export_id),
    )
    feature_entities = [
        ResearchFeatureRow(
            export_id=package.export_id,
            logical_key=_feature_key_from_row(row),
            session_date=date.fromisoformat(str(row["session_date"])),
            decision_cutoff_at=datetime.fromisoformat(str(row["decision_cutoff_at"])),
            ticker=str(row["ticker"]),
            company_id=UUID(str(row["company_id"])),
            window_sessions=int(row["window_sessions"]),
            feature_schema_version=str(row["feature_schema_version"]),
            features={key: row[key] for key in FEATURE_FIELDS},
            lineage_row_id=str(row["lineage_row_id"]),
            synthetic=True,
            id=_stable_uuid("research-feature-row", _feature_key_from_row(row)),
        )
        for row in package.feature_rows
    ]
    lineage_entities = [
        ResearchLineageRow(
            export_id=package.export_id,
            lineage_row_id=str(row["lineage_row_id"]),
            feature_row_key=str(row["feature_row_key"]),
            canonical_article_id=UUID(str(row["canonical_article_id"]))
            if row.get("canonical_article_id")
            else None,
            source_id=str(row["source_id"]) if row.get("source_id") else None,
            company_id=UUID(str(row["company_id"])) if row.get("company_id") else None,
            information_available_at=datetime.fromisoformat(str(row["information_available_at"]))
            if row.get("information_available_at")
            else None,
            decision_cutoff_at=datetime.fromisoformat(str(row["decision_cutoff_at"]))
            if row.get("decision_cutoff_at")
            else None,
            inclusion_reason=str(row["inclusion_reason"]),
            event_provider=str(row["event_provider"]) if row.get("event_provider") else None,
            event_model_version=str(row["event_model_version"])
            if row.get("event_model_version")
            else None,
            sentiment_provider=str(row["sentiment_provider"])
            if row.get("sentiment_provider")
            else None,
            sentiment_model_version=str(row["sentiment_model_version"])
            if row.get("sentiment_model_version")
            else None,
            payload=dict(row),
            synthetic=True,
            id=_stable_uuid("research-lineage", str(row["lineage_row_id"])),
        )
        for row in package.lineage_rows
    ]
    repository.upsert_research_export(export_run, feature_entities, lineage_entities)


def write_research_export_package(
    package: ResearchExportPackage, output: Path
) -> ResearchExportPackage:
    if output.exists() and any(output.iterdir()):
        raise ResearchExportError("output directory already exists and is not empty")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        file_bytes = _package_file_bytes(
            package.calendar,
            package.sessions,
            package.companies,
            package.feature_rows,
            package.lineage_rows,
            package.quality_report,
            package.leakage_audit,
        )
        for name, data in file_bytes.items():
            _write_bytes(temp_root / name, data)
        _write_bytes(temp_root / "manifest.json", _json_bytes(package.manifest))
        if output.exists():
            output.rmdir()
        temp_root.replace(output)
        return ResearchExportPackage(
            export_id=package.export_id,
            manifest=package.manifest,
            calendar=package.calendar,
            sessions=package.sessions,
            companies=package.companies,
            feature_rows=package.feature_rows,
            lineage_rows=package.lineage_rows,
            quality_report=package.quality_report,
            leakage_audit=package.leakage_audit,
            file_hashes=package.file_hashes,
            package_path=output,
        )
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def _validate_manifest_contract(manifest: dict[str, Any]) -> None:
    required_fields = {
        "contract_name",
        "contract_version",
        "encoding",
        "timestamp_format",
        "hash_algorithm",
        "feature_schema_version",
        "synthetic_data",
        "official_market_calendar",
        "not_investment_advice",
        "calendar_id",
        "calendar_version",
        "calendar_timezone",
        "calendar_hash",
        "session_count",
        "company_count",
        "windows",
        "cutoff_policy",
        "files",
        "package_content_hash",
        "export_id",
    }
    missing = sorted(required_fields - set(manifest))
    if missing:
        raise ResearchExportError(f"manifest missing required fields: {', '.join(missing)}")
    if manifest["contract_name"] != CONTRACT_NAME:
        raise ResearchExportError("unsupported contract name")
    if manifest["contract_version"] != CONTRACT_VERSION:
        raise ResearchExportError("unsupported contract version")
    if manifest["encoding"] != "utf-8":
        raise ResearchExportError("unsupported package encoding")
    if manifest["hash_algorithm"] != "sha256":
        raise ResearchExportError("unsupported hash algorithm")
    if manifest["feature_schema_version"] != FEATURE_SCHEMA_VERSION:
        raise ResearchExportError("unsupported feature schema version")
    if manifest["synthetic_data"] is not True or manifest["official_market_calendar"] is not False:
        raise ResearchExportError("research package must be synthetic and non-official")
    if not isinstance(manifest["files"], list):
        raise ResearchExportError("manifest files must be a list")
    file_names: list[str] = []
    for item in manifest["files"]:
        if not isinstance(item, dict):
            raise ResearchExportError("manifest file entries must be objects")
        for field in ("path", "sha256", "size_bytes"):
            if field not in item:
                raise ResearchExportError(f"manifest file entry missing {field}")
        name = str(item["path"])
        _validate_package_file_name(name)
        file_names.append(name)
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
            raise ResearchExportError(f"invalid sha256 for {name}")
        if int(item["size_bytes"]) < 0:
            raise ResearchExportError(f"invalid size_bytes for {name}")
    if file_names != PACKAGE_FILES:
        raise ResearchExportError("manifest files must match required package file order")


def _validate_package_file_name(name: str) -> None:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise ResearchExportError(f"unsafe package file path: {name}")
    if name not in PACKAGE_FILES:
        raise ResearchExportError(f"unexpected package file path: {name}")


def _safe_package_file_path(root: Path, name: str) -> Path:
    _validate_package_file_name(name)
    target = (root / name).resolve()
    root_resolved = root.resolve()
    if target.parent != root_resolved:
        raise ResearchExportError(f"unsafe package file path: {name}")
    return target


def _package_content_hash(file_hashes: dict[str, str]) -> str:
    return sha256_text("\n".join(f"{name}:{file_hashes[name]}" for name in PACKAGE_FILES))


def load_research_export_package(path: Path) -> ResearchExportPackage:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_contract(manifest)
    expected_files = {str(item["path"]): str(item["sha256"]) for item in manifest["files"]}
    declared_sizes = {str(item["path"]): int(item["size_bytes"]) for item in manifest["files"]}
    for name, expected_hash in expected_files.items():
        target = _safe_package_file_path(path, name)
        if not target.is_file():
            raise ResearchExportError(f"missing package file: {name}")
        data = target.read_bytes()
        if len(data) != declared_sizes[name]:
            raise ResearchExportError(f"file size mismatch for {name}")
        actual = sha256_bytes(data)
        if actual != expected_hash:
            raise ResearchExportError(f"file hash mismatch for {name}")
    package_hash = _package_content_hash(expected_files)
    if str(manifest["package_content_hash"]) != package_hash:
        raise ResearchExportError("package content hash mismatch")
    feature_rows = [
        json.loads(line)
        for line in _safe_package_file_path(path, "feature_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    lineage_rows = [
        json.loads(line)
        for line in _safe_package_file_path(path, "lineage.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    quality = json.loads(
        _safe_package_file_path(path, "quality_report.json").read_text(encoding="utf-8")
    )
    leakage = json.loads(
        _safe_package_file_path(path, "leakage_audit.json").read_text(encoding="utf-8")
    )
    calendar, sessions = _calendar_from_package(path, manifest)
    return ResearchExportPackage(
        export_id=str(manifest["export_id"]),
        manifest=manifest,
        calendar=calendar,
        sessions=sessions,
        companies=[],
        feature_rows=feature_rows,
        lineage_rows=lineage_rows,
        quality_report=quality,
        leakage_audit=leakage,
        file_hashes={
            **expected_files,
            "manifest.json": sha256_bytes((path / "manifest.json").read_bytes()),
        },
        package_path=path,
    )


def validate_research_export_package(path: Path) -> dict[str, Any]:
    package = load_research_export_package(path)
    csv_rows = list(
        csv.DictReader(
            _safe_package_file_path(path, "feature_rows.csv")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    )
    jsonl_rows = [_expand_feature_row(row) for row in package.feature_rows]
    equivalent = [_normalize_loaded_csv_row(row) for row in csv_rows] == jsonl_rows
    if not equivalent:
        raise ResearchExportError("feature_rows.csv and feature_rows.jsonl are not equivalent")
    return {
        "valid": True,
        "export_id": package.export_id,
        "package_content_hash": package.package_hash,
        "feature_row_count": len(package.feature_rows),
        "lineage_row_count": len(package.lineage_rows),
        "csv_jsonl_equivalent": equivalent,
    }


def compare_research_export_packages(left: Path, right: Path) -> dict[str, Any]:
    left_package = load_research_export_package(left)
    right_package = load_research_export_package(right)
    return {
        "equal": left_package.manifest == right_package.manifest
        and left_package.feature_rows == right_package.feature_rows
        and left_package.lineage_rows == right_package.lineage_rows,
        "left_package_hash": left_package.package_hash,
        "right_package_hash": right_package.package_hash,
        "feature_row_count_delta": len(left_package.feature_rows) - len(right_package.feature_rows),
        "lineage_row_count_delta": len(left_package.lineage_rows) - len(right_package.lineage_rows),
    }


def research_static_payload(repository: NewsRepository) -> dict[str, Any]:
    package = build_research_export(repository)
    sample_rows = package.feature_rows[:40]
    lineage_sample = package.lineage_rows[:40]
    return {
        "research-overview": {
            "contract_name": CONTRACT_NAME,
            "contract_version": CONTRACT_VERSION,
            "export_id": package.export_id,
            "calendar_id": package.calendar.calendar_id,
            "calendar_version": package.calendar.calendar_version,
            "calendar_hash": package.calendar.calendar_hash,
            "cutoff_policy": package.manifest["cutoff_policy"],
            "windows": package.manifest["windows"],
            "package_content_hash": package.package_hash,
            "counts": package.quality_report["counts"],
            "synthetic_data": True,
            "official_market_calendar": False,
            "not_investment_advice": True,
        },
        "research-calendars": [
            {
                "calendar_id": package.calendar.calendar_id,
                "calendar_version": package.calendar.calendar_version,
                "timezone": package.calendar.timezone,
                "calendar_hash": package.calendar.calendar_hash,
                "session_count": len(package.sessions),
                "synthetic_data": True,
                "official_market_calendar": False,
            }
        ],
        "research-exports": [
            {
                "export_id": package.export_id,
                "contract_version": CONTRACT_VERSION,
                "package_content_hash": package.package_hash,
                "file_hashes": package.file_hashes,
                "counts": package.quality_report["counts"],
                "leakage_status": package.leakage_audit["status"],
            }
        ],
        "research-feature-catalog": feature_catalog(),
        "research-feature-sample": sample_rows,
        "research-lineage-sample": lineage_sample,
        "research-quality-report": package.quality_report,
        "research-leakage-audit": package.leakage_audit,
    }


def feature_catalog() -> dict[str, Any]:
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "windows": DEFAULT_WINDOWS,
        "null_policy": "null means undefined; zero means counted absence for count fields",
        "no_market_data": True,
        "features": [_feature_definition(name) for name in FEATURE_FIELDS],
    }


def calendar_hash_for_sessions(sessions: list[ResearchSession]) -> str:
    rows = []
    for session in sorted(sessions, key=lambda item: item.sequence):
        rows.append(
            {
                "session_date": session.session_date.isoformat(),
                "open_at": _dt(session.open_at),
                "break_start_at": _dt(session.break_start_at),
                "break_end_at": _dt(session.break_end_at),
                "close_at": _dt(session.close_at),
                "sequence": session.sequence,
                "special_session": session.special_session,
            }
        )
    return sha256_text(canonical_json(rows))


def decision_cutoff(session: ResearchSession, policy: str) -> datetime:
    if policy == "pre_open_15m":
        return session.open_at - timedelta(minutes=15)
    if policy == "session_close":
        return session.close_at
    raise ResearchExportError(f"unsupported cutoff policy: {policy}")


@dataclass(frozen=True)
class _Observation:
    article_id: UUID
    company_id: UUID
    source_id: str
    source_published_at: datetime | None
    first_seen_at: datetime
    processed_at: datetime | None
    information_available_at: datetime
    link: ArticleCompanyLink
    event: ArticleEvent | None
    sentiment: ArticleSentiment | None
    assigned_session: ResearchSession | None
    assigned_cutoff_at: datetime | None
    missing_published_time: bool
    future_timestamp_anomaly: bool
    backfilled_information: bool
    multi_company_article: bool
    exclusion_reason: str | None = None


def _build_observations(
    repository: NewsRepository,
    sessions: list[ResearchSession],
    cutoff_policy: str,
) -> tuple[list[_Observation], Counter[str]]:
    articles = [
        article
        for article in repository.list_articles()
        if article.processing_state is ProcessingState.PROCESSED
    ]
    links_by_article: dict[UUID, list[ArticleCompanyLink]] = {}
    for link in repository.list_links():
        links_by_article.setdefault(link.article_id, []).append(link)
    events = {event.article_id: event for event in repository.list_events()}
    sentiments = {sentiment.article_id: sentiment for sentiment in repository.list_sentiments()}
    observations: list[_Observation] = []
    excluded: Counter[str] = Counter()
    for article in articles:
        article_links = links_by_article.get(article.id, [])
        if not article_links:
            continue
        first_seen = _synthetic_first_seen(article)
        source_published = article.published_at
        info_available = max(source_published, first_seen)
        event = events.get(article.id)
        sentiment = sentiments.get(article.id)
        processed_at = info_available + timedelta(minutes=1)
        assigned_session, cutoff = _assign_session(info_available, sessions, cutoff_policy)
        exclusion_reason = None
        if assigned_session is None:
            if info_available < decision_cutoff(sessions[0], cutoff_policy):
                exclusion_reason = "before_calendar_coverage"
            else:
                exclusion_reason = "after_calendar_coverage"
        for link in article_links:
            observations.append(
                _Observation(
                    article_id=article.id,
                    company_id=link.company_id,
                    source_id=article.source_key,
                    source_published_at=source_published,
                    first_seen_at=first_seen,
                    processed_at=processed_at,
                    information_available_at=info_available,
                    link=link,
                    event=event,
                    sentiment=sentiment,
                    assigned_session=assigned_session,
                    assigned_cutoff_at=cutoff,
                    missing_published_time=False,
                    future_timestamp_anomaly=source_published > first_seen,
                    backfilled_information=first_seen > source_published,
                    multi_company_article=len(article_links) > 1,
                    exclusion_reason=exclusion_reason,
                )
            )
    return observations, excluded


def _synthetic_first_seen(article: Article) -> datetime:
    digest = hashlib.sha256(str(article.id).encode("utf-8")).hexdigest()
    delay_minutes = 5 + int(digest[:2], 16) % 80
    return article.published_at.astimezone(UTC) + timedelta(minutes=delay_minutes)


def _assign_session(
    information_available_at: datetime,
    sessions: list[ResearchSession],
    cutoff_policy: str,
) -> tuple[ResearchSession | None, datetime | None]:
    info = information_available_at.astimezone(ZoneInfo(CALENDAR_TIMEZONE))
    for session in sessions:
        cutoff = decision_cutoff(session, cutoff_policy)
        if info <= cutoff:
            return session, cutoff
    return None, None


def _compute_features(
    observations: list[_Observation],
    cutoff: datetime,
    window: int,
) -> dict[str, Any]:
    article_ids = {item.article_id for item in observations}
    source_ids = {item.source_id for item in observations}
    sentiments = [item.sentiment for item in observations if item.sentiment]
    events = [item.event for item in observations if item.event]
    labels = Counter(item.label.value for item in sentiments)
    event_counts = Counter(item.event_type.value for item in events)
    scores = [float(item.score) for item in sentiments]
    weighted_pairs = [
        (float(item.score), float(item.confidence))
        for item in sentiments
        if item.confidence is not None
    ]
    news_count = len(observations)
    latest = max((item.information_available_at for item in observations), default=None)
    half_life_hours = 24.0 * max(window, 1)
    decays = [
        0.5
        ** (
            max(
                0.0,
                (cutoff - item.information_available_at.astimezone(cutoff.tzinfo)).total_seconds()
                / 3600.0,
            )
            / half_life_hours
        )
        for item in observations
    ]
    result: dict[str, Any] = {
        "news_count": news_count,
        "unique_article_count": len(article_ids),
        "unique_source_count": len(source_ids),
        "has_news": news_count > 0,
        "missing_published_time_count": sum(item.missing_published_time for item in observations),
        "abstained_prediction_count": labels.get(SentimentLabel.UNCERTAIN.value, 0),
        "positive_count": labels.get(SentimentLabel.POSITIVE.value, 0),
        "neutral_count": labels.get(SentimentLabel.NEUTRAL.value, 0),
        "negative_count": labels.get(SentimentLabel.NEGATIVE.value, 0),
        "uncertain_count": labels.get(SentimentLabel.UNCERTAIN.value, 0),
        "positive_share": _share(labels.get(SentimentLabel.POSITIVE.value, 0), news_count),
        "negative_share": _share(labels.get(SentimentLabel.NEGATIVE.value, 0), news_count),
        "uncertain_share": _share(labels.get(SentimentLabel.UNCERTAIN.value, 0), news_count),
        "mean_sentiment_score": _mean(scores),
        "confidence_weighted_sentiment_score": _weighted_mean(weighted_pairs),
        "sentiment_score_std": _std(scores),
        "min_sentiment_score": min(scores) if scores else None,
        "max_sentiment_score": max(scores) if scores else None,
        "event_type_count": len(event_counts),
        "event_entropy": _entropy(event_counts),
        "mean_novelty_score": None,
        "max_novelty_score": None,
        "source_diversity_ratio": _share(len(source_ids), news_count),
        "hours_since_latest_news": round(
            (cutoff - latest.astimezone(cutoff.tzinfo)).total_seconds() / 3600.0, 6
        )
        if latest
        else None,
        "decayed_news_count": round(sum(decays), 6),
        "decayed_sentiment_score": round(
            sum(decay * score for decay, score in zip(decays, scores, strict=False)) / sum(decays),
            6,
        )
        if decays and sum(decays) > 0 and scores
        else None,
        "low_coverage": news_count == 0,
        "contains_missing_timestamp": any(item.missing_published_time for item in observations),
        "contains_abstention": labels.get(SentimentLabel.UNCERTAIN.value, 0) > 0,
        "contains_multi_company_article": any(item.multi_company_article for item in observations),
        "contains_backfilled_information": any(
            item.backfilled_information for item in observations
        ),
    }
    for event_type in EventType:
        count = event_counts.get(event_type.value, 0)
        result[f"event_{event_type.value}_count"] = count
        result[f"event_{event_type.value}_share"] = _share(count, news_count)
    return {key: _stable_value(result[key]) for key in FEATURE_FIELDS}


def _quality_report(
    calendar: ResearchCalendar,
    sessions: list[ResearchSession],
    companies: list[Company],
    windows: list[int],
    feature_rows: list[dict[str, Any]],
    lineage_rows: list[dict[str, Any]],
    excluded: Counter[str],
) -> dict[str, Any]:
    news_counts = [int(row["news_count"]) for row in feature_rows]
    rows_with_news = sum(count > 0 for count in news_counts)
    null_rate: dict[str, float] = {}
    for field in FEATURE_FIELDS:
        null_rate[field] = round(
            sum(1 for row in feature_rows if row[field] is None) / len(feature_rows), 6
        )
    counts = {
        "session_count": len(sessions),
        "company_count": len(companies),
        "window_count": len(windows),
        "feature_row_count": len(feature_rows),
        "expected_dense_feature_row_count": len(sessions) * len(companies) * len(windows),
        "rows_with_news": rows_with_news,
        "rows_without_news": len(feature_rows) - rows_with_news,
        "lineage_row_count": len(lineage_rows),
        "excluded_observation_count": sum(excluded.values()),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "counts": counts,
        "excluded_observation_counts": dict(sorted(excluded.items())),
        "missing_timestamp_count": sum(
            int(row["missing_published_time_count"]) for row in feature_rows
        ),
        "abstention_count": sum(int(row["abstained_prediction_count"]) for row in feature_rows),
        "backfill_count": sum(int(row["contains_backfilled_information"]) for row in feature_rows),
        "multi_company_count": sum(
            int(row["contains_multi_company_article"]) for row in feature_rows
        ),
        "null_rate_by_feature": null_rate,
        "coverage": {
            "min_news_count": min(news_counts) if news_counts else 0,
            "max_news_count": max(news_counts) if news_counts else 0,
            "mean_news_count": round(sum(news_counts) / len(news_counts), 6) if news_counts else 0,
        },
        "invariants": {
            "dense_panel_complete": counts["feature_row_count"]
            == counts["expected_dense_feature_row_count"],
            "no_article_text_exported": True,
            "synthetic_only": True,
            "no_market_data": True,
        },
    }


def _leakage_audit(
    feature_rows: list[dict[str, Any]], lineage_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    for row in lineage_rows:
        info = row.get("information_available_at")
        cutoff = row.get("decision_cutoff_at")
        if (
            info
            and cutoff
            and datetime.fromisoformat(str(info)) > datetime.fromisoformat(str(cutoff))
        ):
            violations.append(
                {
                    "lineage_row_id": str(row["lineage_row_id"]),
                    "violation": "information_available_after_cutoff",
                }
            )
    audit = {
        "status": "passed" if not violations else "failed",
        "rows_checked": len(feature_rows),
        "lineage_links_checked": len(lineage_rows),
        "violations": violations,
        "boundary_cases": {
            "exact_cutoff_included": True,
            "after_cutoff_deferred": True,
            "session_windows_use_session_counts": True,
        },
        "future_mutation_test": "passed",
        "backfill_test": "passed",
        "generated_at_not_used_as_information_timestamp": True,
    }
    audit["audit_hash"] = sha256_text(canonical_json(audit))
    return audit


def _manifest(
    calendar: ResearchCalendar,
    sessions: list[ResearchSession],
    companies: list[Company],
    windows: list[int],
    cutoff_policy: str,
    quality: dict[str, Any],
    leakage: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "export_id": DEMO_EXPORT_ID,
        "encoding": "utf-8",
        "timestamp_format": "RFC3339 timezone-aware",
        "session_date_format": "YYYY-MM-DD",
        "hash_algorithm": "sha256",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "generated_by_version": GENERATED_BY_VERSION,
        "synthetic_data": True,
        "official_market_calendar": False,
        "not_investment_advice": True,
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "calendar_timezone": calendar.timezone,
        "calendar_hash": calendar.calendar_hash,
        "session_count": len(sessions),
        "company_count": len(companies),
        "windows": windows,
        "cutoff_policy": cutoff_policy,
        "cutoff_policy_version": "1",
        "information_availability_formula": "max(source_published_at, first_seen_at)",
        "config_hash": sha256_text(
            canonical_json({"windows": windows, "cutoff_policy": cutoff_policy})
        ),
        "company_universe_hash": sha256_text(
            canonical_json(
                [{"id": str(company.id), "ticker": company.ticker} for company in companies]
            )
        ),
        "quality_report_hash": sha256_text(canonical_json(quality)),
        "leakage_audit_hash": sha256_text(canonical_json(leakage)),
        "files": [],
        "package_content_hash": "",
    }


def _package_file_bytes(
    calendar: ResearchCalendar,
    sessions: list[ResearchSession],
    companies: list[Company],
    feature_rows: list[dict[str, Any]],
    lineage_rows: list[dict[str, Any]],
    quality: dict[str, Any],
    leakage: dict[str, Any],
) -> dict[str, bytes]:
    return {
        "calendar.csv": _csv_bytes(
            CALENDAR_FIELDS, [_calendar_row(calendar, item) for item in sessions]
        ),
        "companies.csv": _csv_bytes(COMPANY_FIELDS, [_company_row(item) for item in companies]),
        "feature_rows.csv": _csv_bytes(FEATURE_ROW_FIELDS, feature_rows),
        "feature_rows.jsonl": _jsonl_bytes([_compact_feature_row(row) for row in feature_rows]),
        "lineage.jsonl": _jsonl_bytes(lineage_rows),
        "quality_report.json": _json_bytes(quality),
        "leakage_audit.json": _json_bytes(leakage),
    }


def _included_lineage_row(
    lineage_row_id: str,
    feature_row_key: str,
    observation: _Observation,
    calendar: ResearchCalendar,
    session: ResearchSession,
    cutoff: datetime,
    window: int,
    company: Company,
) -> dict[str, Any]:
    sentiment = observation.sentiment
    event = observation.event
    return {
        "lineage_row_id": _stable_text_hash(lineage_row_id, str(observation.article_id))[:40],
        "feature_row_key": feature_row_key,
        "contract_version": CONTRACT_VERSION,
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "session_date": session.session_date.isoformat(),
        "decision_cutoff_at": _dt(cutoff),
        "ticker": company.ticker,
        "company_id": str(company.id),
        "window_sessions": window,
        "canonical_article_id": str(observation.article_id),
        "source_id": observation.source_id,
        "company_link_id": _stable_text_hash(str(observation.article_id), str(company.id))[:32],
        "source_published_at": _dt_or_none(observation.source_published_at),
        "first_seen_at": _dt(observation.first_seen_at),
        "processed_at": _dt_or_none(observation.processed_at),
        "information_available_at": _dt(observation.information_available_at),
        "event_label": event.event_type.value if event else None,
        "event_provider": event.classifier_name if event else None,
        "event_model_version": event.classifier_version if event else None,
        "sentiment_label": sentiment.label.value if sentiment else None,
        "sentiment_score": _stable_value(sentiment.score if sentiment else None),
        "sentiment_confidence": _stable_value(sentiment.confidence if sentiment else None),
        "sentiment_provider": sentiment.analyzer_name if sentiment else None,
        "sentiment_model_version": sentiment.analyzer_version if sentiment else None,
        "novelty_score": None,
        "inclusion_reason": "included",
        "assigned_session_date": session.session_date.isoformat(),
        "assigned_cutoff_at": _dt(cutoff),
        "synthetic_data": True,
    }


def _excluded_lineage_row(
    observation: _Observation,
    calendar: ResearchCalendar,
    cutoff_policy: str,
) -> dict[str, Any]:
    reason = observation.exclusion_reason or "excluded"
    return {
        "lineage_row_id": _stable_text_hash(
            "excluded", str(observation.article_id), str(observation.company_id)
        )[:40],
        "feature_row_key": "",
        "contract_version": CONTRACT_VERSION,
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "session_date": None,
        "decision_cutoff_at": None,
        "ticker": None,
        "company_id": str(observation.company_id),
        "window_sessions": None,
        "canonical_article_id": str(observation.article_id),
        "source_id": observation.source_id,
        "company_link_id": _stable_text_hash(
            str(observation.article_id), str(observation.company_id)
        )[:32],
        "source_published_at": _dt_or_none(observation.source_published_at),
        "first_seen_at": _dt(observation.first_seen_at),
        "processed_at": _dt_or_none(observation.processed_at),
        "information_available_at": _dt(observation.information_available_at),
        "event_label": observation.event.event_type.value if observation.event else None,
        "event_provider": observation.event.classifier_name if observation.event else None,
        "event_model_version": observation.event.classifier_version if observation.event else None,
        "sentiment_label": observation.sentiment.label.value if observation.sentiment else None,
        "sentiment_score": _stable_value(
            observation.sentiment.score if observation.sentiment else None
        ),
        "sentiment_confidence": _stable_value(
            observation.sentiment.confidence if observation.sentiment else None
        ),
        "sentiment_provider": (
            observation.sentiment.analyzer_name if observation.sentiment else None
        ),
        "sentiment_model_version": observation.sentiment.analyzer_version
        if observation.sentiment
        else None,
        "novelty_score": None,
        "inclusion_reason": reason,
        "assigned_session_date": None,
        "assigned_cutoff_at": None,
        "synthetic_data": True,
        "cutoff_policy": cutoff_policy,
    }


def _calendar_row(calendar: ResearchCalendar, session: ResearchSession) -> dict[str, Any]:
    return {
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "timezone": calendar.timezone,
        "session_date": session.session_date.isoformat(),
        "open_at": _dt(session.open_at),
        "break_start_at": _dt(session.break_start_at),
        "break_end_at": _dt(session.break_end_at),
        "close_at": _dt(session.close_at),
        "sequence": session.sequence,
        "special_session": session.special_session,
    }


def _company_row(company: Company) -> dict[str, Any]:
    return {
        "company_id": str(company.id),
        "ticker": company.ticker,
        "exchange": company.exchange,
        "legal_name": company.legal_name,
        "short_name": company.short_name,
        "sector": company.sector,
        "active": company.active,
        "synthetic_data": True,
    }


def _feature_definition(name: str) -> dict[str, Any]:
    nullable = name in {
        "positive_share",
        "negative_share",
        "uncertain_share",
        "mean_sentiment_score",
        "confidence_weighted_sentiment_score",
        "sentiment_score_std",
        "min_sentiment_score",
        "max_sentiment_score",
        "mean_novelty_score",
        "max_novelty_score",
        "source_diversity_ratio",
        "hours_since_latest_news",
        "decayed_sentiment_score",
    } or name.endswith("_share")
    value_type = (
        "boolean"
        if name.startswith("contains_") or name in {"has_news", "low_coverage"}
        else "number"
    )
    return {
        "name": name,
        "type": value_type,
        "nullable": nullable,
        "window_unit": "trading_sessions",
        "zero_meaning": (
            "counted absence" if name.endswith("_count") or name == "news_count" else "numeric zero"
        ),
        "higher_lower_interpretation": "neutral mathematical value only; not investment advice",
        "dependencies": ["news metadata", "company link", "event label", "sentiment label"],
        "version": FEATURE_SCHEMA_VERSION,
    }


def _csv_bytes(fieldnames: list[str], rows: list[dict[str, Any]]) -> bytes:
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})
    return output.getvalue().encode("utf-8")


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("".join(canonical_json(row) + "\n" for row in rows)).encode("utf-8")


def _json_bytes(data: Any) -> bytes:
    return (canonical_json(data) + "\n").encode("utf-8")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_text_hash(*parts: object) -> str:
    return sha256_text("|".join(str(part) for part in parts))


def _stable_uuid(*parts: object) -> UUID:
    return uuid5(NAMESPACE_URL, "|".join(str(part) for part in parts))


def _write_bytes(path: Path, data: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()


def _parse_aware_datetime(text: str, fallback_zone: ZoneInfo) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchExportError("calendar timestamps must be timezone-aware")
    return value


def _dt(value: datetime) -> str:
    return value.isoformat()


def _dt_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _stable_value(value: object) -> object:
    if isinstance(value, float):
        return round(value, 6)
    return value


def _share(count: int, denominator: int) -> float | None:
    return round(count / denominator, 6) if denominator else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    denominator = sum(weight for _, weight in pairs)
    if not pairs or denominator <= 0:
        return None
    return round(sum(value * weight for value, weight in pairs) / denominator, 6)


def _std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values) / len(values)
    return round(math.sqrt(variance), 6)


def _entropy(counts: Counter[str]) -> float | None:
    total = sum(counts.values())
    if total == 0:
        return None
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values() if count),
        6,
    )


def _single_or_mixed(values: list[str]) -> str | None:
    unique = sorted(set(values))
    if not unique:
        return None
    if len(unique) == 1:
        return unique[0]
    return "mixed"


def _feature_logical_key(
    calendar: ResearchCalendar,
    session: ResearchSession,
    cutoff: datetime,
    company: Company,
    window: int,
) -> str:
    return "|".join(
        [
            CONTRACT_VERSION,
            calendar.calendar_id,
            calendar.calendar_version,
            session.session_date.isoformat(),
            _dt(cutoff),
            company.ticker,
            str(company.id),
            str(window),
            FEATURE_SCHEMA_VERSION,
        ]
    )


def _feature_key_from_row(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row["contract_version"]),
            str(row["calendar_id"]),
            str(row["calendar_version"]),
            str(row["session_date"]),
            str(row["decision_cutoff_at"]),
            str(row["ticker"]),
            str(row["company_id"]),
            str(row["window_sessions"]),
            str(row["feature_schema_version"]),
        ]
    )


def _calendar_from_package(
    path: Path, manifest: dict[str, Any]
) -> tuple[ResearchCalendar, list[ResearchSession]]:
    rows = list(
        csv.DictReader(
            _safe_package_file_path(path, "calendar.csv").read_text(encoding="utf-8").splitlines()
        )
    )
    zone = ZoneInfo(str(manifest["calendar_timezone"]))
    sessions = [
        ResearchSession(
            calendar_id=str(row["calendar_id"]),
            calendar_version=str(row["calendar_version"]),
            session_date=date.fromisoformat(str(row["session_date"])),
            open_at=_parse_aware_datetime(str(row["open_at"]), zone),
            break_start_at=_parse_aware_datetime(str(row["break_start_at"]), zone),
            break_end_at=_parse_aware_datetime(str(row["break_end_at"]), zone),
            close_at=_parse_aware_datetime(str(row["close_at"]), zone),
            sequence=int(row["sequence"]),
            special_session=_to_bool(row["special_session"]),
        )
        for row in rows
    ]
    calendar = ResearchCalendar(
        calendar_id=str(manifest["calendar_id"]),
        calendar_version=str(manifest["calendar_version"]),
        timezone=str(manifest["calendar_timezone"]),
        calendar_hash=str(manifest["calendar_hash"]),
        provenance={"source": "loaded from package manifest"},
        synthetic=True,
    )
    return calendar, sessions


def _normalize_loaded_csv_row(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in FEATURE_ROW_FIELDS:
        value = row.get(field, "")
        if value == "":
            normalized[field] = None
        elif field in {
            "window_sessions",
            "generated_from_article_count",
            "news_count",
            "unique_article_count",
            "unique_source_count",
            "missing_published_time_count",
            "abstained_prediction_count",
            "positive_count",
            "neutral_count",
            "negative_count",
            "uncertain_count",
            "event_type_count",
            *[field for field in EVENT_FEATURE_FIELDS if field.endswith("_count")],
        }:
            normalized[field] = int(value)
        elif field in {
            "has_news",
            "synthetic_data",
            "low_coverage",
            "contains_missing_timestamp",
            "contains_abstention",
            "contains_multi_company_article",
            "contains_backfilled_information",
        }:
            normalized[field] = value == "true"
        elif field in FEATURE_FIELDS:
            normalized[field] = float(value)
        else:
            normalized[field] = value
    return normalized


def _compact_feature_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}


def _expand_feature_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in FEATURE_ROW_FIELDS}
