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
    assert '"articles": 49' in first.output
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
