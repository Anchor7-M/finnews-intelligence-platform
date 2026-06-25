from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings


def test_paper_execution_api_is_read_only_and_paginated() -> None:
    api = TestClient(create_app(Settings(profile="memory")))

    overview = api.get("/api/v1/paper/overview", headers={"x-request-id": "paper"})
    assert overview.status_code == 200
    assert overview.headers["x-request-id"] == "paper"
    assert overview.json()["paper_order_count"] == 30
    assert overview.json()["no_real_order"] is True

    policies = api.get("/api/v1/paper/risk-policies").json()
    assert policies[0]["paper_only"] is True

    decisions = api.get(
        "/api/v1/paper/risk-decisions",
        params={"scenario": "paper-planted-reaction-v1", "limit": 5},
    ).json()
    assert decisions["total"] == 36
    assert len(decisions["items"]) == 5

    orders = api.get(
        "/api/v1/paper/orders",
        params={"scenario": "paper-planted-reaction-v1"},
    ).json()
    assert orders["total"] == 10
    assert all(row["not_investment_advice"] for row in orders["items"])

    fills = api.get("/api/v1/paper/fills", params={"fill_status": "filled"}).json()
    assert fills["total"] == 8

    positions = api.get("/api/v1/paper/positions").json()
    assert positions["total"] == 8

    nav = api.get("/api/v1/paper/nav", params={"scenario": "paper-planted-reaction-v1"}).json()
    assert nav[0]["reconciliation_status"] == "passed"

    runs = api.get("/api/v1/paper/runs").json()
    assert len(runs) == 3
    assert api.post("/api/v1/paper/orders").status_code == 405
    assert api.post("/api/v1/paper/approvals").status_code in {404, 405}


def test_paper_execution_cli_commands_are_offline_and_safe() -> None:
    runner = CliRunner()
    commands = [
        ["paper", "risk", "validate"],
        ["paper", "risk", "evaluate", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "orders", "generate", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "orders", "summary", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "approvals", "simulate", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "fills", "simulate", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "portfolio", "run", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "portfolio", "summary", "--scenario", "paper-planted-reaction-v1"],
        ["paper", "export-static"],
        ["paper", "release-audit"],
    ]
    for command in commands:
        result = runner.invoke(cli_app, command)
        assert result.exit_code == 0, result.output
        body = json.loads(result.output)
        assert "MetaTrader5" not in result.output
        assert "real account" not in result.output.lower()
        if isinstance(body, dict) and "synthetic_data" in body:
            assert body["synthetic_data"] is True

    missing = runner.invoke(
        cli_app,
        ["paper", "portfolio", "run", "--scenario", "paper-missing-v1"],
    )
    assert missing.exit_code != 0
