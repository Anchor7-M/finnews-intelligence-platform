from __future__ import annotations

from pathlib import Path

import pytest

from finnews.infrastructure.sources.registry import load_source_definitions
from finnews.infrastructure.sources.reviews import (
    SourceReviewError,
    load_source_reviews,
    source_config_digest,
    validate_source_review_integrity,
)

SOURCE_YAML = """
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
    review_evidence_id: reviewed-rss
"""


def write_source(tmp_path: Path) -> tuple[Path, str]:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "reviewed.yaml").write_text(SOURCE_YAML, encoding="utf-8")
    source = load_source_definitions(source_dir)[0]
    return source_dir, source_config_digest(source)


def review_yaml(digest: str) -> str:
    return f"""
source_id: reviewed-rss
review_schema_version: m1b-v1
review_decision: approved
review_scope: Engineering usage-policy review.
reviewed_at: "2026-06-22"
reviewer: local-review
official_owner: Example Owner
official_source: Example RSS
documentation_url: https://official.example/docs
terms_or_policy_url: https://official.example/policy
access_cost: free
authentication_requirement: No authentication.
allowed_methods: ["GET", "HEAD"]
allowed_hostnames: ["official.example"]
documented_endpoint_patterns: ['https://official\\.example/feed\\.xml']
rate_limit_evidence: Conservative local testing only.
user_agent_requirement: Clear research User-Agent.
content_available: ["metadata"]
content_to_store: ["title", "url"]
content_not_to_store: ["body"]
redistribution_assessment: Metadata only; not legal advice.
attribution_requirement: Attribute official owner.
robots_or_automated_access_notes: No page scraping.
privacy_notes: No personal data.
known_risks: ["availability may change"]
live_smoke_status: not_run
live_smoke_checked_at: null
evidence_checked_at: "2026-06-22"
evidence_urls: ["https://official.example/docs", "https://official.example/policy"]
review_notes: Approved for engineering metadata pilot.
source_config_sha256: {digest}
"""


def write_review(tmp_path: Path, digest: str, *, text: str | None = None) -> Path:
    review_dir = tmp_path / "reviews"
    review_dir.mkdir()
    (review_dir / "reviewed.yaml").write_text(text or review_yaml(digest), encoding="utf-8")
    return review_dir


def test_valid_review_integrity(tmp_path: Path) -> None:
    source_dir, digest = write_source(tmp_path)
    review_dir = write_review(tmp_path, digest)
    sources = load_source_definitions(source_dir)
    reviews = load_source_reviews(review_dir)
    assert validate_source_review_integrity(sources, reviews) == ["reviewed-rss"]


def test_unknown_review_field_is_rejected(tmp_path: Path) -> None:
    _, digest = write_source(tmp_path)
    review_dir = write_review(tmp_path, digest, text=review_yaml(digest) + "extra: nope\n")
    with pytest.raises(SourceReviewError, match="extra"):
        load_source_reviews(review_dir)


def test_missing_evidence_url_is_rejected(tmp_path: Path) -> None:
    _, digest = write_source(tmp_path)
    text = review_yaml(digest).replace(
        'evidence_urls: ["https://official.example/docs", "https://official.example/policy"]',
        "evidence_urls: []",
    )
    review_dir = write_review(tmp_path, digest, text=text)
    with pytest.raises(SourceReviewError, match="evidence_urls"):
        load_source_reviews(review_dir)


def test_stale_review_and_host_mismatch_are_rejected(tmp_path: Path) -> None:
    source_dir, digest = write_source(tmp_path)
    stale_dir = write_review(tmp_path, "a" * 64)
    with pytest.raises(SourceReviewError, match="stale"):
        validate_source_review_integrity(
            load_source_definitions(source_dir), load_source_reviews(stale_dir)
        )
    host_dir = tmp_path / "host-reviews"
    host_dir.mkdir()
    host_dir.joinpath("reviewed.yaml").write_text(
        review_yaml(digest).replace("official.example", "other.example"), encoding="utf-8"
    )
    with pytest.raises(SourceReviewError, match="missing from review"):
        validate_source_review_integrity(
            load_source_definitions(source_dir), load_source_reviews(host_dir)
        )
