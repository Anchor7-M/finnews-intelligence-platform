from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from alembic import command
from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.application.services.export_static import build_static_payload
from finnews.application.services.pipeline import NewsPipeline
from finnews.bootstrap import FIXTURE_DIR, load_default_records
from finnews.infrastructure.persistence.postgres.models import (
    ArticleCompanyLinkModel,
    CompanyModel,
    RawArticleModel,
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
    maker = sessionmaker(bind=create_engine(settings.database_url, future=True), future=True)
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


@pytest.mark.postgres
def test_alembic_upgrade_downgrade_schema_types_constraints_and_indexes(engine: Engine) -> None:
    drop_schema_objects()
    inspector = inspect(engine)
    assert EXPECTED_TABLES.isdisjoint(set(inspector.get_table_names()))

    command.upgrade(alembic_config(), "head")
    assert ScriptDirectory.from_config(alembic_config()).get_current_head() == "0001_initial_schema"
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
    assert inspector.get_foreign_keys("article_company_links")

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
        assert ("published_at", "timestamptz", "timestamp with time zone") in by_column
        assert session.execute(text("show server_encoding")).scalar_one() == "UTF8"
        client_encoding = session.execute(text("select current_setting('client_encoding')"))
        assert client_encoding.scalar_one() == "UTF8"

    command.downgrade(alembic_config(), "base")
    assert EXPECTED_TABLES.isdisjoint(set(inspect(engine).get_table_names()))
    command.upgrade(alembic_config(), "head")
    assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))


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
