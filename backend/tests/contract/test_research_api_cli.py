from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings


def test_research_api_read_only_endpoints() -> None:
    client = TestClient(create_app(Settings(profile="memory")))

    overview = client.get("/api/v1/research/overview")
    assert overview.status_code == 200
    assert overview.json()["counts"]["feature_row_count"] == 2880

    features = client.get("/api/v1/research/features?window=1&limit=5")
    assert features.status_code == 200
    assert features.json()["total"] >= 1

    catalog = client.get("/api/v1/research/feature-catalog")
    assert catalog.status_code == 200
    assert catalog.json()["no_market_data"] is True

    assert client.post("/api/v1/research/exports").status_code == 405


def test_research_cli_build_validate_compare_and_lineage(tmp_path: Path) -> None:
    runner = CliRunner()
    left = tmp_path / "left"
    right = tmp_path / "right"

    result = runner.invoke(
        cli_app,
        ["research", "export", "build", "--output", str(left)],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        cli_app,
        ["research", "export", "build", "--output", str(right)],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli_app, ["research", "export", "validate", "--path", str(left)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["feature_row_count"] == 2880

    result = runner.invoke(
        cli_app,
        ["research", "export", "compare", "--left", str(left), "--right", str(right)],
    )
    assert result.exit_code == 0, result.output

    first_lineage = json.loads((left / "lineage.jsonl").read_text(encoding="utf-8").splitlines()[0])
    result = runner.invoke(
        cli_app,
        [
            "research",
            "export",
            "lineage",
            "--path",
            str(left),
            "--row-id",
            first_lineage["lineage_row_id"],
        ],
    )
    assert result.exit_code == 0, result.output
    assert "summary" not in result.output and "body" not in result.output
