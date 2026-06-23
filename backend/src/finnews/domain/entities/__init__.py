from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from finnews.domain.enums import (
    AssetClass,
    AssetStatus,
    CrossAssetEventFamily,
    DuplicateType,
    EventType,
    FetchOutcome,
    ImpactDirection,
    ImpactHorizon,
    ImpactRelationshipType,
    IngestionPolicy,
    ProcessingState,
    ResearchSignalStatus,
    RunStatus,
    SentimentLabel,
    SourceApprovalStatus,
    SourceErrorCategory,
    SourceHealthStatus,
    SourceType,
    SymbolNamespace,
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


@dataclass(frozen=True)
class SourceRetryPolicy:
    max_retries: int = 2
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    display_name: str
    source_type: SourceType
    approved_hostnames: list[str]
    review_status: SourceApprovalStatus
    enabled: bool = False
    base_url: str | None = None
    import_format: str | None = None
    terms_url: str | None = None
    documentation_url: str | None = None
    reviewed_date: str | None = None
    reviewer: str | None = None
    content_storage_policy: IngestionPolicy = IngestionPolicy.METADATA_ONLY
    provenance_required: bool = True
    language: str = "en"
    timezone: str = "UTC"
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000
    retry_policy: SourceRetryPolicy = field(default_factory=SourceRetryPolicy)
    minimum_interval_seconds: int = 3600
    cursor_strategy: str | None = None
    field_mapping: dict[str, str] = field(default_factory=dict)
    user_agent: str = "finnews-intelligence-platform/0.1 (+local research)"
    notes: str = ""
    risk_classification: str = "medium"
    adapter_version: str = "m1a-v1"
    review_evidence_id: str | None = None
    source_config_sha256: str | None = None
    endpoint_template: str | None = None
    parameter_schema: dict[str, str] = field(default_factory=dict)
    user_agent_env_var: str | None = None
    user_agent_template: str | None = None
    max_items_per_smoke: int = 5

    @property
    def fetch_allowed(self) -> bool:
        return self.enabled and self.review_status is SourceApprovalStatus.APPROVED


@dataclass
class SourceFetchState:
    source_id: str
    etag: str | None = None
    last_modified: str | None = None
    cursor: str | None = None
    last_attempted_at: datetime | None = None
    last_successful_at: datetime | None = None
    next_allowed_at: datetime | None = None
    last_http_status: int | None = None
    last_response_hash: str | None = None
    last_response_byte_count: int = 0
    last_item_count: int = 0
    consecutive_failure_count: int = 0
    last_error_category: SourceErrorCategory = SourceErrorCategory.NONE
    last_error_summary: str = ""
    health_status: SourceHealthStatus = SourceHealthStatus.UNKNOWN
    adapter_version: str = "m1a-v1"
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class SourceFetchAttempt:
    source_id: str
    outcome: FetchOutcome
    started_at: datetime
    finished_at: datetime
    id: UUID = field(default_factory=new_id)
    http_status: int | None = None
    item_count: int = 0
    new_count: int = 0
    duplicate_count: int = 0
    rejected_count: int = 0
    response_byte_count: int = 0
    response_hash: str | None = None
    retry_count: int = 0
    duration_ms: int = 0
    error_category: SourceErrorCategory = SourceErrorCategory.NONE
    error_summary: str = ""
    etag_present: bool = False
    last_modified_present: bool = False
    cursor_before: str | None = None
    cursor_after: str | None = None
    dry_run: bool = False


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
class NlpModelRegistryEntry:
    model_id: str
    task: str
    provider: str
    model_kind: str
    status: str
    dataset_id: str
    dataset_version: str
    dataset_sha256: str
    split_hashes: dict[str, str]
    label_set: list[str]
    metrics: dict[str, object]
    calibration: dict[str, object]
    artifact_sha256: str
    artifact_size_bytes: int
    manifest_sha256: str
    config_sha256: str
    artifact_uri: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class NlpEvaluationRun:
    evaluation_id: str
    model_id: str
    task: str
    dataset_id: str
    dataset_version: str
    dataset_sha256: str
    split_name: str
    metrics: dict[str, object]
    slice_metrics: dict[str, object]
    calibration: dict[str, object]
    error_analysis: dict[str, object]
    selection_procedure: dict[str, object]
    evaluated_at: datetime = field(default_factory=utc_now)


@dataclass
class ResearchCalendar:
    calendar_id: str
    calendar_version: str
    timezone: str
    calendar_hash: str
    provenance: dict[str, object]
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class ResearchSession:
    calendar_id: str
    calendar_version: str
    session_date: date
    open_at: datetime
    break_start_at: datetime
    break_end_at: datetime
    close_at: datetime
    sequence: int
    special_session: bool = False
    id: UUID = field(default_factory=new_id)


@dataclass
class ResearchExportRun:
    export_id: str
    contract_version: str
    config_hash: str
    calendar_id: str
    calendar_version: str
    calendar_hash: str
    cutoff_policy: str
    windows: list[int]
    company_universe_hash: str
    package_hash: str
    status: str
    counts: dict[str, object]
    quality_summary: dict[str, object]
    leakage_status: str
    leakage_hash: str
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ResearchFeatureRow:
    export_id: str
    logical_key: str
    session_date: date
    decision_cutoff_at: datetime
    ticker: str
    company_id: UUID
    window_sessions: int
    feature_schema_version: str
    features: dict[str, object]
    lineage_row_id: str
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class ResearchLineageRow:
    export_id: str
    lineage_row_id: str
    feature_row_key: str
    canonical_article_id: UUID | None
    source_id: str | None
    company_id: UUID | None
    information_available_at: datetime | None
    decision_cutoff_at: datetime | None
    inclusion_reason: str
    event_provider: str | None = None
    event_model_version: str | None = None
    sentiment_provider: str | None = None
    sentiment_model_version: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass(frozen=True)
class Venue:
    venue_id: str
    display_name: str
    country_region: str
    timezone: str
    synthetic: bool = True


@dataclass
class Asset:
    asset_id: str
    display_name: str
    asset_class: AssetClass
    canonical_symbol: str | None
    home_venue: str | None
    country_region: str
    base_currency: str | None = None
    quote_currency: str | None = None
    parent_asset_id: str | None = None
    expiry: date | None = None
    contract_metadata: dict[str, object] = field(default_factory=dict)
    status: AssetStatus = AssetStatus.ACTIVE
    synthetic: bool = True
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = "cross-asset-v1"
    id: UUID = field(default_factory=new_id)


@dataclass
class SymbolAlias:
    asset_id: str
    namespace: SymbolNamespace
    symbol: str
    normalized_symbol: str
    provider: str
    provider_version: str
    active: bool = True
    confidence: float = 1.0
    provenance: dict[str, object] = field(default_factory=dict)
    valid_from: date | None = None
    valid_to: date | None = None
    id: UUID = field(default_factory=new_id)


@dataclass
class ProviderSymbol:
    asset_id: str
    namespace: SymbolNamespace
    provider: str
    symbol: str
    provider_version: str
    active: bool = True
    provenance: dict[str, object] = field(default_factory=dict)
    id: UUID = field(default_factory=new_id)


@dataclass
class BrokerSymbolMapping:
    asset_id: str
    broker_profile_id: str
    mt5_symbol: str
    enabled: bool
    provenance: dict[str, object] = field(default_factory=dict)
    local_note: str | None = None
    id: UUID = field(default_factory=new_id)


@dataclass
class AssetRelationship:
    relationship_id: str
    source_asset_id: str
    target_asset_id: str
    relationship_type: ImpactRelationshipType
    direction: str
    confidence: float | None
    active: bool = True
    provenance: dict[str, object] = field(default_factory=dict)
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class CrossAssetEvent:
    event_id: str
    event_family: CrossAssetEventFamily
    event_subtype: str
    description: str
    information_available_at: datetime
    affected_region: str
    relevant_currency: str | None
    source_provenance: dict[str, object]
    provider: str
    provider_version: str
    confidence: float | None
    uncertainty_flags: list[str] = field(default_factory=list)
    duplicate_of_event_id: str | None = None
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class AssetImpactHypothesis:
    impact_id: str
    event_id: str
    asset_id: str
    relationship_type: ImpactRelationshipType
    direction: ImpactDirection
    impact_strength: float
    confidence: float | None
    horizon: ImpactHorizon
    evidence_codes: list[str]
    provider: str
    provider_version: str
    information_cutoff_at: datetime
    created_at: datetime
    expires_at: datetime | None
    status: str
    rejection_reason: str | None = None
    uncertainty_reason: str | None = None
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class MarketSignalCandidate:
    signal_id: str
    impact_id: str
    event_id: str
    asset_id: str
    direction: ImpactDirection
    horizon: ImpactHorizon
    status: ResearchSignalStatus
    confidence: float | None
    score: float | None
    information_cutoff_at: datetime
    generated_at: datetime
    expires_at: datetime | None
    provider: str
    provider_version: str
    evidence_codes: list[str]
    quality_tags: list[str]
    risk_tags: list[str]
    payload_hash: str
    idempotency_key: str
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


@dataclass
class SignalPublicationRun:
    run_id: str
    contract_name: str
    contract_version: str
    generated_at: datetime
    count: int
    status: str
    manifest_hash: str
    file_hashes: dict[str, str]
    synthetic: bool = True
    id: UUID = field(default_factory=new_id)


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
