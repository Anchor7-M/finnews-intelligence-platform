from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.application.services.market_reaction import market_data_contract_example_rows
from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings


def test_market_reaction_api_read_only_filters_and_pagination() -> None:
    api = TestClient(create_app(Settings(profile="memory")))

    overview = api.get("/api/v1/market-reaction/overview", headers={"x-request-id": "m3c"})
    assert overview.status_code == 200
    assert overview.headers["x-request-id"] == "m3c"
    overview_body = overview.json()
    assert overview_body["scenario_count"] == 3
    assert overview_body["total_bar_count"] == 6480
    assert overview_body["no_live_market_data"] is True

    scenarios = api.get("/api/v1/market-reaction/scenarios").json()
    assert len(scenarios) == 3

    studies = api.get(
        "/api/v1/market-reaction/studies",
        params={"scenario": "synthetic-planted-reaction-v1", "horizon": "one_week", "limit": 5},
    ).json()
    assert studies["total"] >= 1
    assert len(studies["items"]) == 5
    assert {row["reaction_window"] for row in studies["items"]} == {"one_week"}

    labels = api.get(
        "/api/v1/market-reaction/labels",
        params={
            "scenario": "synthetic-planted-reaction-v1",
            "horizon": "one_week",
            "label": "muted",
            "limit": 10,
        },
    ).json()
    assert labels["total"] >= 1
    assert {row["scenario_id"] for row in labels["items"]} == {"synthetic-planted-reaction-v1"}
    assert {row["label"] for row in labels["items"]} == {"muted"}

    metrics = api.get(
        "/api/v1/market-reaction/metrics",
        params={"scenario": "synthetic-planted-reaction-v1", "horizon": "one_week"},
    ).json()
    assert metrics["total"] == 1
    assert metrics["items"][0]["slice_type"] == "horizon"

    errors = api.get(
        "/api/v1/market-reaction/error-analysis",
        params={"scenario": "synthetic-regime-shift-v1", "limit": 3},
    ).json()
    assert len(errors["items"]) == 3

    packages = api.get("/api/v1/market-data/packages").json()
    assert packages["total"] == 3
    assert packages["items"][0]["no_live_market_data"] is True

    bars = api.get(
        "/api/v1/market-data/bars",
        params={"scenario": "synthetic-null-reaction-v1", "regime": "calm", "limit": 5},
    ).json()
    assert bars["total"] == 432
    assert len(bars["items"]) == 5
    assert {row["market_state"] for row in bars["items"]} == {"calm"}

    assert api.post("/api/v1/market-data/bars").status_code == 405


def test_market_reaction_cli_commands_are_offline_and_deterministic(tmp_path: Path) -> None:
    runner = CliRunner()
    rows = market_data_contract_example_rows()
    jsonl = tmp_path / "bars.jsonl"
    jsonl.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    first = runner.invoke(cli_app, ["market-data", "contract", "validate", "--path", str(jsonl)])
    second = runner.invoke(cli_app, ["market-data", "contract", "validate", "--path", str(jsonl)])
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert (
        json.loads(first.output)["deterministic_hash"]
        == json.loads(second.output)["deterministic_hash"]
    )

    result = runner.invoke(
        cli_app,
        [
            "market-data",
            "build-demo",
            "--scenario",
            "synthetic-planted-reaction-v1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["bar_count"] == 2160

    for command in [
        ["reaction", "overview"],
        ["reaction", "study", "build", "--scenario", "synthetic-planted-reaction-v1"],
        ["reaction", "labels", "--scenario", "synthetic-planted-reaction-v1"],
        ["reaction", "evaluate", "--scenario", "synthetic-planted-reaction-v1"],
        [
            "reaction",
            "compare",
            "--left",
            "synthetic-null-reaction-v1",
            "--right",
            "synthetic-planted-reaction-v1",
        ],
        ["reaction", "error-analysis", "--scenario", "synthetic-planted-reaction-v1"],
    ]:
        result = runner.invoke(cli_app, command)
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["synthetic_data"] is True

    import_result = runner.invoke(
        cli_app, ["market-data", "import-local", "--path", str(jsonl), "--dry-run"]
    )
    assert import_result.exit_code == 0, import_result.output
    import_body = json.loads(import_result.output)
    assert import_body["imported"] is False
    assert import_body["local_path_persisted"] is False


def test_market_reaction_cli_rejects_unknown_scenarios_and_forbidden_fields(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        ["market-data", "build-demo", "--scenario", "synthetic-missing-v1"],
    )
    assert result.exit_code != 0

    rows = market_data_contract_example_rows()
    rows[0]["future_return"] = "0.4"
    jsonl = tmp_path / "forbidden.jsonl"
    jsonl.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    result = runner.invoke(cli_app, ["market-data", "contract", "validate", "--path", str(jsonl)])
    assert result.exit_code != 0
    assert "forbidden fields" in result.output
