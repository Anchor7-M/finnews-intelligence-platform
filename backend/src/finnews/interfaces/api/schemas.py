from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ErrorEnvelope(BaseModel):
    error: dict[str, str]


class ArticleResponse(BaseModel):
    id: UUID
    title: str
    summary: str
    language: str
    published_at: datetime
    market_date: date
    url: str
    source_key: str
    source_name: str
    processing_state: str
    tickers: list[str]
    event: str
    sentiment: str


class ArticleListResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    limit: int
    offset: int


class CompanyResponse(BaseModel):
    id: UUID
    ticker: str
    exchange: str
    legal_name: str
    short_name: str
    sector: str
    active: bool


class DigestResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    digest_date: date
    timezone: str
    article_count: int
    company_count: int
    event_counts: dict[str, int]
    sentiment_counts: dict[str, int]
    payload: dict[str, object]


class SignalResponse(BaseModel):
    signal_date: date
    ticker: str
    article_count: int
    unique_source_count: int
    weighted_sentiment_score: float
    negative_event_count: int
    event_distribution: dict[str, int]
    novelty_score: float
    source_diversity_score: float
    schema_version: str


class OverviewResponse(BaseModel):
    synthetic: bool
    not_investment_advice: bool
    article_count: int
    company_count: int
    event_distribution: dict[str, int]
    sentiment_distribution: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    profile: str
