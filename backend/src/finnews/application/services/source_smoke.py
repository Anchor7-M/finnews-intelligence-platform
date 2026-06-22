from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from finnews.application.ports.http import HttpRequest, HttpResponse
from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import SourceType
from finnews.infrastructure.http.client import BoundedSourceHttpClient, HttpPolicyError
from finnews.infrastructure.sources.announcements import (
    AnnouncementParseError,
    normalize_cik,
    parse_json_announcement_bytes,
)
from finnews.infrastructure.sources.feed import FeedParseError, parse_feed_bytes
from finnews.infrastructure.sources.registry import load_enabled_local_override_source_ids
from finnews.infrastructure.sources.reviews import (
    SourceReview,
    SourceReviewError,
    validate_source_review_integrity,
)

SmokeExitKind = Literal[
    "success",
    "no_change",
    "policy_blocked",
    "disabled",
    "missing_prerequisite",
    "network_failure",
    "parse_failure",
    "persistence_failure",
]

SMOKE_EXIT_CODES: dict[SmokeExitKind, int] = {
    "success": 0,
    "no_change": 0,
    "policy_blocked": 4,
    "disabled": 5,
    "missing_prerequisite": 6,
    "network_failure": 7,
    "parse_failure": 8,
    "persistence_failure": 9,
}


@dataclass(frozen=True)
class SmokeOptions:
    source_id: str
    max_items: int = 5
    conditional_check: bool = False
    persist: bool = False
    confirm_live: bool = False
    report_path: Path | None = None


@dataclass(frozen=True)
class SmokeResult:
    exit_kind: SmokeExitKind
    source_id: str
    review_decision: str
    host: str
    http_status: int | None
    duration_ms: int
    response_byte_count: int
    parsed_item_count: int
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    etag_available: bool
    last_modified_available: bool
    conditional_outcome: str
    persistence_mode: str
    error_category: str
    request_count: int
    report_path: str | None = None

    def safe_dict(self) -> dict[str, object]:
        return {
            "exit_kind": self.exit_kind,
            "source_id": self.source_id,
            "review_decision": self.review_decision,
            "host": self.host,
            "http_status": self.http_status,
            "duration_ms": self.duration_ms,
            "response_byte_count": self.response_byte_count,
            "parsed_item_count": self.parsed_item_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "duplicate_count": self.duplicate_count,
            "etag_available": self.etag_available,
            "last_modified_available": self.last_modified_available,
            "conditional_outcome": self.conditional_outcome,
            "persistence_mode": self.persistence_mode,
            "error_category": self.error_category,
            "request_count": self.request_count,
            "report_path": self.report_path,
        }


class SmokeGateError(ValueError):
    def __init__(self, exit_kind: SmokeExitKind, category: str, message: str) -> None:
        super().__init__(message)
        self.exit_kind = exit_kind
        self.category = category


class SourceSmokeService:
    def __init__(
        self,
        sources: list[SourceDefinition],
        reviews: list[SourceReview],
        *,
        http_client_factory: Callable[[SourceDefinition], BoundedSourceHttpClient] | None = None,
    ) -> None:
        self.sources = {source.source_id: source for source in sources}
        self.reviews = {review.source_id: review for review in reviews}
        self.http_client_factory = http_client_factory or (
            lambda source: BoundedSourceHttpClient(source)
        )

    def run(self, options: SmokeOptions) -> SmokeResult:
        started = time.perf_counter()
        request_count = 0
        source = self.sources.get(options.source_id)
        review = self.reviews.get(options.source_id)
        try:
            if source is None:
                raise SmokeGateError("policy_blocked", "source_missing", "source not found")
            if review is None:
                raise SmokeGateError("policy_blocked", "review_missing", "review not found")
            source = self._gated_source(source, review, options)
            host = urlparse(source.base_url or "").hostname or ""
            client = self.http_client_factory(source)
            response = client.get(HttpRequest(source.base_url or ""))
            request_count += 1
            parsed_count, rejected_count = self._parse_count(response, source, options.max_items)
            conditional_outcome = "not_requested"
            if options.conditional_check and response.status_code != 304:
                headers = _conditional_headers(response)
                if headers:
                    second = client.get(HttpRequest(source.base_url or "", headers=headers))
                    request_count += 1
                    conditional_outcome = (
                        "not_modified" if second.status_code == 304 else "returned_response"
                    )
                else:
                    conditional_outcome = "validators_absent"
            result = SmokeResult(
                exit_kind="no_change" if response.status_code == 304 else "success",
                source_id=source.source_id,
                review_decision=review.review_decision,
                host=host,
                http_status=response.status_code,
                duration_ms=_duration_ms(started),
                response_byte_count=len(response.content),
                parsed_item_count=parsed_count,
                accepted_count=parsed_count if not options.persist else 0,
                rejected_count=rejected_count,
                duplicate_count=0,
                etag_available=bool(response.headers.get("etag")),
                last_modified_available=bool(response.headers.get("last-modified")),
                conditional_outcome=conditional_outcome,
                persistence_mode="persist" if options.persist else "no_persist",
                error_category="none",
                request_count=request_count,
                report_path=str(options.report_path) if options.report_path else None,
            )
        except SmokeGateError as exc:
            result = _error_result(options, review, source, started, exc.exit_kind, exc.category)
        except HttpPolicyError as exc:
            result = _error_result(
                options,
                review,
                source,
                started,
                "network_failure",
                exc.category.value,
                request_count=request_count,
            )
        except (FeedParseError, AnnouncementParseError) as exc:
            result = _error_result(
                options, review, source, started, "parse_failure", str(exc), request_count=1
            )
        if options.report_path:
            _write_report(options.report_path, result)
        return result

    def _gated_source(
        self, source: SourceDefinition, review: SourceReview, options: SmokeOptions
    ) -> SourceDefinition:
        if not 1 <= options.max_items <= 5:
            raise SmokeGateError("policy_blocked", "invalid_max_items", "max items must be 1..5")
        if options.persist:
            raise SmokeGateError(
                "policy_blocked", "persist_blocked", "Milestone 1B live smoke uses no-persist"
            )
        if not options.confirm_live:
            raise SmokeGateError(
                "policy_blocked", "confirmation_missing", "--confirm-live is required"
            )
        if os.environ.get("FINNEWS_ALLOW_LIVE_NETWORK") != "1":
            raise SmokeGateError(
                "policy_blocked", "live_env_missing", "FINNEWS_ALLOW_LIVE_NETWORK=1 is required"
            )
        if review.review_decision != "approved":
            raise SmokeGateError("policy_blocked", "review_not_approved", "review not approved")
        try:
            validate_source_review_integrity([source], [review])
        except SourceReviewError as exc:
            raise SmokeGateError("policy_blocked", "review_integrity", str(exc)) from exc
        if not source.enabled:
            raise SmokeGateError("disabled", "source_disabled", "source is disabled")
        if source.source_id not in load_enabled_local_override_source_ids():
            raise SmokeGateError(
                "disabled", "local_override_missing", "source must be enabled by local override"
            )
        if source.source_id == "sec-edgar-submissions":
            source = _prepare_sec_source(source)
        return source

    def _parse_count(
        self, response: HttpResponse, source: SourceDefinition, max_items: int
    ) -> tuple[int, int]:
        if response.status_code == 304:
            return 0, 0
        if source.source_type in {SourceType.RSS, SourceType.ATOM}:
            parsed = parse_feed_bytes(response.content, source)
        elif source.source_type is SourceType.DOCUMENTED_JSON_API:
            parsed = parse_json_announcement_bytes(response.content, source)
        else:
            raise AnnouncementParseError("unsupported smoke source type")
        return min(len(parsed.records), max_items), parsed.rejected_count


def _prepare_sec_source(source: SourceDefinition) -> SourceDefinition:
    contact = os.environ.get("FINNEWS_SEC_CONTACT")
    raw_cik = os.environ.get("FINNEWS_SEC_TEST_CIK")
    if not contact or not raw_cik:
        raise SmokeGateError(
            "missing_prerequisite",
            "sec_prerequisite_missing",
            "SEC contact metadata and/or test CIK was not supplied locally.",
        )
    cik = normalize_cik(raw_cik)
    base_url = (source.endpoint_template or "").format(cik=cik)
    template = source.user_agent_template or source.user_agent
    return replace(
        source,
        base_url=base_url,
        user_agent=template.format(contact=contact),
        parameter_schema={**source.parameter_schema, "cik": cik},
    )


def _conditional_headers(response: HttpResponse) -> dict[str, str]:
    headers: dict[str, str] = {}
    if response.headers.get("etag"):
        headers["If-None-Match"] = response.headers["etag"]
    if response.headers.get("last-modified"):
        headers["If-Modified-Since"] = response.headers["last-modified"]
    return headers


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _error_result(
    options: SmokeOptions,
    review: SourceReview | None,
    source: SourceDefinition | None,
    started: float,
    exit_kind: SmokeExitKind,
    category: str,
    *,
    request_count: int = 0,
) -> SmokeResult:
    return SmokeResult(
        exit_kind=exit_kind,
        source_id=options.source_id,
        review_decision=review.review_decision if review else "missing",
        host=(urlparse(source.base_url or "").hostname or "") if source else "",
        http_status=None,
        duration_ms=_duration_ms(started),
        response_byte_count=0,
        parsed_item_count=0,
        accepted_count=0,
        rejected_count=0,
        duplicate_count=0,
        etag_available=False,
        last_modified_available=False,
        conditional_outcome="not_requested",
        persistence_mode="persist" if options.persist else "no_persist",
        error_category=category,
        request_count=request_count,
        report_path=str(options.report_path) if options.report_path else None,
    )


def _write_report(path: Path, result: SmokeResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.safe_dict(), indent=2, sort_keys=True), encoding="utf-8")
