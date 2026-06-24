from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from finnews.application.ports.repositories import NewsRepository
from finnews.application.services.cross_asset import build_cross_asset_demo
from finnews.domain.entities import (
    OfficialDataReleaseRun,
    OfficialDataset,
    OfficialObservation,
    OfficialObservationRevision,
    OfficialReleaseEvent,
    OfficialSeriesProfile,
    RegulatoryDocument,
    SeriesAssetAssociation,
)
from finnews.domain.enums import CrossAssetEventFamily

OFFICIAL_DATA_FIXTURE_VERSION = "official-data-synthetic-v1"
OFFICIAL_DATA_LEDGER_SCHEMA_VERSION = "m3b-release-ledger-v1"
OFFICIAL_DATA_GENERATED_AT = datetime(2026, 6, 24, 0, 0, tzinfo=UTC)
OFFICIAL_SOURCE_IDS = {
    "bls-public-data",
    "eia-open-data-v2",
    "cftc-cot-pre",
    "federal-register-api",
}


class OfficialDataError(ValueError):
    pass


@dataclass(frozen=True)
class OfficialObservationRecord:
    source_id: str
    dataset_id: str
    profile_id: str
    period_start: date
    period_end: date
    dimensions: dict[str, str]
    value: Decimal
    first_seen_at: datetime
    source_updated_at: datetime | None
    provenance: dict[str, object]


@dataclass(frozen=True)
class OfficialDataBundle:
    datasets: list[OfficialDataset]
    profiles: list[OfficialSeriesProfile]
    observation_records: list[OfficialObservationRecord]
    release_runs: list[OfficialDataReleaseRun]
    regulatory_documents: list[RegulatoryDocument]
    associations: list[SeriesAssetAssociation]
    events: list[OfficialReleaseEvent]


def build_official_data_demo() -> OfficialDataBundle:
    datasets = _datasets()
    profiles = _profiles()
    records = _observation_records(profiles)
    documents = _regulatory_documents()
    associations = _associations(profiles)
    events = _events(records, documents)
    runs = _release_runs(records)
    return OfficialDataBundle(
        datasets=datasets,
        profiles=profiles,
        observation_records=records,
        release_runs=runs,
        regulatory_documents=documents,
        associations=associations,
        events=events,
    )


def persist_official_data_demo(repository: NewsRepository) -> dict[str, int]:
    bundle = build_official_data_demo()
    for dataset in bundle.datasets:
        repository.upsert_official_dataset(dataset)
    for profile in bundle.profiles:
        repository.upsert_official_series_profile(profile)
    observation_counts = ingest_official_observation_records(repository, bundle.observation_records)
    for run in bundle.release_runs:
        repository.add_official_data_release_run(run)
    for document in bundle.regulatory_documents:
        repository.upsert_regulatory_document(document)
    for association in bundle.associations:
        repository.upsert_series_asset_association(association)
    for event in bundle.events:
        repository.upsert_official_release_event(event)
    return {
        "datasets": len(bundle.datasets),
        "series_profiles": len(bundle.profiles),
        "regulatory_documents": len(bundle.regulatory_documents),
        "series_asset_associations": len(bundle.associations),
        "official_release_events": len(bundle.events),
        **observation_counts,
    }


def ingest_official_observation_records(
    repository: NewsRepository, records: list[OfficialObservationRecord]
) -> dict[str, int]:
    new_observations = 0
    new_revisions = 0
    unchanged = 0
    for record in sorted(records, key=_record_order_key):
        _validate_record_time(record)
        key = observation_business_key(
            record.source_id,
            record.dataset_id,
            record.profile_id,
            record.period_start,
            record.period_end,
            record.dimensions,
        )
        existing = next(
            (
                item
                for item in repository.list_official_observations()
                if item.observation_key == key
            ),
            None,
        )
        current_revision = existing.current_revision if existing else 0
        current_value = existing.current_value if existing else None
        if current_value == record.value:
            unchanged += 1
            continue
        previous_values = {
            revision.value for revision in repository.list_official_observation_revisions(key)
        }
        if record.value in previous_values:
            unchanged += 1
            continue
        revision_number = current_revision + 1
        information_time, quality_flags = information_available_at(
            record.first_seen_at, record.source_updated_at
        )
        observation = OfficialObservation(
            id=existing.id if existing else _stable_uuid("official-observation", key),
            observation_key=key,
            source_id=record.source_id,
            dataset_id=record.dataset_id,
            profile_id=record.profile_id,
            period_start=record.period_start,
            period_end=record.period_end,
            dimensions=dict(record.dimensions),
            current_revision=revision_number,
            current_value=record.value,
            first_seen_at=existing.first_seen_at if existing else record.first_seen_at,
            information_available_at=information_time,
            synthetic=True,
        )
        revision = OfficialObservationRevision(
            id=_stable_uuid("official-observation-revision", key, revision_number),
            observation_key=key,
            revision_number=revision_number,
            value=record.value,
            first_seen_at=record.first_seen_at,
            source_updated_at=record.source_updated_at,
            information_available_at=information_time,
            provenance=dict(record.provenance),
            quality_flags=quality_flags,
        )
        repository.upsert_official_observation(observation, revision)
        new_observations += int(existing is None)
        new_revisions += 1
    return {
        "official_observations": new_observations,
        "official_observation_revisions": new_revisions,
        "official_observation_unchanged": unchanged,
    }


def observation_business_key(
    source_id: str,
    dataset_id: str,
    profile_id: str,
    period_start: date,
    period_end: date,
    dimensions: dict[str, str],
) -> str:
    normalized = {
        "source_id": source_id,
        "dataset_id": dataset_id,
        "profile_id": profile_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "dimensions": {key: dimensions[key] for key in sorted(dimensions)},
    }
    return hashlib.sha256(_canonical_json(normalized).encode("utf-8")).hexdigest()


def information_available_at(
    first_seen_at: datetime, source_updated_at: datetime | None
) -> tuple[datetime, list[str]]:
    if first_seen_at.tzinfo is None:
        raise OfficialDataError("first_seen_at must be timezone-aware")
    if source_updated_at is not None and source_updated_at.tzinfo is None:
        raise OfficialDataError("source_updated_at must be timezone-aware")
    if source_updated_at is None:
        return first_seen_at, ["source_updated_at_missing"]
    if source_updated_at > first_seen_at + timedelta(minutes=5):
        return first_seen_at, ["future_source_updated_at"]
    return max(first_seen_at, source_updated_at), []


def official_data_static_payload(repository: NewsRepository) -> dict[str, Any]:
    datasets = repository.list_official_datasets()
    profiles = repository.list_official_series_profiles()
    observations = repository.list_official_observations()
    revisions = repository.list_official_observation_revisions()
    documents = repository.list_regulatory_documents()
    associations = repository.list_series_asset_associations()
    events = repository.list_official_release_events()
    runs = repository.list_official_data_release_runs()
    return {
        "official-data-overview": official_data_overview(repository),
        "official-datasets": [_dataset_row(row) for row in datasets],
        "official-series": [_profile_row(row) for row in profiles],
        "official-observations": [_observation_row(row) for row in observations],
        "official-observation-revisions": [_revision_row(row) for row in revisions],
        "official-regulatory-documents": [_document_row(row) for row in documents],
        "official-series-asset-associations": [_association_row(row) for row in associations],
        "official-release-events": [_event_row(row) for row in events],
        "official-data-release-runs": [_run_row(row) for row in runs],
    }


def official_data_overview(repository: NewsRepository) -> dict[str, Any]:
    datasets = repository.list_official_datasets()
    profiles = repository.list_official_series_profiles()
    observations = repository.list_official_observations()
    revisions = repository.list_official_observation_revisions()
    documents = repository.list_regulatory_documents()
    associations = repository.list_series_asset_associations()
    events = repository.list_official_release_events()
    source_counts = Counter(dataset.source_id for dataset in datasets)
    return {
        "synthetic_data": True,
        "not_investment_advice": True,
        "live_data_persisted": False,
        "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
        "generated_at": OFFICIAL_DATA_GENERATED_AT.isoformat(),
        "dataset_count": len(datasets),
        "series_profile_count": len(profiles),
        "definition_count_total": len(profiles),
        "observation_count": len(observations),
        "revision_count": len(revisions),
        "changed_value_revision_count": sum(
            1 for revision in revisions if revision.revision_number > 1
        ),
        "physical_revision_row_count": len(revisions),
        "revised_observation_count": sum(
            1 for observation in observations if observation.current_revision > 1
        ),
        "regulatory_document_count": len(documents),
        "series_asset_association_count": len(associations),
        "official_release_event_count": len(events),
        "source_counts": dict(sorted(source_counts.items())),
        "revision_policy": "append_only_point_in_time",
        "body_storage": "metadata_and_source_abstracts_only",
    }


def _datasets() -> list[OfficialDataset]:
    rows = [
        (
            "bls-ces",
            "bls-public-data",
            "BLS Current Employment Statistics",
            "labor_market",
            "Selected synthetic payroll and hours observations.",
            "https://www.bls.gov/developers/",
            "append_only_when_value_changes",
            "monthly",
            "varies",
        ),
        (
            "eia-petroleum-stocks",
            "eia-open-data-v2",
            "EIA Petroleum Stocks",
            "commodity_supply",
            "Selected synthetic energy inventory observations.",
            "https://www.eia.gov/opendata/documentation.php",
            "append_only_when_value_changes",
            "weekly",
            "thousand_barrels",
        ),
        (
            "cftc-cot-pre",
            "cftc-cot-pre",
            "CFTC COT PRE",
            "derivatives_positioning",
            "Selected synthetic trader-positioning observations.",
            "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
            "append_only_when_value_changes",
            "weekly",
            "contracts",
        ),
        (
            "federal-register-documents",
            "federal-register-api",
            "Federal Register Documents",
            "regulation",
            "Selected synthetic regulatory metadata and abstracts.",
            "https://www.federalregister.gov/developers/documentation/api/v1",
            "document_metadata_versions_retained",
            "event",
            None,
        ),
    ]
    return [
        OfficialDataset(
            id=_stable_uuid("official-dataset", dataset_id),
            dataset_id=dataset_id,
            source_id=source_id,
            display_name=display_name,
            category=category,
            description=description,
            documentation_url=documentation_url,
            revision_policy=revision_policy,
            frequency=frequency,
            unit=unit,
            synthetic=True,
            provenance={"fixture_version": OFFICIAL_DATA_FIXTURE_VERSION},
        )
        for (
            dataset_id,
            source_id,
            display_name,
            category,
            description,
            documentation_url,
            revision_policy,
            frequency,
            unit,
        ) in rows
    ]


def _profiles() -> list[OfficialSeriesProfile]:
    rows: list[
        tuple[
            str,
            str,
            str,
            str,
            dict[str, object],
            dict[str, str],
            str | None,
            str,
            str | None,
        ]
    ] = [
        (
            "bls-ces-total-nonfarm",
            "bls-ces",
            "bls-public-data",
            "Total nonfarm payrolls",
            {"series_id": "CES0000000001"},
            {"measure": "employment", "seasonal": "sa"},
            "thousands_of_persons",
            "monthly",
            "seasonally_adjusted",
        ),
        (
            "bls-ces-manufacturing",
            "bls-ces",
            "bls-public-data",
            "Manufacturing payrolls",
            {"series_id": "CES3000000001"},
            {"measure": "employment", "sector": "manufacturing", "seasonal": "sa"},
            "thousands_of_persons",
            "monthly",
            "seasonally_adjusted",
        ),
        (
            "bls-ces-avg-hourly-earnings",
            "bls-ces",
            "bls-public-data",
            "Average hourly earnings",
            {"series_id": "CES0500000003"},
            {"measure": "earnings", "seasonal": "sa"},
            "usd_per_hour",
            "monthly",
            "seasonally_adjusted",
        ),
        (
            "bls-ces-unemployment-rate",
            "bls-ces",
            "bls-public-data",
            "Unemployment rate proxy",
            {"series_id": "LNS14000000"},
            {"measure": "unemployment_rate", "seasonal": "sa"},
            "percent",
            "monthly",
            "seasonally_adjusted",
        ),
        (
            "eia-crude-stocks",
            "eia-petroleum-stocks",
            "eia-open-data-v2",
            "Commercial crude oil stocks",
            {"route": "petroleum/stoc/wstk", "series": "WCESTUS1"},
            {"commodity": "crude_oil", "region": "us"},
            "thousand_barrels",
            "weekly",
            None,
        ),
        (
            "eia-gasoline-stocks",
            "eia-petroleum-stocks",
            "eia-open-data-v2",
            "Motor gasoline stocks",
            {"route": "petroleum/stoc/wstk", "series": "WGTSTUS1"},
            {"commodity": "gasoline", "region": "us"},
            "thousand_barrels",
            "weekly",
            None,
        ),
        (
            "eia-natural-gas-storage",
            "eia-petroleum-stocks",
            "eia-open-data-v2",
            "Natural gas storage",
            {"route": "natural-gas/stor/wkly", "series": "WNGSRUS2"},
            {"commodity": "natural_gas", "region": "us"},
            "bcf",
            "weekly",
            None,
        ),
        (
            "eia-distillate-stocks",
            "eia-petroleum-stocks",
            "eia-open-data-v2",
            "Distillate fuel oil stocks",
            {"route": "petroleum/stoc/wstk", "series": "WDISTUS1"},
            {"commodity": "distillate", "region": "us"},
            "thousand_barrels",
            "weekly",
            None,
        ),
        (
            "cftc-equity-index-positioning",
            "cftc-cot-pre",
            "cftc-cot-pre",
            "Equity index positioning",
            {"resource": "6dca-aqww", "market_code": "13874A"},
            {"market": "equity_index", "report": "pre"},
            "contracts",
            "weekly",
            None,
        ),
        (
            "cftc-rates-positioning",
            "cftc-cot-pre",
            "cftc-cot-pre",
            "Treasury futures positioning",
            {"resource": "6dca-aqww", "market_code": "020601"},
            {"market": "rates", "report": "pre"},
            "contracts",
            "weekly",
            None,
        ),
        (
            "cftc-metals-positioning",
            "cftc-cot-pre",
            "cftc-cot-pre",
            "Precious metals futures positioning",
            {"resource": "6dca-aqww", "market_code": "088691"},
            {"market": "precious_metal", "report": "pre"},
            "contracts",
            "weekly",
            None,
        ),
        (
            "cftc-energy-positioning",
            "cftc-cot-pre",
            "cftc-cot-pre",
            "Energy futures positioning",
            {"resource": "6dca-aqww", "market_code": "067651"},
            {"market": "energy", "report": "pre"},
            "contracts",
            "weekly",
            None,
        ),
        (
            "fr-energy-regulation",
            "federal-register-documents",
            "federal-register-api",
            "Energy regulatory documents",
            {"conditions[term]": "energy", "per_page": 5},
            {"topic": "energy"},
            None,
            "event",
            None,
        ),
        (
            "fr-bank-capital-regulation",
            "federal-register-documents",
            "federal-register-api",
            "Bank capital regulatory documents",
            {"conditions[term]": "bank capital", "per_page": 8},
            {"topic": "bank_capital"},
            None,
            "event",
            None,
        ),
        (
            "fr-commodity-reporting-regulation",
            "federal-register-documents",
            "federal-register-api",
            "Commodity reporting regulatory documents",
            {"conditions[term]": "commodity reporting", "per_page": 8},
            {"topic": "commodity_reporting"},
            None,
            "event",
            None,
        ),
        (
            "fr-market-structure-regulation",
            "federal-register-documents",
            "federal-register-api",
            "Market structure regulatory documents",
            {"conditions[term]": "market structure", "per_page": 5},
            {"topic": "market_structure"},
            None,
            "event",
            None,
        ),
    ]
    return [
        OfficialSeriesProfile(
            id=_stable_uuid("official-profile", profile_id),
            profile_id=profile_id,
            dataset_id=dataset_id,
            source_id=source_id,
            display_name=display_name,
            query=query,
            dimensions=dimensions,
            unit=unit,
            frequency=frequency,
            seasonal_adjustment=seasonal_adjustment,
            synthetic=True,
            provenance={"fixture_version": OFFICIAL_DATA_FIXTURE_VERSION},
        )
        for (
            profile_id,
            dataset_id,
            source_id,
            display_name,
            query,
            dimensions,
            unit,
            frequency,
            seasonal_adjustment,
        ) in rows
    ]


def _observation_records(
    profiles: list[OfficialSeriesProfile],
) -> list[OfficialObservationRecord]:
    numeric_profiles = [
        profile for profile in profiles if profile.source_id != "federal-register-api"
    ]
    records: list[OfficialObservationRecord] = []
    for profile_index, profile in enumerate(numeric_profiles):
        for period_index in range(12):
            period_start = date(2026, 1 + period_index, 1)
            if profile.frequency == "weekly":
                period_start = date(2026, 1, 2) + timedelta(days=period_index * 7)
            period_end = period_start
            first_seen = OFFICIAL_DATA_GENERATED_AT - timedelta(days=120 - period_index)
            base_value = Decimal(1000 + profile_index * 37 + period_index * 11).quantize(
                Decimal("0.1")
            )
            records.append(
                OfficialObservationRecord(
                    source_id=profile.source_id,
                    dataset_id=profile.dataset_id,
                    profile_id=profile.profile_id,
                    period_start=period_start,
                    period_end=period_end,
                    dimensions=dict(profile.dimensions),
                    value=base_value,
                    first_seen_at=first_seen,
                    source_updated_at=first_seen - timedelta(minutes=10),
                    provenance={
                        "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                        "profile_query": profile.query,
                    },
                )
            )
            if period_index in {4, 9}:
                revised_seen = first_seen + timedelta(days=7)
                records.append(
                    OfficialObservationRecord(
                        source_id=profile.source_id,
                        dataset_id=profile.dataset_id,
                        profile_id=profile.profile_id,
                        period_start=period_start,
                        period_end=period_end,
                        dimensions=dict(profile.dimensions),
                        value=base_value + Decimal("1.5"),
                        first_seen_at=revised_seen,
                        source_updated_at=revised_seen - timedelta(minutes=3),
                        provenance={
                            "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                            "revision_fixture": True,
                        },
                    )
                )
    return records


def _regulatory_documents() -> list[RegulatoryDocument]:
    docs: list[RegulatoryDocument] = []
    topics = [
        (
            "fr-energy-regulation",
            "energy",
            ["Department of Energy"],
            ["10 CFR 430"],
            ["1904-AF01"],
        ),
        (
            "fr-market-structure-regulation",
            "market structure",
            ["Securities and Exchange Commission"],
            ["17 CFR 242"],
            ["3235-AM88"],
        ),
        (
            "fr-bank-capital-regulation",
            "bank capital",
            ["Federal Reserve System"],
            ["12 CFR 217"],
            ["7100-AG77"],
        ),
        (
            "fr-commodity-reporting-regulation",
            "commodity reporting",
            ["Commodity Futures Trading Commission"],
            ["17 CFR 45"],
            ["3038-AF45"],
        ),
    ]
    for topic_index, (profile_id, topic, agencies, cfr, rin) in enumerate(topics):
        for item_index in range(8):
            ordinal = topic_index * 8 + item_index + 1
            publication_day = date(2026, 3, 1) + timedelta(days=ordinal - 1)
            available_at = datetime(2026, 3, 1, 12, 0, tzinfo=UTC) + timedelta(days=ordinal - 1)
            document_id = f"FR-SYN-{ordinal:04d}"
            docs.append(
                RegulatoryDocument(
                    id=_stable_uuid("reg-doc", document_id),
                    document_id=document_id,
                    source_id="federal-register-api",
                    title=f"Synthetic {topic} regulatory document {item_index + 1}",
                    abstract=(
                        "Source-provided synthetic abstract for "
                        f"{topic} metadata fixture {item_index + 1}."
                    ),
                    publication_date=publication_day,
                    document_type="Proposed Rule" if item_index % 2 else "Notice",
                    agencies=agencies,
                    cfr_references=cfr,
                    rin=rin,
                    html_url=(
                        "https://www.federalregister.gov/documents/"
                        f"2026/03/{publication_day.day:02d}/{document_id.lower()}"
                    ),
                    pdf_url=(
                        f"https://www.govinfo.gov/content/pkg/{document_id}/pdf/{document_id}.pdf"
                    ),
                    information_available_at=available_at,
                    source_updated_at=available_at,
                    synthetic=True,
                    provenance={
                        "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                        "profile_id": profile_id,
                        "full_text_requested": False,
                        "pdf_downloaded": False,
                    },
                )
            )
    return docs


def _associations(profiles: list[OfficialSeriesProfile]) -> list[SeriesAssetAssociation]:
    assets = build_cross_asset_demo().assets
    associations: list[SeriesAssetAssociation] = []
    for profile_index, profile in enumerate(profiles):
        for target_index in range(5):
            asset = assets[(profile_index * 3 + target_index) % len(assets)]
            associations.append(
                SeriesAssetAssociation(
                    id=_stable_uuid("series-asset", profile.profile_id, asset.asset_id),
                    association_id=f"ODA-ASSOC-{len(associations) + 1:03d}",
                    profile_id=profile.profile_id,
                    asset_id=asset.asset_id,
                    relationship_type="macro_relevance_hypothesis",
                    rationale=(
                        "Synthetic mapping for research navigation only; not a direction, "
                        "recommendation, or executable signal."
                    ),
                    confidence=round(0.45 + (target_index % 5) / 10, 2),
                    active=True,
                    synthetic=True,
                    provenance={"fixture_version": OFFICIAL_DATA_FIXTURE_VERSION},
                )
            )
    return associations


def _events(
    records: list[OfficialObservationRecord], documents: list[RegulatoryDocument]
) -> list[OfficialReleaseEvent]:
    events: list[OfficialReleaseEvent] = []
    family_by_source = {
        "bls-public-data": CrossAssetEventFamily.LABOR_MARKET,
        "eia-open-data-v2": CrossAssetEventFamily.INVENTORY_DEMAND,
        "cftc-cot-pre": CrossAssetEventFamily.DERIVATIVES_POSITIONING,
    }
    first_by_profile: dict[str, OfficialObservationRecord] = {}
    revised_records: list[OfficialObservationRecord] = []
    for record in records:
        first_by_profile.setdefault(record.profile_id, record)
        if record.provenance.get("revision_fixture") is True:
            revised_records.append(record)
    for index, record in enumerate(first_by_profile.values(), start=1):
        info_time, _ = information_available_at(record.first_seen_at, record.source_updated_at)
        events.append(
            OfficialReleaseEvent(
                id=_stable_uuid("official-event", "obs", index),
                event_id=f"ODE-OBS-{index:03d}",
                source_id=record.source_id,
                dataset_id=record.dataset_id,
                profile_id=record.profile_id,
                document_id=None,
                event_family=family_by_source[record.source_id],
                description=f"Synthetic official release for {record.profile_id}",
                information_available_at=info_time,
                revision_number=1,
                provenance={
                    "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                    "origin": "initial_observation",
                },
                synthetic=True,
            )
        )
    for index, record in enumerate(revised_records, start=1):
        info_time, _ = information_available_at(record.first_seen_at, record.source_updated_at)
        events.append(
            OfficialReleaseEvent(
                id=_stable_uuid("official-event", "revision", index),
                event_id=f"ODE-REV-{index:03d}",
                source_id=record.source_id,
                dataset_id=record.dataset_id,
                profile_id=record.profile_id,
                document_id=None,
                event_family=family_by_source[record.source_id],
                description=f"Synthetic changed-value revision for {record.profile_id}",
                information_available_at=info_time,
                revision_number=2,
                provenance={
                    "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                    "origin": "changed_value_revision",
                },
                synthetic=True,
            )
        )
    for index, document in enumerate(documents[:12], start=1):
        profile_id = str(document.provenance.get("profile_id", "fr-energy-regulation"))
        events.append(
            OfficialReleaseEvent(
                id=_stable_uuid("official-event", "doc", document.document_id),
                event_id=f"ODE-DOC-{index:03d}",
                source_id=document.source_id,
                dataset_id="federal-register-documents",
                profile_id=profile_id,
                document_id=document.document_id,
                event_family=CrossAssetEventFamily.REGULATION_ENFORCEMENT,
                description=f"Synthetic regulatory metadata release for {document.document_id}",
                information_available_at=document.information_available_at,
                revision_number=None,
                provenance={
                    "fixture_version": OFFICIAL_DATA_FIXTURE_VERSION,
                    "origin": "regulatory_document",
                },
                synthetic=True,
            )
        )
    return events


def _release_runs(records: list[OfficialObservationRecord]) -> list[OfficialDataReleaseRun]:
    by_source: dict[tuple[str, str], list[OfficialObservationRecord]] = {}
    for record in records:
        by_source.setdefault((record.source_id, record.dataset_id), []).append(record)
    runs = [
        OfficialDataReleaseRun(
            id=_stable_uuid("official-release-run", source_id, dataset_id),
            release_run_id=f"ODR-{index:03d}",
            source_id=source_id,
            dataset_id=dataset_id,
            observed_at=OFFICIAL_DATA_GENERATED_AT + timedelta(minutes=index),
            profile_count=len({record.profile_id for record in rows}),
            observation_count=len(rows),
            new_revision_count=len(rows),
            unchanged_count=0,
            status="completed",
            no_persist_live=False,
            synthetic=True,
        )
        for index, ((source_id, dataset_id), rows) in enumerate(sorted(by_source.items()), start=1)
    ]
    runs.append(
        OfficialDataReleaseRun(
            id=_stable_uuid("official-release-run", "federal-register-api", "documents"),
            release_run_id="ODR-004",
            source_id="federal-register-api",
            dataset_id="federal-register-documents",
            observed_at=OFFICIAL_DATA_GENERATED_AT + timedelta(minutes=4),
            profile_count=4,
            observation_count=32,
            new_revision_count=0,
            unchanged_count=0,
            status="completed",
            no_persist_live=False,
            synthetic=True,
        )
    )
    return runs


def build_official_data_release_ledger(
    repository: NewsRepository, postgres_table_counts: dict[str, int] | None = None
) -> dict[str, Any]:
    datasets = repository.list_official_datasets()
    profiles = repository.list_official_series_profiles()
    observations = repository.list_official_observations()
    revisions = repository.list_official_observation_revisions()
    documents = repository.list_regulatory_documents()
    associations = repository.list_series_asset_associations()
    events = repository.list_official_release_events()
    runs = repository.list_official_data_release_runs()
    static_payload = official_data_static_payload(repository)
    series_profiles = [
        row for row in profiles if row.source_id in {"bls-public-data", "eia-open-data-v2"}
    ]
    query_profiles = [
        row for row in profiles if row.source_id in {"cftc-cot-pre", "federal-register-api"}
    ]
    changed_revisions = [row for row in revisions if row.revision_number > 1]
    ledger: dict[str, Any] = {
        "schema_version": OFFICIAL_DATA_LEDGER_SCHEMA_VERSION,
        "generator_version": OFFICIAL_DATA_FIXTURE_VERSION,
        "synthetic_data": True,
        "not_investment_advice": True,
        "live_data_persisted": False,
        "official_source_definition_count": len(
            [
                row
                for row in repository.list_source_definitions()
                if row.source_id in OFFICIAL_SOURCE_IDS
            ]
        ),
        "physical_dataset_table_count": len(datasets),
        "dataset_definition_count": len(datasets),
        "series_definition_count": len(series_profiles),
        "query_profile_count": len(query_profiles),
        "definition_count_total": len(profiles),
        "observation_business_key_count": len(observations),
        "observation_revision_row_count": len(revisions),
        "current_observation_count": len(observations),
        "superseded_revision_count": len(changed_revisions),
        "changed_value_revision_count": len(changed_revisions),
        "regulatory_document_count": len(documents),
        "series_asset_association_count": len(associations),
        "derived_release_event_count": len(events),
        "release_run_count": len(runs),
        "static_export_record_counts": {
            name: len(value) if isinstance(value, list) else 1
            for name, value in static_payload.items()
        },
        "postgres_table_counts": postgres_table_counts or {},
        "source_distribution": _count_by(profiles, "source_id"),
        "observation_distribution": _count_by(observations, "source_id"),
        "changed_revision_distribution": _count_by_revision_source(changed_revisions, observations),
        "document_distribution": _count_documents_by_profile(documents),
        "association_distribution": _count_associations_by_source(associations, profiles),
        "event_distribution": _count_by(events, "source_id"),
        "revision_storage_model": (
            "official_observations stores one current row per business key; "
            "official_observation_revisions stores revision 1 plus changed-value revisions"
        ),
    }
    ledger["deterministic_hashes"] = {
        "datasets": _hash_rows(_dataset_row(row) for row in datasets),
        "profiles": _hash_rows(_profile_row(row) for row in profiles),
        "observations": _hash_rows(_observation_row(row) for row in observations),
        "revisions": _hash_rows(_revision_row(row) for row in revisions),
        "documents": _hash_rows(_document_row(row) for row in documents),
        "associations": _hash_rows(_association_row(row) for row in associations),
        "events": _hash_rows(_event_row(row) for row in events),
    }
    ledger["ledger_sha256"] = sha256_text(
        _canonical_json({key: value for key, value in ledger.items() if key != "ledger_sha256"})
    )
    return ledger


def official_observation_as_of(
    repository: NewsRepository, observation_key: str, as_of: datetime
) -> OfficialObservationRevision | None:
    if as_of.tzinfo is None:
        raise OfficialDataError("as_of must be timezone-aware")
    candidates = [
        revision
        for revision in repository.list_official_observation_revisions(observation_key)
        if revision.information_available_at <= as_of
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (item.information_available_at, item.revision_number),
    )[-1]


def _validate_record_time(record: OfficialObservationRecord) -> None:
    information_available_at(record.first_seen_at, record.source_updated_at)


def _record_order_key(record: OfficialObservationRecord) -> tuple[str, datetime, Decimal]:
    key = observation_business_key(
        record.source_id,
        record.dataset_id,
        record.profile_id,
        record.period_start,
        record.period_end,
        record.dimensions,
    )
    info_time, _ = information_available_at(record.first_seen_at, record.source_updated_at)
    return key, info_time, record.value


def _dataset_row(row: OfficialDataset) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
    }


def _profile_row(row: OfficialSeriesProfile) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
    }


def _observation_row(row: OfficialObservation) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
        "current_value": str(row.current_value),
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "first_seen_at": row.first_seen_at.isoformat(),
        "information_available_at": row.information_available_at.isoformat(),
    }


def _revision_row(row: OfficialObservationRevision) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
        "value": str(row.value),
        "first_seen_at": row.first_seen_at.isoformat(),
        "source_updated_at": row.source_updated_at.isoformat() if row.source_updated_at else None,
        "information_available_at": row.information_available_at.isoformat(),
    }


def _document_row(row: RegulatoryDocument) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
        "publication_date": row.publication_date.isoformat(),
        "information_available_at": row.information_available_at.isoformat(),
        "source_updated_at": row.source_updated_at.isoformat() if row.source_updated_at else None,
    }


def _association_row(row: SeriesAssetAssociation) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
    }


def _event_row(row: OfficialReleaseEvent) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
        "event_family": row.event_family.value,
        "information_available_at": row.information_available_at.isoformat(),
    }


def _run_row(row: OfficialDataReleaseRun) -> dict[str, Any]:
    return {
        **row.__dict__,
        "id": str(row.id),
        "observed_at": row.observed_at.isoformat(),
    }


def _stable_uuid(*parts: object) -> UUID:
    return uuid5(NAMESPACE_URL, "|".join(str(part) for part in parts))


def _canonical_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_rows(rows: Iterable[dict[str, Any]]) -> str:
    return sha256_text(_canonical_json(list(rows)))


def _count_by(rows: Iterable[object], attr: str) -> dict[str, int]:
    return dict(sorted(Counter(str(getattr(row, attr)) for row in rows).items()))


def _count_by_revision_source(
    revisions: list[OfficialObservationRevision], observations: list[OfficialObservation]
) -> dict[str, int]:
    source_by_key = {row.observation_key: row.source_id for row in observations}
    return dict(sorted(Counter(source_by_key[row.observation_key] for row in revisions).items()))


def _count_documents_by_profile(documents: list[RegulatoryDocument]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(str(row.provenance.get("profile_id", "unknown")) for row in documents).items()
        )
    )


def _count_associations_by_source(
    associations: list[SeriesAssetAssociation], profiles: list[OfficialSeriesProfile]
) -> dict[str, int]:
    source_by_profile = {row.profile_id: row.source_id for row in profiles}
    return dict(sorted(Counter(source_by_profile[row.profile_id] for row in associations).items()))
