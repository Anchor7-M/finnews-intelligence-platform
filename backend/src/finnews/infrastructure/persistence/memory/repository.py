from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from uuid import UUID

from finnews.domain.entities import (
    Article,
    ArticleCompanyLink,
    ArticleDuplicate,
    ArticleEvent,
    ArticleSentiment,
    Company,
    CompanyAlias,
    DailyCompanySignal,
    DailyDigest,
    IngestionRun,
    PipelineRun,
    RawArticle,
    Source,
)
from finnews.infrastructure.normalization import comparison_text


class MemoryNewsRepository:
    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.ingestion_runs: list[IngestionRun] = []
        self.raw_articles: dict[str, RawArticle] = {}
        self.articles: dict[UUID, Article] = {}
        self.articles_by_hash: dict[str, Article] = {}
        self.duplicates: list[ArticleDuplicate] = []
        self.companies: dict[str, Company] = {}
        self.aliases: list[CompanyAlias] = []
        self.links: dict[UUID, list[ArticleCompanyLink]] = {}
        self.events: dict[UUID, ArticleEvent] = {}
        self.sentiments: dict[UUID, ArticleSentiment] = {}
        self.digests: dict[date, DailyDigest] = {}
        self.signals: dict[tuple[date, UUID], DailyCompanySignal] = {}
        self.pipeline_runs: list[PipelineRun] = []

    def upsert_source(self, source: Source) -> Source:
        existing = self.sources.get(source.source_key)
        if existing:
            return existing
        self.sources[source.source_key] = source
        return source

    def add_ingestion_run(self, run: IngestionRun) -> IngestionRun:
        self.ingestion_runs.append(run)
        return run

    def add_raw_article(self, raw: RawArticle) -> RawArticle | None:
        key = f"{raw.source_id}:{raw.source_article_id}"
        if key in self.raw_articles:
            return None
        self.raw_articles[key] = raw
        return raw

    def add_article(self, article: Article) -> Article | None:
        existing = self.articles_by_hash.get(article.exact_content_hash)
        if existing:
            return None
        self.articles[article.id] = article
        self.articles_by_hash[article.exact_content_hash] = article
        return article

    def add_duplicate(self, duplicate: ArticleDuplicate) -> None:
        if duplicate.candidate_article_id == duplicate.canonical_article_id:
            return
        self.duplicates.append(duplicate)

    def upsert_company(self, company: Company, aliases: Iterable[str]) -> Company:
        ticker = company.ticker.upper()
        existing = self.companies.get(ticker)
        if existing:
            company = existing
        else:
            company.ticker = ticker
            self.companies[ticker] = company
        existing_aliases = {(alias.company_id, alias.normalized_alias) for alias in self.aliases}
        for alias in aliases:
            normalized = comparison_text(alias)
            key = (company.id, normalized)
            if key not in existing_aliases:
                self.aliases.append(CompanyAlias(company.id, alias, normalized))
        return company

    def replace_article_links(self, article_id: UUID, links: Sequence[ArticleCompanyLink]) -> None:
        self.links[article_id] = list(links)

    def replace_article_event(self, event: ArticleEvent) -> None:
        self.events[event.article_id] = event

    def replace_article_sentiment(self, sentiment: ArticleSentiment) -> None:
        self.sentiments[sentiment.article_id] = sentiment

    def upsert_digest(self, digest: DailyDigest) -> DailyDigest:
        self.digests[digest.digest_date] = digest
        return digest

    def upsert_signal(self, signal: DailyCompanySignal) -> DailyCompanySignal:
        self.signals[(signal.signal_date, signal.company_id)] = signal
        return signal

    def add_pipeline_run(self, run: PipelineRun) -> PipelineRun:
        self.pipeline_runs.append(run)
        return run

    def list_articles(self) -> list[Article]:
        return sorted(
            self.articles.values(), key=lambda item: (item.published_at, item.id), reverse=True
        )

    def list_companies(self) -> list[Company]:
        return sorted(self.companies.values(), key=lambda item: item.ticker)

    def list_aliases(self) -> list[CompanyAlias]:
        return list(self.aliases)

    def list_links(self) -> list[ArticleCompanyLink]:
        return [link for links in self.links.values() for link in links]

    def list_events(self) -> list[ArticleEvent]:
        return list(self.events.values())

    def list_sentiments(self) -> list[ArticleSentiment]:
        return list(self.sentiments.values())

    def list_duplicates(self) -> list[ArticleDuplicate]:
        return list(self.duplicates)

    def list_digests(self) -> list[DailyDigest]:
        return sorted(self.digests.values(), key=lambda item: item.digest_date, reverse=True)

    def list_signals(self) -> list[DailyCompanySignal]:
        return sorted(
            self.signals.values(), key=lambda item: (item.signal_date, item.ticker), reverse=True
        )

    def list_pipeline_runs(self) -> list[PipelineRun]:
        return list(self.pipeline_runs)

    def get_article(self, article_id: UUID) -> Article | None:
        return self.articles.get(article_id)

    def get_company_by_ticker(self, ticker: str) -> Company | None:
        return self.companies.get(ticker.upper())

    def get_digest(self, digest_date: date) -> DailyDigest | None:
        return self.digests.get(digest_date)
