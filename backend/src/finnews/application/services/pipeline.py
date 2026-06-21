from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from uuid import UUID

from finnews.application.ports.repositories import NewsRepository
from finnews.domain.entities import (
    Article,
    ArticleCompanyLink,
    ArticleDuplicate,
    ArticleEvent,
    ArticleSentiment,
    Company,
    DailyCompanySignal,
    DailyDigest,
    IngestionRun,
    PipelineRun,
    RawArticle,
    Source,
    SourceRecord,
)
from finnews.domain.enums import DuplicateType, ProcessingState, RunStatus, SentimentLabel
from finnews.domain.value_objects import utc_now
from finnews.infrastructure.nlp.deduplication import find_near_duplicate
from finnews.infrastructure.nlp.events import classify_event
from finnews.infrastructure.nlp.linking import link_companies
from finnews.infrastructure.nlp.sentiment import analyze_sentiment
from finnews.infrastructure.normalization import (
    deterministic_hash,
    market_date,
    normalize_display_text,
    normalize_url,
    parse_timestamp,
    validate_language,
)
from finnews.settings import Settings


class NewsPipeline:
    def __init__(self, repository: NewsRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def load_companies(self, path: Path) -> int:
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for item in data:
            company = Company(
                ticker=str(item["ticker"]),
                exchange=str(item["exchange"]),
                legal_name=str(item["legal_name"]),
                short_name=str(item["short_name"]),
                sector=str(item["sector"]),
            )
            aliases = [str(alias) for alias in item.get("aliases", [])]
            self.repository.upsert_company(company, aliases)
            count += 1
        return count

    def ingest_records(self, records: Iterable[SourceRecord]) -> dict[str, int]:
        counts = Counter[str]()
        for record in records:
            counts["fetched"] += 1
            source = self.repository.upsert_source(
                Source(
                    source_key=record.source_key,
                    display_name=record.source_name,
                    source_type=record.source_type,
                )
            )
            run = self.repository.add_ingestion_run(IngestionRun(source_id=source.id))
            try:
                language = validate_language(record.language)
                published = parse_timestamp(record.published_at)
                url = normalize_url(record.url)
                title = normalize_display_text(record.title, 240)
                summary = normalize_display_text(record.summary, 800)
                if not title:
                    raise ValueError("title is required")
                content_hash = deterministic_hash(title, summary, language)
                raw = RawArticle(
                    source_id=source.id,
                    source_article_id=record.article_id,
                    canonical_url=url,
                    source_title=title,
                    source_summary=summary,
                    source_language=language,
                    published_at=published,
                    raw_metadata=record.raw_metadata,
                    normalized_content_hash=content_hash,
                    ingestion_run_id=run.id,
                )
                accepted_raw = self.repository.add_raw_article(raw)
                if accepted_raw is None:
                    counts["exact_duplicate"] += 1
                    run.exact_duplicate_count += 1
                    run.status = RunStatus.COMPLETED
                    run.finished_at = utc_now()
                    continue
                article = Article(
                    canonical_raw_article_id=accepted_raw.id,
                    normalized_title=title,
                    normalized_summary=summary,
                    language=language,
                    published_at=published,
                    local_market_date=market_date(published, self.settings.market_timezone),
                    canonical_url=url,
                    exact_content_hash=content_hash,
                    source_key=source.source_key,
                    source_name=source.display_name,
                )
                existing = self.repository.add_article(article)
                if existing is None:
                    counts["exact_duplicate"] += 1
                    run.exact_duplicate_count += 1
                    run.status = RunStatus.COMPLETED
                    run.finished_at = utc_now()
                    continue
                near = find_near_duplicate(
                    article,
                    [item for item in self.repository.list_articles() if item.id != article.id],
                    self.settings.near_duplicate_threshold,
                    self.settings.near_duplicate_window_hours,
                    self.settings.near_duplicate_max_candidates,
                )
                if near:
                    canonical, score = near
                    article.processing_state = ProcessingState.DUPLICATE
                    self.repository.add_duplicate(
                        ArticleDuplicate(
                            candidate_article_id=article.id,
                            canonical_article_id=canonical.id,
                            duplicate_type=DuplicateType.NEAR,
                            similarity_score=round(score, 4),
                            algorithm_name="tfidf_cosine",
                        )
                    )
                    counts["near_duplicate"] += 1
                    run.near_duplicate_count += 1
                counts["accepted"] += 1
                run.accepted_count += 1
                run.status = RunStatus.COMPLETED
                run.finished_at = utc_now()
            except Exception as exc:  # validation quarantine, not batch failure
                counts["rejected"] += 1
                run.rejected_count += 1
                run.status = RunStatus.FAILED
                run.error_summary = str(exc)
                run.finished_at = utc_now()
        return dict(counts)

    def process_articles(self) -> dict[str, int]:
        counts = Counter[str]()
        aliases = self.repository.list_aliases()
        for article in self.repository.list_articles():
            links = link_companies(article, aliases)
            self.repository.replace_article_links(article.id, links)
            self.repository.replace_article_event(classify_event(article))
            self.repository.replace_article_sentiment(analyze_sentiment(article))
            counts["processed"] += 1
        return dict(counts)

    def generate_digest(self, digest_date: date) -> DailyDigest:
        articles = [
            item
            for item in self.repository.list_articles()
            if item.local_market_date == digest_date
        ]
        article_ids = {item.id for item in articles}
        links = [link for link in self.repository.list_links() if link.article_id in article_ids]
        events = [
            event for event in self.repository.list_events() if event.article_id in article_ids
        ]
        sentiments = [
            sentiment
            for sentiment in self.repository.list_sentiments()
            if sentiment.article_id in article_ids
        ]
        event_counts = Counter(event.event_type.value for event in events)
        sentiment_counts = Counter(sentiment.label.value for sentiment in sentiments)
        companies = {link.company_id for link in links}
        digest = DailyDigest(
            digest_date=digest_date,
            timezone=self.settings.market_timezone,
            article_count=len(articles),
            company_count=len(companies),
            event_counts=dict(event_counts),
            sentiment_counts=dict(sentiment_counts),
            digest_payload={
                "synthetic": True,
                "not_investment_advice": True,
                "groups": _digest_groups(articles, links, events, sentiments),
            },
        )
        return self.repository.upsert_digest(digest)

    def generate_signals(self, signal_date: date) -> list[DailyCompanySignal]:
        articles = [
            item
            for item in self.repository.list_articles()
            if item.local_market_date == signal_date
        ]
        article_by_id = {item.id: item for item in articles}
        links_by_company: dict[UUID, list[ArticleCompanyLink]] = defaultdict(list)
        for link in self.repository.list_links():
            if link.article_id in article_by_id:
                links_by_company[link.company_id].append(link)
        sentiment_by_article = {item.article_id: item for item in self.repository.list_sentiments()}
        event_by_article = {item.article_id: item for item in self.repository.list_events()}
        companies = {company.id: company for company in self.repository.list_companies()}
        signals: list[DailyCompanySignal] = []
        for company_id, links in links_by_company.items():
            linked_articles = [article_by_id[link.article_id] for link in links]
            sentiments = [
                sentiment_by_article[item.id]
                for item in linked_articles
                if item.id in sentiment_by_article
            ]
            events = [
                event_by_article[item.id] for item in linked_articles if item.id in event_by_article
            ]
            unique_sources = {item.source_key for item in linked_articles}
            negative_count = sum(1 for item in sentiments if item.label is SentimentLabel.NEGATIVE)
            weighted = sum(item.score * item.confidence for item in sentiments) / max(
                1.0, sum(item.confidence for item in sentiments)
            )
            event_distribution = Counter(item.event_type.value for item in events)
            company = companies[company_id]
            signal = DailyCompanySignal(
                signal_date=signal_date,
                company_id=company.id,
                ticker=company.ticker,
                article_count=len(linked_articles),
                unique_source_count=len(unique_sources),
                weighted_sentiment_score=round(weighted, 3),
                negative_event_count=negative_count,
                event_distribution=dict(event_distribution),
                novelty_score=round(min(1.0, len(event_distribution) / 4), 3),
                source_diversity_score=round(min(1.0, len(unique_sources) / 3), 3),
            )
            signals.append(self.repository.upsert_signal(signal))
        return signals

    def run_demo(self, records: Iterable[SourceRecord], companies_path: Path) -> PipelineRun:
        started = time.perf_counter()
        warnings: list[str] = []
        errors: list[str] = []
        timings: dict[str, float] = {}
        counts: dict[str, int] = {}
        try:
            step = time.perf_counter()
            counts["companies"] = self.load_companies(companies_path)
            timings["companies"] = time.perf_counter() - step
            step = time.perf_counter()
            ingest_counts = self.ingest_records(records)
            counts.update({f"ingest_{key}": value for key, value in ingest_counts.items()})
            timings["ingest"] = time.perf_counter() - step
            step = time.perf_counter()
            counts.update(self.process_articles())
            timings["process"] = time.perf_counter() - step
            for digest_date in sorted(
                {article.local_market_date for article in self.repository.list_articles()}
            ):
                self.generate_digest(digest_date)
                self.generate_signals(digest_date)
            status = RunStatus.COMPLETED
        except Exception as exc:
            status = RunStatus.FAILED
            errors.append(str(exc))
        run = PipelineRun(
            status=status,
            started_at=utc_now(),
            finished_at=utc_now(),
            per_step_timings={key: round(value, 4) for key, value in timings.items()},
            per_step_counts=counts,
            warnings=warnings,
            errors=errors,
        )
        run.per_step_timings["total"] = round(time.perf_counter() - started, 4)
        return self.repository.add_pipeline_run(run)


def _digest_groups(
    articles: list[Article],
    links: list[ArticleCompanyLink],
    events: list[ArticleEvent],
    sentiments: list[ArticleSentiment],
) -> list[dict[str, object]]:
    link_map: dict[UUID, list[ArticleCompanyLink]] = defaultdict(list)
    for link in links:
        link_map[link.article_id].append(link)
    event_map = {event.article_id: event for event in events}
    sentiment_map = {sentiment.article_id: sentiment for sentiment in sentiments}
    groups: list[dict[str, object]] = []
    for article in articles:
        event = event_map.get(article.id)
        sentiment = sentiment_map.get(article.id)
        groups.append(
            {
                "article_id": str(article.id),
                "title": article.normalized_title,
                "source": article.source_name,
                "url": article.canonical_url,
                "event": event.event_type.value if event else "other",
                "sentiment": sentiment.label.value if sentiment else "neutral",
                "company_ids": [str(link.company_id) for link in link_map.get(article.id, [])],
            }
        )
    return groups
