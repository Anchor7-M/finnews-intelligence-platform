from __future__ import annotations

from pathlib import Path

import pytest

from finnews.domain.enums import SourceApprovalStatus, SourceType
from finnews.infrastructure.sources.registry import SourceConfigError, load_source_definitions
from finnews.infrastructure.sources.reviews import source_config_digest


def write_config(path: Path, body: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    config = path / "sources.yaml"
    config.write_text(body, encoding="utf-8")
    return config


VALID_CONFIG = """
sources:
  - source_id: mock-approved-rss
    display_name: Mock Approved RSS
    source_type: rss
    base_url: https://mock.local/rss.xml
    approved_hostnames: ["mock.local"]
    terms_url: https://mock.local/terms
    documentation_url: https://mock.local/docs
    review_status: approved
    enabled: true
    reviewer: test
    content_storage_policy: metadata_only
    provenance_required: true
    language: en
    timezone: UTC
    max_response_bytes: 1024
    retry_policy: {max_retries: 2, base_delay_seconds: 0, max_delay_seconds: 0}
    minimum_interval_seconds: 0
    field_mapping: {}
    user_agent: finnews-intelligence-platform/0.1 test
    risk_classification: low
"""


def test_valid_config_loads_typed_definition(tmp_path: Path) -> None:
    write_config(tmp_path, VALID_CONFIG)
    definitions = load_source_definitions(tmp_path)
    assert definitions[0].source_id == "mock-approved-rss"
    assert definitions[0].source_type is SourceType.RSS
    assert definitions[0].review_status is SourceApprovalStatus.APPROVED
    assert definitions[0].fetch_allowed is True


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("terms_url: https://mock.local/terms", "terms_url"),
        ("source_type: rss", "source_type"),
        ('approved_hostnames: ["mock.local"]', "approved_hostnames"),
    ],
)
def test_invalid_config_fails_clearly(tmp_path: Path, replacement: str, message: str) -> None:
    write_config(tmp_path, VALID_CONFIG.replace(replacement, ""))
    with pytest.raises(SourceConfigError, match=message):
        load_source_definitions(tmp_path)


def test_unapproved_enabled_source_is_rejected(tmp_path: Path) -> None:
    write_config(
        tmp_path, VALID_CONFIG.replace("review_status: approved", "review_status: unreviewed")
    )
    with pytest.raises(SourceConfigError, match="enabled sources must be approved"):
        load_source_definitions(tmp_path)


def test_secret_like_field_is_rejected(tmp_path: Path) -> None:
    write_config(tmp_path, VALID_CONFIG.replace("risk_classification: low", "api_token: nope"))
    with pytest.raises(SourceConfigError, match="secret-like field"):
        load_source_definitions(tmp_path)


def test_unknown_field_is_rejected(tmp_path: Path) -> None:
    write_config(tmp_path, VALID_CONFIG.replace("risk_classification: low", "unexpected: nope"))
    with pytest.raises(SourceConfigError, match="unexpected"):
        load_source_definitions(tmp_path)


def test_official_data_source_extensions_are_loaded_and_hashed(tmp_path: Path) -> None:
    extended = VALID_CONFIG.replace(
        "risk_classification: low",
        """
    risk_classification: low
    http_method: POST
    request_body_template:
      seriesid: ["CES0000000001"]
      startyear: "2025"
      endyear: "2025"
    required_local_env_vars:
      - FINNEWS_BLS_API_KEY
    pagination_strategy: bounded_year_window
    dataset_profiles:
      nonfarm_payrolls:
        dataset_id: bls-ces
        series_id: CES0000000001
        default_asset_links: ["macro-us-labor", "idx-spx"]
""",
    )
    write_config(tmp_path, extended)
    definition = load_source_definitions(tmp_path)[0]
    assert definition.http_method == "POST"
    assert definition.required_local_env_vars == ["FINNEWS_BLS_API_KEY"]
    assert definition.dataset_profiles["nonfarm_payrolls"]["dataset_id"] == "bls-ces"
    assert (
        source_config_digest(definition)
        != "d2ac863035cc919f9bea3abf59c4a92b3047e46445e206466ba2b2431987e190"
    )


def test_duplicate_source_ids_are_rejected(tmp_path: Path) -> None:
    write_config(tmp_path, VALID_CONFIG + VALID_CONFIG.split("sources:", 1)[1])
    with pytest.raises(SourceConfigError, match="duplicate source_id"):
        load_source_definitions(tmp_path)
