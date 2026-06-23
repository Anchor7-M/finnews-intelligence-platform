from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings


def test_official_data_api_contract() -> None:
    client = TestClient(create_app(Settings(profile="memory")))
    overview = client.get("/api/v1/official-data/overview")
    assert overview.status_code == 200
    assert overview.json()["dataset_count"] == 4
    assert overview.json()["live_data_persisted"] is False

    datasets = client.get("/api/v1/official-data/datasets?source_id=bls-public-data")
    assert datasets.status_code == 200
    assert datasets.json()["total"] == 1

    series = client.get("/api/v1/official-data/series?dataset_id=bls-ces")
    assert series.status_code == 200
    assert series.json()["total"] == 3

    observations = client.get("/api/v1/official-data/observations?limit=1")
    assert observations.status_code == 200
    assert observations.json()["total"] == 24
    observation_key = observations.json()["items"][0]["observation_key"]

    revisions = client.get(f"/api/v1/official-data/observations/{observation_key}/revisions")
    assert revisions.status_code == 200
    assert revisions.json()[0]["observation_key"] == observation_key

    documents = client.get("/api/v1/official-data/regulatory-documents?agency=Energy")
    assert documents.status_code == 200
    assert documents.json()["total"] >= 1
    assert "pdf_url" in documents.json()["items"][0]

    associations = client.get("/api/v1/official-data/series-asset-associations?limit=200")
    assert associations.status_code == 200
    assert associations.json()["total"] == 80

    events = client.get("/api/v1/official-data/release-events?event_family=labor_market")
    assert events.status_code == 200
    assert events.json()["total"] >= 1


def test_official_data_cli_contract() -> None:
    runner = CliRunner()
    summary = runner.invoke(cli_app, ["official-data", "summary"])
    assert summary.exit_code == 0
    summary_payload = json.loads(summary.stdout)
    assert summary_payload["synthetic_data"] is True
    assert summary_payload["dataset_count"] == 4

    validation = runner.invoke(cli_app, ["official-data", "validate-fixtures"])
    assert validation.exit_code == 0
    validation_payload = json.loads(validation.stdout)
    assert validation_payload["valid"] is True

    blocked = runner.invoke(cli_app, ["official-data", "live-smoke", "--source", "bls-public-data"])
    assert blocked.exit_code == 4
    assert json.loads(blocked.stdout)["request_count"] == 0
