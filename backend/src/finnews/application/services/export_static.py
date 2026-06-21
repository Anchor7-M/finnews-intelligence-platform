from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from finnews.application.ports.repositories import NewsRepository


def export_static(repository: NewsRepository, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload = build_static_payload(repository)
    for name, data in payload.items():
        (output / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )


def build_static_payload(repository: NewsRepository) -> dict[str, Any]:
    articles = repository.list_articles()
    companies = repository.list_companies()
    links = repository.list_links()
    events = repository.list_events()
    sentiments = repository.list_sentiments()
    digests = repository.list_digests()
    signals = repository.list_signals()
    event_by_article = {item.article_id: item for item in events}
    sentiment_by_article = {item.article_id: item for item in sentiments}
    links_by_article: dict[UUID, list[str]] = {}
    ticker_by_id = {item.id: item.ticker for item in companies}
    for link in links:
        links_by_article.setdefault(link.article_id, []).append(
            ticker_by_id.get(link.company_id, "UNKNOWN")
        )
    article_rows = [
        {
            "id": article.id,
            "title": article.normalized_title,
            "summary": article.normalized_summary,
            "language": article.language,
            "published_at": article.published_at,
            "market_date": article.local_market_date,
            "url": article.canonical_url,
            "source_key": article.source_key,
            "source_name": article.source_name,
            "processing_state": article.processing_state.value,
            "tickers": links_by_article.get(article.id, []),
            "event": event_by_article[article.id].event_type.value
            if article.id in event_by_article
            else "other",
            "sentiment": sentiment_by_article[article.id].label.value
            if article.id in sentiment_by_article
            else "neutral",
        }
        for article in articles
    ]
    return {
        "overview": {
            "synthetic": True,
            "not_investment_advice": True,
            "article_count": len(articles),
            "company_count": len(companies),
            "event_distribution": _counts(row["event"] for row in article_rows),
            "sentiment_distribution": _counts(row["sentiment"] for row in article_rows),
            "latest_pipeline": repository.list_pipeline_runs()[-1]
            if repository.list_pipeline_runs()
            else None,
        },
        "articles": article_rows,
        "companies": [
            {
                "id": company.id,
                "ticker": company.ticker,
                "exchange": company.exchange,
                "legal_name": company.legal_name,
                "short_name": company.short_name,
                "sector": company.sector,
                "active": company.active,
            }
            for company in companies
        ],
        "digests": [
            {
                "digest_date": digest.digest_date,
                "timezone": digest.timezone,
                "article_count": digest.article_count,
                "company_count": digest.company_count,
                "event_counts": digest.event_counts,
                "sentiment_counts": digest.sentiment_counts,
                "payload": digest.digest_payload,
            }
            for digest in digests
        ],
        "signals": [
            {
                "signal_date": signal.signal_date,
                "ticker": signal.ticker,
                "article_count": signal.article_count,
                "unique_source_count": signal.unique_source_count,
                "weighted_sentiment_score": signal.weighted_sentiment_score,
                "negative_event_count": signal.negative_event_count,
                "event_distribution": signal.event_distribution,
                "novelty_score": signal.novelty_score,
                "source_diversity_score": signal.source_diversity_score,
                "schema_version": signal.signal_schema_version,
            }
            for signal in signals
        ],
    }


def _counts(values: Iterable[object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        key = str(value)
        result[key] = result.get(key, 0) + 1
    return result


def _json_default(value: object) -> str:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return str(value)
    return str(value)
