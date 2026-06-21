from __future__ import annotations

from datetime import timedelta
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from finnews.domain.entities import Article


def find_near_duplicate(
    candidate: Article,
    articles: list[Article],
    threshold: float,
    window_hours: int,
    max_candidates: int,
) -> tuple[Article, float] | None:
    lower = candidate.published_at - timedelta(hours=window_hours)
    upper = candidate.published_at + timedelta(hours=window_hours)
    pool = [
        item
        for item in articles
        if lower <= item.published_at <= upper
        and item.exact_content_hash != candidate.exact_content_hash
    ]
    pool = sorted(
        pool, key=lambda item: abs((candidate.published_at - item.published_at).total_seconds())
    )[:max_candidates]
    if not pool:
        return None
    corpus = [
        f"{candidate.normalized_title} {candidate.normalized_summary}",
        *[f"{item.normalized_title} {item.normalized_summary}" for item in pool],
    ]
    matrix = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(corpus)
    scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    candidate_text = corpus[0]
    blended_scores = [
        max(float(score), SequenceMatcher(None, candidate_text, comparison_text).ratio())
        for score, comparison_text in zip(scores, corpus[1:], strict=True)
    ]
    best_score = max(blended_scores)
    best_index = blended_scores.index(best_score)
    if best_score >= threshold:
        return pool[best_index], best_score
    return None
