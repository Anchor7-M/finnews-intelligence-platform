from __future__ import annotations

from typer.testing import CliRunner

from finnews.interfaces.cli.app import app

runner = CliRunner()


def test_cli_help_lists_required_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in [
        "doctor",
        "process",
        "digest",
        "signals",
        "export-static",
        "evaluate-demo",
        "demo",
    ]:
        assert command in result.output


def test_cli_memory_demo_static_export_and_idempotent_repeat(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = runner.invoke(app, ["demo", "--profile", "memory"])
    second = runner.invoke(app, ["demo", "--profile", "memory"])
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert '"articles": 46' in first.output
    assert '"exact_duplicate_observation_count": 8' in first.output
    assert '"near_duplicate_observation_count": 10' in first.output
    output = tmp_path / "static"
    export = runner.invoke(app, ["export-static", "--output", str(output)])
    assert export.exit_code == 0
    assert (output / "overview.json").exists()


def test_cli_invalid_date_missing_fixture_and_doctor_no_secrets() -> None:
    invalid = runner.invoke(app, ["digest", "--date", "bad-date"])
    missing = runner.invoke(app, ["ingest", "fixture", "--path", "missing.jsonl"])
    doctor = runner.invoke(app, ["doctor"])
    assert invalid.exit_code != 0
    assert missing.exit_code != 0
    assert doctor.exit_code == 0
    assert "finnews:finnews" not in doctor.output
    assert "secret" not in doctor.output.lower()


def test_cli_evaluate_demo_reports_matching_deduplication_metrics() -> None:
    result = runner.invoke(app, ["evaluate-demo"])
    assert result.exit_code == 0
    assert "synthetic_demo_matches=54 synthetic_demo_total=54" in result.output
    assert "synthetic_disposition_matches=68 synthetic_disposition_total=68" in result.output
    assert '"duplicate_observation_count": 18' in result.output
