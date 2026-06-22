from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path

from finnews.domain.enums import EventType, SentimentLabel
from finnews.infrastructure.nlp.benchmark.generator import (
    LANGUAGE_BY_FAMILY,
    SPLIT_BY_FAMILY,
    _hash_records,
    build_benchmark,
    load_records,
)
from finnews.infrastructure.nlp.benchmark.models import CHALLENGE_FLAGS, DATASET_ID, BenchmarkRecord
from finnews.infrastructure.normalization import comparison_text


class BenchmarkValidationError(ValueError):
    pass


def validate_benchmark_dir(dataset_dir: Path) -> dict[str, object]:
    records = load_records(dataset_dir)
    expected = build_benchmark()
    errors: list[str] = []
    _validate_counts(records, errors)
    _validate_splits(records, errors)
    _validate_duplicates(records, errors)
    _validate_challenges(records, errors)
    _validate_regeneration(records, expected, errors)
    _validate_manifest(dataset_dir, records, errors)
    if errors:
        raise BenchmarkValidationError("; ".join(errors))
    return summary(records, dataset_dir)


def summary(
    records: Sequence[BenchmarkRecord], dataset_dir: Path | None = None
) -> dict[str, object]:
    typed = load_records(dataset_dir) if dataset_dir else list(records)
    return {
        "dataset_id": DATASET_ID,
        "record_count": len(typed),
        "language_counts": dict(sorted(Counter(record.language for record in typed).items())),
        "split_counts": dict(sorted(Counter(record.split for record in typed).items())),
        "event_counts": dict(sorted(Counter(record.event_label.value for record in typed).items())),
        "sentiment_counts": dict(
            sorted(Counter(record.sentiment_label.value for record in typed).items())
        ),
        "challenge_record_count": sum(1 for record in typed if record.challenge_flags),
        "challenge_test_count": sum(
            1 for record in typed if record.split == "test" and record.challenge_flags
        ),
        "dataset_sha256": _file_hash(dataset_dir / "records.jsonl") if dataset_dir else None,
        "split_hashes": _split_hashes(typed),
    }


def _validate_counts(records: Sequence[BenchmarkRecord], errors: list[str]) -> None:
    if len(records) != 1296:
        errors.append(f"expected 1296 records, got {len(records)}")
    _expect_counts(
        Counter(record.language for record in records), {"zh": 864, "en": 432}, "language", errors
    )
    _expect_counts(
        Counter(record.split for record in records),
        {"train": 648, "validation": 324, "test": 324},
        "split",
        errors,
    )
    _expect_counts(
        Counter(record.event_label for record in records),
        {event: 144 for event in EventType},
        "event",
        errors,
    )
    _expect_counts(
        Counter(record.sentiment_label for record in records),
        {sentiment: 324 for sentiment in SentimentLabel},
        "sentiment",
        errors,
    )
    combo_counts = Counter((record.event_label, record.sentiment_label) for record in records)
    if any(
        combo_counts[(event, sentiment)] != 36
        for event in EventType
        for sentiment in SentimentLabel
    ):
        errors.append("event/sentiment combinations are not balanced")
    if len({record.company_id for record in records}) < 36:
        errors.append("expected at least 36 fictional companies")
    if len({record.industry for record in records}) < 12:
        errors.append("expected at least 12 industries")


def _validate_splits(records: Sequence[BenchmarkRecord], errors: list[str]) -> None:
    family_splits: dict[str, set[str]] = defaultdict(set)
    group_splits: dict[str, set[str]] = defaultdict(set)
    group_paraphrases: dict[str, set[int]] = defaultdict(set)
    for record in records:
        family_splits[record.template_family_id].add(record.split)
        group_splits[record.story_group_id].add(record.split)
        group_paraphrases[record.story_group_id].add(record.paraphrase_id)
        if SPLIT_BY_FAMILY.get(record.template_family_id) != record.split:
            errors.append(f"{record.record_id}: split does not match family policy")
        if LANGUAGE_BY_FAMILY.get(record.template_family_id) != record.language:
            errors.append(f"{record.record_id}: language does not match family policy")
    if any(len(splits) != 1 for splits in family_splits.values()):
        errors.append("template family appears in multiple splits")
    if any(len(splits) != 1 for splits in group_splits.values()):
        errors.append("story group appears in multiple splits")
    if any(paraphrases != {0, 1, 2} for paraphrases in group_paraphrases.values()):
        errors.append("story group paraphrases are incomplete or split")


def _validate_duplicates(records: Sequence[BenchmarkRecord], errors: list[str]) -> None:
    ids = [record.record_id for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate record IDs")
    text_by_split: dict[str, set[str]] = defaultdict(set)
    all_text: list[str] = []
    for record in records:
        text = comparison_text(record.combined_text)
        text_by_split[record.split].add(text)
        all_text.append(text)
        if record.event_label.value in text and record.sentiment_label.value in text:
            errors.append(f"{record.record_id}: label value leaked into feature text")
    if len(all_text) != len(set(all_text)):
        errors.append("exact duplicate normalized text")
    for left in ("train", "validation", "test"):
        for right in ("train", "validation", "test"):
            if left >= right:
                continue
            if text_by_split[left] & text_by_split[right]:
                errors.append(f"exact normalized text overlap between {left} and {right}")


def _validate_challenges(records: Sequence[BenchmarkRecord], errors: list[str]) -> None:
    challenge_records = [record for record in records if record.challenge_flags]
    test_challenge_records = [
        record for record in records if record.split == "test" and record.challenge_flags
    ]
    if len(challenge_records) < 324:
        errors.append("expected at least 324 challenge records")
    if len(test_challenge_records) < 108:
        errors.append("expected at least 108 test challenge records")
    test_flags = {flag for record in test_challenge_records for flag in record.challenge_flags}
    missing = set(CHALLENGE_FLAGS) - test_flags
    if missing:
        errors.append(f"challenge flags missing from test: {sorted(missing)}")


def _validate_regeneration(
    records: Sequence[BenchmarkRecord], expected: Sequence[BenchmarkRecord], errors: list[str]
) -> None:
    actual_payload = "\n".join(record.model_dump_json() for record in records)
    expected_payload = "\n".join(record.model_dump_json() for record in expected)
    if actual_payload != expected_payload:
        errors.append("records do not match deterministic regeneration")


def _validate_manifest(
    dataset_dir: Path, records: Sequence[BenchmarkRecord], errors: list[str]
) -> None:
    manifest_path = dataset_dir / "manifest.json"
    split_path = dataset_dir / "split_hashes.json"
    lock_path = dataset_dir / "test_lock.json"
    for path in (manifest_path, split_path, lock_path):
        if not path.is_file():
            errors.append(f"missing {path.name}")
            return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split_hashes = json.loads(split_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    dataset_hash = _file_hash(dataset_dir / "records.jsonl")
    computed_split_hashes = _split_hashes(records)
    if manifest.get("dataset_sha256") != dataset_hash:
        errors.append("manifest dataset hash mismatch")
    if split_hashes != computed_split_hashes:
        errors.append("split hashes mismatch")
    if lock.get("test_split_sha256") != computed_split_hashes["test"]:
        errors.append("test lock hash mismatch")


def _expect_counts(
    actual: Counter[object], expected: dict[object, int], label: str, errors: list[str]
) -> None:
    if dict(actual) != expected:
        errors.append(f"{label} counts mismatch: {dict(actual)}")


def _split_hashes(records: Sequence[BenchmarkRecord]) -> dict[str, str]:
    return {
        split: _hash_records([record for record in records if record.split == split])
        for split in ("train", "validation", "test")
    }


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
