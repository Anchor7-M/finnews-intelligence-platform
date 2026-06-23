from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from finnews.application.services.official_data import (
    OFFICIAL_DATA_FIXTURE_VERSION,
    OfficialDataError,
    OfficialObservationRecord,
)
from finnews.domain.entities import RegulatoryDocument


class OfficialSourceParseError(ValueError):
    pass


def parse_bls_observations(payload: bytes, *, profile_id: str) -> list[OfficialObservationRecord]:
    data = _json_object(payload)
    series_rows = _get_path(data, ["Results", "series"])
    if not isinstance(series_rows, list):
        raise OfficialSourceParseError("BLS payload missing Results.series list")
    records: list[OfficialObservationRecord] = []
    for series in series_rows:
        if not isinstance(series, dict):
            continue
        series_id = str(series.get("seriesID", ""))
        rows = series.get("data", [])
        if not isinstance(rows, list):
            raise OfficialSourceParseError("BLS series data must be a list")
        for row in rows:
            if not isinstance(row, dict):
                continue
            year = str(row.get("year", ""))
            period = str(row.get("period", ""))
            period_start = _bls_period_start(year, period)
            records.append(
                OfficialObservationRecord(
                    source_id="bls-public-data",
                    dataset_id="bls-ces",
                    profile_id=profile_id,
                    period_start=period_start,
                    period_end=period_start,
                    dimensions={"series_id": series_id, "period": period},
                    value=_decimal(row.get("value")),
                    first_seen_at=_fixture_seen_at(),
                    source_updated_at=None,
                    provenance={
                        "adapter": "bls_public_data_v1",
                        "series_id": series_id,
                        "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                    },
                )
            )
    return records


def parse_eia_observations(payload: bytes, *, profile_id: str) -> list[OfficialObservationRecord]:
    data = _json_object(payload)
    rows = _get_path(data, ["response", "data"])
    if not isinstance(rows, list):
        raise OfficialSourceParseError("EIA payload missing response.data list")
    records: list[OfficialObservationRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        period = str(row.get("period", ""))
        records.append(
            OfficialObservationRecord(
                source_id="eia-open-data-v2",
                dataset_id="eia-petroleum-stocks",
                profile_id=profile_id,
                period_start=_period_date(period),
                period_end=_period_date(period),
                dimensions={"series": str(row.get("series", "")), "unit": str(row.get("units", ""))},
                value=_decimal(row.get("value")),
                first_seen_at=_fixture_seen_at(),
                source_updated_at=None,
                provenance={
                    "adapter": "eia_open_data_v2",
                    "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                },
            )
        )
    return records


def parse_cftc_cot_observations(
    payload: bytes, *, profile_id: str
) -> list[OfficialObservationRecord]:
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        raise OfficialSourceParseError("CFTC payload must be a list")
    records: list[OfficialObservationRecord] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        report_date = _period_date(str(row.get("report_date_as_yyyy_mm_dd", "")))
        market_code = str(row.get("cftc_contract_market_code", ""))
        records.append(
            OfficialObservationRecord(
                source_id="cftc-cot-pre",
                dataset_id="cftc-cot-pre",
                profile_id=profile_id,
                period_start=report_date,
                period_end=report_date,
                dimensions={
                    "market_code": market_code,
                    "market_name": str(row.get("market_and_exchange_names", "")),
                    "measure": "open_interest_all",
                },
                value=_decimal(row.get("open_interest_all")),
                first_seen_at=_fixture_seen_at(),
                source_updated_at=None,
                provenance={
                    "adapter": "cftc_cot_pre",
                    "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                },
            )
        )
    return records


def parse_federal_register_documents(payload: bytes) -> list[RegulatoryDocument]:
    data = _json_object(payload)
    rows = data.get("results")
    if not isinstance(rows, list):
        raise OfficialSourceParseError("Federal Register payload missing results list")
    documents: list[RegulatoryDocument] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        document_id = str(row.get("document_number", ""))
        publication_date = _period_date(str(row.get("publication_date", "")))
        available_at = datetime.combine(publication_date, datetime.min.time(), tzinfo=UTC)
        documents.append(
            RegulatoryDocument(
                document_id=document_id,
                source_id="federal-register-api",
                title=str(row.get("title", "")),
                abstract=str(row.get("abstract", "")),
                publication_date=publication_date,
                document_type=str(row.get("type", "")),
                agencies=_agency_names(row.get("agencies")),
                cfr_references=[str(item) for item in row.get("cfr_references", [])],
                rin=[str(item) for item in row.get("regulation_id_numbers", [])],
                html_url=str(row.get("html_url", "")),
                pdf_url=str(row.get("pdf_url")) if row.get("pdf_url") else None,
                information_available_at=available_at,
                source_updated_at=available_at,
                synthetic=True,
                provenance={
                    "adapter": "federal_register_api",
                    "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                    "body_stored": False,
                    "pdf_downloaded": False,
                },
            )
        )
    return documents


def _json_object(payload: bytes) -> dict[str, Any]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialSourceParseError("payload must be UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise OfficialSourceParseError("payload must be a JSON object")
    return data


def _get_path(data: dict[str, Any], path: list[str]) -> object:
    current: object = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OfficialSourceParseError(f"invalid decimal value: {value}") from exc


def _period_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OfficialSourceParseError(f"invalid period date: {value}") from exc


def _bls_period_start(year: str, period: str) -> date:
    if not year.isdigit() or not period.startswith("M") or not period[1:].isdigit():
        raise OfficialSourceParseError("BLS period must use M01..M12")
    month = int(period[1:])
    if not 1 <= month <= 12:
        raise OfficialSourceParseError("BLS period month out of range")
    return date(int(year), month, 1)


def _agency_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def _fixture_seen_at() -> datetime:
    value = datetime(2026, 6, 24, 0, 0, tzinfo=UTC)
    if value.tzinfo is None:
        raise OfficialDataError("fixture timestamp must be timezone-aware")
    return value
