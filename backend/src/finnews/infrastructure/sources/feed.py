from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime

from finnews.domain.entities import SourceDefinition, SourceRecord
from finnews.domain.enums import SourceType


@dataclass(frozen=True)
class ParsedSourceRecords:
    records: list[SourceRecord]
    rejected_count: int = 0
    warnings: list[str] = field(default_factory=list)
    next_cursor: str | None = None


class FeedParseError(ValueError):
    pass


def parse_feed_bytes(content: bytes, source: SourceDefinition) -> ParsedSourceRecords:
    _reject_unsafe_xml(content)
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise FeedParseError("malformed feed XML") from exc
    if _local_name(root.tag) == "feed":
        return _read_atom(root, source)
    if _local_name(root.tag) == "rss":
        return _read_rss(root, source)
    raise FeedParseError("unsupported feed root")


def _read_rss(root: ET.Element, source: SourceDefinition) -> ParsedSourceRecords:
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else []
    records: list[SourceRecord] = []
    warnings: list[str] = []
    rejected = 0
    for index, item in enumerate(items, start=1):
        try:
            guid = _text(item, "guid") or _text(item, "link")
            title = _text(item, "title")
            link = _text(item, "link")
            summary = _text(item, "description")
            published = parsedate_to_datetime(_text(item, "pubDate")).isoformat()
            categories = [_clean_text(child.text) for child in item.findall("category")]
            records.append(
                SourceRecord(
                    source_key=source.source_id,
                    source_name=source.display_name,
                    source_type=SourceType.RSS,
                    article_id=guid or f"{source.source_id}-rss-{index}",
                    url=link,
                    title=title,
                    summary=summary,
                    language=_detect_language(title + summary, source.language),
                    published_at=published,
                    raw_metadata={
                        "source_definition_id": source.source_id,
                        "guid": guid,
                        "categories": categories,
                    },
                )
            )
        except Exception:
            rejected += 1
            warnings.append(f"rss item {index} rejected")
    return ParsedSourceRecords(records=records, rejected_count=rejected, warnings=warnings)


def _read_atom(root: ET.Element, source: SourceDefinition) -> ParsedSourceRecords:
    records: list[SourceRecord] = []
    warnings: list[str] = []
    rejected = 0
    entries = [child for child in root if _local_name(child.tag) == "entry"]
    for index, entry in enumerate(entries, start=1):
        try:
            title = _child_text(entry, "title")
            summary = _child_text(entry, "summary") or _child_text(entry, "content")
            entry_id = _child_text(entry, "id")
            updated = _child_text(entry, "updated") or _child_text(entry, "published")
            link = _atom_link(entry) or entry_id
            categories = [
                child.attrib.get("term", "")
                for child in entry
                if _local_name(child.tag) == "category"
            ]
            records.append(
                SourceRecord(
                    source_key=source.source_id,
                    source_name=source.display_name,
                    source_type=SourceType.ATOM,
                    article_id=entry_id or f"{source.source_id}-atom-{index}",
                    url=link,
                    title=title,
                    summary=summary,
                    language=_detect_language(title + summary, source.language),
                    published_at=updated,
                    raw_metadata={
                        "source_definition_id": source.source_id,
                        "id": entry_id,
                        "categories": categories,
                    },
                )
            )
        except Exception:
            rejected += 1
            warnings.append(f"atom entry {index} rejected")
    return ParsedSourceRecords(records=records, rejected_count=rejected, warnings=warnings)


def _reject_unsafe_xml(content: bytes) -> None:
    prefix = content[:1024].lower()
    if b"<!doctype" in prefix or b"<!entity" in prefix:
        raise FeedParseError("unsafe XML DTD/entity declarations are not allowed")


def _text(element: ET.Element, name: str) -> str:
    return _clean_text(element.findtext(name))


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if _local_name(child.tag) == name:
            return _clean_text(child.text)
    return ""


def _atom_link(entry: ET.Element) -> str:
    for child in entry:
        if _local_name(child.tag) == "link":
            return child.attrib.get("href", "")
    return ""


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _detect_language(text: str, fallback: str) -> str:
    return "zh" if any("\u4e00" <= char <= "\u9fff" for char in text) else fallback
