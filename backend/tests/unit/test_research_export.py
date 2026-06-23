from __future__ import annotations

import csv
from pathlib import Path

from finnews.application.services.research_export import (
    DEFAULT_WINDOWS,
    build_demo_calendar,
    build_research_export,
    compare_research_export_packages,
    decision_cutoff,
    load_local_calendar,
    validate_research_export_package,
    write_research_export_package,
)
from finnews.bootstrap import build_memory_repository


def test_demo_calendar_has_exact_synthetic_sessions() -> None:
    calendar, sessions = build_demo_calendar()

    assert calendar.calendar_id == "synthetic-ashare-demo-calendar"
    assert calendar.timezone == "Asia/Shanghai"
    assert len(sessions) == 60
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "session_date",
                "open_at",
                "break_start_at",
                "break_end_at",
                "close_at",
                "sequence",
                "special_session",
            ],
        )
        writer.writeheader()
        for session in sessions[:3]:
            writer.writerow(
                {
                    "session_date": session.session_date.isoformat(),
                    "open_at": session.open_at.isoformat(),
                    "break_start_at": session.break_start_at.isoformat(),
                    "break_end_at": session.break_end_at.isoformat(),
                    "close_at": session.close_at.isoformat(),
                    "sequence": session.sequence,
                    "special_session": "false",
                }
            )

    imported, imported_sessions = load_local_calendar(path)

    assert imported.calendar_id == "local-user-calendar"
    assert len(imported_sessions) == 3
    assert decision_cutoff(imported_sessions[0], "pre_open_15m") < imported_sessions[0].open_at
    assert imported.calendar_hash != calendar.calendar_hash
