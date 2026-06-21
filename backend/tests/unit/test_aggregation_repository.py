from __future__ import annotations

from datetime import date

from finnews.application.services.export_static import build_static_payload
from finnews.application.services.pipeline import NewsPipeline
from finnews.bootstrap import FIXTURE_DIR, load_default_records
from finnews.domain.errors import NotFoundError
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.settings import Settings


def build_repo() -> MemoryNewsRepository:
    settings = Settings(profile="memory")
    repo = MemoryNewsRepository()
    NewsPipeline(repo, settings).run_demo(
        load_default_records(settings), FIXTURE_DIR / "companies.json"
    )
    return repo


def test_pipeline_reports_raw_canonical_duplicate_digest_and_signal_counts() -> None:
    repo = build_repo()
    run = repo.list_pipeline_runs()[-1]
    assert run.per_step_counts["ingest_fetched"] == 68
    assert run.per_step_counts["ingest_rejected"] == 4
    assert run.per_step_counts["ingest_exact_duplicate"] >= 8
    assert run.per_step_counts["ingest_near_duplicate"] >= 10
    assert len(repo.list_companies()) == 12
    assert len({article.source_key for article in repo.list_articles()}) >= 5
    canonical_articles = [
        item for item in repo.list_articles() if item.processing_state.value == "processed"
    ]
    assert len(canonical_articles) < run.per_step_counts["ingest_fetched"]
    assert repo.list_digests()
    assert repo.list_signals()


def test_aggregation_fields_and_empty_date_behavior_are_deterministic() -> None:
    repo = build_repo()
    pipeline = NewsPipeline(repo, Settings(profile="memory"))
    empty = pipeline.generate_digest(date(2030, 1, 1))
    assert empty.article_count == 0
    assert empty.company_count == 0
    signal = repo.list_signals()[0]
    assert signal.article_count >= 1
    assert signal.unique_source_count >= 1
    assert -1 <= signal.weighted_sentiment_score <= 1
    assert signal.negative_event_count >= 0
    assert 0 <= signal.novelty_score <= 1
    assert 0 <= signal.source_diversity_score <= 1
    payload = build_static_payload(repo)
    assert payload["overview"]["article_count"] == len(repo.list_articles())


def test_memory_repository_uniqueness_update_read_and_not_found_behavior() -> None:
    repo = build_repo()
    article = repo.list_articles()[0]
    company = repo.list_companies()[0]
    assert repo.get_article(article.id) == article
    assert repo.get_company_by_ticker(company.ticker.lower()) == company
    assert repo.get_article(company.id) is None
    assert repo.get_company_by_ticker("NOPE") is None
    assert repo.upsert_digest(repo.list_digests()[0]) == repo.get_digest(
        repo.list_digests()[0].digest_date
    )
    assert NotFoundError("demo").args[0] == "demo"
