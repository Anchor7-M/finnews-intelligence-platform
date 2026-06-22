from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from finnews.application.ports.http import HttpRequest, HttpResponse
from finnews.application.services.source_ingestion import SourceIngestionService
from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import (
    FetchOutcome,
    SourceApprovalStatus,
    SourceErrorCategory,
    SourceHealthStatus,
    SourceType,
)
from finnews.infrastructure.http.client import BoundedSourceHttpClient, HttpPolicyError
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.settings import Settings

RSS_BODY = (
    b"<rss><channel><item><guid>item-1</guid>"
    b"<title>Alpine Robotics announces earnings update</title>"
    b"<link>https://mock.local/a</link>"
    b"<description>Alpine Robotics reports better margin outlook.</description>"
    b"<pubDate>Mon, 22 Jun 2026 00:00:00 GMT</pubDate>"
    b"</item></channel></rss>"
)


def source(source_type: SourceType = SourceType.RSS) -> SourceDefinition:
    return SourceDefinition(
        source_id="mock-approved-rss" if source_type is SourceType.RSS else "mock-export-json",
        display_name="Mock Approved Source",
        source_type=source_type,
        approved_hostnames=["mock.local"],
        review_status=SourceApprovalStatus.APPROVED,
        enabled=True,
        base_url="https://mock.local/feed.xml" if source_type is SourceType.RSS else None,
        import_format="json" if source_type is SourceType.USER_EXPORT_JSON else None,
        terms_url="https://mock.local/terms",
        documentation_url="https://mock.local/docs",
        reviewer="test",
        field_mapping={
            "id": "id",
            "title": "title",
            "url": "url",
            "published_at": "published_at",
            "summary": "summary",
            "ticker": "ticker",
        },
        minimum_interval_seconds=0,
    )


def service_with_transport(
    repo: MemoryNewsRepository, transport: httpx.MockTransport
) -> SourceIngestionService:
    return SourceIngestionService(
        repo,
        Settings(profile="memory"),
        http_client_factory=lambda definition: BoundedSourceHttpClient(
            definition, transport=transport, resolver=lambda _: ["93.184.216.34"]
        ),
    )


def test_fetch_stores_etag_and_second_fetch_sends_conditionals() -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source())
    seen_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        if len(seen_headers) == 1:
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/rss+xml",
                    "etag": '"abc"',
                    "last-modified": "Mon, 22 Jun 2026 00:00:00 GMT",
                },
                content=RSS_BODY,
            )
        return httpx.Response(304, headers={"content-type": "application/rss+xml"})

    service = service_with_transport(repo, httpx.MockTransport(handler))
    first = service.fetch_source(definition.source_id)
    second = service.fetch_source(definition.source_id)
    state = repo.get_source_fetch_state(definition.source_id)
    assert first.outcome is FetchOutcome.SUCCESS
    assert second.outcome is FetchOutcome.NO_CHANGE
    assert state is not None
    assert state.etag == '"abc"'
    assert seen_headers[1]["if-none-match"] == '"abc"'
    assert seen_headers[1]["if-modified-since"] == "Mon, 22 Jun 2026 00:00:00 GMT"


def test_retryable_status_recovers_without_real_sleep() -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source())
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, headers={"content-type": "application/rss+xml"})
        return httpx.Response(
            200, headers={"content-type": "application/rss+xml"}, content=RSS_BODY
        )

    service = service_with_transport(repo, httpx.MockTransport(handler))
    result = service.fetch_source(definition.source_id)
    assert result.outcome is FetchOutcome.SUCCESS
    assert result.retry_count == 1
    assert calls == 2


def test_parse_failure_keeps_prior_good_validators() -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source())
    bodies = [RSS_BODY, b"<rss><broken>"]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml", "etag": '"good"'},
            content=bodies.pop(0),
        )

    service = service_with_transport(repo, httpx.MockTransport(handler))
    assert service.fetch_source(definition.source_id).outcome is FetchOutcome.SUCCESS
    assert service.fetch_source(definition.source_id).outcome is FetchOutcome.FAILED
    state = repo.get_source_fetch_state(definition.source_id)
    assert state is not None
    assert state.etag == '"good"'
    assert state.health_status is SourceHealthStatus.FAILING


def test_user_json_import_is_idempotent(tmp_path: Path) -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source(SourceType.USER_EXPORT_JSON))
    path = tmp_path / "announcements.json"
    path.write_text(json.dumps([announcement_row()]), encoding="utf-8")
    service = SourceIngestionService(repo, Settings(profile="memory"))
    first = service.import_announcements(definition.source_id, path)
    second = service.import_announcements(definition.source_id, path)
    assert first.new_count == 1
    assert second.duplicate_count == 1
    assert len(repo.list_articles()) == 1


def test_dry_run_leaves_persistent_state_unchanged(tmp_path: Path) -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source(SourceType.USER_EXPORT_JSON))
    path = tmp_path / "announcements.json"
    path.write_text(json.dumps([announcement_row()]), encoding="utf-8")
    service = SourceIngestionService(repo, Settings(profile="memory"))
    result = service.import_announcements(definition.source_id, path, dry_run=True)
    assert result.dry_run is True
    assert result.new_count == 1
    assert repo.list_articles() == []
    assert repo.list_source_fetch_attempts() == []
    assert repo.get_source_fetch_state(definition.source_id) is None


def test_dry_run_with_existing_state_does_not_mutate_state() -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source())
    bodies = [RSS_BODY, b"<rss><broken>"]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml", "etag": '"stable"'},
            content=bodies.pop(0),
        )

    service = service_with_transport(repo, httpx.MockTransport(handler))
    assert service.fetch_source(definition.source_id).outcome is FetchOutcome.SUCCESS
    before = repo.get_source_fetch_state(definition.source_id)
    assert before is not None
    dry_run = service.fetch_source(definition.source_id, dry_run=True)
    after = repo.get_source_fetch_state(definition.source_id)
    assert dry_run.outcome is FetchOutcome.FAILED
    assert after is before
    assert after.etag == '"stable"'
    assert after.consecutive_failure_count == 0
    assert after.health_status is SourceHealthStatus.HEALTHY
    assert len(repo.list_source_fetch_attempts()) == 1


def test_ordinary_4xx_is_not_retried() -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source())
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, headers={"content-type": "application/rss+xml"})

    result = service_with_transport(repo, httpx.MockTransport(handler)).fetch_source(
        definition.source_id
    )
    assert result.outcome is FetchOutcome.FAILED
    assert result.retry_count == 0
    assert calls == 1


def test_timeout_retry_and_retry_after_date_are_bounded() -> None:
    repo = MemoryNewsRepository()
    definition = repo.upsert_source_definition(source())
    sleeps: list[float] = []

    class TimeoutThenSuccess:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, _: HttpRequest) -> HttpResponse:
            self.calls += 1
            if self.calls == 1:
                raise HttpPolicyError(SourceErrorCategory.TIMEOUT, "timeout token=secret")
            return HttpResponse(
                url="https://mock.local/feed.xml",
                status_code=200,
                headers={"content-type": "application/rss+xml"},
                content=RSS_BODY,
            )

    client = TimeoutThenSuccess()
    service = SourceIngestionService(
        repo,
        Settings(profile="memory"),
        http_client_factory=lambda _: client,
        sleeper=sleeps.append,
        jitter=lambda _: 0.25,
    )
    result = service.fetch_source(definition.source_id)
    assert result.outcome is FetchOutcome.SUCCESS
    assert result.retry_count == 1
    assert sleeps == [1.25]

    retry_at = (datetime.now(UTC) + timedelta(seconds=60)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    response = HttpResponse(
        url="https://mock.local/feed.xml",
        status_code=429,
        headers={"retry-after": retry_at},
        content=b"",
    )

    class AlwaysRateLimited:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, _: HttpRequest) -> HttpResponse:
            self.calls += 1
            return response

    rate_client = AlwaysRateLimited()
    rate_sleeps: list[float] = []
    rate_service = SourceIngestionService(
        repo,
        Settings(profile="memory"),
        http_client_factory=lambda _: rate_client,
        sleeper=rate_sleeps.append,
    )
    rate_service.fetch_source(definition.source_id)
    assert rate_client.calls == 3
    assert all(0 <= item <= 30 for item in rate_sleeps)


def announcement_row() -> dict[str, str]:
    return {
        "id": "ann-1",
        "title": "Alpine Robotics announces earnings update",
        "url": "https://mock.local/a",
        "published_at": "2026-06-22T00:00:00Z",
        "summary": "Alpine Robotics reports better margin outlook.",
        "ticker": "ALP",
    }
