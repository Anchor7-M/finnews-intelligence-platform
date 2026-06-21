from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from finnews.domain.entities import Article
from finnews.infrastructure.nlp.deduplication import find_near_duplicate


def article(title: str, published_at: datetime) -> Article:
    return Article(
        canonical_raw_article_id=uuid4(),
        normalized_title=title,
        normalized_summary="Alpha service demand strongly improved margins for demo case.",
        language="en",
        published_at=published_at,
        local_market_date=published_at.date(),
        canonical_url=f"https://demo.local/{uuid4()}",
        exact_content_hash=str(uuid4()),
        source_key="test",
        source_name="Test",
    )


def test_near_duplicate_threshold_boundary_and_similarity_storage_value() -> None:
    now = datetime(2026, 6, 20, tzinfo=UTC)
    canonical = article("Alpine Robotics reports higher quarterly earnings on service demand", now)
    candidate = article(
        "Alpine Robotics reports higher quarterly earnings as service demand rises", now
    )
    assert find_near_duplicate(candidate, [canonical], 0.99, 72, 10) is None
    match = find_near_duplicate(candidate, [canonical], 0.80, 72, 10)
    assert match is not None
    assert match[0].id == canonical.id
    assert 0.80 <= match[1] <= 1.0


def test_candidate_window_and_max_candidate_count_are_bounded() -> None:
    now = datetime(2026, 6, 20, tzinfo=UTC)
    old_match = article(
        "Alpine Robotics reports higher quarterly earnings on service demand",
        now - timedelta(days=10),
    )
    recent_non_match = article("Unrelated routine calendar item", now)
    candidate = article(
        "Alpine Robotics reports higher quarterly earnings as service demand rises", now
    )
    assert find_near_duplicate(candidate, [old_match], 0.80, 24, 10) is None
    assert find_near_duplicate(candidate, [recent_non_match, old_match], 0.80, 24 * 30, 1) is None


def test_chinese_near_duplicate() -> None:
    now = datetime(2026, 6, 20, tzinfo=UTC)
    canonical = article("阿尔派机器人公布季度业绩增长", now)
    canonical.normalized_summary = "虚构公司阿尔派机器人表示服务需求改善，利润率明显提升。"
    candidate = article("阿尔派机器人公布季度业绩明显增长", now)
    candidate.normalized_summary = "虚构公司阿尔派机器人今日表示服务需求改善，利润率明显提升。"
    assert find_near_duplicate(candidate, [canonical], 0.80, 72, 10) is not None
