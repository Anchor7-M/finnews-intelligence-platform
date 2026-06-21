from __future__ import annotations

from pathlib import Path

from finnews.application.services.pipeline import NewsPipeline
from finnews.domain.entities import SourceRecord
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
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


def load_default_records(settings: Settings) -> list[SourceRecord]:
    jsonl = JsonlFixtureSource(
        FIXTURE_DIR / "articles.jsonl", settings.max_fixture_bytes
    ).read_records()
    feed = LocalFeedSource(
        FIXTURE_DIR / "sample_feed.xml", settings.max_fixture_bytes
    ).read_records()
    return [*jsonl, *feed]
