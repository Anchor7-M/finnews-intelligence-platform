from __future__ import annotations

import json
from pathlib import Path

from finnews.bootstrap import FIXTURE_DIR, load_default_records
from finnews.settings import Settings


def test_committed_fixture_composition_requirements() -> None:
    records = [
        json.loads(line)
        for line in (FIXTURE_DIR / "articles.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    companies = json.loads((FIXTURE_DIR / "companies.json").read_text(encoding="utf-8"))
    manifest = json.loads((FIXTURE_DIR / "fixture_manifest.json").read_text(encoding="utf-8"))
    labels = json.loads((FIXTURE_DIR / "expected_labels.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 20260622
    assert len(records) >= 60
    assert len(companies) >= 12
    assert manifest["exact_duplicate_observations"] >= 8
    assert manifest["near_duplicate_observations"] >= 10
    assert sum(1 for label in labels.values() if label["disposition"] == "exact_duplicate") == 8
    assert sum(1 for label in labels.values() if label["disposition"] == "near_duplicate") == 10
    assert {"en", "zh"}.issubset(
        {record["language"] for record in records if record["duplicate_kind"] != "malformed"}
    )
    assert {"positive", "neutral", "negative", "uncertain"}.issubset(
        set(manifest["sentiment_categories"])
    )
    assert {
        "earnings",
        "merger_acquisition",
        "policy_regulation",
        "operations_product",
        "financing_capital",
        "litigation_penalty",
        "governance_personnel",
        "macro_market",
        "other",
    }.issubset(set(manifest["event_categories"]))
    assert any(not record.get("article_id") for record in records)
    assert any("utm_" in record["url"] for record in records)
    assert sum(1 for record in records if record["duplicate_kind"] == "malformed") >= 4


def test_default_fixture_loading_counts_raw_sources_and_feed() -> None:
    records = load_default_records(Settings(profile="memory"))
    assert len(records) == 68
    assert len({record.source_key for record in records}) >= 5


def test_fixture_files_stay_below_size_limit() -> None:
    total = sum(path.stat().st_size for path in Path(FIXTURE_DIR).glob("*") if path.is_file())
    assert total < 5_000_000
