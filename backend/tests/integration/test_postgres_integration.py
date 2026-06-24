from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from alembic import command
from finnews.application.services.cross_asset import (
    build_cross_asset_demo,
    cross_asset_static_payload,
    persist_cross_asset_demo,
)
from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.application.services.export_static import build_static_payload
from finnews.application.services.official_data import (
    build_official_data_release_ledger,
    official_data_overview,
    persist_official_data_demo,
)
from finnews.application.services.pipeline import NewsPipeline
from finnews.application.services.research_export import (
    build_research_export,
    persist_research_export,
)
from finnews.bootstrap import FIXTURE_DIR, load_default_records
from finnews.domain.entities import (
    NlpEvaluationRun,
    NlpModelRegistryEntry,
    SourceDefinition,
    SourceFetchAttempt,
    SourceFetchState,
)
from finnews.domain.enums import FetchOutcome, SourceApprovalStatus, SourceHealthStatus, SourceType
from finnews.domain.value_objects import utc_now
from finnews.infrastructure.persistence.postgres.models import (
    ArticleCompanyLinkModel,
    AssetImpactHypothesisModel,
    AssetModel,
    CompanyModel,
    MarketBarModel,
    MarketBarRevisionModel,
    MarketBarSeriesModel,
    MarketDataPackageModel,
    MarketReactionLabelModel,
    MarketReactionStudyModel,
    MarketSignalCandidateModel,
    OfficialDataReleaseRunModel,
    OfficialDatasetModel,
    OfficialObservationModel,
    OfficialObservationRevisionModel,
    OfficialReleaseEventModel,
    OfficialSeriesProfileModel,
    RawArticleModel,
    RegulatoryDocumentModel,
    SeriesAssetAssociationModel,
    SignalErrorCaseModel,
    SignalQualityMetricModel,
    SignalQualityRunModel,
    SourceModel,
)
from finnews.infrastructure.persistence.postgres.repository import PostgresNewsRepository
from finnews.interfaces.api.app import create_app
from finnews.interfaces.cli.app import app
from finnews.settings import Settings, get_settings

EXPECTED_TABLES = {
    "sources",
    "ingestion_runs",
    "raw_articles",
    "articles",
    "article_duplicates",
    "observation_dispositions",
    "companies",
    "company_aliases",
    "article_company_links",
    "article_events",
    "article_sentiments",
    "daily_digests",
    "daily_company_signals",
    "pipeline_runs",
    "source_definitions",
    "source_fetch_states",
    "source_fetch_attempts",
    "nlp_model_registry",
    "nlp_evaluation_runs",
    "research_calendars",
    "research_sessions",
    "research_export_runs",
    "research_feature_rows",
    "research_lineage_rows",
    "assets",
    "asset_symbol_aliases",
    "asset_provider_symbols",
    "broker_symbol_mappings",
    "asset_relationships",
    "cross_asset_events",
    "asset_impact_hypotheses",
    "market_signal_candidates",
    "signal_publication_runs",
    "official_datasets",
    "official_series_profiles",
    "official_observations",
    "official_observation_revisions",
    "official_data_release_runs",
    "regulatory_documents",
    "series_asset_associations",
    "official_release_events",
    "market_data_packages",
    "market_bar_series",
    "market_bars",
    "market_bar_revisions",
    "market_reaction_studies",
    "market_reaction_labels",
    "signal_quality_runs",
    "signal_quality_metrics",
    "signal_error_cases",
    "mt5_readonly_profiles",
    "mt5_readonly_symbol_mappings",
    "mt5_readonly_runs",
    "mt5_bar_export_manifests",
}
EXPECTED_METRICS = {
    "raw_observation_count": 68,
    "rejected_observation_count": 4,
    "valid_observation_count": 64,
    "canonical_article_count": 46,
    "exact_duplicate_observation_count": 8,
    "near_duplicate_observation_count": 10,
    "duplicate_observation_count": 18,
    "exact_duplicate_pair_count": 8,
    "near_duplicate_pair_count": 10,
    "duplicate_cluster_count": 18,
}


@pytest.fixture()
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("FINNEWS_PROFILE", "postgres")
    monkeypatch.setenv("FINNEWS_DATABASE_URL", os.environ["FINNEWS_DATABASE_URL"])
    get_settings.cache_clear()
    return Settings(profile="postgres", database_url=os.environ["FINNEWS_DATABASE_URL"])


@pytest.fixture()
def engine(settings: Settings) -> Iterator[Engine]:
    engine = create_engine(settings.database_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


def alembic_config() -> Config:
    return Config("alembic.ini")


def reset_schema() -> None:
    drop_schema_objects()
    command.upgrade(alembic_config(), "head")


def drop_schema_objects() -> None:
    engine = create_engine(os.environ["FINNEWS_DATABASE_URL"], future=True)
    with engine.begin() as connection:
        for table in [*EXPECTED_TABLES, "alembic_version"]:
            connection.execute(text(f"drop table if exists {table} cascade"))
    engine.dispose()


def session_for(settings: Settings) -> Session:
    maker = sessionmaker(
        bind=create_engine(settings.database_url, future=True, poolclass=NullPool),
        future=True,
    )
    return maker()


def run_full_pipeline(settings: Settings) -> PostgresNewsRepository:
    session = session_for(settings)
    repo = PostgresNewsRepository(session)
    NewsPipeline(repo, settings).run_demo(
        load_default_records(settings), FIXTURE_DIR / "companies.json"
    )
    session.commit()
    return repo


def table_counts(session: Session) -> dict[str, int]:
    return {
        table: session.execute(text(f"select count(*) from {table}")).scalar_one()
        for table in sorted(EXPECTED_TABLES)
    }


def model_count(session: Session, model: Any) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.postgres
def test_alembic_upgrade_downgrade_schema_types_constraints_and_indexes(engine: Engine) -> None:
    drop_schema_objects()
    inspector = inspect(engine)
    assert EXPECTED_TABLES.isdisjoint(set(inspector.get_table_names()))

    command.upgrade(alembic_config(), "head")
    assert ScriptDirectory.from_config(alembic_config()).get_current_head() == "0008_mt5_readonly"
    command.current(alembic_config())

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables)
    for table in EXPECTED_TABLES:
        assert inspector.get_pk_constraint(table)["constrained_columns"]
    assert ("source_id", "source_article_id") in {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("raw_articles")
    }
    assert ("ticker", "exchange") in {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("companies")
    }
    indexes = {item["name"] for item in inspector.get_indexes("articles")}
    assert {"ix_articles_published_at", "ix_articles_state"}.issubset(indexes)
    source_indexes = {item["name"] for item in inspector.get_indexes("source_fetch_attempts")}
    assert "ix_source_fetch_attempts_source_started" in source_indexes
    asset_indexes = {item["name"] for item in inspector.get_indexes("assets")}
    assert {"ix_assets_class_region", "ix_assets_status"}.issubset(asset_indexes)
    official_observation_indexes = {
        item["name"] for item in inspector.get_indexes("official_observations")
    }
    assert {
        "ix_official_observations_profile_period",
        "ix_official_observations_dataset",
    }.issubset(official_observation_indexes)
    assert "ix_official_series_source_dataset" in {
        item["name"] for item in inspector.get_indexes("official_series_profiles")
    }
    assert "ix_official_revisions_available" in {
        item["name"] for item in inspector.get_indexes("official_observation_revisions")
    }
    assert "ix_market_bars_asset_time" in {
        item["name"] for item in inspector.get_indexes("market_bars")
    }
    assert "ix_market_reaction_labels_scenario" in {
        item["name"] for item in inspector.get_indexes("market_reaction_labels")
    }
    assert inspector.get_foreign_keys("article_company_links")
    assert inspector.get_foreign_keys("source_fetch_states")

    with Session(engine) as session:
        rows = session.execute(
            text(
                """
                select column_name, udt_name, data_type
                from information_schema.columns
                where table_schema='public'
                """
            )
        ).all()
        by_column = {(row.column_name, row.udt_name, row.data_type) for row in rows}
        assert any(
            column_name == "id" and udt_name == "uuid"
            for column_name, udt_name, _data_type in by_column
        )
        assert ("raw_metadata", "jsonb", "jsonb") in by_column
        assert ("contract_metadata", "jsonb", "jsonb") in by_column
        assert ("evidence_codes", "jsonb", "jsonb") in by_column
        assert ("dimensions", "jsonb", "jsonb") in by_column
        assert ("quality_flags", "jsonb", "jsonb") in by_column
        assert ("provenance", "jsonb", "jsonb") in by_column
        assert ("metadata", "jsonb", "jsonb") in by_column
        assert ("published_at", "timestamptz", "timestamp with time zone") in by_column
        assert session.execute(text("show server_encoding")).scalar_one() == "UTF8"
        client_encoding = session.execute(text("select current_setting('client_encoding')"))
        assert client_encoding.scalar_one() == "UTF8"

    command.downgrade(alembic_config(), "base")
    assert EXPECTED_TABLES.isdisjoint(set(inspect(engine).get_table_names()))
    command.upgrade(alembic_config(), "head")
    assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))


@pytest.mark.postgres
def test_postgres_cross_asset_signal_foundation_idempotency(settings: Settings) -> None:
    reset_schema()
    session = session_for(settings)
    repo = PostgresNewsRepository(session)
    dataset = build_cross_asset_demo()
    persist_cross_asset_demo(repo, dataset)
    session.commit()

    assert len(repo.list_assets()) == 40
    assert len(repo.list_asset_aliases()) == 211
    assert len(repo.list_asset_relationships()) == len(dataset.relationships)
    assert len(repo.list_cross_asset_events()) == 100
    assert len(repo.list_asset_impact_hypotheses()) == 240
    assert len(repo.list_market_signal_candidates()) == 80
    first_counts = {
        "assets": session.scalar(select(func.count()).select_from(AssetModel)),
        "impacts": session.scalar(select(func.count()).select_from(AssetImpactHypothesisModel)),
        "signals": session.scalar(select(func.count()).select_from(MarketSignalCandidateModel)),
    }

    first_signal = repo.list_market_signal_candidates()[0]
    assert first_signal.information_cutoff_at.tzinfo is not None
    assert first_signal.status.value in {
        "research",
        "informational",
        "abstained",
        "rejected",
        "expired",
    }
    assert first_signal.evidence_codes
    first_asset = repo.list_assets()[0]
    assert first_asset.contract_metadata["contract_metadata_available"] is False
    assert "password" not in str(first_asset.provenance).lower()

    payload = cross_asset_static_payload()
    assert payload["cross-asset-overview"]["asset_count"] == 40
    assert payload["mt5-readiness"]["terminal_adapter_status"] == "optional_readonly_cli_only"
    assert payload["market-signal-contract-example"]["no_execution"] is True

    persist_cross_asset_demo(repo, dataset)
    session.commit()
    assert {
        "assets": session.scalar(select(func.count()).select_from(AssetModel)),
        "impacts": session.scalar(select(func.count()).select_from(AssetImpactHypothesisModel)),
        "signals": session.scalar(select(func.count()).select_from(MarketSignalCandidateModel)),
    } == first_counts
    session.close()


@pytest.mark.postgres
def test_postgres_official_data_foundation_idempotency_and_jsonb(settings: Settings) -> None:
    reset_schema()
    session = session_for(settings)
    repo = PostgresNewsRepository(session)
    counts = persist_official_data_demo(repo)
    session.commit()

    overview = official_data_overview(repo)
    assert counts["datasets"] == 4
    assert counts["series_profiles"] == 16
    assert counts["official_observation_revisions"] == 168
    assert overview["definition_count_total"] == 16
    assert overview["observation_count"] == 144
    assert overview["revision_count"] == 168
    assert overview["changed_value_revision_count"] == 24
    assert overview["revised_observation_count"] == 24
    assert overview["regulatory_document_count"] == 32
    assert overview["series_asset_association_count"] == 80
    assert overview["official_release_event_count"] == 48
    first_counts = {
        "datasets": model_count(session, OfficialDatasetModel),
        "series": model_count(session, OfficialSeriesProfileModel),
        "observations": model_count(session, OfficialObservationModel),
        "revisions": model_count(session, OfficialObservationRevisionModel),
        "release_runs": model_count(session, OfficialDataReleaseRunModel),
        "documents": model_count(session, RegulatoryDocumentModel),
        "associations": model_count(session, SeriesAssetAssociationModel),
        "events": model_count(session, OfficialReleaseEventModel),
    }
    assert first_counts == {
        "datasets": 4,
        "series": 16,
        "observations": 144,
        "revisions": 168,
        "release_runs": 4,
        "documents": 32,
        "associations": 80,
        "events": 48,
    }
    ledger = build_official_data_release_ledger(repo, postgres_table_counts=first_counts)
    assert ledger["observation_business_key_count"] == 144
    assert ledger["changed_value_revision_count"] == 24
    assert ledger["postgres_table_counts"] == first_counts
    first_revision = repo.list_official_observation_revisions()[0]
    assert first_revision.information_available_at.tzinfo is not None
    assert isinstance(first_revision.provenance, dict)
    assert "password" not in str(first_revision.provenance).lower()
    assert repo.list_official_observations()[0].dimensions

    second_counts = persist_official_data_demo(repo)
    session.commit()
    assert second_counts["official_observation_revisions"] == 0
    assert second_counts["official_observation_unchanged"] == 168
    assert {
        "datasets": model_count(session, OfficialDatasetModel),
        "series": model_count(session, OfficialSeriesProfileModel),
        "observations": model_count(session, OfficialObservationModel),
        "revisions": model_count(session, OfficialObservationRevisionModel),
        "release_runs": model_count(session, OfficialDataReleaseRunModel),
        "documents": model_count(session, RegulatoryDocumentModel),
        "associations": model_count(session, SeriesAssetAssociationModel),
        "events": model_count(session, OfficialReleaseEventModel),
    } == first_counts
    session.close()


@pytest.mark.postgres
def test_postgres_repository_pipeline_idempotency_and_memory_parity(settings: Settings) -> None:
    reset_schema()
    repo = run_full_pipeline(settings)
    accounting = build_deduplication_accounting(repo)
    assert accounting.metrics == EXPECTED_METRICS
    assert len(repo.list_companies()) == 12
    assert len(repo.list_digests()) == 7
    assert len(repo.list_signals()) == 46
    canonical_ids = {
        item.canonical_article_id
        for item in repo.list_observation_dispositions()
        if item.disposition in {"exact_duplicate", "near_duplicate"}
    }
    assert accounting.metrics["duplicate_cluster_count"] == len(canonical_ids)

    first_counts = table_counts(repo.session)
    print(f"postgres_first_run_counts={first_counts}")
    print(f"postgres_deduplication_metrics={accounting.metrics}")
    assert first_counts["sources"] == 5
    assert first_counts["raw_articles"] == 64
    assert first_counts["articles"] == 56
    assert first_counts["article_duplicates"] == 10
    assert first_counts["observation_dispositions"] == 68
    assert first_counts["pipeline_runs"] == 1

    first_assignments = accounting.canonical_assignments
    repo.session.close()
    second_repo = run_full_pipeline(settings)
    second_accounting = build_deduplication_accounting(second_repo)
    second_counts = table_counts(second_repo.session)
    print(f"postgres_second_run_counts={second_counts}")
    assert second_accounting.metrics == EXPECTED_METRICS
    assert second_accounting.canonical_assignments == first_assignments
    stable_tables = set(first_counts) - {"ingestion_runs", "pipeline_runs"}
    assert {key: second_counts[key] for key in stable_tables} == {
        key: first_counts[key] for key in stable_tables
    }
    assert second_counts["pipeline_runs"] == first_counts["pipeline_runs"] + 1
    assert second_counts["ingestion_runs"] == first_counts["ingestion_runs"] + 68
    second_repo.session.close()


@pytest.mark.postgres
def test_postgres_research_export_metadata_parity(settings: Settings) -> None:
    reset_schema()
    repo = run_full_pipeline(settings)
    package = build_research_export(repo, persist_metadata=False)
    persist_research_export(repo, package)
    repo.session.commit()

    assert repo.get_research_calendar(package.calendar.calendar_id) is not None
    assert len(repo.list_research_sessions(package.calendar.calendar_id)) == 60
    assert repo.get_research_export(package.export_id).package_hash == package.package_hash  # type: ignore[union-attr]
    assert len(repo.list_research_feature_rows(package.export_id)) == 2880
    assert len(repo.list_research_lineage_rows(package.export_id)) == len(package.lineage_rows)
    first_row = repo.list_research_feature_rows(package.export_id)[0]
    assert isinstance(first_row.features, dict)
    assert "title" not in str(repo.list_research_lineage_rows(package.export_id)[0].payload).lower()

    persist_research_export(repo, package)
    repo.session.commit()
    assert len(repo.list_research_feature_rows(package.export_id)) == 2880
    repo.session.close()


@pytest.mark.postgres
def test_postgres_market_reaction_metadata_jsonb_timezone_and_constraints(
    settings: Settings,
) -> None:
    reset_schema()
    session = session_for(settings)
    now = utc_now()
    package = MarketDataPackageModel(
        package_id="synthetic-planted-reaction-v1|package",
        contract_name="finnews-market-bars-v1",
        contract_version="1.0.0",
        scenario_id="synthetic-planted-reaction-v1",
        provider="finnews-synthetic-market-reaction",
        provider_version="market-reaction-synthetic-v1",
        asset_count=1,
        bar_count=1,
        session_count=1,
        content_hash="a" * 64,
        synthetic=True,
        user_imported=False,
        live_data=False,
        metadata_={"no_live_market_data": True},
    )
    series = MarketBarSeriesModel(
        series_id="series-1",
        package_id=package.package_id,
        scenario_id=package.scenario_id,
        asset_id="US-EQ-ALPHA",
        provider_symbol="ALPHA.DEMO",
        granularity="daily",
        timezone="UTC",
        synthetic=True,
        metadata_={"source_profile": "synthetic-test"},
    )
    bar = MarketBarModel(
        bar_id="bar-1",
        series_id=series.series_id,
        scenario_id=series.scenario_id,
        asset_id=series.asset_id,
        session_date=date(2026, 5, 1),
        bar_start_at=now,
        bar_end_at=now,
        available_at=now,
        current_revision=1,
        open=Decimal("100.000000"),
        high=Decimal("101.000000"),
        low=Decimal("99.000000"),
        close=Decimal("100.000000"),
        volume=Decimal("1000.000000"),
        quote_volume=Decimal("100000.000000"),
        market_state="calm",
        synthetic=True,
        quality_flags=[],
    )
    revision = MarketBarRevisionModel(
        bar_id=bar.bar_id,
        revision_number=1,
        first_seen_at=now,
        available_at=now,
        open=Decimal("100.000000"),
        high=Decimal("101.000000"),
        low=Decimal("99.000000"),
        close=Decimal("100.000000"),
        volume=Decimal("1000.000000"),
        quote_volume=Decimal("100000.000000"),
        value_hash="b" * 64,
        quality_flags=[],
    )
    study = MarketReactionStudyModel(
        study_id="study-1",
        scenario_id=package.scenario_id,
        signal_id="SIGNAL-1",
        impact_id="IMPACT-1",
        asset_id=series.asset_id,
        event_family="monetary_policy",
        decision_time=now,
        reaction_window="one_day",
        bar_coverage=1,
        raw_return=Decimal("0.01000000"),
        benchmark_return=Decimal("0.00100000"),
        abnormal_return=Decimal("0.00900000"),
        excluded_reason=None,
        quality_flags=[],
        synthetic=True,
    )
    label = MarketReactionLabelModel(
        label_id="label-1",
        study_id=study.study_id,
        scenario_id=study.scenario_id,
        signal_id=study.signal_id,
        asset_id=study.asset_id,
        horizon="one_day",
        label="consistent_positive",
        threshold_version="m3c-label-threshold-v1",
        abnormal_return=Decimal("0.00900000"),
        coverage=1,
        quality_flags=[],
        point_in_time_evidence={"bar_available_after_decision": True},
        synthetic=True,
    )
    quality_run = SignalQualityRunModel(
        run_id="quality-run-1",
        scenario_id=package.scenario_id,
        generated_at=now,
        metric_count=1,
        content_hash="c" * 64,
        synthetic=True,
        metadata_={"leakage_status": "PASS"},
    )
    metric = SignalQualityMetricModel(
        metric_id="metric-1",
        scenario_id=package.scenario_id,
        slice_type="scenario",
        slice_value="all",
        evaluated_signal_count=1,
        coverage=Decimal("1.000000"),
        directional_consistency_rate=Decimal("1.000000"),
        opposite_rate=Decimal("0.000000"),
        muted_rate=Decimal("0.000000"),
        metrics={"information_coefficient": None},
        synthetic=True,
    )
    error_case = SignalErrorCaseModel(
        error_case_id="error-1",
        scenario_id=package.scenario_id,
        signal_id=study.signal_id,
        asset_id=study.asset_id,
        event_family=study.event_family,
        expected_direction="positive",
        observed_label="consistent_positive",
        abnormal_return=Decimal("0.00900000"),
        horizon="one_day",
        regime="calm",
        error_category="diagnostic",
        metadata_={"overclaim_guardrail": "diagnostic only"},
        synthetic=True,
    )
    session.add_all(
        [
            package,
            series,
            bar,
            revision,
            study,
            label,
            quality_run,
            metric,
            error_case,
        ]
    )
    session.commit()

    assert model_count(session, MarketDataPackageModel) == 1
    assert model_count(session, MarketBarSeriesModel) == 1
    assert model_count(session, MarketBarModel) == 1
    assert model_count(session, MarketBarRevisionModel) == 1
    assert model_count(session, MarketReactionStudyModel) == 1
    assert model_count(session, MarketReactionLabelModel) == 1
    assert model_count(session, SignalQualityRunModel) == 1
    assert model_count(session, SignalQualityMetricModel) == 1
    assert model_count(session, SignalErrorCaseModel) == 1
    stored_package = session.scalar(select(MarketDataPackageModel))
    assert stored_package is not None
    assert stored_package.metadata_["no_live_market_data"] is True
    stored_label = session.scalar(select(MarketReactionLabelModel))
    assert stored_label is not None
    assert stored_label.point_in_time_evidence["bar_available_after_decision"]

    session.add(
        MarketDataPackageModel(
            package_id=package.package_id,
            contract_name=package.contract_name,
            contract_version=package.contract_version,
            scenario_id=package.scenario_id,
            provider=package.provider,
            provider_version=package.provider_version,
            asset_count=1,
            bar_count=1,
            session_count=1,
            content_hash="d" * 64,
            synthetic=True,
            user_imported=False,
            live_data=False,
            metadata_={},
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
    session.close()


@pytest.mark.postgres
def test_postgres_mt5_readonly_metadata_schema_jsonb_and_idempotency(engine: Engine) -> None:
    reset_schema()
    inspector = inspect(engine)
    tables = {
        "mt5_readonly_profiles",
        "mt5_readonly_symbol_mappings",
        "mt5_readonly_runs",
        "mt5_bar_export_manifests",
    }
    assert tables.issubset(set(inspector.get_table_names()))

    forbidden_column_tokens = {
        "password",
        "login",
        "account",
        "order",
        "position",
        "stop_loss",
        "take_profit",
        "margin_required",
    }
    for table in tables:
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert not columns.intersection(forbidden_column_tokens)
        assert inspector.get_pk_constraint(table)["constrained_columns"]

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                insert into mt5_readonly_profiles
                (id, profile_id, display_name, enabled, created_at, updated_at, safe_metadata)
                values
                (
                    '11111111-1111-4111-8111-111111111111',
                    'local-demo',
                    'Local Demo',
                    true,
                    now(),
                    now(),
                    '{"terminal_access_status": "not_attempted"}'::jsonb
                )
                """
            )
        )
        connection.execute(
            text(
                """
                insert into mt5_readonly_symbol_mappings
                (
                    id,
                    profile_id,
                    canonical_asset_id,
                    mt5_symbol,
                    enabled,
                    display_name,
                    timezone,
                    safe_metadata,
                    created_at,
                    updated_at
                )
                values
                (
                    '22222222-2222-4222-8222-222222222222',
                    'local-demo',
                    'fx-eurusd-spot',
                    'SYNTH_EURUSD',
                    true,
                    'Synthetic EUR/USD',
                    'UTC',
                    '{"source": "test"}'::jsonb,
                    now(),
                    now()
                )
                on conflict do nothing
                """
            )
        )
        connection.execute(
            text(
                """
                insert into mt5_readonly_runs
                (
                    id,
                    run_id,
                    profile_id,
                    started_at,
                    finished_at,
                    status,
                    terminal_access_status,
                    mapped_asset_count,
                    exported_bar_count,
                    safe_metadata
                )
                values
                (
                    '33333333-3333-4333-8333-333333333333',
                    'run-local-demo',
                    'local-demo',
                    now(),
                    now(),
                    'no_data',
                    'read_only_ready',
                    1,
                    0,
                    '{"timeframe": "M5"}'::jsonb
                )
                on conflict do nothing
                """
            )
        )
        connection.execute(
            text(
                """
                insert into mt5_bar_export_manifests
                (
                    id,
                    manifest_id,
                    run_id,
                    contract_name,
                    contract_version,
                    timeframe,
                    asset_count,
                    bar_count,
                    content_hash,
                    logical_output_ref,
                    safe_counts,
                    created_at
                )
                values
                (
                    '44444444-4444-4444-8444-444444444444',
                    'manifest-local-demo',
                    'run-local-demo',
                    'finnews-market-bars',
                    '1.0.0',
                    'M5',
                    1,
                    0,
                    repeat('a', 64),
                    'mt5-readonly/local-demo',
                    '{"bars": 0}'::jsonb,
                    now()
                )
                on conflict do nothing
                """
            )
        )
        duplicate_count = connection.execute(
            text(
                """
                select count(*)
                from mt5_bar_export_manifests
                where manifest_id = 'manifest-local-demo'
                """
            )
        ).scalar_one()
        timezone_is_aware = connection.execute(
            text(
                """
                select pg_typeof(started_at)::text
                from mt5_readonly_runs
                where run_id = 'run-local-demo'
                """
            )
        ).scalar_one()
        jsonb_value = connection.execute(
            text(
                """
                select safe_metadata ->> 'timeframe'
                from mt5_readonly_runs
                where run_id = 'run-local-demo'
                """
            )
        ).scalar_one()

    assert duplicate_count == 1
    assert timezone_is_aware == "timestamp with time zone"
    assert jsonb_value == "M5"

    with engine.begin() as connection:
        transaction = connection.begin_nested()
        connection.execute(
            text(
                """
                insert into mt5_readonly_runs
                (
                    id,
                    run_id,
                    profile_id,
                    started_at,
                    status,
                    terminal_access_status,
                    mapped_asset_count,
                    exported_bar_count,
                    safe_metadata
                )
                values
                (
                    '55555555-5555-4555-8555-555555555555',
                    'rollback-run',
                    'local-demo',
                    now(),
                    'blocked',
                    'blocked_by_gate',
                    0,
                    0,
                    '{}'::jsonb
                )
                """
            )
        )
        transaction.rollback()
        rollback_count = connection.execute(
            text("select count(*) from mt5_readonly_runs where run_id = 'rollback-run'")
        ).scalar_one()
    assert rollback_count == 0


@pytest.mark.postgres
def test_repository_contract_constraints_jsonb_timezone_and_rollback(settings: Settings) -> None:
    reset_schema()
    repo = run_full_pipeline(settings)
    article = repo.list_articles()[0]
    assert repo.get_article(article.id) == article
    assert repo.get_article(article.id).published_at.tzinfo is not None  # type: ignore[union-attr]
    assert repo.get_company_by_ticker("alp").ticker == "ALP"  # type: ignore[union-attr]
    assert repo.get_digest(date(2026, 6, 20)) is not None
    raw = repo.session.scalar(select(RawArticleModel).where(RawArticleModel.raw_metadata != {}))
    assert raw is not None and isinstance(raw.raw_metadata, dict)
    payload = build_static_payload(repo)
    assert payload["overview"]["deduplication"] == EXPECTED_METRICS
    assert payload["articles"]

    duplicate_source = SourceModel(
        source_key="synthetic-jsonl-desk",
        display_name="duplicate",
        source_type="fixture",
        enabled=True,
        language_hints=[],
        ingestion_policy="metadata_only",
        rate_limit={},
        created_at=article.created_at,
        updated_at=article.updated_at,
    )
    repo.session.add(duplicate_source)
    with pytest.raises(IntegrityError):
        repo.session.flush()
    repo.session.rollback()
    assert repo.session.scalar(select(func.count()).select_from(SourceModel)) == 5

    link = repo.session.scalar(select(ArticleCompanyLinkModel))
    assert link is not None
    repo.session.add(
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
    with pytest.raises(IntegrityError):
        repo.session.flush()
    repo.session.rollback()
    assert repo.session.scalar(select(func.count()).select_from(CompanyModel)) == 12
    repo.session.close()


@pytest.mark.postgres
def test_source_state_repository_contract_jsonb_and_attempts(settings: Settings) -> None:
    reset_schema()
    session = session_for(settings)
    repo = PostgresNewsRepository(session)
    definition = repo.upsert_source_definition(
        SourceDefinition(
            source_id="pg-mock-rss",
            display_name="PG Mock RSS",
            source_type=SourceType.RSS,
            approved_hostnames=["mock.local"],
            review_status=SourceApprovalStatus.APPROVED,
            enabled=True,
            base_url="https://mock.local/rss.xml",
            terms_url="https://mock.local/terms",
            documentation_url="https://mock.local/docs",
            reviewer="test",
            field_mapping={"id": "id"},
            minimum_interval_seconds=0,
        )
    )
    state = repo.upsert_source_fetch_state(
        SourceFetchState(
            source_id=definition.source_id,
            etag='"pg"',
            last_modified="Mon, 22 Jun 2026 00:00:00 GMT",
            cursor="cursor-1",
            last_successful_at=utc_now(),
            last_response_hash="a" * 64,
            last_response_byte_count=100,
            last_item_count=2,
            health_status=SourceHealthStatus.HEALTHY,
        )
    )
    attempt = repo.add_source_fetch_attempt(
        SourceFetchAttempt(
            source_id=definition.source_id,
            outcome=FetchOutcome.SUCCESS,
            started_at=utc_now(),
            finished_at=utc_now(),
            http_status=200,
            item_count=2,
            new_count=2,
            response_byte_count=100,
            etag_present=True,
            last_modified_present=True,
        )
    )
    session.commit()
    assert repo.get_source_definition("pg-mock-rss") == definition
    assert repo.get_source_fetch_state("pg-mock-rss") == state
    assert repo.list_source_fetch_attempts()[0].id == attempt.id
    assert repo.list_source_definitions()[0].field_mapping == {"id": "id"}
    session.close()


@pytest.mark.postgres
def test_postgres_api_profile_matches_persisted_counts(settings: Settings) -> None:
    reset_schema()
    app_obj = create_app(settings)
    try:
        api = TestClient(app_obj)
        assert api.get("/health/live").json()["profile"] == "postgres"
        assert api.get("/health/ready").json()["status"] == "ready"
        first = api.get("/api/v1/articles", params={"limit": 1}).json()["items"][0]
        endpoints = [
            "/api/v1/articles",
            f"/api/v1/articles/{first['id']}",
            "/api/v1/companies",
            "/api/v1/companies/ALP/articles",
            "/api/v1/events",
            "/api/v1/digests/2026-06-20",
            "/api/v1/signals/daily",
            "/api/v1/pipeline-runs",
            "/api/v1/stats/overview",
        ]
        for endpoint in endpoints:
            assert api.get(endpoint, headers={"x-request-id": "pg"}).status_code == 200
        overview = api.get("/api/v1/stats/overview").json()
        assert overview["deduplication"] == EXPECTED_METRICS
        assert (
            api.get("/api/v1/articles", params={"ticker": "ALP", "limit": 2}).json()["total"] >= 1
        )
        assert api.get("/api/v1/articles", params={"language": "zh"}).json()["total"] >= 1
        assert api.get("/api/v1/articles", params={"limit": 101}).status_code == 422
        not_found = api.get("/api/v1/articles/00000000-0000-0000-0000-000000000000")
        assert not_found.status_code == 404
        assert not_found.json()["error"]["code"] == "not_found"
    finally:
        app_obj.state.repository.session.close()


@pytest.mark.postgres
def test_postgres_cli_profile_without_secret_output(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    reset_schema()
    monkeypatch.setenv("FINNEWS_PROFILE", "postgres")
    monkeypatch.setenv("FINNEWS_DATABASE_URL", settings.database_url)
    get_settings.cache_clear()
    runner = CliRunner()
    doctor = runner.invoke(app, ["doctor"])
    assert doctor.exit_code == 0
    assert "finnews:finnews" not in doctor.output
    upgrade = runner.invoke(app, ["db", "upgrade"])
    assert upgrade.exit_code == 0
    fixture = runner.invoke(
        app, ["ingest", "fixture", "--path", str(FIXTURE_DIR / "articles.jsonl")]
    )
    feed = runner.invoke(
        app, ["ingest", "local-feed", "--path", str(FIXTURE_DIR / "sample_feed.xml")]
    )
    process = runner.invoke(app, ["process"])
    digest = runner.invoke(app, ["digest", "--date", "2026-06-20"])
    signals = runner.invoke(app, ["signals", "--date", "2026-06-20"])
    for result in [fixture, feed, process, digest, signals]:
        assert result.exit_code == 0
        assert "finnews:finnews" not in result.output
    assert '"processed": 46' in process.output
    assert signals.output.startswith("[")


@pytest.mark.postgres
def test_postgres_nlp_model_registry_metadata_jsonb_and_rollback(settings: Settings) -> None:
    reset_schema()
    engine = create_engine(settings.database_url, future=True)
    session = Session(engine)
    repo = PostgresNewsRepository(session)
    model = NlpModelRegistryEntry(
        model_id="m2a-event-demo",
        task="event",
        provider="scikit_learn",
        model_kind="word_char_tfidf_logreg",
        status="demo_candidate",
        dataset_id="synthetic-finnews-nlp-v1",
        dataset_version="1.0.0",
        dataset_sha256="a" * 64,
        split_hashes={"train": "b" * 64, "validation": "c" * 64, "test": "d" * 64},
        label_set=["earnings", "other"],
        metrics={"macro_f1": 0.75, "per_class": {"earnings": {"recall": 1.0}}},
        calibration={"expected_calibration_error": 0.12},
        artifact_uri=None,
        artifact_sha256="e" * 64,
        artifact_size_bytes=1234,
        manifest_sha256="f" * 64,
        config_sha256="1" * 64,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    repo.upsert_nlp_model(model)
    repo.upsert_nlp_model(model)
    evaluation = NlpEvaluationRun(
        evaluation_id="m2a-event-demo-test",
        model_id=model.model_id,
        task="event",
        dataset_id=model.dataset_id,
        dataset_version=model.dataset_version,
        dataset_sha256=model.dataset_sha256,
        split_name="test",
        metrics={"selected_ml": {"macro_f1": 0.75}},
        slice_metrics={"language": [{"name": "zh", "macro_f1": 0.7}]},
        calibration={"alpha": 1.0},
        error_analysis={"confusion_pairs": []},
        selection_procedure={"test_set_used_for_selection": False},
        evaluated_at=utc_now(),
    )
    repo.upsert_nlp_evaluation(evaluation)
    session.commit()
    assert len(repo.list_nlp_models()) == 1
    persisted_model = repo.get_nlp_model(model.model_id)
    assert persisted_model is not None
    assert persisted_model.metrics["macro_f1"] == 0.75
    slice_json = cast(
        dict[str, list[dict[str, Any]]], repo.list_nlp_evaluations(task="event")[0].slice_metrics
    )
    assert slice_json["language"][0]["name"] == "zh"

    repo.upsert_nlp_model(
        NlpModelRegistryEntry(
            **{
                **model.__dict__,
                "model_id": "m2a-rollback",
                "artifact_sha256": "2" * 64,
            }
        )
    )
    session.rollback()
    assert repo.get_nlp_model("m2a-rollback") is None
    assert repo.get_nlp_model(model.model_id) is not None
    session.close()
    engine.dispose()
