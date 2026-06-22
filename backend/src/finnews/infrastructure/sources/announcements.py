from __future__ import annotations

import csv
import json
import re
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
    if mapping.get("record_mode") == "columnar":
        return _records_from_columnar_payload(payload, source)
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


def _records_from_columnar_payload(
    payload: object, source: SourceDefinition
) -> ParsedSourceRecords:
    mapping = source.field_mapping
    columns = _lookup(payload, mapping.get("columns_path", mapping.get("items", "")))
    if not isinstance(columns, dict):
        raise AnnouncementParseError("mapped columnar JSON payload must be an object")
    entity_name = _string(_lookup(payload, mapping.get("entity_name_path", "")))
    cik = normalize_cik(
        _string(_lookup(payload, mapping.get("cik_path", "")))
        or str(source.parameter_schema.get("cik", ""))
    )
    required_columns = [
        mapping.get("id", "accessionNumber"),
        mapping.get("form", "form"),
        mapping.get("filing_date", "filingDate"),
        mapping.get("primary_document", "primaryDocument"),
    ]
    lengths = [_column_length(columns, name) for name in required_columns]
    if len(set(lengths)) != 1:
        raise AnnouncementParseError("SEC columnar arrays must have equal required lengths")
    max_records = min(int(mapping.get("max_records", source.max_items_per_smoke)), lengths[0])
    records: list[SourceRecord] = []
    rejected = 0
    warnings: list[str] = []
    for index in range(max_records):
        try:
            row = {
                key: _column_value(values, index)
                for key, values in columns.items()
                if isinstance(values, list)
            }
            row["entityName"] = entity_name
            row["cik"] = cik
            row["cik_unpadded"] = str(int(cik))
            accession = _required(row, mapping.get("id", "accessionNumber"))
            row["accession_no_dashes"] = accession.replace("-", "")
            records.append(_sec_record_from_row(row, source, index + 1))
        except Exception:
            rejected += 1
            warnings.append(f"columnar row {index + 1} rejected")
    return ParsedSourceRecords(records=records, rejected_count=rejected, warnings=warnings)


def normalize_cik(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits or len(digits) > 10:
        raise AnnouncementParseError("CIK must be one to ten digits")
    return digits.zfill(10)


def _sec_record_from_row(row: dict[str, Any], source: SourceDefinition, index: int) -> SourceRecord:
    mapping = source.field_mapping
    accession = _required(row, mapping.get("id", "accessionNumber"))
    form_type = _required(row, mapping.get("form", "form"))
    published_at = _sec_timestamp(
        _string(row.get(mapping.get("acceptance_datetime", "acceptanceDateTime")))
        or _required(row, mapping.get("filing_date", "filingDate"))
    )
    title = _format_template(mapping.get("title_template", "{form} filing by {entityName}"), row)
    url = _format_template(
        mapping.get(
            "url_template",
            "https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession_no_dashes}/{primaryDocument}",
        ),
        row,
    )
    summary = _format_template(
        mapping.get("summary_template", "SEC {form} filing metadata for {entityName}"), row
    )
    return SourceRecord(
        source_key=source.source_id,
        source_name=source.display_name,
        source_type=SourceType.DOCUMENTED_JSON_API,
        article_id=accession or f"{source.source_id}-{index}",
        url=url,
        title=title,
        summary=summary,
        language=source.language,
        published_at=published_at,
        raw_metadata={
            "source_definition_id": source.source_id,
            "form": form_type,
            "accession_number": accession,
            "cik": row.get("cik", ""),
            "entity_name": row.get("entityName", ""),
            "storage_policy": source.content_storage_policy.value,
        },
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


def _column_length(columns: dict[str, object], key: str) -> int:
    value = columns.get(key)
    if not isinstance(value, list):
        raise AnnouncementParseError(f"missing required SEC column: {key}")
    return len(value)


def _column_value(values: object, index: int) -> object:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return ""


def _format_template(template: str, row: dict[str, Any]) -> str:
    return template.format_map(_SafeFormat(row))


def _sec_timestamp(value: str) -> str:
    if re.fullmatch(r"\d{14}", value):
        return (
            f"{value[0:4]}-{value[4:6]}-{value[6:8]}T{value[8:10]}:{value[10:12]}:{value[12:14]}Z"
        )
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return f"{value}T00:00:00Z"
    if value.endswith("Z") or "+" in value:
        return value
    return f"{value}Z"


class _SafeFormat(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""
