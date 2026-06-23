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
    ResearchCalendar,
    ResearchExportRun,
    ResearchFeatureRow,
    ResearchLineageRow,
    ResearchSession,
    SignalPublicationRun,
    Source,
    SourceDefinition,
    SourceFetchAttempt,
    SourceFetchState,
    SymbolAlias,
    RegulatoryDocument,
    SeriesAssetAssociation,
)
from finnews.infrastructure.normalization import comparison_text


class MemoryNewsRepository:
    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.source_definitions: dict[str, SourceDefinition] = {}
        self.source_fetch_states: dict[str, SourceFetchState] = {}
        self.source_fetch_attempts: list[SourceFetchAttempt] = []
        self.nlp_models: dict[str, NlpModelRegistryEntry] = {}
        self.nlp_evaluations: dict[str, NlpEvaluationRun] = {}
        self.ingestion_runs: list[IngestionRun] = []
        self.raw_articles: dict[str, RawArticle] = {}
        self.articles: dict[UUID, Article] = {}
        self.articles_by_hash: dict[str, Article] = {}
        self.duplicates: list[ArticleDuplicate] = []
        self.observation_dispositions: dict[str, ObservationDisposition] = {}
        self.companies: dict[str, Company] = {}
        self.aliases: list[CompanyAlias] = []
        self.links: dict[UUID, list[ArticleCompanyLink]] = {}
        self.events: dict[UUID, ArticleEvent] = {}
        self.sentiments: dict[UUID, ArticleSentiment] = {}
        self.digests: dict[date, DailyDigest] = {}
        self.signals: dict[tuple[date, UUID], DailyCompanySignal] = {}
        self.pipeline_runs: list[PipelineRun] = []
        self.research_calendars: dict[tuple[str, str], ResearchCalendar] = {}
        self.research_sessions: dict[tuple[str, str], list[ResearchSession]] = {}
        self.research_exports: dict[str, ResearchExportRun] = {}
        self.research_feature_rows: dict[str, ResearchFeatureRow] = {}
        self.research_lineage_rows: dict[str, ResearchLineageRow] = {}
        self.assets: dict[str, Asset] = {}
        self.asset_aliases: dict[str, SymbolAlias] = {}
        self.provider_symbols: dict[str, ProviderSymbol] = {}
        self.broker_symbol_mappings: dict[str, BrokerSymbolMapping] = {}
        self.asset_relationships: dict[str, AssetRelationship] = {}
        self.cross_asset_events: dict[str, CrossAssetEvent] = {}
        self.asset_impacts: dict[str, AssetImpactHypothesis] = {}
        self.market_signals: dict[str, MarketSignalCandidate] = {}
        self.signal_publication_runs: dict[str, SignalPublicationRun] = {}
        self.official_datasets: dict[str, OfficialDataset] = {}
        self.official_series_profiles: dict[str, OfficialSeriesProfile] = {}
        self.official_observations: dict[str, OfficialObservation] = {}
        self.official_observation_revisions: dict[
            tuple[str, int], OfficialObservationRevision
        ] = {}
        self.official_data_release_runs: dict[str, OfficialDataReleaseRun] = {}
        self.regulatory_documents: dict[str, RegulatoryDocument] = {}
        self.series_asset_associations: dict[str, SeriesAssetAssociation] = {}
        self.official_release_events: dict[str, OfficialReleaseEvent] = {}

    def upsert_source(self, source: Source) -> Source:
        existing = self.sources.get(source.source_key)
        if existing:
            return existing
        self.sources[source.source_key] = source
        return source

    def upsert_source_definition(self, definition: SourceDefinition) -> SourceDefinition:
        self.source_definitions[definition.source_id] = definition
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
        return definition

    def list_source_definitions(self) -> list[SourceDefinition]:
        return sorted(self.source_definitions.values(), key=lambda item: item.source_id)

    def get_source_definition(self, source_id: str) -> SourceDefinition | None:
        return self.source_definitions.get(source_id)

    def upsert_source_fetch_state(self, state: SourceFetchState) -> SourceFetchState:
        self.source_fetch_states[state.source_id] = state
        return state

    def get_source_fetch_state(self, source_id: str) -> SourceFetchState | None:
        return self.source_fetch_states.get(source_id)

    def list_source_fetch_states(self) -> list[SourceFetchState]:
        return sorted(self.source_fetch_states.values(), key=lambda item: item.source_id)

    def add_source_fetch_attempt(self, attempt: SourceFetchAttempt) -> SourceFetchAttempt:
        self.source_fetch_attempts.append(attempt)
        return attempt

    def list_source_fetch_attempts(self) -> list[SourceFetchAttempt]:
        return sorted(
            self.source_fetch_attempts,
            key=lambda item: (item.started_at, item.source_id, item.id),
            reverse=True,
        )

    def upsert_nlp_model(self, model: NlpModelRegistryEntry) -> NlpModelRegistryEntry:
        self.nlp_models[model.model_id] = model
        return model

    def get_nlp_model(self, model_id: str) -> NlpModelRegistryEntry | None:
        return self.nlp_models.get(model_id)

    def list_nlp_models(
        self, task: str | None = None, status: str | None = None
    ) -> list[NlpModelRegistryEntry]:
        rows = list(self.nlp_models.values())
        if task:
            rows = [row for row in rows if row.task == task]
        if status:
            rows = [row for row in rows if row.status == status]
        return sorted(rows, key=lambda item: (item.task, item.model_id))

    def upsert_nlp_evaluation(self, evaluation: NlpEvaluationRun) -> NlpEvaluationRun:
        self.nlp_evaluations[evaluation.evaluation_id] = evaluation
        return evaluation

    def get_nlp_evaluation(self, evaluation_id: str) -> NlpEvaluationRun | None:
        return self.nlp_evaluations.get(evaluation_id)

    def list_nlp_evaluations(
        self, task: str | None = None, model_id: str | None = None
    ) -> list[NlpEvaluationRun]:
        rows = list(self.nlp_evaluations.values())
        if task:
            rows = [row for row in rows if row.task == task]
        if model_id:
            rows = [row for row in rows if row.model_id == model_id]
        return sorted(rows, key=lambda item: (item.evaluated_at, item.evaluation_id), reverse=True)

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

    def add_observation_disposition(self, disposition: ObservationDisposition) -> None:
        self.observation_dispositions[disposition.observation_id] = disposition

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

    def list_observation_dispositions(self) -> list[ObservationDisposition]:
        return sorted(self.observation_dispositions.values(), key=lambda item: item.observation_id)

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

    def get_article_by_hash(self, exact_content_hash: str) -> Article | None:
        return self.articles_by_hash.get(exact_content_hash)

    def get_raw_article_by_id(self, raw_article_id: UUID) -> RawArticle | None:
        for raw in self.raw_articles.values():
            if raw.id == raw_article_id:
                return raw
        return None

    def get_company_by_ticker(self, ticker: str) -> Company | None:
        return self.companies.get(ticker.upper())

    def get_digest(self, digest_date: date) -> DailyDigest | None:
        return self.digests.get(digest_date)

    def upsert_research_calendar(
        self, calendar: ResearchCalendar, sessions: Sequence[ResearchSession]
    ) -> ResearchCalendar:
        key = (calendar.calendar_id, calendar.calendar_version)
        self.research_calendars[key] = calendar
        self.research_sessions[key] = sorted(sessions, key=lambda item: item.sequence)
        return calendar

    def get_research_calendar(self, calendar_id: str) -> ResearchCalendar | None:
        matches = [
            item
            for (stored_id, _), item in self.research_calendars.items()
            if stored_id == calendar_id
        ]
        return sorted(matches, key=lambda item: item.calendar_version)[-1] if matches else None

    def list_research_calendars(self) -> list[ResearchCalendar]:
        return sorted(
            self.research_calendars.values(),
            key=lambda item: (item.calendar_id, item.calendar_version),
        )

    def list_research_sessions(
        self, calendar_id: str, calendar_version: str | None = None
    ) -> list[ResearchSession]:
        rows: list[ResearchSession] = []
        for (stored_id, stored_version), sessions in self.research_sessions.items():
            if stored_id == calendar_id and (
                calendar_version is None or stored_version == calendar_version
            ):
                rows.extend(sessions)
        return sorted(rows, key=lambda item: (item.calendar_id, item.sequence))

    def upsert_research_export(
        self,
        export_run: ResearchExportRun,
        feature_rows: Sequence[ResearchFeatureRow],
        lineage_rows: Sequence[ResearchLineageRow],
    ) -> ResearchExportRun:
        self.research_exports[export_run.export_id] = export_run
        for feature_row in feature_rows:
            self.research_feature_rows[feature_row.logical_key] = feature_row
        for lineage_row in lineage_rows:
            self.research_lineage_rows[lineage_row.lineage_row_id] = lineage_row
        return export_run

    def get_research_export(self, export_id: str) -> ResearchExportRun | None:
        return self.research_exports.get(export_id)

    def list_research_exports(self) -> list[ResearchExportRun]:
        return sorted(self.research_exports.values(), key=lambda item: item.export_id)

    def list_research_feature_rows(
        self,
        export_id: str | None = None,
        ticker: str | None = None,
        window_sessions: int | None = None,
    ) -> list[ResearchFeatureRow]:
        rows = list(self.research_feature_rows.values())
        if export_id:
            rows = [row for row in rows if row.export_id == export_id]
        if ticker:
            rows = [row for row in rows if row.ticker == ticker.upper()]
        if window_sessions:
            rows = [row for row in rows if row.window_sessions == window_sessions]
        return sorted(rows, key=lambda item: item.logical_key)

    def get_research_lineage_row(self, lineage_row_id: str) -> ResearchLineageRow | None:
        return self.research_lineage_rows.get(lineage_row_id)

    def list_research_lineage_rows(self, export_id: str | None = None) -> list[ResearchLineageRow]:
        rows = list(self.research_lineage_rows.values())
        if export_id:
            rows = [row for row in rows if row.export_id == export_id]
        return sorted(rows, key=lambda item: item.lineage_row_id)

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
        self.assets = {row.asset_id: row for row in assets}
        self.asset_aliases = {str(row.id): row for row in aliases}
        self.provider_symbols = {str(row.id): row for row in provider_symbols}
        self.broker_symbol_mappings = {str(row.id): row for row in broker_mappings}
        self.asset_relationships = {row.relationship_id: row for row in relationships}
        self.cross_asset_events = {row.event_id: row for row in events}
        self.asset_impacts = {row.impact_id: row for row in impacts}
        self.market_signals = {row.signal_id: row for row in signals}
        self.signal_publication_runs = {publication_run.run_id: publication_run}

    def list_assets(self) -> list[Asset]:
        return sorted(self.assets.values(), key=lambda item: item.asset_id)

    def get_asset(self, asset_id: str) -> Asset | None:
        return self.assets.get(asset_id)

    def list_asset_aliases(self, asset_id: str | None = None) -> list[SymbolAlias]:
        rows = list(self.asset_aliases.values())
        if asset_id:
            rows = [row for row in rows if row.asset_id == asset_id]
        return sorted(rows, key=lambda item: (item.asset_id, item.namespace.value, item.symbol))

    def list_asset_relationships(self, asset_id: str | None = None) -> list[AssetRelationship]:
        rows = list(self.asset_relationships.values())
        if asset_id:
            rows = [
                row
                for row in rows
                if row.source_asset_id == asset_id or row.target_asset_id == asset_id
            ]
        return sorted(rows, key=lambda item: item.relationship_id)

    def list_cross_asset_events(self) -> list[CrossAssetEvent]:
        return sorted(self.cross_asset_events.values(), key=lambda item: item.event_id)

    def list_asset_impact_hypotheses(
        self, asset_id: str | None = None, event_id: str | None = None
    ) -> list[AssetImpactHypothesis]:
        rows = list(self.asset_impacts.values())
        if asset_id:
            rows = [row for row in rows if row.asset_id == asset_id]
        if event_id:
            rows = [row for row in rows if row.event_id == event_id]
        return sorted(rows, key=lambda item: item.impact_id)

    def list_market_signal_candidates(
        self, asset_id: str | None = None, status: str | None = None
    ) -> list[MarketSignalCandidate]:
        rows = list(self.market_signals.values())
        if asset_id:
            rows = [row for row in rows if row.asset_id == asset_id]
        if status:
            rows = [row for row in rows if row.status.value == status]
        return sorted(rows, key=lambda item: item.signal_id)

    def upsert_official_dataset(self, dataset: OfficialDataset) -> OfficialDataset:
        self.official_datasets[dataset.dataset_id] = dataset
        return dataset

    def upsert_official_series_profile(
        self, profile: OfficialSeriesProfile
    ) -> OfficialSeriesProfile:
        self.official_series_profiles[profile.profile_id] = profile
        return profile

    def upsert_official_observation(
        self,
        observation: OfficialObservation,
        revision: OfficialObservationRevision,
    ) -> OfficialObservation:
        self.official_observations[observation.observation_key] = observation
        self.official_observation_revisions[
            (revision.observation_key, revision.revision_number)
        ] = revision
        return observation

    def add_official_data_release_run(
        self, run: OfficialDataReleaseRun
    ) -> OfficialDataReleaseRun:
        self.official_data_release_runs[run.release_run_id] = run
        return run

    def upsert_regulatory_document(self, document: RegulatoryDocument) -> RegulatoryDocument:
        self.regulatory_documents[document.document_id] = document
        return document

    def upsert_series_asset_association(
        self, association: SeriesAssetAssociation
    ) -> SeriesAssetAssociation:
        self.series_asset_associations[association.association_id] = association
        return association

    def upsert_official_release_event(self, event: OfficialReleaseEvent) -> OfficialReleaseEvent:
        self.official_release_events[event.event_id] = event
        return event

    def list_official_datasets(self) -> list[OfficialDataset]:
        return sorted(self.official_datasets.values(), key=lambda item: item.dataset_id)

    def list_official_series_profiles(
        self, source_id: str | None = None
    ) -> list[OfficialSeriesProfile]:
        rows = list(self.official_series_profiles.values())
        if source_id:
            rows = [row for row in rows if row.source_id == source_id]
        return sorted(rows, key=lambda item: item.profile_id)

    def list_official_observations(
        self,
        dataset_id: str | None = None,
        profile_id: str | None = None,
    ) -> list[OfficialObservation]:
        rows = list(self.official_observations.values())
        if dataset_id:
            rows = [row for row in rows if row.dataset_id == dataset_id]
        if profile_id:
            rows = [row for row in rows if row.profile_id == profile_id]
        return sorted(rows, key=lambda item: (item.profile_id, item.period_start))

    def list_official_observation_revisions(
        self, observation_key: str | None = None
    ) -> list[OfficialObservationRevision]:
        rows = list(self.official_observation_revisions.values())
        if observation_key:
            rows = [row for row in rows if row.observation_key == observation_key]
        return sorted(rows, key=lambda item: (item.observation_key, item.revision_number))

    def list_official_data_release_runs(self) -> list[OfficialDataReleaseRun]:
        return sorted(
            self.official_data_release_runs.values(),
            key=lambda item: (item.observed_at, item.release_run_id),
            reverse=True,
        )

    def list_regulatory_documents(self) -> list[RegulatoryDocument]:
        return sorted(
            self.regulatory_documents.values(),
            key=lambda item: (item.publication_date, item.document_id),
            reverse=True,
        )

    def list_series_asset_associations(
        self,
        profile_id: str | None = None,
        asset_id: str | None = None,
    ) -> list[SeriesAssetAssociation]:
        rows = list(self.series_asset_associations.values())
        if profile_id:
            rows = [row for row in rows if row.profile_id == profile_id]
        if asset_id:
            rows = [row for row in rows if row.asset_id == asset_id]
        return sorted(rows, key=lambda item: item.association_id)

    def list_official_release_events(self) -> list[OfficialReleaseEvent]:
        return sorted(self.official_release_events.values(), key=lambda item: item.event_id)
