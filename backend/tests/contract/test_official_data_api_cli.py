from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app as cli_app
from finnews.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]


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
    assert series.json()["total"] == 4

    observations = client.get("/api/v1/official-data/observations?limit=1")
    assert observations.status_code == 200
    assert observations.json()["total"] == 144
    observation_key = observations.json()["items"][0]["observation_key"]

    revisions = client.get(f"/api/v1/official-data/observations/{observation_key}/revisions")
    assert revisions.status_code == 200
    assert revisions.json()[0]["observation_key"] == observation_key
    revised = next(
        row
        for row in client.get("/api/v1/official-data/observations", params={"limit": 200}).json()[
            "items"
        ]
        if row["current_revision"] == 2
    )
    revised_history = client.get(
        f"/api/v1/official-data/observations/{revised['observation_key']}/revisions"
    ).json()
    as_of_before_revision = client.get(
        "/api/v1/official-data/observations",
        params={
            "profile_id": revised["profile_id"],
            "as_of": revised_history[0]["information_available_at"],
            "limit": 200,
        },
    ).json()
    historical = next(
        row
        for row in as_of_before_revision["items"]
        if row["observation_key"] == revised["observation_key"]
    )
    assert historical["current_revision"] == 1

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

    export = runner.invoke(cli_app, ["official-data", "export-static"])
    assert export.exit_code == 0
    export_payload = json.loads(export.stdout)
    assert "official-data-overview" in export_payload["files"]
    overview = json.loads(
        (REPO_ROOT / "frontend" / "public" / "demo-data" / "official-data-overview.json").read_text(
            encoding="utf-8"
        )
    )
    assert overview["dataset_count"] == 4
    assert overview["observation_count"] == 144
    assert overview["changed_value_revision_count"] == 24

    release_audit = runner.invoke(cli_app, ["official-data", "release-audit"])
    assert release_audit.exit_code == 0
    release_payload = json.loads(release_audit.stdout)
    assert release_payload["status"] == "completed"
    ledger = json.loads(
        (REPO_ROOT / "reports" / "official-data" / "m3b-release-ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert ledger["definition_count_total"] == 16
    assert ledger["observation_business_key_count"] == 144
    assert ledger["changed_value_revision_count"] == 24
    assert ledger["static_export_record_counts"]["official-observation-revisions"] == 168

    source_audit = runner.invoke(cli_app, ["official-data", "source-audit"])
    assert source_audit.exit_code == 0
    source_payload = json.loads(source_audit.stdout)
    assert source_payload["source_count"] == 4
    assert source_payload["all_disabled"] is True
    assert source_payload["all_reviews_current"] is True
    source_report_text = (
        REPO_ROOT / "reports" / "official-data" / "m3b-source-review-audit.json"
    ).read_text(encoding="utf-8")
    source_report = json.loads(source_report_text)
    assert source_report["source_count"] == 4
    assert all(row["enabled"] is False for row in source_report["sources"])
    assert "FINNEWS_EIA_API_KEY" in source_report_text
    assert "api_key=" not in source_report_text

    blocked = runner.invoke(cli_app, ["official-data", "live-smoke", "--source", "bls-public-data"])
    assert blocked.exit_code == 4
    assert json.loads(blocked.stdout)["request_count"] == 0
