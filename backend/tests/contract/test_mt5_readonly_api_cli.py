from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings


def test_mt5_readonly_api_is_public_safe_and_read_only() -> None:
    api = TestClient(create_app(Settings(profile="memory")))

    overview = api.get("/api/v1/integrations/mt5/readonly/overview").json()
    readiness = api.get("/api/v1/integrations/mt5/readonly/readiness").json()
    schema = api.get("/api/v1/integrations/mt5/readonly/symbol-map/schema").json()
    runs = api.get("/api/v1/integrations/mt5/readonly/runs").json()

    assert overview["local_cli_only"] is True
    assert overview["public_api_trigger"] == "disabled"
    assert readiness["mt5_terminal_connection"] == "not attempted"
    assert readiness["order_execution"] == "disabled"
    assert readiness["account_access"] == "not_supported"
    assert schema["credentials_allowed"] is False
    assert schema["order_fields_allowed"] is False
    assert isinstance(runs, list)
    rendered = json.dumps({"overview": overview, "readiness": readiness}).lower()
    assert "password" not in rendered
    assert "account_id" not in rendered
    assert api.post("/api/v1/integrations/mt5/readonly/readiness").status_code == 405
    assert api.post("/api/v1/integrations/mt5/readonly/runs").status_code == 405


def test_mt5_readonly_cli_status_validate_and_blocked_export(tmp_path: Path) -> None:
    runner = CliRunner()

    status = runner.invoke(cli_app, ["mt5", "readonly", "status"])
    assert status.exit_code == 0, status.output
    status_payload = json.loads(status.output)
    assert status_payload["readiness"]["terminal_access_status"] == "not_attempted"

    validation = runner.invoke(
        cli_app,
        [
            "mt5",
            "readonly",
            "validate-symbol-map",
            "--path",
            str(
                Path(__file__).resolve().parents[3]
                / "config/integrations/mt5-symbol-map.example.yaml"
            ),
        ],
    )
    assert validation.exit_code == 0, validation.output
    assert json.loads(validation.output)["terminal_contacted"] is False

    blocked = runner.invoke(
        cli_app,
        [
            "mt5",
            "readonly",
            "export-bars",
            "--symbol-map",
            str(tmp_path / "missing.yaml"),
            "--timeframe",
            "D1",
            "--from",
            "2026-06-01T00:00:00+00:00",
            "--to",
            "2026-06-02T00:00:00+00:00",
            "--output",
            str(tmp_path / "outside"),
        ],
    )
    assert blocked.exit_code == 4
    payload = json.loads(blocked.output)
    assert payload["status"] == "blocked_by_gate"
    assert payload["terminal_contacted"] is False


def test_mt5_readonly_forbidden_cli_commands_do_not_exist() -> None:
    runner = CliRunner()
    for command in ["login", "buy", "sell", "order", "position", "history", "check"]:
        result = runner.invoke(cli_app, ["mt5", "readonly", command])
        assert result.exit_code != 0
