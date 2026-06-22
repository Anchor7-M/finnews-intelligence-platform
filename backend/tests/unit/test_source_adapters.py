from __future__ import annotations

from pathlib import Path

import pytest

from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import SourceApprovalStatus, SourceType
from finnews.infrastructure.sources.announcements import (
    AnnouncementParseError,
    parse_json_announcement_bytes,
    read_user_export,
)
from finnews.infrastructure.sources.feed import FeedParseError, parse_feed_bytes


def source(source_type: SourceType, mapping: dict[str, str] | None = None) -> SourceDefinition:
    return SourceDefinition(
        source_id="mock-source",
        display_name="Mock Source",
        source_type=source_type,
        approved_hostnames=["mock.local"],
        review_status=SourceApprovalStatus.APPROVED,
        enabled=True,
        base_url="https://mock.local/feed"
        if source_type not in {SourceType.USER_EXPORT_JSON, SourceType.USER_EXPORT_CSV}
        else None,
        terms_url="https://mock.local/terms",
        documentation_url="https://mock.local/docs",
        reviewer="test",
        field_mapping=mapping or {},
        minimum_interval_seconds=0,
    )


def test_rss_and_atom_parse_summary_only_records() -> None:
    rss = (
        b"<rss><channel><item><guid>1</guid><title>Alpha earnings</title>"
        b"<link>https://mock.local/a</link><description>Summary</description>"
        b"<pubDate>Mon, 22 Jun 2026 00:00:00 GMT</pubDate></item></channel></rss>"
    )
    atom = (
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>2</id>'
        b"<title>Beta update</title><summary>Short</summary>"
        b"<updated>2026-06-22T00:00:00Z</updated>"
        b'<link href="https://mock.local/b" /></entry></feed>'
    )
    assert parse_feed_bytes(rss, source(SourceType.RSS)).records[0].summary == "Summary"
    assert parse_feed_bytes(atom, source(SourceType.ATOM)).records[0].article_id == "2"


def test_feed_malformed_item_isolated_and_unsafe_xml_rejected() -> None:
    rss = (
        b"<rss><channel><item><guid>bad</guid></item><item><guid>ok</guid>"
        b"<title>Ok</title><link>https://mock.local/ok</link>"
        b"<description>Summary</description>"
        b"<pubDate>Mon, 22 Jun 2026 00:00:00 GMT</pubDate></item></channel></rss>"
    )
    parsed = parse_feed_bytes(rss, source(SourceType.RSS))
    assert len(parsed.records) == 1
    assert parsed.rejected_count == 1
    with pytest.raises(FeedParseError, match="DTD"):
        parse_feed_bytes(b"<!DOCTYPE rss><rss />", source(SourceType.RSS))


def test_json_mapping_cursor_and_csv_import(tmp_path: Path) -> None:
    mapping = {
        "items": "items",
        "id": "id",
        "title": "title",
        "url": "url",
        "published_at": "published",
        "summary": "summary",
        "ticker": "ticker",
        "next_cursor": "next",
    }
    json_source = source(SourceType.DOCUMENTED_JSON_API, mapping)
    parsed = parse_json_announcement_bytes(
        b'{"items":[{"id":"a1","title":"Alpha","url":"https://mock.local/a","published":"2026-06-22T00:00:00Z","summary":"Snippet","ticker":"ALP"}],"next":"cursor-2"}',
        json_source,
    )
    assert parsed.records[0].raw_metadata["ticker"] == "ALP"
    assert parsed.next_cursor == "cursor-2"

    csv_path = tmp_path / "export.csv"
    csv_path.write_text(
        "id,title,url,published_at,summary,ticker\nc1,CSV,https://mock.local/c,2026-06-22T00:00:00Z,Snippet,CSV\n",
        encoding="utf-8",
    )
    csv_source = source(
        SourceType.USER_EXPORT_CSV,
        {
            "id": "id",
            "title": "title",
            "url": "url",
            "published_at": "published_at",
            "summary": "summary",
            "ticker": "ticker",
        },
    )
    assert read_user_export(csv_path, csv_source).records[0].article_id == "c1"


def test_json_encoding_failure() -> None:
    with pytest.raises(AnnouncementParseError, match="UTF-8"):
        parse_json_announcement_bytes(b"\xff", source(SourceType.DOCUMENTED_JSON_API))
