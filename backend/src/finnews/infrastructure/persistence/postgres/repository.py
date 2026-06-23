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
    Asset,
    AssetImpactHypothesis,
    AssetRelationship,
    BrokerSymbolMapping,
    Company,
    CompanyAlias,
    CrossAssetEvent,
    DailyCompanySignal,
    DailyDigest,
    IngestionRun,
    MarketSignalCandidate,
    NlpEvaluationRun,
    NlpModelRegistryEntry,
    ObservationDisposition,
    OfficialDataReleaseRun,
    OfficialDataset,
    OfficialObservation,
    OfficialObservationRevision,
    OfficialReleaseEvent,
    OfficialSeriesProfile,
    PipelineRun,
    ProviderSymbol,
    RawArticle,
    RegulatoryDocument,
    ResearchCalendar,
    ResearchExportRun,
    ResearchFeatureRow,
    ResearchLineageRow,
    ResearchSession,
    SeriesAssetAssociation,
    SignalPublicationRun,
    Source,
    SourceDefinition,
    SourceFetchAttempt,
    SourceFetchState,
    SourceRetryPolicy,
    SymbolAlias,
)
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
from finnews.infrastructure.normalization import comparison_text
from finnews.infrastructure.persistence.postgres.models import (
    ArticleCompanyLinkModel,
    ArticleDuplicateModel,
    ArticleEventModel,
    ArticleModel,
    ArticleSentimentModel,
    AssetImpactHypothesisModel,
    AssetModel,
    AssetRelationshipModel,
    BrokerSymbolMappingModel,
    CompanyAliasModel,
    CompanyModel,
    CrossAssetEventModel,
    DailyCompanySignalModel,
    DailyDigestModel,
    IngestionRunModel,
    MarketSignalCandidateModel,
    NlpEvaluationRunModel,
    NlpModelRegistryModel,
    ObservationDispositionModel,
    OfficialDataReleaseRunModel,
    OfficialDatasetModel,
    OfficialObservationModel,
    OfficialObservationRevisionModel,
    OfficialReleaseEventModel,
    OfficialSeriesProfileModel,
    PipelineRunModel,
    ProviderSymbolModel,
    RawArticleModel,
    RegulatoryDocumentModel,
    ResearchCalendarModel,
    ResearchExportRunModel,
    ResearchFeatureRowModel,
    ResearchLineageRowModel,
    ResearchSessionModel,
    SeriesAssetAssociationModel,
    SignalPublicationRunModel,
    SourceDefinitionModel,
    SourceFetchAttemptModel,
    SourceFetchStateModel,
    SourceModel,
    SymbolAliasModel,
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

    def upsert_nlp_model(self, model: NlpModelRegistryEntry) -> NlpModelRegistryEntry:
        row = self.session.get(NlpModelRegistryModel, model.model_id)
        if row is None:
            row = NlpModelRegistryModel(model_id=model.model_id)
            self.session.add(row)
        row.task = model.task
        row.provider = model.provider
        row.model_kind = model.model_kind
        row.status = model.status
        row.dataset_id = model.dataset_id
        row.dataset_version = model.dataset_version
        row.dataset_sha256 = model.dataset_sha256
        row.split_hashes = model.split_hashes
        row.label_set = model.label_set
        row.metrics = model.metrics
        row.calibration = model.calibration
        row.artifact_uri = model.artifact_uri
        row.artifact_sha256 = model.artifact_sha256
        row.artifact_size_bytes = model.artifact_size_bytes
        row.manifest_sha256 = model.manifest_sha256
        row.config_sha256 = model.config_sha256
        row.created_at = model.created_at
        row.updated_at = model.updated_at
        self.session.flush()
        return _nlp_model(row)

    def get_nlp_model(self, model_id: str) -> NlpModelRegistryEntry | None:
        row = self.session.get(NlpModelRegistryModel, model_id)
        return _nlp_model(row) if row else None

    def list_nlp_models(
        self, task: str | None = None, status: str | None = None
    ) -> list[NlpModelRegistryEntry]:
        statement = select(NlpModelRegistryModel)
        if task:
            statement = statement.where(NlpModelRegistryModel.task == task)
        if status:
            statement = statement.where(NlpModelRegistryModel.status == status)
        statement = statement.order_by(NlpModelRegistryModel.task, NlpModelRegistryModel.model_id)
        return [_nlp_model(row) for row in self.session.scalars(statement).all()]

    def upsert_nlp_evaluation(self, evaluation: NlpEvaluationRun) -> NlpEvaluationRun:
        row = self.session.get(NlpEvaluationRunModel, evaluation.evaluation_id)
        if row is None:
            row = NlpEvaluationRunModel(evaluation_id=evaluation.evaluation_id)
            self.session.add(row)
        row.model_id = evaluation.model_id
        row.task = evaluation.task
        row.dataset_id = evaluation.dataset_id
        row.dataset_version = evaluation.dataset_version
        row.dataset_sha256 = evaluation.dataset_sha256
        row.split_name = evaluation.split_name
        row.metrics = evaluation.metrics
        row.slice_metrics = evaluation.slice_metrics
        row.calibration = evaluation.calibration
        row.error_analysis = evaluation.error_analysis
        row.selection_procedure = evaluation.selection_procedure
        row.evaluated_at = evaluation.evaluated_at
        self.session.flush()
        return _nlp_evaluation(row)

    def get_nlp_evaluation(self, evaluation_id: str) -> NlpEvaluationRun | None:
        row = self.session.get(NlpEvaluationRunModel, evaluation_id)
        return _nlp_evaluation(row) if row else None

    def list_nlp_evaluations(
        self, task: str | None = None, model_id: str | None = None
    ) -> list[NlpEvaluationRun]:
        statement = select(NlpEvaluationRunModel)
        if task:
            statement = statement.where(NlpEvaluationRunModel.task == task)
        if model_id:
            statement = statement.where(NlpEvaluationRunModel.model_id == model_id)
        statement = statement.order_by(NlpEvaluationRunModel.evaluated_at.desc())
        return [_nlp_evaluation(row) for row in self.session.scalars(statement).all()]

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

    def upsert_research_calendar(
        self, calendar: ResearchCalendar, sessions: Sequence[ResearchSession]
    ) -> ResearchCalendar:
        model = self.session.scalar(
            select(ResearchCalendarModel).where(
                ResearchCalendarModel.calendar_id == calendar.calendar_id,
                ResearchCalendarModel.calendar_version == calendar.calendar_version,
            )
        )
        if model is None:
            model = ResearchCalendarModel(id=calendar.id)
            self.session.add(model)
        model.calendar_id = calendar.calendar_id
        model.calendar_version = calendar.calendar_version
        model.timezone = calendar.timezone
        model.calendar_hash = calendar.calendar_hash
        model.provenance = calendar.provenance
        model.synthetic = calendar.synthetic
        self.session.execute(
            delete(ResearchSessionModel).where(
                ResearchSessionModel.calendar_id == calendar.calendar_id,
                ResearchSessionModel.calendar_version == calendar.calendar_version,
            )
        )
        for session in sessions:
            self.session.add(_research_session_model(session))
        self.session.flush()
        return calendar

    def get_research_calendar(self, calendar_id: str) -> ResearchCalendar | None:
        model = self.session.scalar(
            select(ResearchCalendarModel)
            .where(ResearchCalendarModel.calendar_id == calendar_id)
            .order_by(ResearchCalendarModel.calendar_version.desc())
        )
        return _research_calendar(model) if model else None

    def list_research_calendars(self) -> list[ResearchCalendar]:
        return [
            _research_calendar(row)
            for row in self.session.scalars(
                select(ResearchCalendarModel).order_by(
                    ResearchCalendarModel.calendar_id,
                    ResearchCalendarModel.calendar_version,
                )
            )
        ]

    def list_research_sessions(
        self, calendar_id: str, calendar_version: str | None = None
    ) -> list[ResearchSession]:
        statement = select(ResearchSessionModel).where(
            ResearchSessionModel.calendar_id == calendar_id
        )
        if calendar_version:
            statement = statement.where(ResearchSessionModel.calendar_version == calendar_version)
        statement = statement.order_by(ResearchSessionModel.sequence)
        return [_research_session(row) for row in self.session.scalars(statement)]

    def upsert_research_export(
        self,
        export_run: ResearchExportRun,
        feature_rows: Sequence[ResearchFeatureRow],
        lineage_rows: Sequence[ResearchLineageRow],
    ) -> ResearchExportRun:
        model = self.session.scalar(
            select(ResearchExportRunModel).where(
                ResearchExportRunModel.export_id == export_run.export_id,
                ResearchExportRunModel.contract_version == export_run.contract_version,
                ResearchExportRunModel.config_hash == export_run.config_hash,
                ResearchExportRunModel.calendar_hash == export_run.calendar_hash,
                ResearchExportRunModel.package_hash == export_run.package_hash,
            )
        )
        if model is None:
            model = ResearchExportRunModel(id=export_run.id)
            self.session.add(model)
        model.export_id = export_run.export_id
        model.contract_version = export_run.contract_version
        model.config_hash = export_run.config_hash
        model.calendar_id = export_run.calendar_id
        model.calendar_version = export_run.calendar_version
        model.calendar_hash = export_run.calendar_hash
        model.cutoff_policy = export_run.cutoff_policy
        model.windows = export_run.windows
        model.company_universe_hash = export_run.company_universe_hash
        model.package_hash = export_run.package_hash
        model.status = export_run.status
        model.counts = export_run.counts
        model.quality_summary = export_run.quality_summary
        model.leakage_status = export_run.leakage_status
        model.leakage_hash = export_run.leakage_hash
        model.synthetic = export_run.synthetic
        model.created_at = export_run.created_at
        self.session.execute(
            delete(ResearchFeatureRowModel).where(
                ResearchFeatureRowModel.export_id == export_run.export_id
            )
        )
        self.session.execute(
            delete(ResearchLineageRowModel).where(
                ResearchLineageRowModel.export_id == export_run.export_id
            )
        )
        for feature_row in feature_rows:
            self.session.add(_research_feature_row_model(feature_row))
        for lineage_row in lineage_rows:
            self.session.add(_research_lineage_row_model(lineage_row))
        self.session.flush()
        return export_run

    def get_research_export(self, export_id: str) -> ResearchExportRun | None:
        model = self.session.scalar(
            select(ResearchExportRunModel).where(ResearchExportRunModel.export_id == export_id)
        )
        return _research_export_run(model) if model else None

    def list_research_exports(self) -> list[ResearchExportRun]:
        return [
            _research_export_run(row)
            for row in self.session.scalars(
                select(ResearchExportRunModel).order_by(ResearchExportRunModel.export_id)
            )
        ]

    def list_research_feature_rows(
        self,
        export_id: str | None = None,
        ticker: str | None = None,
        window_sessions: int | None = None,
    ) -> list[ResearchFeatureRow]:
        statement = select(ResearchFeatureRowModel)
        if export_id:
            statement = statement.where(ResearchFeatureRowModel.export_id == export_id)
        if ticker:
            statement = statement.where(ResearchFeatureRowModel.ticker == ticker.upper())
        if window_sessions:
            statement = statement.where(ResearchFeatureRowModel.window_sessions == window_sessions)
        statement = statement.order_by(ResearchFeatureRowModel.logical_key)
        return [_research_feature_row(row) for row in self.session.scalars(statement)]

    def get_research_lineage_row(self, lineage_row_id: str) -> ResearchLineageRow | None:
        model = self.session.scalar(
            select(ResearchLineageRowModel).where(
                ResearchLineageRowModel.lineage_row_id == lineage_row_id
            )
        )
        return _research_lineage_row(model) if model else None

    def list_research_lineage_rows(self, export_id: str | None = None) -> list[ResearchLineageRow]:
        statement = select(ResearchLineageRowModel)
        if export_id:
            statement = statement.where(ResearchLineageRowModel.export_id == export_id)
        statement = statement.order_by(ResearchLineageRowModel.lineage_row_id)
        return [_research_lineage_row(row) for row in self.session.scalars(statement)]

    def upsert_cross_asset_dataset(
        self,
        assets: Sequence[Asset],
        aliases: Sequence[SymbolAlias],
        provider_symbols: Sequence[ProviderSymbol],
        broker_mappings: Sequence[BrokerSymbolMapping],
        relationships: Sequence[AssetRelationship],
        events: Sequence[CrossAssetEvent],
        impacts: Sequence[AssetImpactHypothesis],
        signals: Sequence[MarketSignalCandidate],
        publication_run: SignalPublicationRun,
    ) -> None:
        for asset in assets:
            model = self.session.scalar(
                select(AssetModel).where(AssetModel.asset_id == asset.asset_id)
            )
            if model is None:
                model = AssetModel(id=asset.id)
                self.session.add(model)
            _fill_asset_model(model, asset)
        self.session.execute(delete(SymbolAliasModel))
        self.session.execute(delete(ProviderSymbolModel))
        self.session.execute(delete(BrokerSymbolMappingModel))
        self.session.execute(delete(AssetRelationshipModel))
        self.session.execute(delete(CrossAssetEventModel))
        self.session.execute(delete(AssetImpactHypothesisModel))
        self.session.execute(delete(MarketSignalCandidateModel))
        self.session.execute(delete(SignalPublicationRunModel))
        for alias in aliases:
            self.session.add(_symbol_alias_model(alias))
        for provider_symbol in provider_symbols:
            self.session.add(_provider_symbol_model(provider_symbol))
        for broker_mapping in broker_mappings:
            self.session.add(_broker_symbol_mapping_model(broker_mapping))
        for relationship in relationships:
            self.session.add(_asset_relationship_model(relationship))
        for event in events:
            self.session.add(_cross_asset_event_model(event))
        for impact in impacts:
            self.session.add(_asset_impact_model(impact))
        for signal in signals:
            self.session.add(_market_signal_model(signal))
        self.session.add(_signal_publication_run_model(publication_run))
        self.session.flush()

    def list_assets(self) -> list[Asset]:
        return [
            _asset(row)
            for row in self.session.scalars(select(AssetModel).order_by(AssetModel.asset_id))
        ]

    def get_asset(self, asset_id: str) -> Asset | None:
        model = self.session.scalar(select(AssetModel).where(AssetModel.asset_id == asset_id))
        return _asset(model) if model else None

    def list_asset_aliases(self, asset_id: str | None = None) -> list[SymbolAlias]:
        statement = select(SymbolAliasModel)
        if asset_id:
            statement = statement.where(SymbolAliasModel.asset_id == asset_id)
        statement = statement.order_by(
            SymbolAliasModel.asset_id, SymbolAliasModel.namespace, SymbolAliasModel.symbol
        )
        return [_symbol_alias(row) for row in self.session.scalars(statement)]

    def list_asset_relationships(self, asset_id: str | None = None) -> list[AssetRelationship]:
        statement = select(AssetRelationshipModel)
        if asset_id:
            statement = statement.where(
                (AssetRelationshipModel.source_asset_id == asset_id)
                | (AssetRelationshipModel.target_asset_id == asset_id)
            )
        statement = statement.order_by(AssetRelationshipModel.relationship_id)
        return [_asset_relationship(row) for row in self.session.scalars(statement)]

    def list_cross_asset_events(self) -> list[CrossAssetEvent]:
        return [
            _cross_asset_event(row)
            for row in self.session.scalars(
                select(CrossAssetEventModel).order_by(CrossAssetEventModel.event_id)
            )
        ]

    def list_asset_impact_hypotheses(
        self, asset_id: str | None = None, event_id: str | None = None
    ) -> list[AssetImpactHypothesis]:
        statement = select(AssetImpactHypothesisModel)
        if asset_id:
            statement = statement.where(AssetImpactHypothesisModel.asset_id == asset_id)
        if event_id:
            statement = statement.where(AssetImpactHypothesisModel.event_id == event_id)
        statement = statement.order_by(AssetImpactHypothesisModel.impact_id)
        return [_asset_impact(row) for row in self.session.scalars(statement)]

    def list_market_signal_candidates(
        self, asset_id: str | None = None, status: str | None = None
    ) -> list[MarketSignalCandidate]:
        statement = select(MarketSignalCandidateModel)
        if asset_id:
            statement = statement.where(MarketSignalCandidateModel.asset_id == asset_id)
        if status:
            statement = statement.where(MarketSignalCandidateModel.status == status)
        statement = statement.order_by(MarketSignalCandidateModel.signal_id)
        return [_market_signal(row) for row in self.session.scalars(statement)]

    def upsert_official_dataset(self, dataset: OfficialDataset) -> OfficialDataset:
        model = self.session.scalar(
            select(OfficialDatasetModel).where(
                OfficialDatasetModel.dataset_id == dataset.dataset_id
            )
        )
        if model is None:
            model = OfficialDatasetModel(id=dataset.id, dataset_id=dataset.dataset_id)
            self.session.add(model)
        _fill_official_dataset_model(model, dataset)
        self.session.flush()
        return _official_dataset(model)

    def upsert_official_series_profile(
        self, profile: OfficialSeriesProfile
    ) -> OfficialSeriesProfile:
        model = self.session.scalar(
            select(OfficialSeriesProfileModel).where(
                OfficialSeriesProfileModel.profile_id == profile.profile_id
            )
        )
        if model is None:
            model = OfficialSeriesProfileModel(id=profile.id, profile_id=profile.profile_id)
            self.session.add(model)
        _fill_official_series_profile_model(model, profile)
        self.session.flush()
        return _official_series_profile(model)

    def upsert_official_observation(
        self,
        observation: OfficialObservation,
        revision: OfficialObservationRevision,
    ) -> OfficialObservation:
        model = self.session.scalar(
            select(OfficialObservationModel).where(
                OfficialObservationModel.observation_key == observation.observation_key
            )
        )
        if model is None:
            model = OfficialObservationModel(
                id=observation.id, observation_key=observation.observation_key
            )
            self.session.add(model)
        _fill_official_observation_model(model, observation)
        revision_model = self.session.scalar(
            select(OfficialObservationRevisionModel).where(
                OfficialObservationRevisionModel.observation_key == revision.observation_key,
                OfficialObservationRevisionModel.revision_number == revision.revision_number,
            )
        )
        if revision_model is None:
            self.session.add(_official_observation_revision_model(revision))
        self.session.flush()
        return _official_observation(model)

    def add_official_data_release_run(self, run: OfficialDataReleaseRun) -> OfficialDataReleaseRun:
        model = self.session.scalar(
            select(OfficialDataReleaseRunModel).where(
                OfficialDataReleaseRunModel.release_run_id == run.release_run_id
            )
        )
        if model is None:
            model = _official_data_release_run_model(run)
            self.session.add(model)
        self.session.flush()
        return _official_data_release_run(model)

    def upsert_regulatory_document(self, document: RegulatoryDocument) -> RegulatoryDocument:
        model = self.session.scalar(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.document_id == document.document_id
            )
        )
        if model is None:
            model = RegulatoryDocumentModel(id=document.id, document_id=document.document_id)
            self.session.add(model)
        _fill_regulatory_document_model(model, document)
        self.session.flush()
        return _regulatory_document(model)

    def upsert_series_asset_association(
        self, association: SeriesAssetAssociation
    ) -> SeriesAssetAssociation:
        model = self.session.scalar(
            select(SeriesAssetAssociationModel).where(
                SeriesAssetAssociationModel.association_id == association.association_id
            )
        )
        if model is None:
            model = SeriesAssetAssociationModel(
                id=association.id, association_id=association.association_id
            )
            self.session.add(model)
        _fill_series_asset_association_model(model, association)
        self.session.flush()
        return _series_asset_association(model)

    def upsert_official_release_event(self, event: OfficialReleaseEvent) -> OfficialReleaseEvent:
        model = self.session.scalar(
            select(OfficialReleaseEventModel).where(
                OfficialReleaseEventModel.event_id == event.event_id
            )
        )
        if model is None:
            model = OfficialReleaseEventModel(id=event.id, event_id=event.event_id)
            self.session.add(model)
        _fill_official_release_event_model(model, event)
        self.session.flush()
        return _official_release_event(model)

    def list_official_datasets(self) -> list[OfficialDataset]:
        return [
            _official_dataset(row)
            for row in self.session.scalars(
                select(OfficialDatasetModel).order_by(OfficialDatasetModel.dataset_id)
            )
        ]

    def list_official_series_profiles(
        self, source_id: str | None = None
    ) -> list[OfficialSeriesProfile]:
        statement = select(OfficialSeriesProfileModel)
        if source_id:
            statement = statement.where(OfficialSeriesProfileModel.source_id == source_id)
        statement = statement.order_by(OfficialSeriesProfileModel.profile_id)
        return [_official_series_profile(row) for row in self.session.scalars(statement)]

    def list_official_observations(
        self,
        dataset_id: str | None = None,
        profile_id: str | None = None,
    ) -> list[OfficialObservation]:
        statement = select(OfficialObservationModel)
        if dataset_id:
            statement = statement.where(OfficialObservationModel.dataset_id == dataset_id)
        if profile_id:
            statement = statement.where(OfficialObservationModel.profile_id == profile_id)
        statement = statement.order_by(
            OfficialObservationModel.profile_id, OfficialObservationModel.period_start
        )
        return [_official_observation(row) for row in self.session.scalars(statement)]

    def list_official_observation_revisions(
        self, observation_key: str | None = None
    ) -> list[OfficialObservationRevision]:
        statement = select(OfficialObservationRevisionModel)
        if observation_key:
            statement = statement.where(
                OfficialObservationRevisionModel.observation_key == observation_key
            )
        statement = statement.order_by(
            OfficialObservationRevisionModel.observation_key,
            OfficialObservationRevisionModel.revision_number,
        )
        return [_official_observation_revision(row) for row in self.session.scalars(statement)]

    def list_official_data_release_runs(self) -> list[OfficialDataReleaseRun]:
        return [
            _official_data_release_run(row)
            for row in self.session.scalars(
                select(OfficialDataReleaseRunModel).order_by(
                    OfficialDataReleaseRunModel.observed_at.desc()
                )
            )
        ]

    def list_regulatory_documents(self) -> list[RegulatoryDocument]:
        return [
            _regulatory_document(row)
            for row in self.session.scalars(
                select(RegulatoryDocumentModel).order_by(
                    RegulatoryDocumentModel.publication_date.desc(),
                    RegulatoryDocumentModel.document_id,
                )
            )
        ]

    def list_series_asset_associations(
        self,
        profile_id: str | None = None,
        asset_id: str | None = None,
    ) -> list[SeriesAssetAssociation]:
        statement = select(SeriesAssetAssociationModel)
        if profile_id:
            statement = statement.where(SeriesAssetAssociationModel.profile_id == profile_id)
        if asset_id:
            statement = statement.where(SeriesAssetAssociationModel.asset_id == asset_id)
        statement = statement.order_by(SeriesAssetAssociationModel.association_id)
        return [_series_asset_association(row) for row in self.session.scalars(statement)]

    def list_official_release_events(self) -> list[OfficialReleaseEvent]:
        return [
            _official_release_event(row)
            for row in self.session.scalars(
                select(OfficialReleaseEventModel).order_by(OfficialReleaseEventModel.event_id)
            )
        ]


def _fill_official_dataset_model(model: OfficialDatasetModel, row: OfficialDataset) -> None:
    model.source_id = row.source_id
    model.display_name = row.display_name
    model.category = row.category
    model.description = row.description
    model.documentation_url = row.documentation_url
    model.revision_policy = row.revision_policy
    model.frequency = row.frequency
    model.unit = row.unit
    model.synthetic = row.synthetic
    model.provenance = row.provenance


def _official_dataset(row: OfficialDatasetModel) -> OfficialDataset:
    return OfficialDataset(
        id=row.id,
        dataset_id=row.dataset_id,
        source_id=row.source_id,
        display_name=row.display_name,
        category=row.category,
        description=row.description,
        documentation_url=row.documentation_url,
        revision_policy=row.revision_policy,
        frequency=row.frequency,
        unit=row.unit,
        synthetic=row.synthetic,
        provenance=dict(row.provenance),
    )


def _fill_official_series_profile_model(
    model: OfficialSeriesProfileModel, row: OfficialSeriesProfile
) -> None:
    model.dataset_id = row.dataset_id
    model.source_id = row.source_id
    model.display_name = row.display_name
    model.query = row.query
    model.dimensions = row.dimensions
    model.unit = row.unit
    model.frequency = row.frequency
    model.seasonal_adjustment = row.seasonal_adjustment
    model.synthetic = row.synthetic
    model.provenance = row.provenance


def _official_series_profile(row: OfficialSeriesProfileModel) -> OfficialSeriesProfile:
    return OfficialSeriesProfile(
        id=row.id,
        profile_id=row.profile_id,
        dataset_id=row.dataset_id,
        source_id=row.source_id,
        display_name=row.display_name,
        query=dict(row.query),
        dimensions=dict(row.dimensions),
        unit=row.unit,
        frequency=row.frequency,
        seasonal_adjustment=row.seasonal_adjustment,
        synthetic=row.synthetic,
        provenance=dict(row.provenance),
    )


def _fill_official_observation_model(
    model: OfficialObservationModel, row: OfficialObservation
) -> None:
    model.source_id = row.source_id
    model.dataset_id = row.dataset_id
    model.profile_id = row.profile_id
    model.period_start = row.period_start
    model.period_end = row.period_end
    model.dimensions = row.dimensions
    model.current_revision = row.current_revision
    model.current_value = row.current_value
    model.first_seen_at = row.first_seen_at
    model.information_available_at = row.information_available_at
    model.synthetic = row.synthetic


def _official_observation(row: OfficialObservationModel) -> OfficialObservation:
    return OfficialObservation(
        id=row.id,
        observation_key=row.observation_key,
        source_id=row.source_id,
        dataset_id=row.dataset_id,
        profile_id=row.profile_id,
        period_start=row.period_start,
        period_end=row.period_end,
        dimensions=dict(row.dimensions),
        current_revision=row.current_revision,
        current_value=row.current_value,
        first_seen_at=row.first_seen_at,
        information_available_at=row.information_available_at,
        synthetic=row.synthetic,
    )


def _official_observation_revision_model(
    row: OfficialObservationRevision,
) -> OfficialObservationRevisionModel:
    return OfficialObservationRevisionModel(
        id=row.id,
        observation_key=row.observation_key,
        revision_number=row.revision_number,
        value=row.value,
        first_seen_at=row.first_seen_at,
        source_updated_at=row.source_updated_at,
        information_available_at=row.information_available_at,
        provenance=row.provenance,
        quality_flags=row.quality_flags,
    )


def _official_observation_revision(
    row: OfficialObservationRevisionModel,
) -> OfficialObservationRevision:
    return OfficialObservationRevision(
        id=row.id,
        observation_key=row.observation_key,
        revision_number=row.revision_number,
        value=row.value,
        first_seen_at=row.first_seen_at,
        source_updated_at=row.source_updated_at,
        information_available_at=row.information_available_at,
        provenance=dict(row.provenance),
        quality_flags=list(row.quality_flags),
    )


def _official_data_release_run_model(row: OfficialDataReleaseRun) -> OfficialDataReleaseRunModel:
    return OfficialDataReleaseRunModel(
        id=row.id,
        release_run_id=row.release_run_id,
        source_id=row.source_id,
        dataset_id=row.dataset_id,
        observed_at=row.observed_at,
        profile_count=row.profile_count,
        observation_count=row.observation_count,
        new_revision_count=row.new_revision_count,
        unchanged_count=row.unchanged_count,
        status=row.status,
        no_persist_live=row.no_persist_live,
        synthetic=row.synthetic,
    )


def _official_data_release_run(row: OfficialDataReleaseRunModel) -> OfficialDataReleaseRun:
    return OfficialDataReleaseRun(
        id=row.id,
        release_run_id=row.release_run_id,
        source_id=row.source_id,
        dataset_id=row.dataset_id,
        observed_at=row.observed_at,
        profile_count=row.profile_count,
        observation_count=row.observation_count,
        new_revision_count=row.new_revision_count,
        unchanged_count=row.unchanged_count,
        status=row.status,
        no_persist_live=row.no_persist_live,
        synthetic=row.synthetic,
    )


def _fill_regulatory_document_model(
    model: RegulatoryDocumentModel, row: RegulatoryDocument
) -> None:
    model.source_id = row.source_id
    model.title = row.title
    model.abstract = row.abstract
    model.publication_date = row.publication_date
    model.document_type = row.document_type
    model.agencies = row.agencies
    model.cfr_references = row.cfr_references
    model.rin = row.rin
    model.html_url = row.html_url
    model.pdf_url = row.pdf_url
    model.information_available_at = row.information_available_at
    model.source_updated_at = row.source_updated_at
    model.synthetic = row.synthetic
    model.provenance = row.provenance


def _regulatory_document(row: RegulatoryDocumentModel) -> RegulatoryDocument:
    return RegulatoryDocument(
        id=row.id,
        document_id=row.document_id,
        source_id=row.source_id,
        title=row.title,
        abstract=row.abstract,
        publication_date=row.publication_date,
        document_type=row.document_type,
        agencies=list(row.agencies),
        cfr_references=list(row.cfr_references),
        rin=list(row.rin),
        html_url=row.html_url,
        pdf_url=row.pdf_url,
        information_available_at=row.information_available_at,
        source_updated_at=row.source_updated_at,
        synthetic=row.synthetic,
        provenance=dict(row.provenance),
    )


def _fill_series_asset_association_model(
    model: SeriesAssetAssociationModel, row: SeriesAssetAssociation
) -> None:
    model.profile_id = row.profile_id
    model.asset_id = row.asset_id
    model.relationship_type = row.relationship_type
    model.rationale = row.rationale
    model.confidence = row.confidence
    model.active = row.active
    model.synthetic = row.synthetic
    model.provenance = row.provenance


def _series_asset_association(row: SeriesAssetAssociationModel) -> SeriesAssetAssociation:
    return SeriesAssetAssociation(
        id=row.id,
        association_id=row.association_id,
        profile_id=row.profile_id,
        asset_id=row.asset_id,
        relationship_type=row.relationship_type,
        rationale=row.rationale,
        confidence=row.confidence,
        active=row.active,
        synthetic=row.synthetic,
        provenance=dict(row.provenance),
    )


def _fill_official_release_event_model(
    model: OfficialReleaseEventModel, row: OfficialReleaseEvent
) -> None:
    model.source_id = row.source_id
    model.dataset_id = row.dataset_id
    model.profile_id = row.profile_id
    model.document_id = row.document_id
    model.event_family = row.event_family.value
    model.description = row.description
    model.information_available_at = row.information_available_at
    model.revision_number = row.revision_number
    model.provenance = row.provenance
    model.synthetic = row.synthetic


def _official_release_event(row: OfficialReleaseEventModel) -> OfficialReleaseEvent:
    return OfficialReleaseEvent(
        id=row.id,
        event_id=row.event_id,
        source_id=row.source_id,
        dataset_id=row.dataset_id,
        profile_id=row.profile_id,
        document_id=row.document_id,
        event_family=CrossAssetEventFamily(row.event_family),
        description=row.description,
        information_available_at=row.information_available_at,
        revision_number=row.revision_number,
        provenance=dict(row.provenance),
        synthetic=row.synthetic,
    )


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


def _fill_asset_model(model: AssetModel, asset: Asset) -> None:
    model.asset_id = asset.asset_id
    model.display_name = asset.display_name
    model.asset_class = asset.asset_class.value
    model.canonical_symbol = asset.canonical_symbol
    model.home_venue = asset.home_venue
    model.country_region = asset.country_region
    model.base_currency = asset.base_currency
    model.quote_currency = asset.quote_currency
    model.parent_asset_id = asset.parent_asset_id
    model.expiry = asset.expiry
    model.contract_metadata = asset.contract_metadata
    model.status = asset.status.value
    model.synthetic = asset.synthetic
    model.provenance = asset.provenance
    model.schema_version = asset.schema_version


def _asset(row: AssetModel) -> Asset:
    return Asset(
        id=row.id,
        asset_id=row.asset_id,
        display_name=row.display_name,
        asset_class=AssetClass(row.asset_class),
        canonical_symbol=row.canonical_symbol,
        home_venue=row.home_venue,
        country_region=row.country_region,
        base_currency=row.base_currency,
        quote_currency=row.quote_currency,
        parent_asset_id=row.parent_asset_id,
        expiry=row.expiry,
        contract_metadata=dict(row.contract_metadata),
        status=AssetStatus(row.status),
        synthetic=row.synthetic,
        provenance=dict(row.provenance),
        schema_version=row.schema_version,
    )


def _symbol_alias_model(row: SymbolAlias) -> SymbolAliasModel:
    return SymbolAliasModel(
        id=row.id,
        asset_id=row.asset_id,
        namespace=row.namespace.value,
        symbol=row.symbol,
        normalized_symbol=row.normalized_symbol,
        provider=row.provider,
        provider_version=row.provider_version,
        active=row.active,
        confidence=row.confidence,
        provenance=row.provenance,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def _symbol_alias(row: SymbolAliasModel) -> SymbolAlias:
    return SymbolAlias(
        id=row.id,
        asset_id=row.asset_id,
        namespace=SymbolNamespace(row.namespace),
        symbol=row.symbol,
        normalized_symbol=row.normalized_symbol,
        provider=row.provider,
        provider_version=row.provider_version,
        active=row.active,
        confidence=row.confidence,
        provenance=dict(row.provenance),
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def _provider_symbol_model(row: ProviderSymbol) -> ProviderSymbolModel:
    return ProviderSymbolModel(
        id=row.id,
        asset_id=row.asset_id,
        namespace=row.namespace.value,
        provider=row.provider,
        symbol=row.symbol,
        provider_version=row.provider_version,
        active=row.active,
        provenance=row.provenance,
    )


def _broker_symbol_mapping_model(row: BrokerSymbolMapping) -> BrokerSymbolMappingModel:
    return BrokerSymbolMappingModel(
        id=row.id,
        asset_id=row.asset_id,
        broker_profile_id=row.broker_profile_id,
        mt5_symbol=row.mt5_symbol,
        enabled=row.enabled,
        provenance=row.provenance,
        local_note=row.local_note,
    )


def _asset_relationship_model(row: AssetRelationship) -> AssetRelationshipModel:
    return AssetRelationshipModel(
        id=row.id,
        relationship_id=row.relationship_id,
        source_asset_id=row.source_asset_id,
        target_asset_id=row.target_asset_id,
        relationship_type=row.relationship_type.value,
        direction=row.direction,
        confidence=row.confidence,
        active=row.active,
        provenance=row.provenance,
        synthetic=row.synthetic,
    )


def _asset_relationship(row: AssetRelationshipModel) -> AssetRelationship:
    return AssetRelationship(
        id=row.id,
        relationship_id=row.relationship_id,
        source_asset_id=row.source_asset_id,
        target_asset_id=row.target_asset_id,
        relationship_type=ImpactRelationshipType(row.relationship_type),
        direction=row.direction,
        confidence=row.confidence,
        active=row.active,
        provenance=dict(row.provenance),
        synthetic=row.synthetic,
    )


def _cross_asset_event_model(row: CrossAssetEvent) -> CrossAssetEventModel:
    return CrossAssetEventModel(
        id=row.id,
        event_id=row.event_id,
        event_family=row.event_family.value,
        event_subtype=row.event_subtype,
        description=row.description,
        information_available_at=row.information_available_at,
        affected_region=row.affected_region,
        relevant_currency=row.relevant_currency,
        source_provenance=row.source_provenance,
        provider=row.provider,
        provider_version=row.provider_version,
        confidence=row.confidence,
        uncertainty_flags=row.uncertainty_flags,
        duplicate_of_event_id=row.duplicate_of_event_id,
        synthetic=row.synthetic,
    )


def _cross_asset_event(row: CrossAssetEventModel) -> CrossAssetEvent:
    return CrossAssetEvent(
        id=row.id,
        event_id=row.event_id,
        event_family=CrossAssetEventFamily(row.event_family),
        event_subtype=row.event_subtype,
        description=row.description,
        information_available_at=row.information_available_at,
        affected_region=row.affected_region,
        relevant_currency=row.relevant_currency,
        source_provenance=dict(row.source_provenance),
        provider=row.provider,
        provider_version=row.provider_version,
        confidence=row.confidence,
        uncertainty_flags=list(row.uncertainty_flags),
        duplicate_of_event_id=row.duplicate_of_event_id,
        synthetic=row.synthetic,
    )


def _asset_impact_model(row: AssetImpactHypothesis) -> AssetImpactHypothesisModel:
    return AssetImpactHypothesisModel(
        id=row.id,
        impact_id=row.impact_id,
        event_id=row.event_id,
        asset_id=row.asset_id,
        relationship_type=row.relationship_type.value,
        direction=row.direction.value,
        impact_strength=row.impact_strength,
        confidence=row.confidence,
        horizon=row.horizon.value,
        evidence_codes=row.evidence_codes,
        provider=row.provider,
        provider_version=row.provider_version,
        information_cutoff_at=row.information_cutoff_at,
        created_at=row.created_at,
        expires_at=row.expires_at,
        status=row.status,
        rejection_reason=row.rejection_reason,
        uncertainty_reason=row.uncertainty_reason,
        synthetic=row.synthetic,
    )


def _asset_impact(row: AssetImpactHypothesisModel) -> AssetImpactHypothesis:
    return AssetImpactHypothesis(
        id=row.id,
        impact_id=row.impact_id,
        event_id=row.event_id,
        asset_id=row.asset_id,
        relationship_type=ImpactRelationshipType(row.relationship_type),
        direction=ImpactDirection(row.direction),
        impact_strength=row.impact_strength,
        confidence=row.confidence,
        horizon=ImpactHorizon(row.horizon),
        evidence_codes=list(row.evidence_codes),
        provider=row.provider,
        provider_version=row.provider_version,
        information_cutoff_at=row.information_cutoff_at,
        created_at=row.created_at,
        expires_at=row.expires_at,
        status=row.status,
        rejection_reason=row.rejection_reason,
        uncertainty_reason=row.uncertainty_reason,
        synthetic=row.synthetic,
    )


def _market_signal_model(row: MarketSignalCandidate) -> MarketSignalCandidateModel:
    return MarketSignalCandidateModel(
        id=row.id,
        signal_id=row.signal_id,
        impact_id=row.impact_id,
        event_id=row.event_id,
        asset_id=row.asset_id,
        direction=row.direction.value,
        horizon=row.horizon.value,
        status=row.status.value,
        confidence=row.confidence,
        score=row.score,
        information_cutoff_at=row.information_cutoff_at,
        generated_at=row.generated_at,
        expires_at=row.expires_at,
        provider=row.provider,
        provider_version=row.provider_version,
        evidence_codes=row.evidence_codes,
        quality_tags=row.quality_tags,
        risk_tags=row.risk_tags,
        payload_hash=row.payload_hash,
        idempotency_key=row.idempotency_key,
        synthetic=row.synthetic,
    )


def _market_signal(row: MarketSignalCandidateModel) -> MarketSignalCandidate:
    return MarketSignalCandidate(
        id=row.id,
        signal_id=row.signal_id,
        impact_id=row.impact_id,
        event_id=row.event_id,
        asset_id=row.asset_id,
        direction=ImpactDirection(row.direction),
        horizon=ImpactHorizon(row.horizon),
        status=ResearchSignalStatus(row.status),
        confidence=row.confidence,
        score=row.score,
        information_cutoff_at=row.information_cutoff_at,
        generated_at=row.generated_at,
        expires_at=row.expires_at,
        provider=row.provider,
        provider_version=row.provider_version,
        evidence_codes=list(row.evidence_codes),
        quality_tags=list(row.quality_tags),
        risk_tags=list(row.risk_tags),
        payload_hash=row.payload_hash,
        idempotency_key=row.idempotency_key,
        synthetic=row.synthetic,
    )


def _signal_publication_run_model(row: SignalPublicationRun) -> SignalPublicationRunModel:
    return SignalPublicationRunModel(
        id=row.id,
        run_id=row.run_id,
        contract_name=row.contract_name,
        contract_version=row.contract_version,
        generated_at=row.generated_at,
        count=row.count,
        status=row.status,
        manifest_hash=row.manifest_hash,
        file_hashes=row.file_hashes,
        synthetic=row.synthetic,
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


def _nlp_model(row: NlpModelRegistryModel) -> NlpModelRegistryEntry:
    return NlpModelRegistryEntry(
        model_id=row.model_id,
        task=row.task,
        provider=row.provider,
        model_kind=row.model_kind,
        status=row.status,
        dataset_id=row.dataset_id,
        dataset_version=row.dataset_version,
        dataset_sha256=row.dataset_sha256,
        split_hashes=dict(row.split_hashes),
        label_set=list(row.label_set),
        metrics=dict(row.metrics),
        calibration=dict(row.calibration),
        artifact_uri=row.artifact_uri,
        artifact_sha256=row.artifact_sha256,
        artifact_size_bytes=row.artifact_size_bytes,
        manifest_sha256=row.manifest_sha256,
        config_sha256=row.config_sha256,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _nlp_evaluation(row: NlpEvaluationRunModel) -> NlpEvaluationRun:
    return NlpEvaluationRun(
        evaluation_id=row.evaluation_id,
        model_id=row.model_id,
        task=row.task,
        dataset_id=row.dataset_id,
        dataset_version=row.dataset_version,
        dataset_sha256=row.dataset_sha256,
        split_name=row.split_name,
        metrics=dict(row.metrics),
        slice_metrics=dict(row.slice_metrics),
        calibration=dict(row.calibration),
        error_analysis=dict(row.error_analysis),
        selection_procedure=dict(row.selection_procedure),
        evaluated_at=row.evaluated_at,
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


def _research_calendar(row: ResearchCalendarModel) -> ResearchCalendar:
    return ResearchCalendar(
        id=row.id,
        calendar_id=row.calendar_id,
        calendar_version=row.calendar_version,
        timezone=row.timezone,
        calendar_hash=row.calendar_hash,
        provenance=dict(row.provenance),
        synthetic=row.synthetic,
    )


def _research_session(row: ResearchSessionModel) -> ResearchSession:
    return ResearchSession(
        id=row.id,
        calendar_id=row.calendar_id,
        calendar_version=row.calendar_version,
        session_date=row.session_date,
        open_at=row.open_at,
        break_start_at=row.break_start_at,
        break_end_at=row.break_end_at,
        close_at=row.close_at,
        sequence=row.sequence,
        special_session=row.special_session,
    )


def _research_export_run(row: ResearchExportRunModel) -> ResearchExportRun:
    return ResearchExportRun(
        id=row.id,
        export_id=row.export_id,
        contract_version=row.contract_version,
        config_hash=row.config_hash,
        calendar_id=row.calendar_id,
        calendar_version=row.calendar_version,
        calendar_hash=row.calendar_hash,
        cutoff_policy=row.cutoff_policy,
        windows=list(row.windows),
        company_universe_hash=row.company_universe_hash,
        package_hash=row.package_hash,
        status=row.status,
        counts=dict(row.counts),
        quality_summary=dict(row.quality_summary),
        leakage_status=row.leakage_status,
        leakage_hash=row.leakage_hash,
        synthetic=row.synthetic,
        created_at=row.created_at,
    )


def _research_feature_row(row: ResearchFeatureRowModel) -> ResearchFeatureRow:
    return ResearchFeatureRow(
        id=row.id,
        export_id=row.export_id,
        logical_key=row.logical_key,
        session_date=row.session_date,
        decision_cutoff_at=row.decision_cutoff_at,
        ticker=row.ticker,
        company_id=row.company_id,
        window_sessions=row.window_sessions,
        feature_schema_version=row.feature_schema_version,
        features=dict(row.features),
        lineage_row_id=row.lineage_row_id,
        synthetic=row.synthetic,
    )


def _research_lineage_row(row: ResearchLineageRowModel) -> ResearchLineageRow:
    return ResearchLineageRow(
        id=row.id,
        export_id=row.export_id,
        lineage_row_id=row.lineage_row_id,
        feature_row_key=row.feature_row_key,
        canonical_article_id=row.canonical_article_id,
        source_id=row.source_id,
        company_id=row.company_id,
        information_available_at=row.information_available_at,
        decision_cutoff_at=row.decision_cutoff_at,
        inclusion_reason=row.inclusion_reason,
        event_provider=row.event_provider,
        event_model_version=row.event_model_version,
        sentiment_provider=row.sentiment_provider,
        sentiment_model_version=row.sentiment_model_version,
        payload=dict(row.payload),
        synthetic=row.synthetic,
    )


def _research_session_model(session: ResearchSession) -> ResearchSessionModel:
    return ResearchSessionModel(
        id=session.id,
        calendar_id=session.calendar_id,
        calendar_version=session.calendar_version,
        session_date=session.session_date,
        open_at=session.open_at,
        break_start_at=session.break_start_at,
        break_end_at=session.break_end_at,
        close_at=session.close_at,
        sequence=session.sequence,
        special_session=session.special_session,
    )


def _research_feature_row_model(row: ResearchFeatureRow) -> ResearchFeatureRowModel:
    return ResearchFeatureRowModel(
        id=row.id,
        export_id=row.export_id,
        logical_key=row.logical_key,
        session_date=row.session_date,
        decision_cutoff_at=row.decision_cutoff_at,
        ticker=row.ticker,
        company_id=row.company_id,
        window_sessions=row.window_sessions,
        feature_schema_version=row.feature_schema_version,
        features=row.features,
        lineage_row_id=row.lineage_row_id,
        synthetic=row.synthetic,
    )


def _research_lineage_row_model(row: ResearchLineageRow) -> ResearchLineageRowModel:
    return ResearchLineageRowModel(
        id=row.id,
        export_id=row.export_id,
        lineage_row_id=row.lineage_row_id,
        feature_row_key=row.feature_row_key,
        canonical_article_id=row.canonical_article_id,
        source_id=row.source_id,
        company_id=row.company_id,
        information_available_at=row.information_available_at,
        decision_cutoff_at=row.decision_cutoff_at,
        inclusion_reason=row.inclusion_reason,
        event_provider=row.event_provider,
        event_model_version=row.event_model_version,
        sentiment_provider=row.sentiment_provider,
        sentiment_model_version=row.sentiment_model_version,
        payload=row.payload,
        synthetic=row.synthetic,
    )
