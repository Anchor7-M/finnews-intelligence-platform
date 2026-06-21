from __future__ import annotations

from finnews.domain.entities import Article, ArticleEvent
from finnews.domain.enums import EventType
from finnews.infrastructure.normalization import comparison_text

KEYWORDS: dict[EventType, list[str]] = {
    EventType.EARNINGS: ["earnings", "margin", "quarterly", "业绩", "利润"],
    EventType.MERGER_ACQUISITION: ["merger", "acquisition", "transaction", "并购", "收购"],
    EventType.POLICY_REGULATION: ["policy", "regulation", "监管", "政策", "规则"],
    EventType.OPERATIONS_PRODUCT: [
        "product",
        "platform",
        "outage",
        "resolved",
        "交付",
        "发布",
        "平台",
    ],
    EventType.FINANCING_CAPITAL: ["financing", "capital", "module line", "融资", "资本"],
    EventType.LITIGATION_PENALTY: ["litigation", "lawsuit", "penalty", "诉讼", "处罚"],
    EventType.GOVERNANCE_PERSONNEL: ["appoint", "chief", "leadership", "任命", "高管"],
    EventType.MACRO_MARKET: ["macro", "market", "inflation", "市场", "宏观"],
}


def classify_event(article: Article) -> ArticleEvent:
    text = comparison_text(f"{article.normalized_title} {article.normalized_summary}")
    best = EventType.OTHER
    evidence: list[str] = []
    for event_type, words in KEYWORDS.items():
        hits = [word for word in words if comparison_text(word) in text]
        if hits and len(hits) > len(evidence):
            best = event_type
            evidence = hits
    confidence = 0.45 if best is EventType.OTHER else min(0.95, 0.55 + 0.15 * len(evidence))
    return ArticleEvent(
        article_id=article.id, event_type=best, confidence=confidence, evidence=evidence
    )
