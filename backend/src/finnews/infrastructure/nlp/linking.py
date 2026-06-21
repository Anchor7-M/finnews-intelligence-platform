from __future__ import annotations

from finnews.domain.entities import Article, ArticleCompanyLink, CompanyAlias
from finnews.infrastructure.normalization import comparison_text


def link_companies(article: Article, aliases: list[CompanyAlias]) -> list[ArticleCompanyLink]:
    haystack = comparison_text(f"{article.normalized_title} {article.normalized_summary}")
    matches: list[tuple[int, CompanyAlias]] = []
    for alias in aliases:
        needle = comparison_text(alias.alias)
        if needle and needle in haystack:
            matches.append((len(needle), alias))
    matches.sort(key=lambda item: item[0], reverse=True)
    seen: set[str] = set()
    links: list[ArticleCompanyLink] = []
    for _, alias in matches:
        key = str(alias.company_id)
        if key in seen:
            continue
        seen.add(key)
        links.append(
            ArticleCompanyLink(
                article_id=article.id,
                company_id=alias.company_id,
                confidence=0.95,
                matched_alias=alias.alias,
                evidence_text_span=alias.alias,
            )
        )
    return links
