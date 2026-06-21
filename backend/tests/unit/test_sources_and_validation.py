from __future__ import annotations

from pathlib import Path

import pytest

from finnews.application.services.pipeline import NewsPipeline
from finnews.domain.entities import SourceRecord
from finnews.domain.enums import SourceType
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.sources.fixtures import JsonlFixtureSource
from finnews.infrastructure.sources.local_feed import LocalFeedSource
from finnews.settings import Settings


def test_malformed_jsonl_record_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"source_key":"test","source_name":"Test","source_type":"fixture","article_id":"ok",'
        '"url":"https://demo.local/ok","title":"ok","summary":"ok","language":"en",'
        '"published_at":"2026-06-20T10:00:00+08:00"}\n{bad json}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformed JSONL"):
        JsonlFixtureSource(path).read_records()


def test_oversized_input_rejection(tmp_path: Path) -> None:
    path = tmp_path / "large.jsonl"
    path.write_text("x" * 20, encoding="utf-8")
    with pytest.raises(ValueError, match="fixture exceeds"):
        JsonlFixtureSource(path, max_bytes=10).read_records()


def test_missing_required_values_invalid_language_and_timestamp_do_not_stop_batch() -> None:
    repo = MemoryNewsRepository()
    pipeline = NewsPipeline(repo, Settings(profile="memory"))
    good = SourceRecord(
        source_key="test",
        source_name="Test",
        source_type=SourceType.FIXTURE,
        article_id="good",
        url="https://demo.local/good?utm_source=x",
        title="ALP routine calendar notice",
        summary="Alpine Robotics published a routine calendar notice.",
        language="en",
        published_at="2026-06-20T10:00:00+08:00",
    )
    bad_missing = SourceRecord(
        "test",
        "Test",
        SourceType.FIXTURE,
        "missing",
        "https://demo.local/missing",
        "",
        "summary",
        "en",
        "2026-06-20T10:00:00+08:00",
    )
    bad_lang = SourceRecord(
        "test",
        "Test",
        SourceType.FIXTURE,
        "lang",
        "https://demo.local/lang",
        "title",
        "summary",
        "fr",
        "2026-06-20T10:00:00+08:00",
    )
    bad_time = SourceRecord(
        "test",
        "Test",
        SourceType.FIXTURE,
        "time",
        "https://demo.local/time",
        "title",
        "summary",
        "en",
        "not-a-date",
    )
    counts = pipeline.ingest_records([bad_missing, bad_lang, bad_time, good])
    assert counts["rejected"] == 3
    assert counts["accepted"] == 1
    assert len(repo.list_articles()) == 1


def test_local_atom_fixture_parser(tmp_path: Path) -> None:
    atom = tmp_path / "feed.atom"
    atom.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>atom-001</id>
    <title>QuantHarbor routine calendar notice</title>
    <link href="https://demo.local/atom/qnt?utm_source=atom" />
    <summary>QuantHarbor published a routine update.</summary>
    <updated>2026-06-20T10:00:00+08:00</updated>
  </entry>
</feed>
""",
        encoding="utf-8",
    )
    records = LocalFeedSource(atom).read_records()
    assert len(records) == 1
    assert records[0].source_type is SourceType.ATOM
    assert records[0].article_id == "atom-001"
