from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from finnews.application.ports.repositories import NewsRepository
from finnews.domain.entities import ObservationDisposition

DEDUPLICATION_METRIC_KEYS = [
    "raw_observation_count",
    "rejected_observation_count",
    "valid_observation_count",
    "canonical_article_count",
    "exact_duplicate_observation_count",
    "near_duplicate_observation_count",
    "duplicate_observation_count",
    "exact_duplicate_pair_count",
    "near_duplicate_pair_count",
    "duplicate_cluster_count",
]


@dataclass(frozen=True)
class DeduplicationAccounting:
    metrics: dict[str, int]
    grouped_observation_ids: dict[str, list[str]]
    canonical_assignments: dict[str, str]
    duplicate_details: list[dict[str, Any]]


def build_deduplication_accounting(repository: NewsRepository) -> DeduplicationAccounting:
    dispositions = repository.list_observation_dispositions()
    grouped = {
        "rejected": sorted(_ids(dispositions, "rejected")),
        "canonical": sorted(_ids(dispositions, "canonical")),
        "exact_duplicate": sorted(_ids(dispositions, "exact_duplicate")),
        "near_duplicate": sorted(_ids(dispositions, "near_duplicate")),
    }
    exact_ids = set(grouped["exact_duplicate"])
    near_ids = set(grouped["near_duplicate"])
    overlap = exact_ids & near_ids
    if overlap:
        raise ValueError(f"observations classified as both exact and near duplicates: {overlap}")

    valid = [
        item
        for item in dispositions
        if item.disposition in {"canonical", "exact_duplicate", "near_duplicate"}
    ]
    canonical = [item for item in dispositions if item.disposition == "canonical"]
    exact = [item for item in dispositions if item.disposition == "exact_duplicate"]
    near = [item for item in dispositions if item.disposition == "near_duplicate"]
    rejected = [item for item in dispositions if item.disposition == "rejected"]

    canonical_article_ids = {
        _require_article_id(item) for item in canonical if item.canonical_article_id is not None
    }
    assignments: dict[str, str] = {}
    clusters: dict[UUID, list[str]] = {}
    for item in valid:
        if not item.canonical_observation_id:
            raise ValueError(f"valid observation {item.observation_id} has no canonical reference")
        article_id = _require_article_id(item)
        assignments[item.observation_id] = item.canonical_observation_id
        clusters.setdefault(article_id, []).append(item.observation_id)
        if item.disposition != "canonical" and article_id not in canonical_article_ids:
            raise ValueError(
                f"duplicate observation {item.observation_id} references non-canonical article"
            )
        if item.disposition == "canonical" and item.canonical_observation_id != item.observation_id:
            raise ValueError(f"canonical observation {item.observation_id} is not self-referential")

    metrics = {
        "raw_observation_count": len(dispositions),
        "rejected_observation_count": len(rejected),
        "valid_observation_count": len(valid),
        "canonical_article_count": len(canonical),
        "exact_duplicate_observation_count": len(exact),
        "near_duplicate_observation_count": len(near),
        "duplicate_observation_count": len(exact) + len(near),
        "exact_duplicate_pair_count": len(exact),
        "near_duplicate_pair_count": len(near),
        "duplicate_cluster_count": sum(1 for ids in clusters.values() if len(ids) >= 2),
    }
    _validate_invariants(metrics)
    details = [
        {
            "observation_id": item.observation_id,
            "source_key": item.source_key,
            "disposition": item.disposition,
            "canonical_observation_id": item.canonical_observation_id,
            "canonical_article_id": str(item.canonical_article_id)
            if item.canonical_article_id
            else None,
            "duplicate_type": item.duplicate_type.value if item.duplicate_type else None,
            "similarity_score": item.similarity_score,
            "explanation": item.explanation,
            "fixture_group": item.fixture_group,
        }
        for item in dispositions
    ]
    return DeduplicationAccounting(metrics, grouped, assignments, details)


def _ids(dispositions: list[ObservationDisposition], disposition: str) -> list[str]:
    return [item.observation_id for item in dispositions if item.disposition == disposition]


def _require_article_id(item: ObservationDisposition) -> UUID:
    if item.canonical_article_id is None:
        raise ValueError(f"observation {item.observation_id} has no canonical article")
    return item.canonical_article_id


def _validate_invariants(metrics: dict[str, int]) -> None:
    if (
        metrics["raw_observation_count"]
        != metrics["rejected_observation_count"] + metrics["valid_observation_count"]
    ):
        raise ValueError("raw observation accounting invariant failed")
    if metrics["valid_observation_count"] != (
        metrics["canonical_article_count"]
        + metrics["exact_duplicate_observation_count"]
        + metrics["near_duplicate_observation_count"]
    ):
        raise ValueError("valid observation accounting invariant failed")
    if metrics["duplicate_observation_count"] != (
        metrics["exact_duplicate_observation_count"] + metrics["near_duplicate_observation_count"]
    ):
        raise ValueError("duplicate observation accounting invariant failed")
