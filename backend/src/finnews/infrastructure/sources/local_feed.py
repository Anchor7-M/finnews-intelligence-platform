from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

from finnews.domain.entities import SourceRecord
from finnews.domain.enums import SourceType


class LocalFeedSource:
    def __init__(self, path: Path, max_bytes: int = 5_000_000) -> None:
        self.path = path
        self.max_bytes = max_bytes

    def read_records(self) -> list[SourceRecord]:
        resolved = self.path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(str(self.path))
        if resolved.stat().st_size > self.max_bytes:
            raise ValueError(f"feed exceeds {self.max_bytes} bytes")

        parser = ET.XMLParser()
        root = ET.parse(resolved, parser=parser).getroot()
        if root.tag.endswith("feed"):
            return self._read_atom(root, resolved)
        return self._read_rss(root, resolved)

    def _read_rss(self, root: ET.Element, resolved: Path) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
        for item in items:
            guid = (item.findtext("guid") or item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            iso_date = parsedate_to_datetime(pub_date).isoformat()
            language = _detect_language(title + description)
            records.append(
                SourceRecord(
                    source_key="synthetic-local-feed",
                    source_name="Synthetic Local Feed",
                    source_type=SourceType.RSS,
                    article_id=guid,
                    url=link,
                    title=title,
                    summary=description,
                    language=language,
                    published_at=iso_date,
                    raw_metadata={"guid": guid, "feed_path": str(resolved)},
                )
            )
        return records

    def _read_atom(self, root: ET.Element, resolved: Path) -> list[SourceRecord]:
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", namespace) or root.findall("entry")
        records: list[SourceRecord] = []
        for entry in entries:
            title = (
                entry.findtext("atom:title", default="", namespaces=namespace)
                or entry.findtext("title")
                or ""
            ).strip()
            summary = (
                entry.findtext("atom:summary", default="", namespaces=namespace)
                or entry.findtext("summary")
                or ""
            ).strip()
            entry_id = (
                entry.findtext("atom:id", default="", namespaces=namespace)
                or entry.findtext("id")
                or ""
            ).strip()
            updated = (
                entry.findtext("atom:updated", default="", namespaces=namespace)
                or entry.findtext("updated")
                or ""
            ).strip()
            link_element = entry.find("atom:link", namespace)
            if link_element is None:
                link_element = entry.find("link")
            link = link_element.attrib.get("href", "") if link_element is not None else entry_id
            records.append(
                SourceRecord(
                    source_key="synthetic-local-atom",
                    source_name="Synthetic Local Atom",
                    source_type=SourceType.ATOM,
                    article_id=entry_id,
                    url=link,
                    title=title,
                    summary=summary,
                    language=_detect_language(title + summary),
                    published_at=updated,
                    raw_metadata={"id": entry_id, "feed_path": str(resolved)},
                )
            )
        return records


def _detect_language(text: str) -> str:
    return "zh" if any("\u4e00" <= char <= "\u9fff" for char in text) else "en"
