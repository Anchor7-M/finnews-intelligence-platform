from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app
from finnews.settings import Settings, get_settings

CONFIG = """
sources:
  - source_id: mock-export-json
    display_name: Mock JSON Export
    source_type: user_export_json
    import_format: json
    approved_hostnames: []
    terms_url: https://mock.local/terms
    documentation_url: https://mock.local/docs
    review_status: approved
    enabled: true
    reviewer: test
    content_storage_policy: metadata_only
    provenance_required: true
    language: en
    timezone: UTC
    max_response_bytes: 2048
    retry_policy: {max_retries: 0, base_delay_seconds: 0, max_delay_seconds: 0}
    minimum_interval_seconds: 0
    field_mapping:
      id: id
      title: title
      url: url
      published_at: published_at
      summary: summary
      ticker: ticker
    user_agent: finnews-intelligence-platform/0.1 test
    risk_classification: low
"""


def write_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "sources"
    config_dir.mkdir()
    (config_dir / "sources.yaml").write_text(CONFIG, encoding="utf-8")
    return config_dir


def test_source_api_endpoints_and_error_envelope(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FINNEWS_SOURCE_CONFIG_DIR", str(write_config(tmp_path)))
    get_settings.cache_clear()
    api = TestClient(create_app(Settings(profile="memory")))
    response = api.get("/api/v1/sources", headers={"x-request-id": "source-test"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "source-test"
    body = response.json()
    assert body["items"][0]["source_id"] == "mock-export-json"
    assert "password" not in str(body).lower()
    assert api.get("/api/v1/sources/mock-export-json").status_code == 200
    assert api.get("/api/v1/sources/mock-export-json/health").status_code == 200
    attempts = api.get("/api/v1/source-fetch-attempts?limit=10").json()
    assert attempts["total"] == 0
    not_found = api.get("/api/v1/sources/missing")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"


def test_source_cli_validate_list_import_and_safe_output(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_dir = write_config(tmp_path)
    export_path = tmp_path / "announcements.json"
    export_path.write_text(json.dumps([announcement_row()]), encoding="utf-8")
    monkeypatch.setenv("FINNEWS_SOURCE_CONFIG_DIR", str(config_dir))
    get_settings.cache_clear()
    runner = CliRunner()
    assert runner.invoke(app, ["source", "validate-config"]).exit_code == 0
    listed = runner.invoke(app, ["source", "list"])
    assert listed.exit_code == 0
    assert "mock-export-json" in listed.output
    imported = runner.invoke(
        app,
        [
            "source",
            "import-announcements",
            "--source",
            "mock-export-json",
            "--path",
            str(export_path),
        ],
    )
    assert imported.exit_code == 0
    assert '"outcome": "success"' in imported.output
    assert "finnews:finnews" not in imported.output


def test_source_fetch_all_approved_no_network_sources_is_no_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FINNEWS_SOURCE_CONFIG_DIR", str(write_config(tmp_path)))
    get_settings.cache_clear()
    result = CliRunner().invoke(app, ["source", "fetch", "--all-approved", "--dry-run"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "reason": "no approved enabled network sources",
        "status": "no_work",
    }


def announcement_row() -> dict[str, str]:
    return {
        "id": "ann-1",
        "title": "Alpine Robotics announces earnings update",
        "url": "https://mock.local/a",
        "published_at": "2026-06-22T00:00:00Z",
        "summary": "Alpine Robotics reports better margin outlook.",
        "ticker": "ALP",
    }
