from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from finnews.application.ports.http import BoundedHttpClient, HttpRequest, HttpResponse
from finnews.application.ports.repositories import NewsRepository
from finnews.application.services.pipeline import NewsPipeline
from finnews.domain.entities import (
    SourceDefinition,
    SourceFetchAttempt,
    SourceFetchState,
    SourceRecord,
)
from finnews.domain.enums import (
    FetchOutcome,
    SourceApprovalStatus,
    SourceErrorCategory,
    SourceHealthStatus,
    SourceType,
)
from finnews.domain.value_objects import utc_now
from finnews.infrastructure.http.client import HttpPolicyError
from finnews.infrastructure.sources.announcements import (
    AnnouncementParseError,
    parse_json_announcement_bytes,
    read_user_export,
)
from finnews.infrastructure.sources.feed import (
    FeedParseError,
    ParsedSourceRecords,
    parse_feed_bytes,
)
from finnews.settings import Settings

RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class SourceRunResult:
    source_id: str
    outcome: FetchOutcome
    item_count: int
    new_count: int
    duplicate_count: int
    rejected_count: int
    http_status: int | None
    response_byte_count: int
    retry_count: int
    health: SourceHealthStatus
    error_category: SourceErrorCategory = SourceErrorCategory.NONE
    error_summary: str = ""
    dry_run: bool = False


class SourceIngestionService:
    def __init__(
        self,
        repository: NewsRepository,
        settings: Settings,
        *,
        http_client_factory: Callable[[SourceDefinition], BoundedHttpClient] | None = None,
        sleeper: Callable[[float], None] | None = None,
        jitter: Callable[[int], float] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.http_client_factory = http_client_factory
        self.sleeper = sleeper or (lambda _: None)
        self.jitter = jitter or (lambda _: 0.0)
        self.clock = clock or time.perf_counter

    def fetch_source(self, source_id: str, *, dry_run: bool = False) -> SourceRunResult:
        source = self._require_runnable_source(source_id)
        state = self.repository.get_source_fetch_state(source.source_id) or SourceFetchState(
            source_id=source.source_id, adapter_version=source.adapter_version
        )
        if dry_run:
            state = deepcopy(state)
        now = utc_now()
        if state.next_allowed_at and state.next_allowed_at > now:
            result = self._record_blocked(
                source,
                state,
                SourceErrorCategory.RATE_LIMITED,
                "source minimum interval has not elapsed",
                dry_run,
            )
            return result
        request_headers: dict[str, str] = {}
        if state.etag:
            request_headers["If-None-Match"] = state.etag
        if state.last_modified:
            request_headers["If-Modified-Since"] = state.last_modified
        started = utc_now()
        parsed: ParsedSourceRecords | None = None
        try:
            response, retry_count = self._fetch_with_retry(source, request_headers)
            if response.status_code != 304:
                try:
                    parsed = self._parse_response(source, response)
                except HttpPolicyError as exc:
                    exc.retry_count = retry_count
                    raise
        except HttpPolicyError as exc:
            return self._record_failure(
                source,
                state,
                started,
                exc.category,
                _sanitize(str(exc)),
                dry_run,
                retry_count=exc.retry_count,
            )
        if response.status_code == 304:
            finished = utc_now()
            state.last_attempted_at = finished
            state.last_successful_at = finished
            state.last_http_status = 304
            state.last_item_count = 0
            state.consecutive_failure_count = 0
            state.last_error_category = SourceErrorCategory.NONE
            state.last_error_summary = ""
            state.health_status = SourceHealthStatus.HEALTHY
            state.next_allowed_at = None
            state.updated_at = finished
            attempt = SourceFetchAttempt(
                source_id=source.source_id,
                outcome=FetchOutcome.NO_CHANGE,
                started_at=started,
                finished_at=finished,
                http_status=304,
                retry_count=retry_count,
                duration_ms=0,
                etag_present=bool(state.etag),
                last_modified_present=bool(state.last_modified),
                cursor_before=state.cursor,
                cursor_after=state.cursor,
                dry_run=dry_run,
            )
            if not dry_run:
                self.repository.add_source_fetch_attempt(attempt)
                self.repository.upsert_source_fetch_state(state)
            return self._result_from_attempt(attempt, state)
        if parsed is None:
            raise RuntimeError("source response was not parsed")
        return self._persist_success(
            source,
            state,
            parsed,
            response,
            retry_count=retry_count,
            dry_run=dry_run,
        )

    def import_announcements(
        self, source_id: str, path: Path, *, dry_run: bool = False
    ) -> SourceRunResult:
        source = self._require_import_source(source_id)
        state = self.repository.get_source_fetch_state(source.source_id) or SourceFetchState(
            source_id=source.source_id, adapter_version=source.adapter_version
        )
        if dry_run:
            state = deepcopy(state)
        started = utc_now()
        try:
            parsed = read_user_export(path, source)
        except (AnnouncementParseError, UnicodeDecodeError, FileNotFoundError) as exc:
            return self._record_failure(
                source,
                state,
                started,
                SourceErrorCategory.VALIDATION,
                _sanitize(str(exc)),
                dry_run,
            )
        return self._persist_records(
            source,
            state,
            parsed,
            response=None,
            retry_count=0,
            dry_run=dry_run,
            started=started,
        )

    def _fetch_with_retry(
        self, source: SourceDefinition, headers: dict[str, str]
    ) -> tuple[HttpResponse, int]:
        if self.http_client_factory is None:
            raise RuntimeError("HTTP client factory is required for network fetches")
        client = self.http_client_factory(source)
        retries = 0
        while True:
            try:
                response = client.get(HttpRequest(url=source.base_url or "", headers=headers))
            except HttpPolicyError as exc:
                if exc.category not in {
                    SourceErrorCategory.TIMEOUT,
                    SourceErrorCategory.CONNECTION,
                    SourceErrorCategory.TRANSIENT_HTTP,
                }:
                    raise
                if retries >= source.retry_policy.max_retries:
                    exc.retry_count = retries
                    raise
                retries += 1
                self.sleeper(_retry_delay(source, retries, None, self.jitter))
                continue
            if response.status_code not in RETRYABLE_STATUSES:
                return response, retries
            if retries >= source.retry_policy.max_retries:
                return response, retries
            retries += 1
            self.sleeper(
                _retry_delay(source, retries, response.headers.get("retry-after"), self.jitter)
            )

    def _parse_response(
        self, source: SourceDefinition, response: HttpResponse
    ) -> ParsedSourceRecords:
        if response.status_code >= 400:
            category = (
                SourceErrorCategory.TRANSIENT_HTTP
                if response.status_code in RETRYABLE_STATUSES
                else SourceErrorCategory.PERMANENT_HTTP
            )
            raise HttpPolicyError(category, f"source returned HTTP {response.status_code}")
        try:
            if source.source_type in {SourceType.RSS, SourceType.ATOM}:
                return parse_feed_bytes(response.content, source)
            if source.source_type is SourceType.DOCUMENTED_JSON_API:
                return parse_json_announcement_bytes(response.content, source)
        except FeedParseError as exc:
            raise HttpPolicyError(SourceErrorCategory.PARSE, _sanitize(str(exc))) from exc
        except AnnouncementParseError as exc:
            raise HttpPolicyError(SourceErrorCategory.PARSE, _sanitize(str(exc))) from exc
        raise HttpPolicyError(SourceErrorCategory.VALIDATION, "unsupported source type")

    def _persist_success(
        self,
        source: SourceDefinition,
        state: SourceFetchState,
        parsed: ParsedSourceRecords,
        response: HttpResponse,
        *,
        retry_count: int,
        dry_run: bool,
    ) -> SourceRunResult:
        return self._persist_records(
            source,
            state,
            parsed,
            response=response,
            retry_count=retry_count,
            dry_run=dry_run,
            started=utc_now(),
        )

    def _persist_records(
        self,
        source: SourceDefinition,
        state: SourceFetchState,
        parsed: ParsedSourceRecords,
        response: HttpResponse | None,
        *,
        retry_count: int,
        dry_run: bool,
        started: datetime,
    ) -> SourceRunResult:
        started_at = started
        records = _records_with_source_metadata(parsed.records, source)
        cursor_before = state.cursor
        counts: dict[str, int] = {}
        if not dry_run:
            counts = NewsPipeline(self.repository, self.settings).ingest_records(records)
        finished = utc_now()
        body_hash = hashlib.sha256(response.content).hexdigest() if response else None
        byte_count = (
            len(response.content)
            if response
            else sum(
                len(record.title.encode("utf-8")) + len(record.summary.encode("utf-8"))
                for record in records
            )
        )
        new_count = counts.get("accepted", len(records) if dry_run else 0)
        duplicate_count = counts.get("exact_duplicate", 0) + counts.get("near_duplicate", 0)
        rejected_count = counts.get("rejected", 0) + parsed.rejected_count
        state.last_attempted_at = finished
        state.last_successful_at = finished
        state.last_http_status = response.status_code if response else None
        state.last_response_hash = body_hash
        state.last_response_byte_count = byte_count
        state.last_item_count = len(records)
        state.consecutive_failure_count = 0
        state.last_error_category = SourceErrorCategory.NONE
        state.last_error_summary = ""
        state.health_status = SourceHealthStatus.HEALTHY
        state.cursor = parsed.next_cursor or state.cursor
        state.next_allowed_at = (
            finished + timedelta(seconds=source.minimum_interval_seconds)
            if source.minimum_interval_seconds
            else None
        )
        state.adapter_version = source.adapter_version
        state.updated_at = finished
        if response:
            state.etag = response.headers.get("etag") or state.etag
            state.last_modified = response.headers.get("last-modified") or state.last_modified
        attempt = SourceFetchAttempt(
            source_id=source.source_id,
            outcome=FetchOutcome.DRY_RUN if dry_run else FetchOutcome.SUCCESS,
            started_at=started_at,
            finished_at=finished,
            http_status=response.status_code if response else None,
            item_count=len(records),
            new_count=new_count,
            duplicate_count=duplicate_count,
            rejected_count=rejected_count,
            response_byte_count=byte_count,
            response_hash=body_hash,
            retry_count=retry_count,
            duration_ms=0,
            etag_present=bool(state.etag),
            last_modified_present=bool(state.last_modified),
            cursor_before=cursor_before,
            cursor_after=parsed.next_cursor or state.cursor,
            dry_run=dry_run,
        )
        if not dry_run:
            self.repository.add_source_fetch_attempt(attempt)
            self.repository.upsert_source_fetch_state(state)
        return self._result_from_attempt(attempt, state)

    def _require_runnable_source(self, source_id: str) -> SourceDefinition:
        source = self.repository.get_source_definition(source_id)
        if source is None:
            raise ValueError(f"source {source_id} not found")
        if source.review_status is not SourceApprovalStatus.APPROVED:
            raise ValueError(f"source {source_id} is not approved")
        if not source.enabled:
            raise ValueError(f"source {source_id} is disabled")
        if source.source_type not in {
            SourceType.RSS,
            SourceType.ATOM,
            SourceType.DOCUMENTED_JSON_API,
        }:
            raise ValueError(f"source {source_id} is not a network source")
        return source

    def _require_import_source(self, source_id: str) -> SourceDefinition:
        source = self.repository.get_source_definition(source_id)
        if source is None:
            raise ValueError(f"source {source_id} not found")
        if source.review_status is not SourceApprovalStatus.APPROVED:
            raise ValueError(f"source {source_id} is not approved")
        if not source.enabled:
            raise ValueError(f"source {source_id} is disabled")
        if source.source_type not in {SourceType.USER_EXPORT_JSON, SourceType.USER_EXPORT_CSV}:
            raise ValueError(f"source {source_id} is not a user export source")
        return source

    def _record_blocked(
        self,
        source: SourceDefinition,
        state: SourceFetchState,
        category: SourceErrorCategory,
        summary: str,
        dry_run: bool,
    ) -> SourceRunResult:
        return self._record_failure(source, state, utc_now(), category, summary, dry_run)

    def _record_failure(
        self,
        source: SourceDefinition,
        state: SourceFetchState,
        started_at: datetime,
        category: SourceErrorCategory,
        summary: str,
        dry_run: bool,
        retry_count: int = 0,
    ) -> SourceRunResult:
        finished = utc_now()
        state.last_attempted_at = finished
        state.consecutive_failure_count += 1
        state.last_error_category = category
        state.last_error_summary = _sanitize(summary)
        state.health_status = (
            SourceHealthStatus.BLOCKED
            if category in {SourceErrorCategory.POLICY_BLOCKED, SourceErrorCategory.RATE_LIMITED}
            else SourceHealthStatus.FAILING
        )
        state.updated_at = finished
        attempt = SourceFetchAttempt(
            source_id=source.source_id,
            outcome=FetchOutcome.POLICY_BLOCKED
            if category is SourceErrorCategory.POLICY_BLOCKED
            else FetchOutcome.FAILED,
            started_at=started_at,
            finished_at=finished,
            error_category=category,
            error_summary=state.last_error_summary,
            retry_count=retry_count,
            dry_run=dry_run,
        )
        if not dry_run:
            self.repository.add_source_fetch_attempt(attempt)
            self.repository.upsert_source_fetch_state(state)
        return self._result_from_attempt(attempt, state)

    def _result_from_attempt(
        self, attempt: SourceFetchAttempt, state: SourceFetchState
    ) -> SourceRunResult:
        return SourceRunResult(
            source_id=attempt.source_id,
            outcome=attempt.outcome,
            item_count=attempt.item_count,
            new_count=attempt.new_count,
            duplicate_count=attempt.duplicate_count,
            rejected_count=attempt.rejected_count,
            http_status=attempt.http_status,
            response_byte_count=attempt.response_byte_count,
            retry_count=attempt.retry_count,
            health=state.health_status,
            error_category=attempt.error_category,
            error_summary=attempt.error_summary,
            dry_run=attempt.dry_run,
        )


def _records_with_source_metadata(
    records: list[SourceRecord], source: SourceDefinition
) -> list[SourceRecord]:
    return [
        SourceRecord(
            source_key=record.source_key,
            source_name=record.source_name,
            source_type=record.source_type,
            article_id=record.article_id,
            url=record.url,
            title=record.title,
            summary=record.summary,
            language=record.language,
            published_at=record.published_at,
            raw_metadata={
                **record.raw_metadata,
                "source_definition_id": source.source_id,
                "storage_policy": source.content_storage_policy.value,
            },
        )
        for record in records
    ]


def _retry_delay(
    source: SourceDefinition,
    retry_number: int,
    retry_after: str | None,
    jitter: Callable[[int], float] | None = None,
) -> float:
    jitter = jitter or (lambda _: 0.0)
    if retry_after:
        parsed_retry_after = _parse_retry_after(retry_after)
        if parsed_retry_after is not None:
            return float(min(parsed_retry_after, source.retry_policy.max_delay_seconds))
    delay = source.retry_policy.base_delay_seconds * (2 ** max(0, retry_number - 1))
    return float(min(delay + jitter(retry_number), source.retry_policy.max_delay_seconds))


def _sanitize(value: str) -> str:
    text = value.replace("\n", " ").replace("\r", " ")
    text = re.sub(
        r"(?i)(authorization|bearer|token|api[_-]?key|password|cookie)=?\s*[^,\s;]+",
        r"\1=[redacted]",
        text,
    )
    text = re.sub(r"[A-Za-z]:\\[^\s]+", "[local-path-redacted]", text)
    text = re.sub(r"postgresql\+psycopg://[^\s]+", "[database-url-redacted]", text)
    return text[:240]


def _parse_retry_after(value: str) -> float | None:
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
    return max(0.0, seconds)
