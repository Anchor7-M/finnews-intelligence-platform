from __future__ import annotations

from pathlib import Path

import pytest

from finnews.infrastructure.sources.registry import SourceConfigError, load_source_definitions

CONFIG = """
sources:
  - source_id: reviewed-rss
    display_name: Reviewed RSS
    source_type: rss
    base_url: https://official.example/feed.xml
    approved_hostnames: ["official.example"]
    terms_url: https://official.example/policy
    documentation_url: https://official.example/docs
    review_status: approved
    enabled: false
    reviewer: local-review
    content_storage_policy: metadata_only
    provenance_required: true
    language: en
    timezone: UTC
    max_response_bytes: 2000000
    retry_policy: {max_retries: 1, base_delay_seconds: 1, max_delay_seconds: 30}
    minimum_interval_seconds: 3600
    field_mapping: {}
    user_agent: finnews-intelligence-platform/0.1 test
    risk_classification: low
  - source_id: unreviewed-rss
    display_name: Unreviewed RSS
    source_type: rss
    base_url: https://unreviewed.example/feed.xml
    approved_hostnames: ["unreviewed.example"]
    terms_url: https://unreviewed.example/policy
    documentation_url: https://unreviewed.example/docs
    review_status: unreviewed
    enabled: false
    content_storage_policy: metadata_only
    provenance_required: true
    language: en
    timezone: UTC
    max_response_bytes: 2000000
    retry_policy: {max_retries: 1, base_delay_seconds: 1, max_delay_seconds: 30}
    minimum_interval_seconds: 3600
    field_mapping: {}
    user_agent: finnews-intelligence-platform/0.1 test
    risk_classification: low
"""


def write_config(tmp_path: Path) -> Path:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    source_dir.joinpath("sources.yaml").write_text(CONFIG, encoding="utf-8")
    return source_dir


def test_local_override_can_enable_approved_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = write_config(tmp_path)
    override = tmp_path / "sources.local.yaml"
    override.write_text(
        "sources:\n  - source_id: reviewed-rss\n    enabled: true\n", encoding="utf-8"
    )
    monkeypatch.setenv("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(override))
    sources = {source.source_id: source for source in load_source_definitions(source_dir)}
    assert sources["reviewed-rss"].enabled is True
    assert sources["reviewed-rss"].approved_hostnames == ["official.example"]


def test_local_override_blocks_unknown_unapproved_and_extra_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = write_config(tmp_path)
    override = tmp_path / "sources.local.yaml"
    monkeypatch.setenv("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(override))
    override.write_text(
        "sources:\n  - source_id: missing-rss\n    enabled: true\n", encoding="utf-8"
    )
    with pytest.raises(SourceConfigError, match="unknown"):
        load_source_definitions(source_dir)
    override.write_text(
        "sources:\n  - source_id: unreviewed-rss\n    enabled: true\n", encoding="utf-8"
    )
    with pytest.raises(SourceConfigError, match="unapproved"):
        load_source_definitions(source_dir)
    override.write_text(
        "sources:\n"
        "  - source_id: reviewed-rss\n"
        "    enabled: true\n"
        "    approved_hostnames: ['evil.example']\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceConfigError, match="approved_hostnames"):
        load_source_definitions(source_dir)
