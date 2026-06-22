from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from typer.testing import CliRunner

from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.application.services.export_static import build_static_payload, export_static
from finnews.application.services.pipeline import NewsPipeline
from finnews.bootstrap import FIXTURE_DIR, load_default_records
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.sources.local_feed import LocalFeedSource
from finnews.interfaces.cli.app import app
from finnews.settings import Settings

EXPECTED_METRICS = {
    "raw_observation_count": 68,
    "rejected_observation_count": 4,
    "valid_observation_count": 64,
    "canonical_article_count": 46,
    "exact_duplicate_observation_count": 8,
    "near_duplicate_observation_count": 10,
    "duplicate_observation_count": 18,
    "exact_duplicate_pair_count": 8,
    "near_duplicate_pair_count": 10,
    "duplicate_cluster_count": 18,
}


def build_repo() -> MemoryNewsRepository:
    settings = Settings(profile="memory")
    repo = MemoryNewsRepository()
    NewsPipeline(repo, settings).run_demo(
        load_default_records(settings), FIXTURE_DIR / "companies.json"
    )
    return repo


def test_observation_pair_cluster_accounting_and_invariants() -> None:
    accounting = build_deduplication_accounting(build_repo())
    assert accounting.metrics == EXPECTED_METRICS
    assert (
        accounting.metrics["raw_observation_count"]
        == accounting.metrics["rejected_observation_count"]
        + accounting.metrics["valid_observation_count"]
    )
    assert accounting.metrics["valid_observation_count"] == (
        accounting.metrics["canonical_article_count"]
        + accounting.metrics["exact_duplicate_observation_count"]
        + accounting.metrics["near_duplicate_observation_count"]
    )
    assert accounting.metrics["duplicate_observation_count"] == (
        accounting.metrics["exact_duplicate_observation_count"]
        + accounting.metrics["near_duplicate_observation_count"]
    )


def test_exact_near_precedence_no_double_counting_and_expected_ids() -> None:
    groups = build_deduplication_accounting(build_repo()).grouped_observation_ids
    assert set(groups["exact_duplicate"]).isdisjoint(groups["near_duplicate"])
    assert groups["exact_duplicate"] == [f"exact-{index:03d}" for index in range(1, 9)]
    assert groups["near_duplicate"] == [f"near-{index:03d}" for index in range(1, 11)]
    assert groups["rejected"] == [
        "bad-empty-title",
        "bad-language",
        "bad-time",
        "bad-url",
    ]


def test_canonical_reference_integrity_and_deterministic_assignments() -> None:
    first = build_deduplication_accounting(build_repo())
    second = build_deduplication_accounting(build_repo())
    assert first.canonical_assignments == second.canonical_assignments
    for observation_id in first.grouped_observation_ids["canonical"]:
        assert first.canonical_assignments[observation_id] == observation_id
    for index in range(1, 9):
        assert first.canonical_assignments[f"exact-{index:03d}"] == f"obs-{index:03d}"
    labels = json.loads((FIXTURE_DIR / "expected_labels.json").read_text(encoding="utf-8"))
    for index in range(1, 11):
        observation_id = f"near-{index:03d}"
        assert (
            first.canonical_assignments[observation_id]
            == labels[observation_id]["expected_canonical_observation_id"]
        )


def test_fixture_labels_match_detected_dispositions() -> None:
    labels = json.loads((FIXTURE_DIR / "expected_labels.json").read_text(encoding="utf-8"))
    accounting = build_deduplication_accounting(build_repo())
    detected = {
        observation_id: disposition
        for disposition, ids in accounting.grouped_observation_ids.items()
        for observation_id in ids
    }
    assert len(labels) == EXPECTED_METRICS["raw_observation_count"]
    assert Counter(label["disposition"] for label in labels.values()) == Counter(
        {
            "canonical": 46,
            "near_duplicate": 10,
            "exact_duplicate": 8,
            "rejected": 4,
        }
    )
    assert {key: value["disposition"] for key, value in labels.items()} == detected
    for observation_id, canonical_id in accounting.canonical_assignments.items():
        assert labels[observation_id]["expected_canonical_observation_id"] == canonical_id


def test_static_api_shape_and_cli_statistics_consistency(tmp_path: Path) -> None:
    repo = build_repo()
    payload = build_static_payload(repo)
    second_payload = build_static_payload(build_repo())
    assert [item["id"] for item in payload["articles"]] == [
        item["id"] for item in second_payload["articles"]
    ]
    assert [item["id"] for item in payload["companies"]] == [
        item["id"] for item in second_payload["companies"]
    ]
    assert payload["overview"]["deduplication"] == EXPECTED_METRICS
    assert payload["overview"]["article_count"] == EXPECTED_METRICS["canonical_article_count"]
    assert payload["overview"]["latest_pipeline"]["status"] == "completed"
    assert (
        payload["overview"]["latest_pipeline"]["per_step_counts"]["canonical_article_count"]
        == EXPECTED_METRICS["canonical_article_count"]
    )
    export_static(repo, tmp_path)
    exported = json.loads((tmp_path / "overview.json").read_text(encoding="utf-8"))
    assert exported["deduplication"] == EXPECTED_METRICS
    assert exported["latest_pipeline"]["status"] == "completed"

    result = CliRunner().invoke(app, ["demo", "--profile", "memory"])
    assert result.exit_code == 0
    demo = json.loads(result.output)
    assert demo["deduplication"] == EXPECTED_METRICS
    assert demo["articles"] == EXPECTED_METRICS["canonical_article_count"]


def test_jsonl_rss_and_atom_combined_accounting(tmp_path: Path) -> None:
    atom = tmp_path / "sample_atom.xml"
    atom.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>atom-unique-001</id>
    <title>Alpine Robotics publishes routine investor calendar notice</title>
    <link href="https://demo.local/atom/alp-unique" />
    <summary>Alpine Robotics published a routine calendar notice.</summary>
    <updated>2026-07-05T00:00:00+00:00</updated>
  </entry>
</feed>
""",
        encoding="utf-8",
    )
    settings = Settings(profile="memory")
    records = [
        *load_default_records(settings),
        *LocalFeedSource(atom, settings.max_fixture_bytes).read_records(),
    ]
    repo = MemoryNewsRepository()
    NewsPipeline(repo, settings).run_demo(records, FIXTURE_DIR / "companies.json")
    metrics = build_deduplication_accounting(repo).metrics
    assert metrics["raw_observation_count"] == 69
    assert metrics["canonical_article_count"] == 47
    assert metrics["duplicate_observation_count"] == 18
