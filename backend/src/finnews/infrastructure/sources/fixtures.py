from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finnews.domain.entities import SourceRecord
from finnews.domain.enums import SourceType


def _check_file(path: Path, max_bytes: int) -> None:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(path))
    if resolved.stat().st_size > max_bytes:
        raise ValueError(f"fixture exceeds {max_bytes} bytes")


class JsonlFixtureSource:
    def __init__(self, path: Path, max_bytes: int = 5_000_000) -> None:
        self.path = path
        self.max_bytes = max_bytes

    def read_records(self) -> list[SourceRecord]:
        _check_file(self.path, self.max_bytes)
        records: list[SourceRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    item: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"malformed JSONL at line {line_number}: {exc.msg}") from exc
                records.append(
                    SourceRecord(
                        source_key=str(item["source_key"]),
                        source_name=str(item["source_name"]),
                        source_type=SourceType(str(item.get("source_type", "fixture"))),
                        article_id=str(item.get("article_id") or ""),
                        url=str(item["url"]),
                        title=str(item["title"]),
                        summary=str(item["summary"]),
                        language=str(item["language"]),
                        published_at=str(item["published_at"]),
                        raw_metadata=item,
                    )
                )
        return records
