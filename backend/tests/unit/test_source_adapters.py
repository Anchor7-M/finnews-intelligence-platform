from __future__ import annotations

import json
from pathlib import Path

import pytest

from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import SourceApprovalStatus, SourceType
from finnews.infrastructure.sources.announcements import (
    AnnouncementParseError,
    normalize_cik,
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


def test_sec_columnar_json_mapping_and_bounds() -> None:
    sec_source = source(
        SourceType.DOCUMENTED_JSON_API,
        {
            "record_mode": "columnar",
            "columns_path": "filings.recent",
            "cik_path": "cik",
            "entity_name_path": "name",
            "id": "accessionNumber",
            "form": "form",
            "filing_date": "filingDate",
            "acceptance_datetime": "acceptanceDateTime",
            "primary_document": "primaryDocument",
            "max_records": "5",
            "title_template": "{form} filing by {entityName}",
            "url_template": "https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession_no_dashes}/{primaryDocument}",
        },
    )
    payload = {
        "cik": "320193",
        "name": "Example Issuer Inc.",
        "filings": {
            "recent": {
                "accessionNumber": [f"0000320193-26-00000{i}" for i in range(1, 7)],
                "form": ["10-K", "8-K", "10-Q", "4", "DEF 14A", "8-K"],
                "filingDate": ["2026-06-20"] * 6,
                "acceptanceDateTime": ["20260620123456"] * 6,
                "primaryDocument": [f"doc{i}.htm" for i in range(1, 7)],
            }
        },
    }
    parsed = parse_json_announcement_bytes(json.dumps(payload).encode("utf-8"), sec_source)
    assert len(parsed.records) == 5
    assert parsed.records[0].article_id == "0000320193-26-000001"
    assert parsed.records[0].title == "10-K filing by Example Issuer Inc."
    assert parsed.records[0].published_at == "2026-06-20T12:34:56Z"
    assert "Archives/edgar/data/320193/000032019326000001/doc1.htm" in parsed.records[0].url
    assert parsed.records[0].raw_metadata["form"] == "10-K"


def test_sec_columnar_json_rejects_unequal_arrays_and_bad_cik() -> None:
    sec_source = source(
        SourceType.DOCUMENTED_JSON_API,
        {"record_mode": "columnar", "columns_path": "filings.recent", "cik_path": "cik"},
    )
    assert normalize_cik("320193") == "0000320193"
    with pytest.raises(AnnouncementParseError, match="CIK"):
        normalize_cik("12345678901")
    payload = {
        "cik": "320193",
        "filings": {
            "recent": {
                "accessionNumber": ["a", "b"],
                "form": ["8-K"],
                "filingDate": ["2026-06-20", "2026-06-21"],
                "primaryDocument": ["a.htm", "b.htm"],
            }
        },
    }
    with pytest.raises(AnnouncementParseError, match="equal"):
        parse_json_announcement_bytes(json.dumps(payload).encode("utf-8"), sec_source)
