from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from finnews.application.ports.repositories import NewsRepository
from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.domain.entities import SourceDefinition, SourceFetchState
from finnews.domain.enums import ProcessingState
from finnews.infrastructure.sources.reviews import (
    SourceReviewError,
    load_source_reviews,
    review_summaries_for_sources,
)


def export_static(repository: NewsRepository, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload = build_static_payload(repository)
    for name, data in payload.items():
        (output / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )


def build_static_payload(repository: NewsRepository) -> dict[str, Any]:
    accounting = build_deduplication_accounting(repository)
    pipeline_runs = repository.list_pipeline_runs()
    articles = [
        article
        for article in repository.list_articles()
        if article.processing_state is ProcessingState.PROCESSED
    ]
    companies = repository.list_companies()
    links = repository.list_links()
    events = repository.list_events()
    sentiments = repository.list_sentiments()
    digests = repository.list_digests()
    signals = repository.list_signals()
    source_definitions = repository.list_source_definitions()
    try:
        source_reviews = load_source_reviews()
    except SourceReviewError:
        source_reviews = []
    review_rows = review_summaries_for_sources(source_definitions, source_reviews)
    review_by_id = {str(row["source_id"]): row for row in review_rows}
    source_states = {state.source_id: state for state in repository.list_source_fetch_states()}
    source_attempts = repository.list_source_fetch_attempts()
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
            "article_count": accounting.metrics["canonical_article_count"],
            "canonical_article_count": accounting.metrics["canonical_article_count"],
            "company_count": len(companies),
            "deduplication": accounting.metrics,
            "deduplication_groups": accounting.grouped_observation_ids,
            "event_distribution": _counts(row["event"] for row in article_rows),
            "sentiment_distribution": _counts(row["sentiment"] for row in article_rows),
            "latest_pipeline": _pipeline_summary(pipeline_runs[-1]) if pipeline_runs else None,
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
        "sources": [
            {
                "source_id": source.source_id,
                "display_name": source.display_name,
                "source_type": source.source_type.value,
                "approval_status": source.review_status.value,
                "enabled": source.enabled,
                "terms_url": source.terms_url,
                "documentation_url": source.documentation_url,
                "content_storage_policy": source.content_storage_policy.value,
                "language": source.language,
                "timezone": source.timezone,
                "risk_classification": source.risk_classification,
                "approved_host_count": len(source.approved_hostnames),
                "synthetic": True,
                "review": review_by_id.get(source.source_id),
            }
            for source in source_definitions
        ],
        "source-reviews": review_rows,
        "source-review-examples": _synthetic_review_examples(),
        "source-health": [
            _source_health_row(source, source_states.get(source.source_id))
            for source in source_definitions
        ],
        "source-fetch-attempts": [
            {
                "id": attempt.id,
                "source_id": attempt.source_id,
                "outcome": attempt.outcome.value,
                "started_at": attempt.started_at,
                "finished_at": attempt.finished_at,
                "http_status": attempt.http_status,
                "item_count": attempt.item_count,
                "new_count": attempt.new_count,
                "duplicate_count": attempt.duplicate_count,
                "rejected_count": attempt.rejected_count,
                "response_byte_count": attempt.response_byte_count,
                "retry_count": attempt.retry_count,
                "error_category": attempt.error_category.value,
                "error_summary": attempt.error_summary,
                "etag_available": attempt.etag_present,
                "last_modified_available": attempt.last_modified_present,
                "dry_run": attempt.dry_run,
            }
            for attempt in source_attempts
        ],
        "source-conditional-examples": [
            {
                "source_id": "example-rss-feed",
                "scenario": "conditional_request",
                "sends_if_none_match": True,
                "sends_if_modified_since": True,
                "stores_raw_body": False,
            },
            {
                "source_id": "example-rss-feed",
                "scenario": "not_modified_304",
                "outcome": "no_change",
                "successful_no_change": True,
            },
            {
                "source_id": "example-announcement-json",
                "scenario": "transient_failure_recovery",
                "max_retries_after_initial": 2,
                "bounded": True,
            },
        ],
    }


def _counts(values: Iterable[object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        key = str(value)
        result[key] = result.get(key, 0) + 1
    return result


def _pipeline_summary(run: object) -> dict[str, object]:
    status = getattr(run, "status", "")
    return {
        "status": getattr(status, "value", str(status)),
        "per_step_counts": getattr(run, "per_step_counts", {}),
        "warnings": getattr(run, "warnings", []),
        "errors": getattr(run, "errors", []),
        "configuration_version": getattr(run, "configuration_version", ""),
        "code_version": getattr(run, "code_version", ""),
    }


def _source_health_row(
    source: SourceDefinition, state: SourceFetchState | None
) -> dict[str, object]:
    return {
        "source_id": source.source_id,
        "display_name": source.display_name,
        "source_type": source.source_type.value,
        "approval_status": source.review_status.value,
        "enabled": source.enabled,
        "health": state.health_status.value if state else "disabled",
        "last_attempted_at": state.last_attempted_at if state else None,
        "last_successful_at": state.last_successful_at if state else None,
        "last_outcome": "not_run" if state is None else "success",
        "last_http_status": state.last_http_status if state else None,
        "last_item_count": state.last_item_count if state else 0,
        "last_response_byte_count": state.last_response_byte_count if state else 0,
        "consecutive_failure_count": state.consecutive_failure_count if state else 0,
        "etag_available": bool(state.etag) if state else False,
        "last_modified_available": bool(state.last_modified) if state else False,
        "last_error_category": state.last_error_category.value if state else "none",
        "synthetic": True,
    }


def _synthetic_review_examples() -> list[dict[str, object]]:
    base = {
        "official_owner": "Synthetic Official Owner",
        "official_source": "Synthetic Official Source",
        "reviewed_at": "2026-06-22",
        "access_cost": "free",
        "authentication_requirement": "none",
        "content_storage_policy": "metadata_only",
        "documentation_url": "https://demo.local/docs",
        "terms_or_policy_url": "https://demo.local/policy",
        "enabled": False,
        "live_smoke_checked_at": None,
        "known_limitations": ["synthetic static-demo review state"],
    }
    return [
        {
            **base,
            "source_id": "synthetic-approved-disabled",
            "review_decision": "approved",
            "live_smoke_status": "not_run",
        },
        {
            **base,
            "source_id": "synthetic-needs-review",
            "review_decision": "needs_review",
            "live_smoke_status": "blocked",
        },
        {
            **base,
            "source_id": "synthetic-rejected",
            "review_decision": "rejected",
            "live_smoke_status": "blocked",
        },
        {
            **base,
            "source_id": "synthetic-smoke-passed",
            "review_decision": "approved",
            "live_smoke_status": "passed",
            "live_smoke_checked_at": "2026-06-22",
        },
        {
            **base,
            "source_id": "synthetic-missing-local-prerequisite",
            "review_decision": "approved",
            "authentication_requirement": "local environment prerequisite",
            "live_smoke_status": "blocked",
        },
    ]


def _json_default(value: object) -> str:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return str(value)
    return str(value)
