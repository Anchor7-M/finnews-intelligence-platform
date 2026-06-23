from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from finnews.application.services import research_export as research_module
from finnews.application.services.research_export import (
    DEFAULT_WINDOWS,
    DEMO_SYNTHETIC_HOLIDAYS,
    ResearchExportError,
    _assign_session,
    _compute_features,
    _Observation,
    build_demo_calendar,
    build_research_export,
    compare_research_export_packages,
    decision_cutoff,
    load_local_calendar,
    validate_research_export_package,
    write_research_export_package,
)
from finnews.bootstrap import build_memory_repository
from finnews.domain.entities import (
    ArticleCompanyLink,
    ArticleEvent,
    ArticleSentiment,
    ResearchSession,
)
from finnews.domain.enums import EventType, SentimentLabel


def test_demo_calendar_has_exact_synthetic_sessions() -> None:
    calendar, sessions = build_demo_calendar()

    assert calendar.calendar_id == "synthetic-ashare-demo-calendar"
    assert calendar.timezone == "Asia/Shanghai"
    assert calendar.provenance["holiday_dates"] == [
        item.isoformat() for item in DEMO_SYNTHETIC_HOLIDAYS
    ]
    assert len(sessions) == 60
    assert not ({session.session_date for session in sessions} & set(DEMO_SYNTHETIC_HOLIDAYS))
    assert {session.session_date.weekday() for session in sessions} <= {0, 1, 2, 3, 4}
    assert all(
        session.open_at < session.break_start_at < session.break_end_at < session.close_at
        for session in sessions
    )


def test_research_export_dense_panel_and_leakage() -> None:
    package = build_research_export(build_memory_repository())

    assert len(package.sessions) == 60
    assert len(package.companies) == 12
    assert package.manifest["windows"] == DEFAULT_WINDOWS
    assert len(package.feature_rows) == 2880
    assert package.quality_report["counts"]["expected_dense_feature_row_count"] == 2880
    assert package.leakage_audit["status"] == "passed"
    assert all(
        "title" not in row and "summary" not in row and "body" not in row
        for row in package.lineage_rows
    )


def test_package_writer_validation_and_csv_jsonl_equivalence(tmp_path: Path) -> None:
    package = build_research_export(build_memory_repository())
    output = tmp_path / "research-export"
    write_research_export_package(package, output)

    result = validate_research_export_package(output)

    assert result["valid"] is True
    assert result["csv_jsonl_equivalent"] is True
    assert result["feature_row_count"] == 2880
    with (output / "feature_rows.csv").open(encoding="utf-8", newline="") as handle:
        assert csv.DictReader(handle).fieldnames is not None


def test_two_clean_builds_are_byte_deterministic(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"

    write_research_export_package(build_research_export(build_memory_repository()), left)
    write_research_export_package(build_research_export(build_memory_repository()), right)

    result = compare_research_export_packages(left, right)
    assert result["equal"] is True


def test_local_calendar_import_csv(tmp_path: Path) -> None:
    calendar, sessions = build_demo_calendar()
    path = tmp_path / "calendar.csv"
    _write_calendar_csv(path, _calendar_rows(sessions[:3]))

    imported, imported_sessions = load_local_calendar(path)

    assert imported.calendar_id == "local-user-calendar"
    assert len(imported_sessions) == 3
    assert decision_cutoff(imported_sessions[0], "pre_open_15m") < imported_sessions[0].open_at
    assert imported.calendar_hash != calendar.calendar_hash


def test_local_calendar_import_json_with_metadata(tmp_path: Path) -> None:
    _, sessions = build_demo_calendar()
    path = tmp_path / "calendar.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "calendar_id": "local-json-calendar",
                    "calendar_version": "demo",
                    "timezone": "Asia/Shanghai",
                    "synthetic": True,
                    "official_calendar": False,
                },
                "sessions": _calendar_rows(sessions[:4]),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    imported, imported_sessions = load_local_calendar(path)

    assert imported.calendar_id == "local-json-calendar"
    assert imported.synthetic is True
    assert imported.provenance["official_calendar"] is False
    assert len(imported_sessions) == 4


def test_local_calendar_rejects_naive_timestamps(tmp_path: Path) -> None:
    _, sessions = build_demo_calendar()
    rows = _calendar_rows(sessions[:2])
    rows[0]["open_at"] = str(rows[0]["open_at"]).replace("+08:00", "")
    path = tmp_path / "calendar.csv"
    _write_calendar_csv(path, rows)

    with pytest.raises(ResearchExportError, match="timezone-aware"):
        load_local_calendar(path)


def test_local_calendar_rejects_duplicate_and_nonmonotonic_sessions(tmp_path: Path) -> None:
    _, sessions = build_demo_calendar()
    rows = _calendar_rows(sessions[:3])
    rows[1]["session_date"] = rows[0]["session_date"]
    rows[2]["sequence"] = "2"
    path = tmp_path / "calendar.csv"
    _write_calendar_csv(path, rows)

    with pytest.raises(ResearchExportError) as exc:
        load_local_calendar(path)

    assert "duplicate session_date" in str(exc.value)
    assert "session sequences must be strictly increasing" in str(exc.value)


def test_local_calendar_rejects_invalid_open_ordering_missing_fields_and_limits(
    tmp_path: Path,
) -> None:
    _, sessions = build_demo_calendar()
    rows = _calendar_rows(sessions[:2])
    rows[0]["break_start_at"] = rows[0]["open_at"]
    ordering_path = tmp_path / "ordering.csv"
    _write_calendar_csv(ordering_path, rows)
    with pytest.raises(ResearchExportError, match="invalid open/break/close ordering"):
        load_local_calendar(ordering_path)

    missing_path = tmp_path / "missing.csv"
    missing_rows = _calendar_rows(sessions[:1])
    missing_rows[0].pop("close_at")
    _write_calendar_csv(missing_path, missing_rows, include_all_fields=False)
    with pytest.raises(ResearchExportError, match="missing required field"):
        load_local_calendar(missing_path)

    invalid_utf8_path = tmp_path / "invalid.csv"
    invalid_utf8_path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ResearchExportError, match="UTF-8"):
        load_local_calendar(invalid_utf8_path)

    with pytest.raises(ResearchExportError, match="size limit"):
        load_local_calendar(ordering_path, max_bytes=1)

    invalid_timezone_path = tmp_path / "calendar.json"
    invalid_timezone_path.write_text(
        json.dumps(
            {
                "metadata": {"timezone": "Invalid/Zone"},
                "sessions": _calendar_rows(sessions[:1]),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ResearchExportError, match="invalid timezone"):
        load_local_calendar(invalid_timezone_path)


def test_cutoff_boundary_assigns_equal_to_current_and_after_to_next_session() -> None:
    _, sessions = build_demo_calendar()
    first_cutoff = decision_cutoff(sessions[0], "pre_open_15m")

    equal_session, equal_cutoff = _assign_session(first_cutoff, sessions, "pre_open_15m")
    after_session, after_cutoff = _assign_session(
        first_cutoff + timedelta(microseconds=1), sessions, "pre_open_15m"
    )

    assert equal_session == sessions[0]
    assert equal_cutoff == first_cutoff
    assert after_session == sessions[1]
    assert after_cutoff == decision_cutoff(sessions[1], "pre_open_15m")


def test_feature_formula_proof_for_counts_shares_entropy_and_decay() -> None:
    company_id = uuid4()
    first_article_id = uuid4()
    second_article_id = uuid4()
    _, sessions = build_demo_calendar()
    cutoff = decision_cutoff(sessions[3], "pre_open_15m")
    first_info = cutoff - timedelta(hours=2)
    second_info = cutoff - timedelta(hours=26)
    observations = [
        _observation(
            article_id=first_article_id,
            company_id=company_id,
            information_available_at=first_info,
            event_type=EventType.EARNINGS,
            sentiment_label=SentimentLabel.POSITIVE,
            sentiment_score=1.0,
            confidence=0.8,
        ),
        _observation(
            article_id=second_article_id,
            company_id=company_id,
            information_available_at=second_info,
            event_type=EventType.MACRO_MARKET,
            sentiment_label=SentimentLabel.NEGATIVE,
            sentiment_score=-1.0,
            confidence=0.2,
        ),
    ]

    result = _compute_features(observations, cutoff, window=1)
    decays = [0.5 ** (2 / 24), 0.5 ** (26 / 24)]
    expected_decay_sentiment = round((decays[0] - decays[1]) / sum(decays), 6)

    assert result["news_count"] == 2
    assert result["unique_article_count"] == 2
    assert result["unique_source_count"] == 1
    assert result["positive_share"] == 0.5
    assert result["negative_share"] == 0.5
    assert result["mean_sentiment_score"] == 0.0
    assert result["confidence_weighted_sentiment_score"] == 0.6
    assert result["sentiment_score_std"] == 1.0
    assert result["event_type_count"] == 2
    assert result["event_entropy"] == 1.0
    assert result["decayed_news_count"] == round(sum(decays), 6)
    assert math.isclose(result["decayed_sentiment_score"], expected_decay_sentiment)


def test_package_validator_rejects_contract_hash_path_and_missing_file(tmp_path: Path) -> None:
    output = tmp_path / "research-export"
    write_research_export_package(build_research_export(build_memory_repository()), output)

    manifest = _read_manifest(output)
    manifest["contract_version"] = "2.0.0"
    _write_manifest(output, manifest)
    with pytest.raises(ResearchExportError, match="unsupported contract version"):
        validate_research_export_package(output)

    hash_path = tmp_path / "hash"
    write_research_export_package(build_research_export(build_memory_repository()), hash_path)
    manifest = _read_manifest(hash_path)
    manifest["package_content_hash"] = "0" * 64
    _write_manifest(hash_path, manifest)
    with pytest.raises(ResearchExportError, match="package content hash mismatch"):
        validate_research_export_package(hash_path)

    traversal_path = tmp_path / "path"
    write_research_export_package(build_research_export(build_memory_repository()), traversal_path)
    manifest = _read_manifest(traversal_path)
    files = cast(list[dict[str, Any]], manifest["files"])
    files[0]["path"] = "../calendar.csv"
    _write_manifest(traversal_path, manifest)
    with pytest.raises(ResearchExportError, match="unsafe package file path"):
        validate_research_export_package(traversal_path)

    missing_path = tmp_path / "missing"
    write_research_export_package(build_research_export(build_memory_repository()), missing_path)
    (missing_path / "calendar.csv").unlink()
    with pytest.raises(ResearchExportError, match="missing package file"):
        validate_research_export_package(missing_path)


def test_contract_schemas_cover_required_example_fields() -> None:
    root = Path(__file__).resolve().parents[3]
    contract_dir = root / "contracts" / "finnews-research-export" / "v1"
    example_dir = contract_dir / "examples" / "synthetic-demo"
    cases = [
        ("manifest.schema.json", json.loads((example_dir / "manifest.json").read_text())),
        ("calendar-row.schema.json", _first_csv_row(example_dir / "calendar.csv")),
        ("company-row.schema.json", _first_csv_row(example_dir / "companies.csv")),
        (
            "feature-row.schema.json",
            json.loads((example_dir / "feature_rows.jsonl").read_text().splitlines()[0]),
        ),
        (
            "lineage-row.schema.json",
            json.loads((example_dir / "lineage.jsonl").read_text().splitlines()[0]),
        ),
    ]

    for schema_name, example in cases:
        schema = json.loads((contract_dir / schema_name).read_text(encoding="utf-8"))
        required = set(schema["required"])
        assert required <= set(example), schema_name
        if schema.get("additionalProperties") is False:
            assert required <= set(schema["properties"]), schema_name


def test_lineage_reconciles_to_dense_feature_rows_without_generated_at_leakage() -> None:
    package = build_research_export(build_memory_repository())
    feature_keys = {research_module._feature_key_from_row(row) for row in package.feature_rows}
    included_lineage = [
        row for row in package.lineage_rows if row["inclusion_reason"] == "included"
    ]

    assert len(feature_keys) == len(package.feature_rows)
    assert all(row["feature_row_key"] in feature_keys for row in included_lineage)
    assert all(
        row["information_available_at"] <= row["decision_cutoff_at"] for row in included_lineage
    )
    assert all("generated_at" not in row for row in package.feature_rows)
    assert all("generated_at" not in row for row in package.lineage_rows)


def _calendar_rows(sessions: list[ResearchSession]) -> list[dict[str, object]]:
    return [
        {
            "session_date": session.session_date.isoformat(),
            "open_at": session.open_at.isoformat(),
            "break_start_at": session.break_start_at.isoformat(),
            "break_end_at": session.break_end_at.isoformat(),
            "close_at": session.close_at.isoformat(),
            "sequence": session.sequence,
            "special_session": "false",
        }
        for session in sessions
    ]


def _write_calendar_csv(
    path: Path, rows: list[dict[str, object]], *, include_all_fields: bool = True
) -> None:
    fieldnames = [
        "session_date",
        "open_at",
        "break_start_at",
        "break_end_at",
        "close_at",
        "sequence",
        "special_session",
    ]
    if not include_all_fields:
        fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_manifest(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((path / "manifest.json").read_text(encoding="utf-8")))


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.joinpath("manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _first_csv_row(path: Path) -> dict[str, str]:
    return cast(dict[str, str], next(csv.DictReader(path.read_text(encoding="utf-8").splitlines())))


def _observation(
    *,
    article_id: UUID,
    company_id: UUID,
    information_available_at: datetime,
    event_type: EventType,
    sentiment_label: SentimentLabel,
    sentiment_score: float,
    confidence: float,
) -> _Observation:
    return _Observation(
        article_id=article_id,
        company_id=company_id,
        source_id="synthetic-source",
        source_published_at=information_available_at,
        first_seen_at=information_available_at,
        processed_at=information_available_at,
        information_available_at=information_available_at,
        link=ArticleCompanyLink(
            article_id=article_id,
            company_id=company_id,
            confidence=1.0,
            matched_alias="Demo",
            evidence_text_span="Demo",
        ),
        event=ArticleEvent(
            article_id=article_id,
            event_type=event_type,
            confidence=confidence,
            evidence=["demo"],
        ),
        sentiment=ArticleSentiment(
            article_id=article_id,
            score=sentiment_score,
            label=sentiment_label,
            confidence=confidence,
            evidence=["demo"],
        ),
        assigned_session=None,
        assigned_cutoff_at=None,
        missing_published_time=False,
        future_timestamp_anomaly=False,
        backfilled_information=False,
        multi_company_article=False,
    )
