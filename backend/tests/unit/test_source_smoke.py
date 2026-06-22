from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from finnews.application.services.source_smoke import SmokeOptions, SourceSmokeService
from finnews.domain.entities import SourceDefinition, SourceRetryPolicy
from finnews.domain.enums import SourceApprovalStatus, SourceType
from finnews.infrastructure.http.client import BoundedSourceHttpClient
from finnews.infrastructure.sources.reviews import SourceReview, source_config_digest

RSS_BODY = (
    b"<rss><channel><item><guid>fed-1</guid>"
    b"<title>Federal Reserve metadata item</title>"
    b"<link>https://www.federalreserve.gov/newsevents/pressreleases/test.htm</link>"
    b"<description>Brief feed summary.</description>"
    b"<pubDate>Mon, 22 Jun 2026 00:00:00 GMT</pubDate>"
    b"</item></channel></rss>"
)


def fed_source(enabled: bool = True) -> SourceDefinition:
    return SourceDefinition(
        source_id="federal-reserve-press-releases",
        display_name="Federal Reserve Board Press Releases RSS",
        source_type=SourceType.RSS,
        approved_hostnames=["www.federalreserve.gov"],
        review_status=SourceApprovalStatus.APPROVED,
        enabled=enabled,
        base_url="https://www.federalreserve.gov/feeds/press_all.xml",
        terms_url="https://www.federalreserve.gov/feeds/feeds.htm",
        documentation_url="https://www.federalreserve.gov/feeds/feeds.htm",
        reviewer="local-review",
        max_response_bytes=2_000_000,
        retry_policy=SourceRetryPolicy(max_retries=1),
        minimum_interval_seconds=21600,
        review_evidence_id="federal-reserve-press-releases",
    )


def review_for(source: SourceDefinition) -> SourceReview:
    return SourceReview.model_validate(
        {
            "source_id": source.source_id,
            "review_schema_version": "m1b-v1",
            "review_decision": "approved",
            "review_scope": "Engineering review",
            "reviewed_at": "2026-06-22",
            "reviewer": "local-review",
            "official_owner": "Federal Reserve",
            "official_source": "RSS",
            "documentation_url": "https://www.federalreserve.gov/feeds/feeds.htm",
            "terms_or_policy_url": "https://www.federalreserve.gov/feeds/feeds.htm",
            "access_cost": "free",
            "authentication_requirement": "none",
            "allowed_methods": ["GET", "HEAD"],
            "allowed_hostnames": ["www.federalreserve.gov"],
            "documented_endpoint_patterns": [
                r"https://www\.federalreserve\.gov/feeds/press_all\.xml"
            ],
            "rate_limit_evidence": "manual only",
            "user_agent_requirement": "clear UA",
            "content_available": ["metadata"],
            "content_to_store": ["title"],
            "content_not_to_store": ["body"],
            "redistribution_assessment": "metadata only",
            "attribution_requirement": "attribute",
            "robots_or_automated_access_notes": "feed only",
            "privacy_notes": "none",
            "known_risks": [],
            "live_smoke_status": "not_run",
            "live_smoke_checked_at": None,
            "evidence_checked_at": "2026-06-22",
            "evidence_urls": ["https://www.federalreserve.gov/feeds/feeds.htm"],
            "review_notes": "approved",
            "source_config_sha256": source_config_digest(source),
        }
    )


def override_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sources.local.yaml"
    path.write_text(
        "sources:\n  - source_id: federal-reserve-press-releases\n    enabled: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(path))


def service(source: SourceDefinition, transport: httpx.MockTransport) -> SourceSmokeService:
    return SourceSmokeService(
        [source],
        [review_for(source)],
        http_client_factory=lambda definition: BoundedSourceHttpClient(
            definition,
            transport=transport,
            resolver=lambda _: ["23.200.1.1"],
        ),
    )


def test_smoke_success_no_persist_and_conditional_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = fed_source()
    override_file(tmp_path, monkeypatch)
    monkeypatch.setenv("FINNEWS_ALLOW_LIVE_NETWORK", "1")
    calls: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.headers))
        if len(calls) == 2:
            return httpx.Response(304, headers={"content-type": "application/rss+xml"})
        return httpx.Response(
            200,
            headers={
                "content-type": "application/rss+xml",
                "etag": '"abc"',
                "last-modified": "Mon, 22 Jun 2026 00:00:00 GMT",
            },
            content=RSS_BODY,
        )

    report = tmp_path / "reports" / "fed.json"
    result = service(source, httpx.MockTransport(handler)).run(
        SmokeOptions(
            source_id=source.source_id,
            max_items=1,
            conditional_check=True,
            confirm_live=True,
            report_path=report,
        )
    )
    assert result.exit_kind == "success"
    assert result.parsed_item_count == 1
    assert result.persistence_mode == "no_persist"
    assert result.conditional_outcome == "not_modified"
    assert result.request_count == 2
    body = json.loads(report.read_text(encoding="utf-8"))
    assert "Federal Reserve metadata item" not in str(body)
    assert body["etag_available"] is True


def test_smoke_gates_missing_live_confirmation_and_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = fed_source(enabled=False)
    override_file(tmp_path, monkeypatch)
    result = service(source, httpx.MockTransport(lambda _: httpx.Response(200))).run(
        SmokeOptions(source_id=source.source_id)
    )
    assert result.exit_kind == "policy_blocked"
    monkeypatch.setenv("FINNEWS_ALLOW_LIVE_NETWORK", "1")
    monkeypatch.setenv("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(tmp_path / "missing.local.yaml"))
    result = service(source, httpx.MockTransport(lambda _: httpx.Response(200))).run(
        SmokeOptions(source_id=source.source_id, confirm_live=True)
    )
    assert result.exit_kind == "disabled"


def test_sec_missing_contact_is_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = SourceDefinition(
        source_id="sec-edgar-submissions",
        display_name="SEC EDGAR Submissions API",
        source_type=SourceType.DOCUMENTED_JSON_API,
        approved_hostnames=["data.sec.gov"],
        review_status=SourceApprovalStatus.APPROVED,
        enabled=True,
        base_url="https://data.sec.gov/submissions/CIK0000000000.json",
        endpoint_template="https://data.sec.gov/submissions/CIK{cik}.json",
        terms_url="https://www.sec.gov/privacy.htm",
        documentation_url="https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        reviewer="local-review",
        field_mapping={"record_mode": "columnar", "columns_path": "filings.recent"},
        parameter_schema={"cik": "ten_digit_cik"},
        user_agent_env_var="FINNEWS_SEC_CONTACT",
        review_evidence_id="sec-edgar-submissions",
    )
    review = review_for(fed_source()).model_copy(
        update={
            "source_id": source.source_id,
            "allowed_hostnames": ["data.sec.gov"],
            "documented_endpoint_patterns": [
                r"https://data\.sec\.gov/submissions/CIK\{cik\}\.json"
            ],
            "source_config_sha256": source_config_digest(source),
        }
    )
    path = tmp_path / "sources.local.yaml"
    path.write_text("sources:\n  - source_id: sec-edgar-submissions\n    enabled: true\n")
    monkeypatch.setenv("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(path))
    monkeypatch.setenv("FINNEWS_ALLOW_LIVE_NETWORK", "1")
    result = SourceSmokeService([source], [review]).run(
        SmokeOptions(source_id=source.source_id, confirm_live=True)
    )
    assert result.exit_kind == "missing_prerequisite"
    assert result.error_category == "sec_prerequisite_missing"
