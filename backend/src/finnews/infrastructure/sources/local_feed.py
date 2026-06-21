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
            language = (
                "zh" if any("\u4e00" <= char <= "\u9fff" for char in title + description) else "en"
            )
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
