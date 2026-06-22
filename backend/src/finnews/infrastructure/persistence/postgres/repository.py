from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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
    ObservationDisposition,
    PipelineRun,
    RawArticle,
    Source,
    SourceDefinition,
    SourceFetchAttempt,
    SourceFetchState,
    SourceRetryPolicy,
)
from finnews.domain.enums import (
    DuplicateType,
    EventType,
    FetchOutcome,
    IngestionPolicy,
    ProcessingState,
    RunStatus,
    SentimentLabel,
    SourceApprovalStatus,
    SourceErrorCategory,
    SourceHealthStatus,
    SourceType,
)
from finnews.infrastructure.normalization import comparison_text
from finnews.infrastructure.persistence.postgres.models import (
    ArticleCompanyLinkModel,
    ArticleDuplicateModel,
    ArticleEventModel,
    ArticleModel,
    ArticleSentimentModel,
    CompanyAliasModel,
    CompanyModel,
    DailyCompanySignalModel,
    DailyDigestModel,
    IngestionRunModel,
    ObservationDispositionModel,
    PipelineRunModel,
    RawArticleModel,
    SourceDefinitionModel,
    SourceFetchAttemptModel,
    SourceFetchStateModel,
    SourceModel,
)


class PostgresNewsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_source(self, source: Source) -> Source:
        existing = self.session.scalar(
            select(SourceModel).where(SourceModel.source_key == source.source_key)
        )
        if existing:
            return _source(existing)
        model = SourceModel(
            id=source.id,
            source_key=source.source_key,
            display_name=source.display_name,
            source_type=source.source_type.value,
            base_url=source.base_url,
            terms_url=source.terms_url,
            enabled=source.enabled,
            language_hints=source.language_hints,
            ingestion_policy=source.ingestion_policy.value,
            rate_limit=source.rate_limit,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )
        self.session.add(model)
        self.session.flush()
        return _source(model)

    def upsert_source_definition(self, definition: SourceDefinition) -> SourceDefinition:
        model = self.session.get(SourceDefinitionModel, definition.source_id)
        if model is None:
            model = SourceDefinitionModel(source_id=definition.source_id)
            self.session.add(model)
        model.display_name = definition.display_name
        model.source_type = definition.source_type.value
        model.approved_hostnames = definition.approved_hostnames
        model.review_status = definition.review_status.value
        model.enabled = definition.enabled
        model.base_url = definition.base_url
        model.import_format = definition.import_format
        model.terms_url = definition.terms_url
        model.documentation_url = definition.documentation_url
        model.reviewed_date = definition.reviewed_date
        model.reviewer = definition.reviewer
        model.content_storage_policy = definition.content_storage_policy.value
        model.provenance_required = definition.provenance_required
        model.language = definition.language
        model.timezone = definition.timezone
        model.connect_timeout_seconds = definition.connect_timeout_seconds
        model.read_timeout_seconds = definition.read_timeout_seconds
        model.max_response_bytes = definition.max_response_bytes
        model.retry_policy = {
            "max_retries": definition.retry_policy.max_retries,
            "base_delay_seconds": definition.retry_policy.base_delay_seconds,
            "max_delay_seconds": definition.retry_policy.max_delay_seconds,
        }
        model.minimum_interval_seconds = definition.minimum_interval_seconds
        model.cursor_strategy = definition.cursor_strategy
        model.field_mapping = definition.field_mapping
        model.user_agent = definition.user_agent
        model.notes = definition.notes
        model.risk_classification = definition.risk_classification
        model.adapter_version = definition.adapter_version
        self.upsert_source(
            Source(
                source_key=definition.source_id,
                display_name=definition.display_name,
                source_type=definition.source_type,
                base_url=definition.base_url,
                terms_url=definition.terms_url,
                enabled=definition.enabled,
                language_hints=[definition.language],
                ingestion_policy=definition.content_storage_policy,
                rate_limit={
                    "minimum_interval_seconds": definition.minimum_interval_seconds,
                    "max_retries": definition.retry_policy.max_retries,
                },
            )
        )
        self.session.flush()
        return _source_definition(model)

    def list_source_definitions(self) -> list[SourceDefinition]:
        return [
            _source_definition(row)
            for row in self.session.scalars(
                select(SourceDefinitionModel).order_by(SourceDefinitionModel.source_id)
            ).all()
        ]

    def get_source_definition(self, source_id: str) -> SourceDefinition | None:
        model = self.session.get(SourceDefinitionModel, source_id)
        return _source_definition(model) if model else None

    def upsert_source_fetch_state(self, state: SourceFetchState) -> SourceFetchState:
        model = self.session.get(SourceFetchStateModel, state.source_id)
        if model is None:
            model = SourceFetchStateModel(source_id=state.source_id)
            self.session.add(model)
        model.etag = state.etag
        model.last_modified = state.last_modified
        model.cursor = state.cursor
        model.last_attempted_at = state.last_attempted_at
        model.last_successful_at = state.last_successful_at
        model.next_allowed_at = state.next_allowed_at
        model.last_http_status = state.last_http_status
        model.last_response_hash = state.last_response_hash
        model.last_response_byte_count = state.last_response_byte_count
        model.last_item_count = state.last_item_count
        model.consecutive_failure_count = state.consecutive_failure_count
        model.last_error_category = state.last_error_category.value
        model.last_error_summary = state.last_error_summary
        model.health_status = state.health_status.value
        model.adapter_version = state.adapter_version
        model.updated_at = state.updated_at
        self.session.flush()
        return state

    def get_source_fetch_state(self, source_id: str) -> SourceFetchState | None:
        model = self.session.get(SourceFetchStateModel, source_id)
        return _source_fetch_state(model) if model else None

    def list_source_fetch_states(self) -> list[SourceFetchState]:
        return [
            _source_fetch_state(row)
            for row in self.session.scalars(
                select(SourceFetchStateModel).order_by(SourceFetchStateModel.source_id)
            ).all()
        ]

    def add_source_fetch_attempt(self, attempt: SourceFetchAttempt) -> SourceFetchAttempt:
        self.session.add(
            SourceFetchAttemptModel(
                id=attempt.id,
                source_id=attempt.source_id,
                outcome=attempt.outcome.value,
                started_at=attempt.started_at,
                finished_at=attempt.finished_at,
                http_status=attempt.http_status,
                item_count=attempt.item_count,
                new_count=attempt.new_count,
                duplicate_count=attempt.duplicate_count,
                rejected_count=attempt.rejected_count,
                response_byte_count=attempt.response_byte_count,
                response_hash=attempt.response_hash,
                retry_count=attempt.retry_count,
                duration_ms=attempt.duration_ms,
                error_category=attempt.error_category.value,
                error_summary=attempt.error_summary,
                etag_present=attempt.etag_present,
                last_modified_present=attempt.last_modified_present,
                cursor_before=attempt.cursor_before,
                cursor_after=attempt.cursor_after,
                dry_run=attempt.dry_run,
            )
        )
        self.session.flush()
        return attempt

    def list_source_fetch_attempts(self) -> list[SourceFetchAttempt]:
        return [
            _source_fetch_attempt(row)
            for row in self.session.scalars(
                select(SourceFetchAttemptModel).order_by(SourceFetchAttemptModel.started_at.desc())
            ).all()
        ]

    def add_ingestion_run(self, run: IngestionRun) -> IngestionRun:
        self.session.add(
            IngestionRunModel(
                id=run.id,
                source_id=run.source_id,
                status=run.status.value,
                started_at=run.started_at,
                finished_at=run.finished_at,
                cursor_before=run.cursor_before,
                cursor_after=run.cursor_after,
                fetched_count=run.fetched_count,
                accepted_count=run.accepted_count,
                rejected_count=run.rejected_count,
                exact_duplicate_count=run.exact_duplicate_count,
                near_duplicate_count=run.near_duplicate_count,
                warning_count=run.warning_count,
                error_summary=run.error_summary,
                code_version=run.code_version,
                configuration_version=run.configuration_version,
            )
        )
        self.session.flush()
        return run

    def add_raw_article(self, raw: RawArticle) -> RawArticle | None:
        existing = self.session.scalar(
            select(RawArticleModel).where(
                RawArticleModel.source_id == raw.source_id,
                RawArticleModel.source_article_id == raw.source_article_id,
            )
        )
        if existing:
            return None
        self.session.add(
            RawArticleModel(
                id=raw.id,
                source_id=raw.source_id,
                source_article_id=raw.source_article_id,
                canonical_url=raw.canonical_url,
                source_title=raw.source_title,
                source_summary=raw.source_summary,
                source_language=raw.source_language,
                published_at=raw.published_at,
                fetched_at=raw.fetched_at,
                raw_metadata=raw.raw_metadata,
                normalized_content_hash=raw.normalized_content_hash,
                ingestion_run_id=raw.ingestion_run_id,
            )
        )
        self.session.flush()
        return raw

    def add_article(self, article: Article) -> Article | None:
        if self.get_article_by_hash(article.exact_content_hash):
            return None
        self.session.add(
            ArticleModel(
                id=article.id,
                canonical_raw_article_id=article.canonical_raw_article_id,
                normalized_title=article.normalized_title,
                normalized_summary=article.normalized_summary,
                language=article.language,
                published_at=article.published_at,
                local_market_date=article.local_market_date,
                canonical_url=article.canonical_url,
                exact_content_hash=article.exact_content_hash,
                processing_state=article.processing_state.value,
                created_at=article.created_at,
                updated_at=article.updated_at,
            )
        )
        self.session.flush()
        return article

    def add_duplicate(self, duplicate: ArticleDuplicate) -> None:
        if duplicate.candidate_article_id == duplicate.canonical_article_id:
            return
        existing = self.session.get(
            ArticleDuplicateModel,
            {
                "candidate_article_id": duplicate.candidate_article_id,
                "canonical_article_id": duplicate.canonical_article_id,
            },
        )
        if existing is None:
            self.session.add(
                ArticleDuplicateModel(
                    candidate_article_id=duplicate.candidate_article_id,
                    canonical_article_id=duplicate.canonical_article_id,
                    duplicate_type=duplicate.duplicate_type.value,
                    similarity_score=duplicate.similarity_score,
                    algorithm_name=duplicate.algorithm_name,
                    algorithm_version=duplicate.algorithm_version,
                    created_at=duplicate.created_at,
                )
            )
        article = self.session.get(ArticleModel, duplicate.candidate_article_id)
        if article:
            article.processing_state = ProcessingState.DUPLICATE.value
        self.session.flush()

    def add_observation_disposition(self, disposition: ObservationDisposition) -> None:
        model = self.session.get(ObservationDispositionModel, disposition.observation_id)
        if model is not None:
            return
        model = ObservationDispositionModel(observation_id=disposition.observation_id)
        self.session.add(model)
        model.source_key = disposition.source_key
        model.disposition = disposition.disposition
        model.canonical_observation_id = disposition.canonical_observation_id
        model.canonical_article_id = disposition.canonical_article_id
        model.duplicate_type = (
            disposition.duplicate_type.value if disposition.duplicate_type else None
        )
        model.similarity_score = disposition.similarity_score
        model.explanation = disposition.explanation
        model.fixture_group = disposition.fixture_group
        self.session.flush()

    def upsert_company(self, company: Company, aliases: Iterable[str]) -> Company:
        ticker = company.ticker.upper()
        model = self.session.scalar(
            select(CompanyModel).where(
                CompanyModel.ticker == ticker,
                CompanyModel.exchange == company.exchange,
            )
        )
        if model is None:
            model = CompanyModel(
                id=company.id,
                ticker=ticker,
                exchange=company.exchange,
                legal_name=company.legal_name,
                short_name=company.short_name,
                sector=company.sector,
                active=company.active,
            )
            self.session.add(model)
            self.session.flush()
        existing_aliases = {
            alias.normalized_alias
            for alias in self.session.scalars(
                select(CompanyAliasModel).where(CompanyAliasModel.company_id == model.id)
            )
        }
        for alias in aliases:
            normalized = comparison_text(alias)
            if normalized not in existing_aliases:
                self.session.add(
                    CompanyAliasModel(
                        company_id=model.id,
                        alias=alias,
                        normalized_alias=normalized,
                        alias_type="name",
                        valid_from=None,
                        valid_to=None,
                    )
                )
                existing_aliases.add(normalized)
        self.session.flush()
        return _company(model)

    def replace_article_links(self, article_id: UUID, links: Sequence[ArticleCompanyLink]) -> None:
        self.session.execute(
            delete(ArticleCompanyLinkModel).where(ArticleCompanyLinkModel.article_id == article_id)
        )
        for link in links:
            self.session.add(
                ArticleCompanyLinkModel(
                    article_id=link.article_id,
                    company_id=link.company_id,
                    confidence=link.confidence,
                    matched_alias=link.matched_alias,
                    evidence_text_span=link.evidence_text_span,
                    linker_name=link.linker_name,
                    linker_version=link.linker_version,
                )
            )
        self.session.flush()

    def replace_article_event(self, event: ArticleEvent) -> None:
        self.session.execute(
            delete(ArticleEventModel).where(ArticleEventModel.article_id == event.article_id)
        )
        self.session.add(
            ArticleEventModel(
                article_id=event.article_id,
                event_type=event.event_type.value,
                confidence=event.confidence,
                evidence=event.evidence,
                classifier_name=event.classifier_name,
                classifier_version=event.classifier_version,
                processed_at=event.processed_at,
            )
        )
        self.session.flush()

    def replace_article_sentiment(self, sentiment: ArticleSentiment) -> None:
        self.session.execute(
            delete(ArticleSentimentModel).where(
                ArticleSentimentModel.article_id == sentiment.article_id
            )
        )
        self.session.add(
            ArticleSentimentModel(
                article_id=sentiment.article_id,
                score=sentiment.score,
                label=sentiment.label.value,
                confidence=sentiment.confidence,
                evidence=sentiment.evidence,
                analyzer_name=sentiment.analyzer_name,
                analyzer_version=sentiment.analyzer_version,
                processed_at=sentiment.processed_at,
            )
        )
        self.session.flush()

    def upsert_digest(self, digest: DailyDigest) -> DailyDigest:
        model = self.session.get(
            DailyDigestModel,
            {"digest_date": digest.digest_date, "timezone": digest.timezone},
        )
        if model is None:
            model = DailyDigestModel(digest_date=digest.digest_date, timezone=digest.timezone)
            self.session.add(model)
        model.generated_at = digest.generated_at
        model.article_count = digest.article_count
        model.company_count = digest.company_count
        model.event_counts = digest.event_counts
        model.sentiment_counts = digest.sentiment_counts
        model.digest_payload = digest.digest_payload
        model.generator_name = digest.generator_name
        model.generator_version = digest.generator_version
        self.session.flush()
        return digest

    def upsert_signal(self, signal: DailyCompanySignal) -> DailyCompanySignal:
        model = self.session.get(
            DailyCompanySignalModel,
            {"signal_date": signal.signal_date, "company_id": signal.company_id},
        )
        if model is None:
            model = DailyCompanySignalModel(
                signal_date=signal.signal_date, company_id=signal.company_id
            )
            self.session.add(model)
        model.ticker = signal.ticker
        model.article_count = signal.article_count
        model.unique_source_count = signal.unique_source_count
        model.weighted_sentiment_score = signal.weighted_sentiment_score
        model.negative_event_count = signal.negative_event_count
        model.event_distribution = signal.event_distribution
        model.novelty_score = signal.novelty_score
        model.source_diversity_score = signal.source_diversity_score
        model.signal_schema_version = signal.signal_schema_version
        model.generated_at = signal.generated_at
        self.session.flush()
        return signal

    def add_pipeline_run(self, run: PipelineRun) -> PipelineRun:
        self.session.add(
            PipelineRunModel(
                id=run.id,
                status=run.status.value,
                started_at=run.started_at,
                finished_at=run.finished_at,
                per_step_timings=run.per_step_timings,
                per_step_counts=run.per_step_counts,
                warnings=run.warnings,
                errors=run.errors,
                configuration_version=run.configuration_version,
                code_version=run.code_version,
            )
        )
        self.session.flush()
        return run

    def list_articles(self) -> list[Article]:
        rows = self.session.scalars(select(ArticleModel)).all()
        return sorted(
            (_article(self.session, row) for row in rows),
            key=_article_sort,
            reverse=True,
        )

    def list_companies(self) -> list[Company]:
        return [
            _company(row)
            for row in self.session.scalars(
                select(CompanyModel).order_by(CompanyModel.ticker)
            ).all()
        ]

    def list_aliases(self) -> list[CompanyAlias]:
        return [_alias(row) for row in self.session.scalars(select(CompanyAliasModel)).all()]

    def list_links(self) -> list[ArticleCompanyLink]:
        return [_link(row) for row in self.session.scalars(select(ArticleCompanyLinkModel)).all()]

    def list_events(self) -> list[ArticleEvent]:
        return [_event(row) for row in self.session.scalars(select(ArticleEventModel)).all()]

    def list_sentiments(self) -> list[ArticleSentiment]:
        return [
            _sentiment(row) for row in self.session.scalars(select(ArticleSentimentModel)).all()
        ]

    def list_duplicates(self) -> list[ArticleDuplicate]:
        return [
            _duplicate(row) for row in self.session.scalars(select(ArticleDuplicateModel)).all()
        ]

    def list_observation_dispositions(self) -> list[ObservationDisposition]:
        return [
            _disposition(row)
            for row in self.session.scalars(
                select(ObservationDispositionModel).order_by(
                    ObservationDispositionModel.observation_id
                )
            ).all()
        ]

    def list_digests(self) -> list[DailyDigest]:
        return [
            _digest(row)
            for row in self.session.scalars(
                select(DailyDigestModel).order_by(DailyDigestModel.digest_date.desc())
            ).all()
        ]

    def list_signals(self) -> list[DailyCompanySignal]:
        rows = self.session.scalars(select(DailyCompanySignalModel)).all()
        return sorted(
            (_signal(row) for row in rows),
            key=lambda item: (item.signal_date, item.ticker),
            reverse=True,
        )

    def list_pipeline_runs(self) -> list[PipelineRun]:
        return [
            _pipeline_run(row)
            for row in self.session.scalars(
                select(PipelineRunModel).order_by(PipelineRunModel.started_at)
            ).all()
        ]

    def get_article(self, article_id: UUID) -> Article | None:
        model = self.session.get(ArticleModel, article_id)
        return _article(self.session, model) if model else None

    def get_article_by_hash(self, exact_content_hash: str) -> Article | None:
        model = self.session.scalar(
            select(ArticleModel).where(ArticleModel.exact_content_hash == exact_content_hash)
        )
        return _article(self.session, model) if model else None

    def get_raw_article_by_id(self, raw_article_id: UUID) -> RawArticle | None:
        model = self.session.get(RawArticleModel, raw_article_id)
        return _raw_article(model) if model else None

    def get_company_by_ticker(self, ticker: str) -> Company | None:
        model = self.session.scalar(
            select(CompanyModel).where(CompanyModel.ticker == ticker.upper())
        )
        return _company(model) if model else None

    def get_digest(self, digest_date: date) -> DailyDigest | None:
        model = self.session.scalar(
            select(DailyDigestModel).where(DailyDigestModel.digest_date == digest_date)
        )
        return _digest(model) if model else None


def _source(row: SourceModel) -> Source:
    return Source(
        id=row.id,
        source_key=row.source_key,
        display_name=row.display_name,
        source_type=SourceType(row.source_type),
        base_url=row.base_url,
        terms_url=row.terms_url,
        enabled=row.enabled,
        language_hints=list(row.language_hints),
        ingestion_policy=IngestionPolicy(row.ingestion_policy),
        rate_limit=dict(row.rate_limit),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _source_definition(row: SourceDefinitionModel) -> SourceDefinition:
    retry_policy = dict(row.retry_policy)
    retry = SourceRetryPolicy(
        max_retries=_json_int(retry_policy.get("max_retries"), 2),
        base_delay_seconds=_json_float(retry_policy.get("base_delay_seconds"), 1.0),
        max_delay_seconds=_json_float(retry_policy.get("max_delay_seconds"), 30.0),
    )
    return SourceDefinition(
        source_id=row.source_id,
        display_name=row.display_name,
        source_type=SourceType(row.source_type),
        approved_hostnames=list(row.approved_hostnames),
        review_status=SourceApprovalStatus(row.review_status),
        enabled=row.enabled,
        base_url=row.base_url,
        import_format=row.import_format,
        terms_url=row.terms_url,
        documentation_url=row.documentation_url,
        reviewed_date=row.reviewed_date,
        reviewer=row.reviewer,
        content_storage_policy=IngestionPolicy(row.content_storage_policy),
        provenance_required=row.provenance_required,
        language=row.language,
        timezone=row.timezone,
        connect_timeout_seconds=row.connect_timeout_seconds,
        read_timeout_seconds=row.read_timeout_seconds,
        max_response_bytes=row.max_response_bytes,
        retry_policy=retry,
        minimum_interval_seconds=row.minimum_interval_seconds,
        cursor_strategy=row.cursor_strategy,
        field_mapping=dict(row.field_mapping),
        user_agent=row.user_agent,
        notes=row.notes,
        risk_classification=row.risk_classification,
        adapter_version=row.adapter_version,
    )


def _json_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _json_float(value: object, default: float) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return default


def _source_fetch_state(row: SourceFetchStateModel) -> SourceFetchState:
    return SourceFetchState(
        source_id=row.source_id,
        etag=row.etag,
        last_modified=row.last_modified,
        cursor=row.cursor,
        last_attempted_at=row.last_attempted_at,
        last_successful_at=row.last_successful_at,
        next_allowed_at=row.next_allowed_at,
        last_http_status=row.last_http_status,
        last_response_hash=row.last_response_hash,
        last_response_byte_count=row.last_response_byte_count,
        last_item_count=row.last_item_count,
        consecutive_failure_count=row.consecutive_failure_count,
        last_error_category=SourceErrorCategory(row.last_error_category),
        last_error_summary=row.last_error_summary,
        health_status=SourceHealthStatus(row.health_status),
        adapter_version=row.adapter_version,
        updated_at=row.updated_at,
    )


def _source_fetch_attempt(row: SourceFetchAttemptModel) -> SourceFetchAttempt:
    return SourceFetchAttempt(
        id=row.id,
        source_id=row.source_id,
        outcome=FetchOutcome(row.outcome),
        started_at=row.started_at,
        finished_at=row.finished_at,
        http_status=row.http_status,
        item_count=row.item_count,
        new_count=row.new_count,
        duplicate_count=row.duplicate_count,
        rejected_count=row.rejected_count,
        response_byte_count=row.response_byte_count,
        response_hash=row.response_hash,
        retry_count=row.retry_count,
        duration_ms=row.duration_ms,
        error_category=SourceErrorCategory(row.error_category),
        error_summary=row.error_summary,
        etag_present=row.etag_present,
        last_modified_present=row.last_modified_present,
        cursor_before=row.cursor_before,
        cursor_after=row.cursor_after,
        dry_run=row.dry_run,
    )


def _raw_article(row: RawArticleModel) -> RawArticle:
    return RawArticle(
        id=row.id,
        source_id=row.source_id,
        source_article_id=row.source_article_id,
        canonical_url=row.canonical_url,
        source_title=row.source_title,
        source_summary=row.source_summary,
        source_language=row.source_language,
        published_at=row.published_at,
        fetched_at=row.fetched_at,
        raw_metadata=row.raw_metadata,
        normalized_content_hash=row.normalized_content_hash,
        ingestion_run_id=row.ingestion_run_id,
    )


def _article(session: Session, row: ArticleModel) -> Article:
    raw = session.get(RawArticleModel, row.canonical_raw_article_id)
    source = session.get(SourceModel, raw.source_id) if raw else None
    return Article(
        id=row.id,
        canonical_raw_article_id=row.canonical_raw_article_id,
        normalized_title=row.normalized_title,
        normalized_summary=row.normalized_summary,
        language=row.language,
        published_at=row.published_at,
        local_market_date=row.local_market_date,
        canonical_url=row.canonical_url,
        exact_content_hash=row.exact_content_hash,
        source_key=source.source_key if source else "unknown",
        source_name=source.display_name if source else "Unknown",
        processing_state=ProcessingState(row.processing_state),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _article_sort(article: Article) -> tuple[object, object]:
    return (article.published_at, article.id)


def _company(row: CompanyModel) -> Company:
    return Company(
        id=row.id,
        ticker=row.ticker,
        exchange=row.exchange,
        legal_name=row.legal_name,
        short_name=row.short_name,
        sector=row.sector,
        active=row.active,
    )


def _alias(row: CompanyAliasModel) -> CompanyAlias:
    return CompanyAlias(
        company_id=row.company_id,
        alias=row.alias,
        normalized_alias=row.normalized_alias,
        alias_type=row.alias_type,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def _link(row: ArticleCompanyLinkModel) -> ArticleCompanyLink:
    return ArticleCompanyLink(
        article_id=row.article_id,
        company_id=row.company_id,
        confidence=row.confidence,
        matched_alias=row.matched_alias,
        evidence_text_span=row.evidence_text_span,
        linker_name=row.linker_name,
        linker_version=row.linker_version,
    )


def _event(row: ArticleEventModel) -> ArticleEvent:
    return ArticleEvent(
        article_id=row.article_id,
        event_type=EventType(row.event_type),
        confidence=row.confidence,
        evidence=list(row.evidence),
        classifier_name=row.classifier_name,
        classifier_version=row.classifier_version,
        processed_at=row.processed_at,
    )


def _sentiment(row: ArticleSentimentModel) -> ArticleSentiment:
    return ArticleSentiment(
        article_id=row.article_id,
        score=row.score,
        label=SentimentLabel(row.label),
        confidence=row.confidence,
        evidence=list(row.evidence),
        analyzer_name=row.analyzer_name,
        analyzer_version=row.analyzer_version,
        processed_at=row.processed_at,
    )


def _duplicate(row: ArticleDuplicateModel) -> ArticleDuplicate:
    return ArticleDuplicate(
        candidate_article_id=row.candidate_article_id,
        canonical_article_id=row.canonical_article_id,
        duplicate_type=DuplicateType(row.duplicate_type),
        similarity_score=row.similarity_score,
        algorithm_name=row.algorithm_name,
        algorithm_version=row.algorithm_version,
        created_at=row.created_at,
    )


def _disposition(row: ObservationDispositionModel) -> ObservationDisposition:
    duplicate_type = DuplicateType(row.duplicate_type) if row.duplicate_type else None
    return ObservationDisposition(
        observation_id=row.observation_id,
        source_key=row.source_key,
        disposition=row.disposition,
        canonical_observation_id=row.canonical_observation_id,
        canonical_article_id=row.canonical_article_id,
        duplicate_type=duplicate_type,
        similarity_score=row.similarity_score,
        explanation=row.explanation,
        fixture_group=row.fixture_group,
    )


def _digest(row: DailyDigestModel) -> DailyDigest:
    return DailyDigest(
        digest_date=row.digest_date,
        timezone=row.timezone,
        generated_at=row.generated_at,
        article_count=row.article_count,
        company_count=row.company_count,
        event_counts=dict(row.event_counts),
        sentiment_counts=dict(row.sentiment_counts),
        digest_payload=dict(row.digest_payload),
        generator_name=row.generator_name,
        generator_version=row.generator_version,
    )


def _signal(row: DailyCompanySignalModel) -> DailyCompanySignal:
    return DailyCompanySignal(
        signal_date=row.signal_date,
        company_id=row.company_id,
        ticker=row.ticker,
        article_count=row.article_count,
        unique_source_count=row.unique_source_count,
        weighted_sentiment_score=row.weighted_sentiment_score,
        negative_event_count=row.negative_event_count,
        event_distribution=dict(row.event_distribution),
        novelty_score=row.novelty_score,
        source_diversity_score=row.source_diversity_score,
        signal_schema_version=row.signal_schema_version,
        generated_at=row.generated_at,
    )


def _pipeline_run(row: PipelineRunModel) -> PipelineRun:
    return PipelineRun(
        id=row.id,
        status=RunStatus(row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        per_step_timings=dict(row.per_step_timings),
        per_step_counts=dict(row.per_step_counts),
        warnings=list(row.warnings),
        errors=list(row.errors),
        configuration_version=row.configuration_version,
        code_version=row.code_version,
    )
