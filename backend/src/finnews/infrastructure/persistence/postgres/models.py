from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
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
