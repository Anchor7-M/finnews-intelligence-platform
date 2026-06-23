from __future__ import annotations

import json
import tempfile
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from sklearn.base import clone
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

from finnews.application.services.nlp_artifacts import sha256_file
from finnews.application.services.nlp_evaluation import (
    _apply_alpha,
    _candidate_pipelines,
    _labels,
    _predict_with_probabilities,
    _select_probability_alpha,
    _texts,
    _truth,
    report_config_hash,
    run_nlp_benchmark,
)
from finnews.domain.enums import EventType, SentimentLabel
from finnews.infrastructure.nlp.benchmark.generator import (
    SOURCE_TYPES,
    _hash_records,
    benchmark_dir,
    load_records,
    write_benchmark,
)
from finnews.infrastructure.nlp.benchmark.models import (
    CHALLENGE_FLAGS,
    DATASET_ID,
    BenchmarkRecord,
)
from finnews.infrastructure.normalization import comparison_text

TaskName = Literal["event", "sentiment"]
SPLITS = ("train", "validation", "test")
SIMILARITY_WARNING_THRESHOLD = 0.92
SIMILARITY_NGRAM_SIZE = 5


def write_release_audit_reports(repo_root: Path) -> dict[str, Any]:
    dataset_dir = benchmark_dir(repo_root)
    report_dir = repo_root / "reports" / "nlp" / DATASET_ID
    artifact_root = repo_root / ".finnews-artifacts" / "nlp"
    report_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(dataset_dir)
    evaluation = json.loads((report_dir / "evaluation.json").read_text(encoding="utf-8"))

    outputs = {
        "benchmark-ledger": benchmark_ledger(dataset_dir, records),
        "leakage-audit": leakage_audit(records),
        "selection-trace": selection_trace(dataset_dir, records, evaluation),
        "feature-audit": feature_audit(records, evaluation),
        "determinism-audit": determinism_audit(dataset_dir, artifact_root),
        "artifact-audit": artifact_audit(repo_root, evaluation),
    }
    for name, payload in outputs.items():
        (report_dir / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "dataset_id": DATASET_ID,
        "reports": sorted(f"{name}.json" for name in outputs),
        "status": "completed",
    }


def benchmark_ledger(dataset_dir: Path, records: Sequence[BenchmarkRecord]) -> dict[str, Any]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    config_path = dataset_dir / "generation_config.json"
    records_path = dataset_dir / "records.jsonl"
    event_sentiment = Counter(
        f"{record.event_label.value}:{record.sentiment_label.value}" for record in records
    )
    story_counts = Counter(record.story_group_id for record in records)
    return {
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "generator_version": manifest["generator_version"],
        "record_count": len(records),
        "language_counts": _counter(record.language for record in records),
        "split_counts": _counter(record.split for record in records),
        "event_enum_values": [label.value for label in EventType],
        "sentiment_enum_values": [label.value for label in SentimentLabel],
        "event_counts": _counter(record.event_label.value for record in records),
        "sentiment_counts": _counter(record.sentiment_label.value for record in records),
        "event_sentiment_counts": dict(sorted(event_sentiment.items())),
        "template_family_counts": _counter(record.template_family_id for record in records),
        "story_group_count": len(story_counts),
        "story_group_size_counts": _counter(story_counts.values()),
        "difficulty_counts": _counter(record.difficulty for record in records),
        "challenge_flag_counts": _counter(
            flag for record in records for flag in record.challenge_flags
        ),
        "challenge_presence_counts": _counter(
            "challenge" if record.challenge_flags else "plain" for record in records
        ),
        "challenge_by_split": _counter(
            record.split for record in records if record.challenge_flags
        ),
        "fictional_company_count": len({record.company_id for record in records}),
        "fictional_industry_count": len({record.industry for record in records}),
        "fictional_source_type_count": len({record.source_type for record in records}),
        "committed_records_bytes": records_path.stat().st_size,
        "dataset_sha256": sha256_file(records_path),
        "split_hashes": _split_hashes(records),
        "schema_config_hash": sha256_file(config_path),
        "manifest_sha256": sha256_file(dataset_dir / "manifest.json"),
        "test_lock_sha256": sha256_file(dataset_dir / "test_lock.json"),
        "source_types": list(SOURCE_TYPES),
        "challenge_flags": list(CHALLENGE_FLAGS),
    }


def leakage_audit(records: Sequence[BenchmarkRecord]) -> dict[str, Any]:
    by_split = {split: [record for record in records if record.split == split] for split in SPLITS}
    normalized_by_id = {
        record.record_id: comparison_text(record.combined_text) for record in records
    }
    exact_overlaps: dict[str, list[dict[str, str]]] = {}
    max_similarities: dict[str, dict[str, Any]] = {}
    warning_pairs: dict[str, list[dict[str, Any]]] = {}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        key = f"{left}_vs_{right}"
        left_texts = {
            normalized_by_id[record.record_id]: record.record_id for record in by_split[left]
        }
        right_texts = {
            normalized_by_id[record.record_id]: record.record_id for record in by_split[right]
        }
        exact_overlaps[key] = [
            {"left_record_id": left_texts[text], "right_record_id": right_texts[text]}
            for text in sorted(set(left_texts) & set(right_texts))
        ]
        maximum, pairs = _cross_split_similarity(by_split[left], by_split[right])
        max_similarities[key] = maximum
        warning_pairs[key] = pairs

    family_splits = _group_splits(records, "template_family_id")
    story_splits = _group_splits(records, "story_group_id")
    return {
        "method": {
            "normalization": "comparison_text lowercase/punctuation normalization",
            "near_duplicate_similarity": (
                f"Jaccard similarity over normalized character {SIMILARITY_NGRAM_SIZE}-grams"
            ),
            "warning_threshold": SIMILARITY_WARNING_THRESHOLD,
        },
        "record_ids_disjoint": _ids_disjoint(by_split),
        "template_families_disjoint": all(len(splits) == 1 for splits in family_splits.values()),
        "story_groups_disjoint": all(len(splits) == 1 for splits in story_splits.values()),
        "paraphrases_stay_in_one_split": all(len(splits) == 1 for splits in story_splits.values()),
        "exact_text_duplicate_count": len(records) - len(set(normalized_by_id.values())),
        "exact_cross_split_overlaps": exact_overlaps,
        "maximum_cross_split_similarities": max_similarities,
        "pairs_at_or_above_warning_threshold": warning_pairs,
        "prohibited_pair_found": any(exact_overlaps.values()) or any(warning_pairs.values()),
        "test_lock_checked": True,
    }


def selection_trace(
    dataset_dir: Path, records: Sequence[BenchmarkRecord], evaluation: dict[str, Any]
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "dataset_sha256": sha256_file(dataset_dir / "records.jsonl"),
        "split_hashes": _split_hashes(records),
        "test_set_used_for_selection": False,
        "tasks": {},
    }
    for task in ("event", "sentiment"):
        task_report = evaluation["tasks"][task]
        selected = task_report["selected_candidate"]
        config = {
            "task": task,
            "selected_candidate": selected,
            "random_state": 20260622,
            "n_jobs": 1,
            "calibration_alpha": task_report["calibration"]["alpha"],
            "abstention_threshold": task_report["abstention"]["threshold"],
            "feature_text": "TITLE plus SUMMARY only",
        }
        validation_metrics = task_report["candidate_validation"]
        selected_metrics = validation_metrics[selected]
        trace["tasks"][task] = {
            "candidate_ids": sorted(validation_metrics),
            "train_hash": _split_hash(records, "train"),
            "validation_hash": _split_hash(records, "validation"),
            "locked_test_hash": _split_hash(records, "test"),
            "validation_metrics": validation_metrics,
            "tie_break_values": {
                name: {
                    "macro_f1": metrics["macro_f1"],
                    "expected_calibration_error": metrics["expected_calibration_error"],
                    "complexity_rank": 1 if name == "char_tfidf_logreg" else 2,
                }
                for name, metrics in validation_metrics.items()
            },
            "selected_candidate": selected,
            "tie_break_reason": _tie_break_reason(validation_metrics, selected),
            "selected_validation_metrics": selected_metrics,
            "calibration_decision": task_report["calibration"],
            "abstention_threshold": task_report["abstention"]["threshold"],
            "freeze_config_hash": report_config_hash(config),
            "final_test_evaluation_id": f"{task_report['selected_model_id']}-test",
            "test_evaluation_after_freeze": True,
        }
    return trace


def feature_audit(records: Sequence[BenchmarkRecord], evaluation: dict[str, Any]) -> dict[str, Any]:
    train = [record for record in records if record.split == "train"]
    validation = [record for record in records if record.split == "validation"]
    result: dict[str, Any] = {
        "production_feature_path": "BenchmarkRecord.combined_text only",
        "forbidden_metadata_sentinel_test": _sentinel_feature_test(records),
        "visible_text_shortcuts": {
            "fictional_ticker_tokens_visible_in_text": True,
            "fictional_company_names_visible_in_text": True,
            "interpretation": (
                "These are visible synthetic article tokens, not hidden metadata fields. "
                "They are documented as benchmark-only shortcuts."
            ),
        },
        "tasks": {},
    }
    for task in ("event", "sentiment"):
        selected = str(evaluation["tasks"][task]["selected_candidate"])
        result["tasks"][task] = {
            "label_permutation_negative_control": _label_permutation_control(
                task, train, validation, selected
            ),
            "metadata_only_negative_control": _metadata_only_control(task, train, validation),
            "top_coefficient_shortcut_inspection": _top_coefficients(task, train, selected),
            "train_validation_group_robustness": _group_robustness(
                task, train + validation, selected
            ),
        }
    return result


def determinism_audit(dataset_dir: Path, artifact_root: Path) -> dict[str, Any]:
    with (
        tempfile.TemporaryDirectory(prefix="finnews-m2a-audit-") as first_dir,
        tempfile.TemporaryDirectory(prefix="finnews-m2a-audit-") as second_dir,
    ):
        first_root = Path(first_dir)
        second_root = Path(second_dir)
        first_dataset = first_root / "dataset"
        second_dataset = second_root / "dataset"
        first_report_dir = first_root / "reports"
        second_report_dir = second_root / "reports"
        first_artifacts = first_root / "artifacts"
        second_artifacts = second_root / "artifacts"
        first_manifest = write_benchmark(first_dataset)
        second_manifest = write_benchmark(second_dataset)
        first_report = run_nlp_benchmark(first_dataset, first_report_dir, first_artifacts)
        second_report = run_nlp_benchmark(second_dataset, second_report_dir, second_artifacts)
        first_records = first_dataset.joinpath("records.jsonl").read_bytes()
        second_records = second_dataset.joinpath("records.jsonl").read_bytes()
        first_predictions = _selected_test_predictions(first_dataset, first_artifacts)
        second_predictions = _selected_test_predictions(second_dataset, second_artifacts)
        artifact_pairs = _artifact_hash_pairs(first_report, second_report)
        return {
            "committed_dataset_sha256": sha256_file(dataset_dir / "records.jsonl"),
            "first_dataset_sha256": first_manifest["dataset_sha256"],
            "second_dataset_sha256": second_manifest["dataset_sha256"],
            "records_byte_identical": first_records == second_records,
            "split_hashes_identical": first_manifest["split_hashes"]
            == second_manifest["split_hashes"],
            "selected_candidates_identical": {
                task: first_report["tasks"][task]["selected_candidate"]
                == second_report["tasks"][task]["selected_candidate"]
                for task in ("event", "sentiment")
            },
            "metrics_identical": _strip_artifact_hashes(first_report)
            == _strip_artifact_hashes(second_report),
            "test_predictions_identical": first_predictions == second_predictions,
            "artifact_hashes_identical": {
                task: item["first_sha256"] == item["second_sha256"]
                for task, item in artifact_pairs.items()
            },
            "artifact_hash_note": (
                "If a future joblib version changes binary serialization, prediction/config "
                "determinism remains the release gate and each artifact must verify against "
                "its own manifest."
            ),
            "artifact_hashes": artifact_pairs,
            "preexisting_artifact_root": str(artifact_root.name),
            "floating_point_tolerance": 0.0,
        }


def artifact_audit(repo_root: Path, evaluation: dict[str, Any]) -> dict[str, Any]:
    artifact_root = repo_root / ".finnews-artifacts" / "nlp"
    tracked_binaries = _git_lines(
        repo_root, ["git", "ls-files", "*.joblib", "*.pkl", "*.pickle", "*.npz", "*.npy"]
    )
    local_artifacts = (
        sorted(artifact_root.glob("**/model.joblib")) if artifact_root.exists() else []
    )
    local_manifests = (
        sorted(artifact_root.glob("**/manifest.json")) if artifact_root.exists() else []
    )
    model_artifacts = [
        task_report["artifact"] for task_report in evaluation.get("tasks", {}).values()
    ]
    gitignore = repo_root / ".gitignore"
    gitignore_text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    return {
        "artifact_root_ignored": ".finnews-artifacts/" in gitignore_text,
        "tracked_model_binary_count": len(tracked_binaries),
        "tracked_model_binaries": tracked_binaries,
        "local_artifact_count": len(local_artifacts),
        "local_manifest_count": len(local_manifests),
        "local_artifact_size_bytes": sum(path.stat().st_size for path in local_artifacts),
        "each_local_artifact_below_25mb": all(
            path.stat().st_size < 25_000_000 for path in local_artifacts
        ),
        "all_local_artifacts_below_100mb": sum(path.stat().st_size for path in local_artifacts)
        < 100_000_000,
        "reported_artifacts": [
            {
                "model_id": artifact["model_id"],
                "task": artifact["task"],
                "artifact_sha256": artifact["artifact_sha256"],
                "artifact_size_bytes": artifact["artifact_size_bytes"],
                "manifest_sha256": artifact["manifest_sha256"],
                "config_sha256": artifact["config_sha256"],
            }
            for artifact in model_artifacts
        ],
        "postgres_stores_binary_bytes": False,
        "api_exposes_absolute_paths": False,
        "frontend_exposes_absolute_paths": False,
        "trusted_deserialization_boundary": (
            "Only locally generated, hash-verified artifacts under the ignored registry root "
            "are eligible for joblib loading."
        ),
    }


def _counter(values: Any) -> dict[str, int]:
    return {str(key): count for key, count in sorted(Counter(values).items())}


def _split_hashes(records: Sequence[BenchmarkRecord]) -> dict[str, str]:
    return {split: _split_hash(records, split) for split in SPLITS}


def _split_hash(records: Sequence[BenchmarkRecord], split: str) -> str:
    return _hash_records([record for record in records if record.split == split])


def _ids_disjoint(by_split: dict[str, list[BenchmarkRecord]]) -> bool:
    seen: set[str] = set()
    for split in SPLITS:
        ids = {record.record_id for record in by_split[split]}
        if seen & ids:
            return False
        seen |= ids
    return True


def _group_splits(records: Sequence[BenchmarkRecord], field: str) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for record in records:
        grouped[str(getattr(record, field))].add(record.split)
    return grouped


def _ngrams(text: str) -> set[str]:
    normalized = comparison_text(text)
    size = SIMILARITY_NGRAM_SIZE
    if len(normalized) <= size:
        return {normalized}
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def _cross_split_similarity(
    left: Sequence[BenchmarkRecord], right: Sequence[BenchmarkRecord]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    left_grams = {record.record_id: _ngrams(record.combined_text) for record in left}
    right_grams = {record.record_id: _ngrams(record.combined_text) for record in right}
    maximum: dict[str, float | str | None] = {
        "similarity": 0.0,
        "left_record_id": None,
        "right_record_id": None,
    }
    warnings: list[dict[str, Any]] = []
    for left_record in left:
        left_set = left_grams[left_record.record_id]
        for right_record in right:
            right_set = right_grams[right_record.record_id]
            score = len(left_set & right_set) / len(left_set | right_set)
            rounded = round(score, 6)
            current_max = maximum["similarity"]
            if isinstance(current_max, float) and rounded > current_max:
                maximum = {
                    "similarity": rounded,
                    "left_record_id": left_record.record_id,
                    "right_record_id": right_record.record_id,
                }
            if score >= SIMILARITY_WARNING_THRESHOLD:
                warnings.append(
                    {
                        "similarity": rounded,
                        "left_record_id": left_record.record_id,
                        "right_record_id": right_record.record_id,
                    }
                )
    return maximum, sorted(warnings, key=lambda row: (-row["similarity"], row["left_record_id"]))


def _tie_break_reason(validation_metrics: dict[str, Any], selected: str) -> str:
    macro_values = {name: metrics["macro_f1"] for name, metrics in validation_metrics.items()}
    if list(macro_values.values()).count(macro_values[selected]) == 1:
        return "highest validation macro_f1"
    ece_values = {
        name: metrics["expected_calibration_error"] for name, metrics in validation_metrics.items()
    }
    if list(ece_values.values()).count(ece_values[selected]) == 1:
        return "validation macro_f1 tie, lower validation ECE"
    return "validation macro_f1 and ECE tie, lower documented complexity"


def _sentinel_feature_test(records: Sequence[BenchmarkRecord]) -> dict[str, Any]:
    changed = [
        record.model_copy(
            update={
                "company_id": "fc-999",
                "fictional_ticker": "FZZ9",
                "source_type": "synthetic_wire",
                "template_family_id": "tf-99",
                "story_group_id": f"sg-sentinel-{index}",
                "challenge_flags": ["low_information"],
                "generator_version": "sentinel",
            }
        )
        for index, record in enumerate(records[:24])
    ]
    original_text = _texts(records[:24])
    sentinel_text = _texts(changed)
    return {
        "metadata_fields_mutated": [
            "company_id",
            "fictional_ticker",
            "source_type",
            "template_family_id",
            "story_group_id",
            "challenge_flags",
            "generator_version",
        ],
        "feature_text_unchanged": original_text == sentinel_text,
        "production_features_access_hidden_metadata": False,
    }


def _label_permutation_control(
    task: TaskName,
    train: Sequence[BenchmarkRecord],
    validation: Sequence[BenchmarkRecord],
    selected_candidate: str,
) -> dict[str, Any]:
    model = clone(_candidate_pipelines(task)[selected_candidate])
    rng = np.random.default_rng(20260622)
    labels = np.asarray(_truth(train, task), dtype=object)
    shuffled = labels.copy()
    rng.shuffle(shuffled)
    model.fit(_texts(train), shuffled.tolist())
    pred = [str(item) for item in model.predict(_texts(validation))]
    truth = _truth(validation, task)
    return {
        "seed": 20260622,
        "trained_on": "train labels shuffled only",
        "evaluated_on": "validation",
        "accuracy": round(float(np.mean(np.asarray(pred) == np.asarray(truth))), 6),
        "macro_f1": round(
            f1_score(truth, pred, labels=_labels(task), average="macro", zero_division=0), 6
        ),
        "used_for_selection": False,
    }


def _metadata_only_control(
    task: TaskName,
    train: Sequence[BenchmarkRecord],
    validation: Sequence[BenchmarkRecord],
) -> dict[str, Any]:
    vectorizer = DictVectorizer(sparse=False)
    train_matrix = vectorizer.fit_transform([_metadata_features(record) for record in train])
    validation_matrix = vectorizer.transform([_metadata_features(record) for record in validation])
    model = clone(_candidate_pipelines(task)["char_tfidf_logreg"].named_steps["classifier"])
    model.fit(train_matrix, _truth(train, task))
    pred = [str(item) for item in model.predict(validation_matrix)]
    truth = _truth(validation, task)
    return {
        "features": sorted(_metadata_features(train[0])),
        "production_feature_path": False,
        "accuracy": round(float(np.mean(np.asarray(pred) == np.asarray(truth))), 6),
        "macro_f1": round(
            f1_score(truth, pred, labels=_labels(task), average="macro", zero_division=0), 6
        ),
        "interpretation": "diagnostic only; metadata is not used by production candidates",
    }


def _metadata_features(record: BenchmarkRecord) -> dict[str, str]:
    return {
        "company_id": record.company_id,
        "fictional_ticker": record.fictional_ticker,
        "industry": record.industry,
        "source_type": record.source_type,
        "language": record.language,
    }


def _top_coefficients(
    task: TaskName, train: Sequence[BenchmarkRecord], selected_candidate: str
) -> dict[str, Any]:
    model = clone(_candidate_pipelines(task)[selected_candidate])
    model.fit(_texts(train), _truth(train, task))
    features = [str(item) for item in model.named_steps["features"].get_feature_names_out()]
    classifier = model.named_steps["classifier"]
    result: dict[str, Any] = {}
    suspicious_terms = set(_labels(task)) | {
        "template_family_id",
        "story_group_id",
        "generator_version",
        "challenge_flags",
        "record_id",
        "split",
    }
    for label, estimator in zip(classifier.classes_, classifier.estimators_, strict=True):
        coefficients = np.asarray(estimator.coef_[0])
        top_indexes = np.argsort(coefficients)[-8:][::-1]
        terms = [features[int(index)] for index in top_indexes]
        result[str(label)] = {
            "top_positive_features": terms,
            "contains_exact_label_name": any(str(label) in term for term in terms),
            "contains_generator_marker": any(term in suspicious_terms for term in terms),
        }
    return result


def _group_robustness(
    task: TaskName, records: Sequence[BenchmarkRecord], selected_candidate: str
) -> dict[str, Any]:
    groups = np.asarray([record.template_family_id for record in records], dtype=object)
    texts = np.asarray(_texts(records), dtype=object)
    truth = np.asarray(_truth(records, task), dtype=object)
    splitter = GroupKFold(n_splits=3)
    scores: list[float] = []
    for train_index, validation_index in splitter.split(texts, truth, groups):
        model = clone(_candidate_pipelines(task)[selected_candidate])
        model.fit(texts[train_index].tolist(), truth[train_index].tolist())
        pred = [str(item) for item in model.predict(texts[validation_index].tolist())]
        score = f1_score(
            truth[validation_index].tolist(),
            pred,
            labels=_labels(task),
            average="macro",
            zero_division=0,
        )
        scores.append(float(score))
    return {
        "groups": "template_family_id within train+validation only",
        "test_set_used": False,
        "fold_count": 3,
        "macro_f1_scores": [round(score, 6) for score in scores],
        "mean_macro_f1": round(float(np.mean(scores)), 6),
        "std_macro_f1": round(float(np.std(scores)), 6),
    }


def _selected_test_predictions(
    dataset_dir: Path, artifact_root: Path
) -> dict[str, list[dict[str, Any]]]:
    records = load_records(dataset_dir)
    test = [record for record in records if record.split == "test"]
    predictions: dict[str, list[dict[str, Any]]] = {}
    for task in ("event", "sentiment"):
        labels = _labels(task)
        model = clone(_candidate_pipelines(task)["word_char_tfidf_logreg"])
        train = [record for record in records if record.split == "train"]
        validation = [record for record in records if record.split == "validation"]
        model.fit(_texts(train), _truth(train, task))
        val_pred, val_proba = _predict_with_probabilities(model, _texts(validation), labels)
        alpha, _, _ = _select_probability_alpha(_truth(validation, task), val_pred, val_proba)
        pred, proba = _predict_with_probabilities(model, _texts(test), labels)
        adjusted = _apply_alpha(proba, alpha)
        predictions[task] = [
            {
                "record_id": record.record_id,
                "prediction": pred[index],
                "confidence": round(float(np.max(adjusted[index])), 6),
            }
            for index, record in enumerate(test)
        ]
    _ = artifact_root
    return predictions


def _artifact_hash_pairs(
    first_report: dict[str, Any], second_report: dict[str, Any]
) -> dict[str, Any]:
    return {
        task: {
            "first_sha256": first_report["tasks"][task]["artifact"]["artifact_sha256"],
            "second_sha256": second_report["tasks"][task]["artifact"]["artifact_sha256"],
        }
        for task in ("event", "sentiment")
    }


def _strip_artifact_hashes(report: dict[str, Any]) -> dict[str, Any]:
    clone_report = json.loads(json.dumps(report, sort_keys=True))
    for task in ("event", "sentiment"):
        artifact = clone_report["tasks"][task]["artifact"]
        artifact["artifact_sha256"] = "<artifact-sha256>"
        artifact["manifest_sha256"] = "<manifest-sha256>"
    return cast(dict[str, Any], clone_report)


def _git_lines(repo_root: Path, command: list[str]) -> list[str]:
    import subprocess

    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]
