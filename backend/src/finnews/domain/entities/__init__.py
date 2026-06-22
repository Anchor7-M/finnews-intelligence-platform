from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from finnews.domain.enums import (
    DuplicateType,
    EventType,
    IngestionPolicy,
    ProcessingState,
    RunStatus,
    SentimentLabel,
    SourceType,
)
from finnews.domain.value_objects import new_id, utc_now


@dataclass
class Source:
    source_key: str
    display_name: str
    source_type: SourceType
    id: UUID = field(default_factory=new_id)
    base_url: str | None = None
    terms_url: str | None = None
    enabled: bool = True
    language_hints: list[str] = field(default_factory=list)
    ingestion_policy: IngestionPolicy = IngestionPolicy.METADATA_ONLY
    rate_limit: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class IngestionRun:
    source_id: UUID
    status: RunStatus = RunStatus.STARTED
    id: UUID = field(default_factory=new_id)
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    cursor_before: str | None = None
    cursor_after: str | None = None
    fetched_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    exact_duplicate_count: int = 0
    near_duplicate_count: int = 0
    warning_count: int = 0
    error_summary: str | None = None
    code_version: str = "0.1.0"
    configuration_version: str = "demo-v1"


@dataclass(frozen=True)
class SourceRecord:
    source_key: str
    source_name: str
    source_type: SourceType
    article_id: str
    url: str
    title: str
    summary: str
    language: str
    published_at: str
    raw_metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class RawArticle:
    source_id: UUID
    source_article_id: str
    canonical_url: str
    source_title: str
    source_summary: str
    source_language: str
    published_at: datetime
    raw_metadata: dict[str, object]
    normalized_content_hash: str
    ingestion_run_id: UUID
    id: UUID = field(default_factory=new_id)
    fetched_at: datetime = field(default_factory=utc_now)


@dataclass
class Article:
    canonical_raw_article_id: UUID
    normalized_title: str
    normalized_summary: str
    language: str
    published_at: datetime
    local_market_date: date
    canonical_url: str
    exact_content_hash: str
    source_key: str
    source_name: str
    processing_state: ProcessingState = ProcessingState.PROCESSED
    id: UUID = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class ArticleDuplicate:
    candidate_article_id: UUID
    canonical_article_id: UUID
    duplicate_type: DuplicateType
    similarity_score: float
    algorithm_name: str
    algorithm_version: str = "1"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ObservationDisposition:
    observation_id: str
    source_key: str
    disposition: str
    canonical_observation_id: str | None
    canonical_article_id: UUID | None
    duplicate_type: DuplicateType | None = None
    similarity_score: float | None = None
    explanation: str = ""
    fixture_group: str = ""


@dataclass
class Company:
    ticker: str
    exchange: str
    legal_name: str
    short_name: str
    sector: str
    active: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class CompanyAlias:
    company_id: UUID
    alias: str
    normalized_alias: str
    alias_type: str = "name"
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass
class ArticleCompanyLink:
    article_id: UUID
    company_id: UUID
    confidence: float
    matched_alias: str
    evidence_text_span: str
    linker_name: str = "deterministic_alias_linker"
    linker_version: str = "1"


@dataclass
class ArticleEvent:
    article_id: UUID
    event_type: EventType
    confidence: float
    evidence: list[str]
    classifier_name: str = "keyword_event_classifier"
    classifier_version: str = "1"
    processed_at: datetime = field(default_factory=utc_now)


@dataclass
class ArticleSentiment:
    article_id: UUID
    score: float
    label: SentimentLabel
    confidence: float
    evidence: list[str]
    analyzer_name: str = "keyword_sentiment_analyzer"
    analyzer_version: str = "1"
    processed_at: datetime = field(default_factory=utc_now)


@dataclass
class DailyDigest:
    digest_date: date
    timezone: str
    article_count: int
    company_count: int
    event_counts: dict[str, int]
    sentiment_counts: dict[str, int]
    digest_payload: dict[str, object]
    generator_name: str = "daily_digest_generator"
    generator_version: str = "1"
    generated_at: datetime = field(default_factory=utc_now)


@dataclass
class DailyCompanySignal:
    signal_date: date
    company_id: UUID
    ticker: str
    article_count: int
    unique_source_count: int
    weighted_sentiment_score: float
    negative_event_count: int
    event_distribution: dict[str, int]
    novelty_score: float
    source_diversity_score: float
    signal_schema_version: str = "demo-v1"
    generated_at: datetime = field(default_factory=utc_now)


@dataclass
class PipelineRun:
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    per_step_timings: dict[str, float]
    per_step_counts: dict[str, int]
    warnings: list[str]
    errors: list[str]
    configuration_version: str = "demo-v1"
    code_version: str = "0.1.0"
    id: UUID = field(default_factory=new_id)
