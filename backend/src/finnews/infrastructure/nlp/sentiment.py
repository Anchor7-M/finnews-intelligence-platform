from __future__ import annotations

from finnews.domain.entities import Article, ArticleSentiment
from finnews.domain.enums import SentimentLabel
from finnews.infrastructure.normalization import comparison_text

POSITIVE = ["higher", "improved", "support", "resolved", "提升", "改善", "增长"]
NEGATIVE = ["risk", "pressure", "outage", "litigation", "interruption", "风险", "压力", "诉讼"]
UNCERTAIN = ["may", "uncertain", "cautious", "non-binding", "可能", "不确定", "评估"]
NEGATORS = ["not", "no", "暂无", "未"]


def analyze_sentiment(article: Article) -> ArticleSentiment:
    text = comparison_text(f"{article.normalized_title} {article.normalized_summary}")
    evidence: list[str] = []
    score = 0.0
    for word in POSITIVE:
        if comparison_text(word) in text:
            score += 0.35
            evidence.append(word)
    for word in NEGATIVE:
        if comparison_text(word) in text:
            score -= 0.35
            evidence.append(word)
    uncertain_hits = [word for word in UNCERTAIN if comparison_text(word) in text]
    evidence.extend(uncertain_hits)
    if any(word in text for word in NEGATORS) and score < 0:
        score += 0.15
    score = max(-1.0, min(1.0, score))
    if uncertain_hits and abs(score) < 0.5:
        label = SentimentLabel.UNCERTAIN
    elif score >= 0.25:
        label = SentimentLabel.POSITIVE
    elif score <= -0.25:
        label = SentimentLabel.NEGATIVE
    else:
        label = SentimentLabel.NEUTRAL
    return ArticleSentiment(
        article_id=article.id,
        score=round(score, 3),
        label=label,
        confidence=0.55 + min(0.35, 0.08 * len(evidence)),
        evidence=evidence,
    )
