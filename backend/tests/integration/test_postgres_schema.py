from __future__ import annotations

import pytest

from finnews.infrastructure.persistence.postgres.models import Base


@pytest.mark.postgres
def test_postgres_metadata_contains_required_tables() -> None:
    required = {
        "sources",
        "ingestion_runs",
        "raw_articles",
        "articles",
        "article_duplicates",
        "companies",
        "company_aliases",
        "article_company_links",
        "article_events",
        "article_sentiments",
        "daily_digests",
        "daily_company_signals",
        "pipeline_runs",
    }
    assert required.issubset(Base.metadata.tables)
