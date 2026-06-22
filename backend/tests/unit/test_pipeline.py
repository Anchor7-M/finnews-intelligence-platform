from __future__ import annotations

from collections import Counter
from pathlib import Path

from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.application.services.pipeline import NewsPipeline
from finnews.bootstrap import FIXTURE_DIR, load_default_records
from finnews.domain.enums import ProcessingState, SentimentLabel
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.settings import Settings


def build_repo() -> MemoryNewsRepository:
    settings = Settings(profile="memory")
    repo = MemoryNewsRepository()
    NewsPipeline(repo, settings).run_demo(
        load_default_records(settings), FIXTURE_DIR / "companies.json"
    )
    return repo


def test_pipeline_rejects_malformed_record_and_is_idempotent() -> None:
    settings = Settings(profile="memory")
    repo = MemoryNewsRepository()
    pipeline = NewsPipeline(repo, settings)
    records = load_default_records(settings)
    first = pipeline.ingest_records(records)
    second = pipeline.ingest_records(records)
    assert first["rejected"] == 4
    assert second["exact_duplicate"] >= first["accepted"]


def test_full_demo_generates_articles_links_events_sentiments_digest_and_signals() -> None:
    repo = build_repo()
    accounting = build_deduplication_accounting(repo)
    assert accounting.metrics["canonical_article_count"] == 46
    assert accounting.metrics["exact_duplicate_observation_count"] == 8
    assert accounting.metrics["near_duplicate_observation_count"] == 10
    assert len(repo.list_companies()) == 12
    assert Counter(article.processing_state.value for article in repo.list_articles()) == {
        "processed": 46,
        "duplicate": 10,
    }
    assert repo.list_links()
    assert repo.list_events()
    assert repo.list_sentiments()
    assert repo.list_digests()
    assert repo.list_signals()


def test_exact_and_near_duplicate_behavior() -> None:
    repo = build_repo()
    exact_hashes = [article.exact_content_hash for article in repo.list_articles()]
    assert len(exact_hashes) == len(set(exact_hashes))
    assert any(
        article.processing_state is ProcessingState.DUPLICATE for article in repo.list_articles()
    )
    assert repo.list_duplicates()


def test_company_alias_resolution_prefers_known_companies() -> None:
    repo = build_repo()
    tickers = {company.ticker for company in repo.list_companies()}
    linked_company_ids = {link.company_id for link in repo.list_links()}
    linked_tickers = {
        company.ticker for company in repo.list_companies() if company.id in linked_company_ids
    }
    assert {"ALP", "BRC", "HLS", "NVM"}.issubset(tickers)
    assert {"ALP", "BRC", "HLS", "NVM"}.issubset(linked_tickers)


def test_event_and_sentiment_evidence() -> None:
    repo = build_repo()
    events = repo.list_events()
    sentiments = repo.list_sentiments()
    assert any(event.event_type.value == "earnings" and event.evidence for event in events)
    assert any(sentiment.label is SentimentLabel.NEGATIVE for sentiment in sentiments)
    assert all(-1 <= sentiment.score <= 1 for sentiment in sentiments)


def test_static_fixture_files_are_small() -> None:
    total = sum(
        path.stat().st_size for path in Path("..").resolve().joinpath("data", "fixtures").glob("*")
    )
    assert total < 5_000_000
