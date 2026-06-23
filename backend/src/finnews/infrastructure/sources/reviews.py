from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import IngestionPolicy, SourceApprovalStatus, SourceType

DEFAULT_SOURCE_REVIEW_DIR = Path(__file__).resolve().parents[5] / "config" / "source-reviews"

ReviewDecision = Literal["approved", "rejected", "needs_review", "suspended"]
AccessCost = Literal["free", "free_with_key", "paid", "unknown"]
LiveSmokeStatus = Literal["not_run", "passed", "failed", "blocked"]


class SourceReviewError(ValueError):
    pass


class SourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    review_schema_version: str = Field(pattern=r"^m1b-v1$")
    review_decision: ReviewDecision
    review_scope: str = Field(min_length=1, max_length=500)
    reviewed_at: str
    reviewer: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    official_owner: str = Field(min_length=1, max_length=240)
    official_source: str = Field(min_length=1, max_length=240)
    documentation_url: str
    terms_or_policy_url: str
    access_cost: AccessCost
    authentication_requirement: str = Field(min_length=1, max_length=240)
    allowed_methods: list[str] = Field(min_length=1)
    allowed_hostnames: list[str] = Field(min_length=1)
    documented_endpoint_patterns: list[str] = Field(min_length=1)
    rate_limit_evidence: str = Field(min_length=1, max_length=1000)
    user_agent_requirement: str = Field(min_length=1, max_length=1000)
    content_available: list[str] = Field(min_length=1)
    content_to_store: list[str] = Field(min_length=1)
    content_not_to_store: list[str] = Field(min_length=1)
    redistribution_assessment: str = Field(min_length=1, max_length=1000)
    attribution_requirement: str = Field(min_length=1, max_length=1000)
    robots_or_automated_access_notes: str = Field(min_length=1, max_length=1000)
    privacy_notes: str = Field(min_length=1, max_length=1000)
    known_risks: list[str] = Field(default_factory=list)
    live_smoke_status: LiveSmokeStatus = "not_run"
    live_smoke_checked_at: str | None = None
    evidence_checked_at: str
    evidence_urls: list[str] = Field(min_length=1)
    review_notes: str = Field(min_length=1, max_length=2000)
    source_config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("documentation_url", "terms_or_policy_url")
    @classmethod
    def validate_https_url(cls, value: str) -> str:
        _validate_url(value)
        return value

    @field_validator("evidence_urls")
    @classmethod
    def validate_evidence_urls(cls, value: list[str]) -> list[str]:
        for url in value:
            _validate_url(url)
        return value

    @field_validator("allowed_methods")
    @classmethod
    def validate_methods(cls, value: list[str]) -> list[str]:
        methods = [item.upper() for item in value]
        if any(item not in {"GET", "HEAD", "POST"} for item in methods):
            raise ValueError("allowed_methods may contain only GET, HEAD, or POST")
        return methods

    @field_validator("allowed_hostnames")
    @classmethod
    def normalize_hosts(cls, value: list[str]) -> list[str]:
        hosts = [item.strip().lower() for item in value if item.strip()]
        if not hosts:
            raise ValueError("allowed_hostnames cannot be empty")
        return hosts

    @field_validator("reviewed_at", "evidence_checked_at")
    @classmethod
    def validate_checked_date(cls, value: str) -> str:
        _parse_date_or_datetime(value)
        return value

    @field_validator("live_smoke_checked_at")
    @classmethod
    def validate_optional_checked_date(cls, value: str | None) -> str | None:
        if value:
            _parse_date_or_datetime(value)
        return value

    def safe_summary(self, enabled: bool | None = None) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "official_owner": self.official_owner,
            "official_source": self.official_source,
            "review_decision": self.review_decision,
            "reviewed_at": self.reviewed_at,
            "access_cost": self.access_cost,
            "authentication_requirement": self.authentication_requirement,
            "content_storage_policy": "metadata_only",
            "documentation_url": self.documentation_url,
            "terms_or_policy_url": self.terms_or_policy_url,
            "enabled": enabled,
            "live_smoke_status": self.live_smoke_status,
            "live_smoke_checked_at": self.live_smoke_checked_at,
            "known_limitations": self.known_risks[:5],
        }


def load_source_reviews(review_dir: Path | None = None) -> list[SourceReview]:
    review_dir = review_dir or Path(
        os.environ.get("FINNEWS_SOURCE_REVIEW_DIR", str(DEFAULT_SOURCE_REVIEW_DIR))
    )
    if not review_dir.exists():
        return []
    reviews: list[SourceReview] = []
    seen: set[str] = set()
    for path in sorted(review_dir.glob("*.yaml")):
        data = _read_yaml(path)
        try:
            review = SourceReview.model_validate(data)
        except ValidationError as exc:
            raise SourceReviewError(f"{path}: source review invalid: {exc}") from exc
        if review.source_id in seen:
            raise SourceReviewError(f"duplicate source review: {review.source_id}")
        seen.add(review.source_id)
        reviews.append(review)
    return reviews


def validate_source_reviews(review_dir: Path | None = None) -> list[str]:
    return [review.source_id for review in load_source_reviews(review_dir)]


def source_config_digest(source: SourceDefinition) -> str:
    payload: dict[str, object] = {
        "source_id": source.source_id,
        "source_type": source.source_type.value,
        "base_url": source.base_url,
        "endpoint_template": source.endpoint_template,
        "approved_hostnames": sorted(source.approved_hostnames),
        "terms_url": source.terms_url,
        "documentation_url": source.documentation_url,
        "content_storage_policy": source.content_storage_policy.value,
        "max_response_bytes": source.max_response_bytes,
        "retry_policy": {
            "max_retries": source.retry_policy.max_retries,
            "base_delay_seconds": source.retry_policy.base_delay_seconds,
            "max_delay_seconds": source.retry_policy.max_delay_seconds,
        },
        "minimum_interval_seconds": source.minimum_interval_seconds,
        "field_mapping": source.field_mapping,
        "parameter_schema": source.parameter_schema,
        "user_agent_env_var": source.user_agent_env_var,
        "user_agent_template": source.user_agent_template,
        "risk_classification": source.risk_classification,
    }
    official_data_extensions = {
        "http_method": source.http_method,
        "request_body_template": source.request_body_template,
        "required_local_env_vars": source.required_local_env_vars,
        "pagination_strategy": source.pagination_strategy,
        "dataset_profiles": source.dataset_profiles,
    }
    if official_data_extensions != {
        "http_method": "GET",
        "request_body_template": {},
        "required_local_env_vars": [],
        "pagination_strategy": None,
        "dataset_profiles": {},
    }:
        payload.update(official_data_extensions)
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def review_summaries_for_sources(
    sources: list[SourceDefinition], reviews: list[SourceReview]
) -> list[dict[str, object]]:
    enabled_by_id = {source.source_id: source.enabled for source in sources}
    return [review.safe_summary(enabled_by_id.get(review.source_id)) for review in reviews]


def validate_source_review_integrity(
    sources: list[SourceDefinition], reviews: list[SourceReview]
) -> list[str]:
    review_by_id = {review.source_id: review for review in reviews}
    validated: list[str] = []
    for source in sources:
        if source.source_type not in {
            SourceType.RSS,
            SourceType.ATOM,
            SourceType.DOCUMENTED_JSON_API,
        }:
            continue
        if source.review_status is not SourceApprovalStatus.APPROVED:
            continue
        review = review_by_id.get(source.review_evidence_id or source.source_id)
        if review is None:
            raise SourceReviewError(f"{source.source_id}: approved network source lacks review")
        if review.source_id != source.source_id:
            raise SourceReviewError(f"{source.source_id}: review source_id mismatch")
        if review.review_decision != "approved":
            raise SourceReviewError(f"{source.source_id}: review decision is not approved")
        if source_config_digest(source) != review.source_config_sha256:
            raise SourceReviewError(f"{source.source_id}: source review is stale")
        missing_hosts = set(source.approved_hostnames) - set(review.allowed_hostnames)
        if missing_hosts:
            raise SourceReviewError(
                f"{source.source_id}: approved host missing from review: {sorted(missing_hosts)}"
            )
        endpoint = source.endpoint_template or source.base_url or ""
        if not any(
            re.fullmatch(pattern, endpoint) for pattern in review.documented_endpoint_patterns
        ):
            raise SourceReviewError(f"{source.source_id}: endpoint does not match review")
        if source.content_storage_policy is not IngestionPolicy.METADATA_ONLY:
            raise SourceReviewError(f"{source.source_id}: unsupported storage policy")
        validated.append(source.source_id)
    return validated


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise SourceReviewError(f"{path}: source review must be UTF-8") from exc
    except yaml.YAMLError as exc:
        raise SourceReviewError(f"{path}: malformed YAML") from exc
    if not isinstance(raw, dict):
        raise SourceReviewError(f"{path}: expected YAML mapping")
    return raw


def _validate_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("review URLs must be absolute https URLs")


def _parse_date_or_datetime(value: str) -> date | datetime:
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("datetime must include timezone")
            return parsed
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("expected ISO date or timezone-aware datetime") from exc
