from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from finnews.domain.entities import SourceDefinition, SourceRecord
from finnews.domain.enums import SourceType
from finnews.infrastructure.sources.feed import ParsedSourceRecords


class AnnouncementParseError(ValueError):
    pass


def parse_json_announcement_bytes(content: bytes, source: SourceDefinition) -> ParsedSourceRecords:
    try:
        payload = json.loads(content.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise AnnouncementParseError("JSON announcement response must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise AnnouncementParseError("malformed JSON announcement response") from exc
    return parse_json_announcement_payload(payload, source)


def parse_json_announcement_payload(
    payload: object, source: SourceDefinition
) -> ParsedSourceRecords:
    mapping = source.field_mapping
    items_path = mapping.get("items", "")
    items = _lookup(payload, items_path) if items_path else payload
    if not isinstance(items, list):
        raise AnnouncementParseError("mapped JSON items must be a list")
    records: list[SourceRecord] = []
    rejected = 0
    warnings: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            rejected += 1
            warnings.append(f"json row {index} rejected")
            continue
        try:
            records.append(
                _record_from_mapping(item, source, SourceType.DOCUMENTED_JSON_API, index)
            )
        except Exception:
            rejected += 1
            warnings.append(f"json row {index} rejected")
    cursor = _string(_lookup(payload, mapping.get("next_cursor", ""))) if mapping else None
    return ParsedSourceRecords(
        records=records,
        rejected_count=rejected,
        warnings=warnings,
        next_cursor=cursor or None,
    )


def read_user_export(path: Path, source: SourceDefinition) -> ParsedSourceRecords:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(path))
    if resolved.stat().st_size > source.max_response_bytes:
        raise AnnouncementParseError(
            f"announcement export exceeds {source.max_response_bytes} bytes"
        )
    if source.source_type is SourceType.USER_EXPORT_JSON:
        return parse_user_export_json(resolved.read_bytes(), source)
    if source.source_type is SourceType.USER_EXPORT_CSV:
        return parse_user_export_csv(resolved.read_bytes(), source)
    raise AnnouncementParseError("source is not a user export source")


def parse_user_export_json(content: bytes, source: SourceDefinition) -> ParsedSourceRecords:
    try:
        payload = json.loads(content.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise AnnouncementParseError("JSON export must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise AnnouncementParseError("malformed JSON export") from exc
    items = (
        payload
        if isinstance(payload, list)
        else _lookup(payload, source.field_mapping.get("items", ""))
    )
    if not isinstance(items, list):
        raise AnnouncementParseError("JSON export must be a list or configured items list")
    return _records_from_rows(items, source, SourceType.USER_EXPORT_JSON)


def parse_user_export_csv(content: bytes, source: SourceDefinition) -> ParsedSourceRecords:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AnnouncementParseError("CSV export must be UTF-8") from exc
    rows = list(csv.DictReader(text.splitlines()))
    return _records_from_rows(rows, source, SourceType.USER_EXPORT_CSV)


def _records_from_rows(
    rows: Sequence[object], source: SourceDefinition, source_type: SourceType
) -> ParsedSourceRecords:
    records: list[SourceRecord] = []
    rejected = 0
    warnings: list[str] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            rejected += 1
            warnings.append(f"row {index} rejected")
            continue
        try:
            records.append(_record_from_mapping(row, source, source_type, index))
        except Exception:
            rejected += 1
            warnings.append(f"row {index} rejected")
    return ParsedSourceRecords(records=records, rejected_count=rejected, warnings=warnings)


def _record_from_mapping(
    row: dict[str, Any],
    source: SourceDefinition,
    source_type: SourceType,
    index: int,
) -> SourceRecord:
    mapping = source.field_mapping
    item_id = _string(row.get(mapping.get("id", "id"))) or f"{source.source_id}-{index}"
    title = _required(row, mapping.get("title", "title"))
    url = _required(row, mapping.get("url", "url"))
    published_at = _required(row, mapping.get("published_at", "published_at"))
    summary = _string(row.get(mapping.get("summary", "summary")))
    ticker = _string(row.get(mapping.get("ticker", "ticker")))
    category = _string(row.get(mapping.get("category", "category")))
    return SourceRecord(
        source_key=source.source_id,
        source_name=source.display_name,
        source_type=source_type,
        article_id=item_id,
        url=url,
        title=title,
        summary=summary,
        language=source.language,
        published_at=published_at,
        raw_metadata={
            "source_definition_id": source.source_id,
            "ticker": ticker,
            "category": category,
            "storage_policy": source.content_storage_policy.value,
        },
    )


def _required(row: dict[str, Any], key: str) -> str:
    value = _string(row.get(key))
    if not value:
        raise AnnouncementParseError(f"missing required field: {key}")
    return value


def _lookup(payload: object, dotted_path: str) -> object:
    if not dotted_path:
        return payload
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _string(value: object) -> str:
    return str(value or "").strip()
