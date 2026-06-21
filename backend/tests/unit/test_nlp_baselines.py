from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from finnews.domain.entities import Article, Company, CompanyAlias
from finnews.domain.enums import EventType, SentimentLabel
from finnews.infrastructure.nlp.events import classify_event
from finnews.infrastructure.nlp.linking import link_companies
from finnews.infrastructure.nlp.sentiment import analyze_sentiment
from finnews.infrastructure.normalization import comparison_text


def make_article(title: str, summary: str = "demo summary") -> Article:
    published = datetime(2026, 6, 20, tzinfo=UTC)
    return Article(
        canonical_raw_article_id=uuid4(),
        normalized_title=title,
        normalized_summary=summary,
        language="en",
        published_at=published,
        local_market_date=published.date(),
        canonical_url=f"https://demo.local/{uuid4()}",
        exact_content_hash=str(uuid4()),
        source_key="test",
        source_name="Test",
    )


def test_company_linking_alias_modes_and_unmatched_behavior() -> None:
    company = Company(
        "ALP", "SYN", "Alpine Robotics Holdings Ltd.", "Alpine Robotics", "Automation"
    )
    aliases = [
        CompanyAlias(company.id, "Alpine", comparison_text("Alpine")),
        CompanyAlias(company.id, "Alpine Robotics", comparison_text("Alpine Robotics")),
        CompanyAlias(company.id, "ALP", comparison_text("ALP")),
        CompanyAlias(
            company.id,
            "Alpine Robotics Holdings Ltd.",
            comparison_text("Alpine Robotics Holdings Ltd."),
        ),
    ]
    legal = link_companies(make_article("Alpine Robotics Holdings Ltd. update"), aliases)
    ticker = link_companies(make_article("ALP update"), aliases)
    short = link_companies(make_article("Alpine Robotics update"), aliases)
    assert legal[0].matched_alias == "Alpine Robotics Holdings Ltd."
    assert ticker[0].matched_alias == "ALP"
    assert short[0].matched_alias == "Alpine Robotics"
    assert short[0].confidence == 0.95
    assert short[0].evidence_text_span == "Alpine Robotics"
    assert link_companies(make_article("Unmatched issuer update"), aliases) == []


def test_event_classifier_covers_every_category_and_fallback() -> None:
    cases = {
        EventType.EARNINGS: "quarterly earnings margin update",
        EventType.MERGER_ACQUISITION: "non-binding merger transaction memo",
        EventType.POLICY_REGULATION: "new policy regulation guidance",
        EventType.OPERATIONS_PRODUCT: "product platform outage resolved",
        EventType.FINANCING_CAPITAL: "financing capital module line",
        EventType.LITIGATION_PENALTY: "litigation penalty lawsuit",
        EventType.GOVERNANCE_PERSONNEL: "appoint chief leadership review",
        EventType.MACRO_MARKET: "macro market inflation orders",
        EventType.OTHER: "routine calendar note",
    }
    for expected, text in cases.items():
        event = classify_event(make_article(text))
        assert event.event_type is expected
        assert event.classifier_version == "1"
        if expected is not EventType.OTHER:
            assert event.evidence


def test_event_classifier_is_deterministic_for_ambiguous_input() -> None:
    article = make_article("earnings merger policy update")
    first = classify_event(article)
    second = classify_event(article)
    assert first.event_type == second.event_type
    assert first.evidence == second.evidence
    assert first.confidence == second.confidence
    assert first.classifier_version == second.classifier_version


def test_sentiment_labels_negation_intensity_evidence_and_bounds() -> None:
    positive = analyze_sentiment(make_article("strongly improved resolved growth"))
    neutral = analyze_sentiment(make_article("routine calendar notice"))
    negative = analyze_sentiment(make_article("litigation risk pressure outage"))
    uncertain = analyze_sentiment(make_article("financing may remain uncertain and cautious"))
    negated = analyze_sentiment(
        make_article("risk pressure", "not a material pressure for operations")
    )
    assert positive.label is SentimentLabel.POSITIVE
    assert neutral.label is SentimentLabel.NEUTRAL
    assert negative.label is SentimentLabel.NEGATIVE
    assert uncertain.label is SentimentLabel.UNCERTAIN
    assert negated.score > negative.score
    assert positive.score > 0.35
    for item in [positive, neutral, negative, uncertain, negated]:
        assert -1 <= item.score <= 1
        assert item.analyzer_version == "1"
    assert positive.evidence
