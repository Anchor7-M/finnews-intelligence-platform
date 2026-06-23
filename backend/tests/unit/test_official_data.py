from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from finnews.application.services.official_data import (
    OfficialDataError,
    OfficialObservationRecord,
    build_official_data_demo,
    information_available_at,
    ingest_official_observation_records,
    official_data_overview,
    persist_official_data_demo,
)
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.sources.official_data import (
    OfficialSourceParseError,
    parse_bls_observations,
    parse_cftc_cot_observations,
    parse_eia_observations,
    parse_federal_register_documents,
)


def test_official_data_fixture_counts_are_deterministic() -> None:
    repo = MemoryNewsRepository()
    counts = persist_official_data_demo(repo)
    overview = official_data_overview(repo)
    assert counts["datasets"] == 4
    assert counts["series_profiles"] == 10
    assert overview["observation_count"] == 24
    assert overview["revision_count"] == 28
    assert overview["revised_observation_count"] == 4
    assert overview["regulatory_document_count"] == 8
    assert overview["series_asset_association_count"] == 80
    assert overview["official_release_event_count"] == 32


def test_observation_ingestion_is_idempotent_and_revision_aware() -> None:
    repo = MemoryNewsRepository()
    first_seen = datetime(2026, 6, 24, tzinfo=UTC)
    record = OfficialObservationRecord(
        source_id="bls-public-data",
        dataset_id="bls-ces",
        profile_id="bls-ces-total-nonfarm",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 1),
        dimensions={"series_id": "CES0000000001"},
        value=Decimal("100.0"),
        first_seen_at=first_seen,
        source_updated_at=first_seen - timedelta(minutes=1),
        provenance={"fixture": True},
    )
    assert ingest_official_observation_records(repo, [record])[
        "official_observation_revisions"
    ] == 1
    assert ingest_official_observation_records(repo, [record])[
        "official_observation_unchanged"
    ] == 1
    changed = OfficialObservationRecord(
        **{**record.__dict__, "value": Decimal("101.0"), "first_seen_at": first_seen + timedelta(days=1)}
    )
    ingest_official_observation_records(repo, [changed])
    observation = repo.list_official_observations()[0]
    assert observation.current_revision == 2
    assert observation.current_value == Decimal("101.0")
    assert len(repo.list_official_observation_revisions(observation.observation_key)) == 2


def test_information_available_at_rejects_naive_timestamps_and_flags_future_source() -> None:
    with pytest.raises(OfficialDataError, match="timezone-aware"):
        information_available_at(datetime(2026, 6, 24), None)
    first_seen = datetime(2026, 6, 24, tzinfo=UTC)
    info_time, flags = information_available_at(first_seen, first_seen + timedelta(hours=1))
    assert info_time == first_seen
    assert flags == ["future_source_updated_at"]


def test_official_source_parsers_normalize_mock_payloads() -> None:
    bls = parse_bls_observations(
        json.dumps(
            {
                "Results": {
                    "series": [
                        {
                            "seriesID": "CES0000000001",
                            "data": [{"year": "2026", "period": "M01", "value": "155000"}],
                        }
                    ]
                }
            }
        ).encode(),
        profile_id="bls-ces-total-nonfarm",
    )
    assert bls[0].period_start == date(2026, 1, 1)
    assert bls[0].value == Decimal("155000")

    eia = parse_eia_observations(
        json.dumps(
            {
                "response": {
                    "data": [
                        {
                            "period": "2026-02-06",
                            "series": "WCESTUS1",
                            "units": "thousand barrels",
                            "value": "432100",
                        }
                    ]
                }
            }
        ).encode(),
        profile_id="eia-crude-stocks",
    )
    assert eia[0].dimensions["series"] == "WCESTUS1"

    cftc = parse_cftc_cot_observations(
        json.dumps(
            [
                {
                    "report_date_as_yyyy_mm_dd": "2026-02-06",
                    "cftc_contract_market_code": "13874A",
                    "market_and_exchange_names": "E-MINI S&P 500",
                    "open_interest_all": "2500000",
                }
            ]
        ).encode(),
        profile_id="cftc-equity-index-positioning",
    )
    assert cftc[0].dimensions["market_code"] == "13874A"

    documents = parse_federal_register_documents(
        json.dumps(
            {
                "results": [
                    {
                        "document_number": "2026-0001",
                        "title": "Synthetic Rule",
                        "abstract": "Synthetic abstract",
                        "publication_date": "2026-03-01",
                        "type": "Rule",
                        "agencies": [{"name": "Synthetic Agency"}],
                        "cfr_references": ["17 CFR 1"],
                        "regulation_id_numbers": ["0000-AA00"],
                        "html_url": "https://www.federalregister.gov/documents/demo",
                        "pdf_url": "https://www.govinfo.gov/demo.pdf",
                    }
                ]
            }
        ).encode()
    )
    assert documents[0].abstract == "Synthetic abstract"
    assert documents[0].provenance["pdf_downloaded"] is False


def test_official_source_parser_rejects_malformed_records() -> None:
    with pytest.raises(OfficialSourceParseError):
        parse_bls_observations(b"{}", profile_id="bls-ces-total-nonfarm")
    with pytest.raises(OfficialSourceParseError):
        parse_eia_observations(b'{"response":{"data":[{"period":"bad","value":"1"}]}}', profile_id="x")


def test_fixture_build_is_stable() -> None:
    left = build_official_data_demo()
    right = build_official_data_demo()
    assert [row.profile_id for row in left.profiles] == [row.profile_id for row in right.profiles]
    assert [row.document_id for row in left.regulatory_documents] == [
        row.document_id for row in right.regulatory_documents
    ]
