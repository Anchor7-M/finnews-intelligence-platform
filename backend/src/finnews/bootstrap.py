from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from finnews.application.services.pipeline import NewsPipeline
from finnews.domain.entities import SourceRecord
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.persistence.postgres.repository import PostgresNewsRepository
from finnews.infrastructure.sources.fixtures import JsonlFixtureSource
from finnews.infrastructure.sources.local_feed import LocalFeedSource
from finnews.settings import Settings, get_settings

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "data" / "fixtures"


def build_memory_repository(settings: Settings | None = None) -> MemoryNewsRepository:
    settings = settings or get_settings()
    repository = MemoryNewsRepository()
    records = load_default_records(settings)
    pipeline = NewsPipeline(repository, settings)
    pipeline.run_demo(records, FIXTURE_DIR / "companies.json")
    return repository


def build_postgres_repository(
    settings: Settings | None = None, *, populate: bool = True
) -> PostgresNewsRepository:
    settings = settings or get_settings()
    session = create_postgres_session(settings)
    repository = PostgresNewsRepository(session)
    if populate:
        pipeline = NewsPipeline(repository, settings)
        pipeline.run_demo(load_default_records(settings), FIXTURE_DIR / "companies.json")
        session.commit()
    return repository


def build_repository(
    settings: Settings | None = None,
) -> MemoryNewsRepository | PostgresNewsRepository:
    settings = settings or get_settings()
    if settings.profile == "postgres":
        return build_postgres_repository(settings)
    return build_memory_repository(settings)


def create_postgres_session(settings: Settings) -> Session:
    engine = create_engine(settings.database_url, future=True)
    maker = sessionmaker(bind=engine, future=True)
    return maker()


def load_default_records(settings: Settings) -> list[SourceRecord]:
    jsonl = JsonlFixtureSource(
        FIXTURE_DIR / "articles.jsonl", settings.max_fixture_bytes
    ).read_records()
    feed = LocalFeedSource(
        FIXTURE_DIR / "sample_feed.xml", settings.max_fixture_bytes
    ).read_records()
    return [*jsonl, *feed]
