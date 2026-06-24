from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceModel(Base):
    __tablename__ = "sources"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    terms_url: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    language_hints: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    ingestion_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    rate_limit: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceDefinitionModel(Base):
    __tablename__ = "source_definitions"
    source_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_hostnames: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    import_format: Mapped[str | None] = mapped_column(String(40))
    terms_url: Mapped[str | None] = mapped_column(Text)
    documentation_url: Mapped[str | None] = mapped_column(Text)
    reviewed_date: Mapped[str | None] = mapped_column(String(40))
    reviewer: Mapped[str | None] = mapped_column(String(120))
    content_storage_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    connect_timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    read_timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    max_response_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_policy: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    minimum_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    cursor_strategy: Mapped[str | None] = mapped_column(String(80))
    field_mapping: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(240), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    risk_classification: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False)


class SourceFetchStateModel(Base):
    __tablename__ = "source_fetch_states"
    __table_args__ = (
        Index("ix_source_fetch_states_health", "health_status"),
        Index("ix_source_fetch_states_next_allowed", "next_allowed_at"),
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_definitions.source_id"), primary_key=True
    )
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    cursor: Mapped[str | None] = mapped_column(Text)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_http_status: Mapped[int | None] = mapped_column(Integer)
    last_response_hash: Mapped[str | None] = mapped_column(String(64))
    last_response_byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    consecutive_failure_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_error_category: Mapped[str] = mapped_column(String(80), nullable=False)
    last_error_summary: Mapped[str] = mapped_column(String(240), nullable=False)
    health_status: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceFetchAttemptModel(Base):
    __tablename__ = "source_fetch_attempts"
    __table_args__ = (
        Index("ix_source_fetch_attempts_source_started", "source_id", "started_at"),
        Index("ix_source_fetch_attempts_outcome", "outcome"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_definitions.source_id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    response_byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    response_hash: Mapped[str | None] = mapped_column(String(64))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_category: Mapped[str] = mapped_column(String(80), nullable=False)
    error_summary: Mapped[str] = mapped_column(String(240), nullable=False)
    etag_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_modified_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cursor_before: Mapped[str | None] = mapped_column(Text)
    cursor_after: Mapped[str | None] = mapped_column(Text)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False)


class NlpModelRegistryModel(Base):
    __tablename__ = "nlp_model_registry"
    __table_args__ = (
        Index("ix_nlp_model_registry_task_status", "task", "status"),
        Index("ix_nlp_model_registry_dataset", "dataset_id", "dataset_version"),
    )
    model_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    task: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model_kind: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    split_hashes: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    label_set: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    calibration: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    config_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NlpEvaluationRunModel(Base):
    __tablename__ = "nlp_evaluation_runs"
    __table_args__ = (
        Index("ix_nlp_evaluation_runs_task_split", "task", "split_name"),
        Index("ix_nlp_evaluation_runs_model", "model_id"),
    )
    evaluation_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("nlp_model_registry.model_id"), nullable=False)
    task: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    split_name: Mapped[str] = mapped_column(String(40), nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    slice_metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    calibration: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    error_analysis: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    selection_procedure: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IngestionRunModel(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor_before: Mapped[str | None] = mapped_column(Text)
    cursor_after: Mapped[str | None] = mapped_column(Text)
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exact_duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    near_duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    code_version: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(80), nullable=False)


class RawArticleModel(Base):
    __tablename__ = "raw_articles"
    __table_args__ = (
        UniqueConstraint("source_id", "source_article_id"),
        Index("ix_raw_source", "source_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    source_article_id: Mapped[str] = mapped_column(String(240), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    source_summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(16), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    normalized_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_run_id: Mapped[UUID] = mapped_column(ForeignKey("ingestion_runs.id"), nullable=False)


class ArticleModel(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("exact_content_hash"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_state", "processing_state"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_raw_article_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_articles.id"), nullable=False
    )
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_summary: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_market_date: Mapped[date] = mapped_column(Date, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    exact_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_state: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArticleDuplicateModel(Base):
    __tablename__ = "article_duplicates"
    candidate_article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    canonical_article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    duplicate_type: Mapped[str] = mapped_column(String(40), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    algorithm_name: Mapped[str] = mapped_column(String(120), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ObservationDispositionModel(Base):
    __tablename__ = "observation_dispositions"
    __table_args__ = (
        Index("ix_observation_dispositions_canonical", "canonical_article_id"),
        Index("ix_observation_dispositions_disposition", "disposition"),
    )
    observation_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    source_key: Mapped[str] = mapped_column(String(120), nullable=False)
    disposition: Mapped[str] = mapped_column(String(40), nullable=False)
    canonical_observation_id: Mapped[str | None] = mapped_column(String(240))
    canonical_article_id: Mapped[UUID | None] = mapped_column(ForeignKey("articles.id"))
    duplicate_type: Mapped[str | None] = mapped_column(String(40))
    similarity_score: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_group: Mapped[str] = mapped_column(String(80), nullable=False)


class CompanyModel(Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("ticker", "exchange"),
        Index("ix_companies_ticker", "ticker"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(240), nullable=False)
    short_name: Mapped[str] = mapped_column(String(160), nullable=False)
    sector: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CompanyAliasModel(Base):
    __tablename__ = "company_aliases"
    __table_args__ = (UniqueConstraint("company_id", "normalized_alias"),)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    alias: Mapped[str] = mapped_column(String(240), primary_key=True)
    normalized_alias: Mapped[str] = mapped_column(String(240), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(80), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class ArticleCompanyLinkModel(Base):
    __tablename__ = "article_company_links"
    __table_args__ = (Index("ix_article_company_links_company", "company_id"),)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    matched_alias: Mapped[str] = mapped_column(String(240), nullable=False)
    evidence_text_span: Mapped[str] = mapped_column(Text, nullable=False)
    linker_name: Mapped[str] = mapped_column(String(120), nullable=False)
    linker_version: Mapped[str] = mapped_column(String(40), nullable=False)


class ArticleEventModel(Base):
    __tablename__ = "article_events"
    __table_args__ = (Index("ix_article_events_type", "event_type"),)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    classifier_name: Mapped[str] = mapped_column(String(120), nullable=False)
    classifier_version: Mapped[str] = mapped_column(String(40), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArticleSentimentModel(Base):
    __tablename__ = "article_sentiments"
    __table_args__ = (Index("ix_article_sentiments_label", "label"),)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    analyzer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    analyzer_version: Mapped[str] = mapped_column(String(40), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DailyDigestModel(Base):
    __tablename__ = "daily_digests"
    digest_date: Mapped[date] = mapped_column(Date, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(80), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    company_count: Mapped[int] = mapped_column(Integer, nullable=False)
    event_counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    sentiment_counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    digest_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    generator_name: Mapped[str] = mapped_column(String(120), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(40), nullable=False)


class DailyCompanySignalModel(Base):
    __tablename__ = "daily_company_signals"
    __table_args__ = (Index("ix_daily_company_signals_date", "signal_date"),)
    signal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weighted_sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    negative_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    event_distribution: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    novelty_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_diversity_score: Mapped[float] = mapped_column(Float, nullable=False)
    signal_schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineRunModel(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    per_step_timings: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    per_step_counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(80), nullable=False)
    code_version: Mapped[str] = mapped_column(String(80), nullable=False)


class ResearchCalendarModel(Base):
    __tablename__ = "research_calendars"
    __table_args__ = (
        UniqueConstraint("calendar_id", "calendar_version"),
        Index("ix_research_calendars_calendar", "calendar_id", "calendar_version"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    calendar_id: Mapped[str] = mapped_column(String(160), nullable=False)
    calendar_version: Mapped[str] = mapped_column(String(80), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    calendar_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ResearchSessionModel(Base):
    __tablename__ = "research_sessions"
    __table_args__ = (
        UniqueConstraint("calendar_id", "calendar_version", "session_date"),
        UniqueConstraint("calendar_id", "calendar_version", "sequence"),
        Index(
            "ix_research_sessions_calendar_sequence",
            "calendar_id",
            "calendar_version",
            "sequence",
        ),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    calendar_id: Mapped[str] = mapped_column(String(160), nullable=False)
    calendar_version: Mapped[str] = mapped_column(String(80), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    break_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    break_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    special_session: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ResearchExportRunModel(Base):
    __tablename__ = "research_export_runs"
    __table_args__ = (
        UniqueConstraint(
            "export_id",
            "contract_version",
            "config_hash",
            "calendar_hash",
            "package_hash",
        ),
        Index("ix_research_export_runs_export", "export_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    export_id: Mapped[str] = mapped_column(String(180), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    calendar_id: Mapped[str] = mapped_column(String(160), nullable=False)
    calendar_version: Mapped[str] = mapped_column(String(80), nullable=False)
    calendar_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cutoff_policy: Mapped[str] = mapped_column(String(80), nullable=False)
    windows: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    company_universe_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    package_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    counts: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    quality_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    leakage_status: Mapped[str] = mapped_column(String(40), nullable=False)
    leakage_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchFeatureRowModel(Base):
    __tablename__ = "research_feature_rows"
    __table_args__ = (
        UniqueConstraint("export_id", "logical_key"),
        Index("ix_research_feature_rows_lookup", "export_id", "ticker", "session_date"),
        Index("ix_research_feature_rows_window", "window_sessions"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    export_id: Mapped[str] = mapped_column(String(180), nullable=False)
    logical_key: Mapped[str] = mapped_column(Text, nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    decision_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    window_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    features: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    lineage_row_id: Mapped[str] = mapped_column(String(80), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ResearchLineageRowModel(Base):
    __tablename__ = "research_lineage_rows"
    __table_args__ = (
        UniqueConstraint("export_id", "lineage_row_id"),
        Index("ix_research_lineage_export", "export_id"),
        Index("ix_research_lineage_article", "canonical_article_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    export_id: Mapped[str] = mapped_column(String(180), nullable=False)
    lineage_row_id: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_row_key: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_article_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    source_id: Mapped[str | None] = mapped_column(String(160))
    company_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    information_available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inclusion_reason: Mapped[str] = mapped_column(String(80), nullable=False)
    event_provider: Mapped[str | None] = mapped_column(String(120))
    event_model_version: Mapped[str | None] = mapped_column(String(80))
    sentiment_provider: Mapped[str | None] = mapped_column(String(120))
    sentiment_model_version: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AssetModel(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_class_region", "asset_class", "country_region"),
        Index("ix_assets_status", "status"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(60), nullable=False)
    canonical_symbol: Mapped[str | None] = mapped_column(String(80))
    home_venue: Mapped[str | None] = mapped_column(String(80))
    country_region: Mapped[str] = mapped_column(String(80), nullable=False)
    base_currency: Mapped[str | None] = mapped_column(String(16))
    quote_currency: Mapped[str | None] = mapped_column(String(16))
    parent_asset_id: Mapped[str | None] = mapped_column(String(120))
    expiry: Mapped[date | None] = mapped_column(Date)
    contract_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)


class SymbolAliasModel(Base):
    __tablename__ = "asset_symbol_aliases"
    __table_args__ = (
        UniqueConstraint("asset_id", "namespace", "symbol", "provider", "provider_version"),
        Index("ix_asset_alias_namespace_symbol", "namespace", "normalized_symbol", "active"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_symbol: Mapped[str] = mapped_column(String(240), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class ProviderSymbolModel(Base):
    __tablename__ = "asset_provider_symbols"
    __table_args__ = (
        UniqueConstraint("asset_id", "namespace", "provider", "symbol"),
        Index("ix_provider_symbols_lookup", "namespace", "provider", "symbol", "active"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    symbol: Mapped[str] = mapped_column(String(240), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class BrokerSymbolMappingModel(Base):
    __tablename__ = "broker_symbol_mappings"
    __table_args__ = (
        UniqueConstraint("broker_profile_id", "mt5_symbol", "enabled"),
        Index("ix_broker_symbol_mappings_asset", "asset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    broker_profile_id: Mapped[str] = mapped_column(String(120), nullable=False)
    mt5_symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    local_note: Mapped[str | None] = mapped_column(Text)


class AssetRelationshipModel(Base):
    __tablename__ = "asset_relationships"
    __table_args__ = (
        UniqueConstraint("relationship_id"),
        Index("ix_asset_relationships_source", "source_asset_id"),
        Index("ix_asset_relationships_target", "target_asset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    relationship_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False)
    direction: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class CrossAssetEventModel(Base):
    __tablename__ = "cross_asset_events"
    __table_args__ = (
        UniqueConstraint("event_id"),
        Index("ix_cross_asset_events_family_time", "event_family", "information_available_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_family: Mapped[str] = mapped_column(String(100), nullable=False)
    event_subtype: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    information_available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    affected_region: Mapped[str] = mapped_column(String(80), nullable=False)
    relevant_currency: Mapped[str | None] = mapped_column(String(16))
    source_provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    uncertainty_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    duplicate_of_event_id: Mapped[str | None] = mapped_column(String(120))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AssetImpactHypothesisModel(Base):
    __tablename__ = "asset_impact_hypotheses"
    __table_args__ = (
        UniqueConstraint("impact_id"),
        Index("ix_asset_impacts_asset_event", "asset_id", "event_id"),
        Index("ix_asset_impacts_direction_horizon", "direction", "horizon"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    impact_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(40), nullable=False)
    impact_strength: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    horizon: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    information_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(160))
    uncertainty_reason: Mapped[str | None] = mapped_column(String(160))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MarketSignalCandidateModel(Base):
    __tablename__ = "market_signal_candidates"
    __table_args__ = (
        UniqueConstraint("signal_id"),
        UniqueConstraint("idempotency_key"),
        Index("ix_market_signals_asset_status", "asset_id", "status"),
        Index("ix_market_signals_horizon_direction", "horizon", "direction"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False)
    impact_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    direction: Mapped[str] = mapped_column(String(40), nullable=False)
    horizon: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float)
    information_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    quality_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risk_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SignalPublicationRunModel(Base):
    __tablename__ = "signal_publication_runs"
    __table_args__ = (UniqueConstraint("run_id"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[str] = mapped_column(String(120), nullable=False)
    contract_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_hashes: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class OfficialDatasetModel(Base):
    __tablename__ = "official_datasets"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    documentation_url: Mapped[str] = mapped_column(Text, nullable=False)
    revision_policy: Mapped[str] = mapped_column(String(120), nullable=False)
    frequency: Mapped[str] = mapped_column(String(40), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(80))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class OfficialSeriesProfileModel(Base):
    __tablename__ = "official_series_profiles"
    __table_args__ = (
        UniqueConstraint("profile_id"),
        Index("ix_official_series_source_dataset", "source_id", "dataset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[str] = mapped_column(String(160), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    query: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    dimensions: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(80))
    frequency: Mapped[str] = mapped_column(String(40), nullable=False)
    seasonal_adjustment: Mapped[str | None] = mapped_column(String(80))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class OfficialObservationModel(Base):
    __tablename__ = "official_observations"
    __table_args__ = (
        Index("ix_official_observations_profile_period", "profile_id", "period_start"),
        Index("ix_official_observations_dataset", "dataset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    observation_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(160), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    dimensions: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    information_available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class OfficialObservationRevisionModel(Base):
    __tablename__ = "official_observation_revisions"
    __table_args__ = (
        UniqueConstraint("observation_key", "revision_number"),
        Index("ix_official_revisions_available", "information_available_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    observation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    information_available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class OfficialDataReleaseRunModel(Base):
    __tablename__ = "official_data_release_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    release_run_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    profile_count: Mapped[int] = mapped_column(Integer, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    new_revision_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    no_persist_live: Mapped[bool] = mapped_column(Boolean, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RegulatoryDocumentModel(Base):
    __tablename__ = "regulatory_documents"
    __table_args__ = (Index("ix_regulatory_documents_publication", "publication_date"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    agencies: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    cfr_references: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    rin: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    html_url: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    information_available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class SeriesAssetAssociationModel(Base):
    __tablename__ = "series_asset_associations"
    __table_args__ = (
        UniqueConstraint("association_id"),
        Index("ix_series_asset_profile", "profile_id"),
        Index("ix_series_asset_asset", "asset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    association_id: Mapped[str] = mapped_column(String(120), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(120), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class OfficialReleaseEventModel(Base):
    __tablename__ = "official_release_events"
    __table_args__ = (
        UniqueConstraint("event_id"),
        Index("ix_official_release_events_source", "source_id"),
        Index("ix_official_release_events_available", "information_available_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    profile_id: Mapped[str | None] = mapped_column(String(160))
    document_id: Mapped[str | None] = mapped_column(String(120))
    event_family: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    information_available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revision_number: Mapped[int | None] = mapped_column(Integer)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MarketDataPackageModel(Base):
    __tablename__ = "market_data_packages"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    package_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    contract_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    asset_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bar_count: Mapped[int] = mapped_column(Integer, nullable=False)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_imported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    live_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)


class MarketBarSeriesModel(Base):
    __tablename__ = "market_bar_series"
    __table_args__ = (
        UniqueConstraint("series_id"),
        UniqueConstraint("package_id", "asset_id", "provider_symbol", "granularity"),
        Index("ix_market_bar_series_asset", "asset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    series_id: Mapped[str] = mapped_column(String(160), nullable=False)
    package_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(160), nullable=False)
    granularity: Mapped[str] = mapped_column(String(40), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)


class MarketBarModel(Base):
    __tablename__ = "market_bars"
    __table_args__ = (
        Index("ix_market_bars_asset_time", "asset_id", "bar_start_at"),
        Index("ix_market_bars_scenario", "scenario_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bar_id: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    series_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    session_date: Mapped[date | None] = mapped_column(Date)
    bar_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bar_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    market_state: Mapped[str] = mapped_column(String(80), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class MarketBarRevisionModel(Base):
    __tablename__ = "market_bar_revisions"
    __table_args__ = (
        UniqueConstraint("bar_id", "revision_number"),
        Index("ix_market_bar_revisions_available", "available_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bar_id: Mapped[str] = mapped_column(String(240), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class MarketReactionStudyModel(Base):
    __tablename__ = "market_reaction_studies"
    __table_args__ = (
        UniqueConstraint("study_id"),
        Index("ix_market_reaction_studies_scenario", "scenario_id"),
        Index("ix_market_reaction_studies_asset", "asset_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    study_id: Mapped[str] = mapped_column(String(240), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False)
    impact_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_family: Mapped[str] = mapped_column(String(100), nullable=False)
    decision_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reaction_window: Mapped[str] = mapped_column(String(40), nullable=False)
    bar_coverage: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    benchmark_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    abnormal_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    excluded_reason: Mapped[str | None] = mapped_column(String(120))
    quality_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MarketReactionLabelModel(Base):
    __tablename__ = "market_reaction_labels"
    __table_args__ = (
        UniqueConstraint("label_id"),
        Index("ix_market_reaction_labels_scenario", "scenario_id"),
        Index("ix_market_reaction_labels_label", "label"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    label_id: Mapped[str] = mapped_column(String(260), nullable=False)
    study_id: Mapped[str] = mapped_column(String(240), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    horizon: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    threshold_version: Mapped[str] = mapped_column(String(80), nullable=False)
    abnormal_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    coverage: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    point_in_time_evidence: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SignalQualityRunModel(Base):
    __tablename__ = "signal_quality_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)


class SignalQualityMetricModel(Base):
    __tablename__ = "signal_quality_metrics"
    __table_args__ = (
        UniqueConstraint("metric_id"),
        Index("ix_signal_quality_metrics_scenario", "scenario_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    metric_id: Mapped[str] = mapped_column(String(240), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    slice_type: Mapped[str] = mapped_column(String(80), nullable=False)
    slice_value: Mapped[str] = mapped_column(String(160), nullable=False)
    evaluated_signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    directional_consistency_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    opposite_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    muted_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SignalErrorCaseModel(Base):
    __tablename__ = "signal_error_cases"
    __table_args__ = (
        UniqueConstraint("error_case_id"),
        Index("ix_signal_error_cases_scenario", "scenario_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    error_case_id: Mapped[str] = mapped_column(String(240), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    signal_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_family: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_direction: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_label: Mapped[str] = mapped_column(String(80), nullable=False)
    abnormal_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    horizon: Mapped[str] = mapped_column(String(40), nullable=False)
    regime: Mapped[str] = mapped_column(String(80), nullable=False)
    error_category: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
