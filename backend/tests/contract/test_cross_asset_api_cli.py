from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings


def test_cross_asset_api_read_only_safe_fields_and_filters() -> None:
    api = TestClient(create_app(Settings(profile="memory")))

    overview = api.get("/api/v1/cross-asset/overview", headers={"x-request-id": "cross"})
    assert overview.status_code == 200
    assert overview.headers["x-request-id"] == "cross"
    body = overview.json()
    assert body["asset_count"] == 40
    assert body["event_count"] == 100
    assert body["impact_hypothesis_count"] == 240
    assert body["signal_candidate_count"] == 80
    assert body["no_execution"] is True

    assets = api.get("/api/v1/assets", params={"asset_class": "fx"}).json()
    assert assets["total"] == 5
    asset_id = assets["items"][0]["asset_id"]
    assert api.get(f"/api/v1/assets/{asset_id}").status_code == 200
    assert api.get(f"/api/v1/assets/{asset_id}/aliases").status_code == 200
    assert api.get(f"/api/v1/assets/{asset_id}/events").status_code == 200
    assert len(api.get("/api/v1/asset-relationships").json()) >= 1
    assert len(api.get("/api/v1/cross-asset/events").json()) == 100

    impacts = api.get("/api/v1/event-impacts", params={"horizon": "one_day"}).json()
    assert impacts["total"] == 60
    signals = api.get("/api/v1/signals", params={"status": "research"}).json()
    assert signals["total"] == 16
    signal_id = signals["items"][0]["signal_id"]
    signal_detail = api.get(f"/api/v1/signals/{signal_id}").json()
    forbidden_text = json.dumps(signal_detail).lower()
    assert "order_type" not in forbidden_text
    assert "password" not in forbidden_text

    readiness = api.get("/api/v1/integrations/mt5/readiness").json()
    assert readiness["mt5_terminal_connection"] == "not implemented"
    assert readiness["order_execution"] == "disabled"
    assert api.post("/api/v1/signals").status_code == 405
    assert api.post("/api/v1/integrations/mt5/readiness").status_code == 405
    assert api.get("/api/v1/assets/MISSING").status_code == 404


def test_cross_asset_cli_commands_are_offline_and_deterministic(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli_app, ["asset", "validate"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["asset_count"] == 40

    result = runner.invoke(
        cli_app,
        ["asset", "resolve", "--namespace", "news_source", "--symbol", "policy pulse"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "ambiguous"

    result = runner.invoke(cli_app, ["cross-asset", "summary"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["impact_hypothesis_count"] == 240

    output = tmp_path / ".finnews-market-signals" / "demo"
    result = runner.invoke(cli_app, ["signal", "export", "--output", str(output)])
    assert result.exit_code == 0, result.output
    first_hash = json.loads(result.output)["package_content_hash"]

    result = runner.invoke(cli_app, ["signal", "validate", "--path", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["package_content_hash"] == first_hash

    result = runner.invoke(
        cli_app,
        ["mt5", "validate-symbol-map", "--path", "config/integrations/mt5-symbol-map.example.yaml"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["terminal_contacted"] is False

    result = runner.invoke(cli_app, ["mt5", "readiness"])
    assert result.exit_code == 0, result.output
    readiness = json.loads(result.output)
    assert readiness["mt5_terminal_connection"] == "not implemented"
    assert readiness["order_execution"] == "disabled"


def test_forbidden_mt5_commands_do_not_exist() -> None:
    runner = CliRunner()
    for command in ["connect", "login", "order", "buy", "sell", "close"]:
        result = runner.invoke(cli_app, ["mt5", command])
        assert result.exit_code != 0
