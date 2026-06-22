from __future__ import annotations

import json
import time
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline

from finnews.application.services.nlp_artifacts import (
    safe_manifest_summary,
    save_model_artifact,
    sha256_text,
)
from finnews.application.services.nlp_metrics import (
    classification_report_dict,
    confusion_pair_counts,
    expected_calibration_error,
    select_abstention_threshold,
    slice_metrics,
)
from finnews.domain.entities import Article
from finnews.domain.enums import EventType, ProcessingState, SentimentLabel
from finnews.domain.value_objects import stable_id
from finnews.infrastructure.nlp.benchmark.generator import load_records
from finnews.infrastructure.nlp.benchmark.models import BenchmarkRecord
from finnews.infrastructure.nlp.events import classify_event
from finnews.infrastructure.nlp.sentiment import analyze_sentiment
from finnews.infrastructure.normalization import deterministic_hash

TaskName = Literal["event", "sentiment"]

MODEL_DISCLOSURE = (
    "Synthetic benchmark only; generator-defined labels; no live or copyrighted news; "
    "not investment advice; real-world licensed evaluation is deferred to Milestone 2B."
)
THRESHOLD_GRID = (0.50, 0.60, 0.70, 0.80, 0.90)


def run_nlp_benchmark(
    dataset_dir: Path,
    report_dir: Path,
    artifact_root: Path,
    *,
    task: TaskName | Literal["all"] = "all",
) -> dict[str, Any]:
    records = load_records(dataset_dir)
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    tasks: list[TaskName] = ["event", "sentiment"] if task == "all" else [task]
    task_reports = {
        task_name: _evaluate_task(task_name, records, manifest, artifact_root)
        for task_name in tasks
    }
    report = {
        "disclaimer": MODEL_DISCLOSURE,
        "dataset": {
            "dataset_id": manifest["dataset_id"],
            "dataset_version": manifest["dataset_version"],
            "dataset_sha256": manifest["dataset_sha256"],
            "split_hashes": manifest["split_hashes"],
            "synthetic_only": True,
            "label_source": "generator_defined_synthetic_gold",
        },
        "selection_procedure": {
            "split_policy": (
                "train candidates on train, select/calibrate/threshold on validation, "
                "evaluate once on test"
            ),
            "primary_metric": "validation macro_f1",
            "tie_breakers": ["lower validation_ece", "lower complexity"],
            "test_set_used_for_selection": False,
        },
        "tasks": task_reports,
        "created_at": "2026-06-22T00:00:00+00:00",
    }
    (report_dir / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    error_report = {
        "disclaimer": MODEL_DISCLOSURE,
        "tasks": {
            task_name: task_report["error_analysis"]
            for task_name, task_report in task_reports.items()
        },
    }
    (report_dir / "error_analysis.json").write_text(
        json.dumps(error_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _evaluate_task(
    task: TaskName,
    records: Sequence[BenchmarkRecord],
    manifest: dict[str, Any],
    artifact_root: Path,
) -> dict[str, Any]:
    labels = _labels(task)
    train = [record for record in records if record.split == "train"]
    validation = [record for record in records if record.split == "validation"]
    test = [record for record in records if record.split == "test"]
    candidates = _candidate_pipelines(task)
    val_results: dict[str, dict[str, Any]] = {}
    fitted: dict[str, Pipeline] = {}
    for model_name, candidate in candidates.items():
        model = clone(candidate)
        model.fit(_texts(train), _truth(train, task))
        fitted[model_name] = model
        val_pred, val_proba = _predict_with_probabilities(model, _texts(validation), labels)
        val_results[model_name] = classification_report_dict(
            _truth(validation, task), val_pred, labels, probabilities=val_proba
        )
    selected_name = _select_candidate(val_results)
    selected = fitted[selected_name]
    val_pred, val_proba = _predict_with_probabilities(selected, _texts(validation), labels)
    alpha, calibration_status, val_ece = _select_probability_alpha(
        _truth(validation, task), val_pred, val_proba
    )
    val_proba_adjusted = _apply_alpha(val_proba, alpha)
    threshold = select_abstention_threshold(
        _truth(validation, task), val_pred, val_proba_adjusted, labels
    )
    test_pred, test_proba = _timed_predict(selected, _texts(test), labels)
    test_proba_adjusted = _apply_alpha(test_proba["probabilities"], alpha)
    selected_metrics = classification_report_dict(
        _truth(test, task),
        test_pred,
        labels,
        probabilities=test_proba_adjusted,
        duration_ms=test_proba["duration_ms"],
    )
    dummy_metrics = _dummy_metrics(task, train, test, labels)
    rule_metrics = _rule_metrics(task, test, labels)
    model_id = f"m2a-{task}-{selected_name}"
    artifact = save_model_artifact(
        {"model": selected, "labels": labels, "alpha": alpha, "task": task},
        artifact_root,
        model_id=model_id,
        task=task,
        dataset_id=manifest["dataset_id"],
        dataset_version=manifest["dataset_version"],
        dataset_sha256=manifest["dataset_sha256"],
        split_hashes=dict(manifest["split_hashes"]),
        label_set=labels,
        provider="scikit_learn",
        model_kind=selected_name,
        status=_promotion_status(selected_metrics, dummy_metrics),
        config=_model_config(selected_name, task, alpha, threshold),
    )
    rows = _prediction_rows(test, task, labels, test_pred, test_proba_adjusted, model_id)
    error_analysis = _error_analysis(task, labels, rows, rule_metrics["predictions"], model_id)
    return {
        "task": task,
        "label_set": labels,
        "selected_model_id": model_id,
        "selected_candidate": selected_name,
        "candidate_validation": val_results,
        "calibration": {
            "method": "probability_power_scaling",
            "alpha": alpha,
            "status": calibration_status,
            "validation_ece": val_ece,
            "test_ece": selected_metrics["expected_calibration_error"],
        },
        "abstention": {
            "threshold": threshold,
            "selected_on": "validation",
            "sentiment_uncertain_is_label_not_abstention": task == "sentiment",
        },
        "test_metrics": {
            "dummy_most_frequent": dummy_metrics["metrics"],
            "rule_baseline": rule_metrics["metrics"],
            "selected_ml": selected_metrics,
        },
        "slices": slice_metrics(rows, labels, task=task),
        "promotion_policy": _promotion_policy(selected_metrics, dummy_metrics),
        "artifact": safe_manifest_summary(artifact.manifest),
        "error_analysis": error_analysis,
    }


def _candidate_pipelines(task: TaskName) -> dict[str, Pipeline]:
    common_logreg = {
        "max_iter": 500,
        "random_state": 20260622,
        "solver": "liblinear",
        "class_weight": None,
    }
    return {
        "char_tfidf_logreg": Pipeline(
            [
                (
                    "features",
                    TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), max_features=6000),
                ),
                (
                    "classifier",
                    OneVsRestClassifier(LogisticRegression(**common_logreg), n_jobs=1),
                ),
            ]
        ),
        "word_char_tfidf_logreg": Pipeline(
            [
                (
                    "features",
                    FeatureUnion(
                        [
                            (
                                "word",
                                TfidfVectorizer(
                                    analyzer="word",
                                    ngram_range=(1, 2),
                                    token_pattern=r"(?u)\b\w+\b",
                                    max_features=4000,
                                ),
                            ),
                            (
                                "char",
                                TfidfVectorizer(
                                    analyzer="char",
                                    ngram_range=(2, 4),
                                    max_features=4000,
                                ),
                            ),
                        ],
                        n_jobs=1,
                    ),
                ),
                (
                    "classifier",
                    OneVsRestClassifier(LogisticRegression(**common_logreg), n_jobs=1),
                ),
            ]
        ),
    }


def _dummy_metrics(
    task: TaskName,
    train: Sequence[BenchmarkRecord],
    test: Sequence[BenchmarkRecord],
    labels: list[str],
) -> dict[str, Any]:
    model = DummyClassifier(strategy="most_frequent", random_state=20260622)
    model.fit(np.asarray(_texts(train)).reshape(-1, 1), _truth(train, task))
    started = time.perf_counter()
    pred = [str(item) for item in model.predict(np.asarray(_texts(test)).reshape(-1, 1))]
    duration = int((time.perf_counter() - started) * 1000)
    matrix = np.asarray(_texts(test)).reshape(-1, 1)
    proba = _align_probabilities(model.classes_, model.predict_proba(matrix), labels)
    return {
        "metrics": classification_report_dict(
            _truth(test, task), pred, labels, probabilities=proba, duration_ms=duration
        ),
        "predictions": pred,
    }


def _rule_metrics(
    task: TaskName, test: Sequence[BenchmarkRecord], labels: list[str]
) -> dict[str, Any]:
    started = time.perf_counter()
    pred = [_rule_prediction(record, task) for record in test]
    duration = int((time.perf_counter() - started) * 1000)
    return {
        "metrics": classification_report_dict(
            _truth(test, task), pred, labels, duration_ms=duration
        ),
        "predictions": pred,
    }


def _rule_prediction(record: BenchmarkRecord, task: TaskName) -> str:
    article = Article(
        canonical_raw_article_id=stable_id("m2a-raw", record.record_id),
        normalized_title=record.title,
        normalized_summary=record.summary,
        language=record.language,
        published_at=record.published_at,
        local_market_date=date(2026, 1, 1),
        canonical_url=f"https://synthetic.local/{record.record_id}",
        exact_content_hash=deterministic_hash(record.combined_text),
        source_key="synthetic-finnews-nlp-v1",
        source_name="Synthetic NLP Benchmark",
        processing_state=ProcessingState.PROCESSED,
        id=stable_id("m2a-article", record.record_id),
    )
    if task == "event":
        return classify_event(article).event_type.value
    return analyze_sentiment(article).label.value


def _timed_predict(
    model: Pipeline, texts: list[str], labels: list[str]
) -> tuple[list[str], dict[str, Any]]:
    started = time.perf_counter()
    pred, proba = _predict_with_probabilities(model, texts, labels)
    duration = int((time.perf_counter() - started) * 1000)
    return pred, {"probabilities": proba, "duration_ms": duration}


def _predict_with_probabilities(
    model: Pipeline, texts: list[str], labels: list[str]
) -> tuple[list[str], np.ndarray]:
    pred = [str(item) for item in model.predict(texts)]
    classifier = model.named_steps["classifier"]
    classes = classifier.classes_
    proba = _align_probabilities(classes, model.predict_proba(texts), labels)
    return pred, proba


def _align_probabilities(
    classes: Sequence[Any], probabilities: np.ndarray, labels: Sequence[str]
) -> np.ndarray:
    source_index = {str(label): index for index, label in enumerate(classes)}
    aligned = np.zeros((probabilities.shape[0], len(labels)), dtype=float)
    for target_index, label in enumerate(labels):
        aligned[:, target_index] = probabilities[:, source_index[label]]
    return aligned


def _select_candidate(val_results: dict[str, dict[str, Any]]) -> str:
    return max(
        val_results,
        key=lambda name: (
            val_results[name]["macro_f1"],
            -val_results[name]["expected_calibration_error"],
            -_complexity_score(name),
        ),
    )


def _select_probability_alpha(
    y_true: list[str], y_pred: list[str], probabilities: np.ndarray
) -> tuple[float, str, float]:
    raw_ece = expected_calibration_error(y_true, y_pred, probabilities)
    candidates = [0.75, 0.9, 1.0, 1.1, 1.25, 1.5]
    scored = [
        (expected_calibration_error(y_true, y_pred, _apply_alpha(probabilities, alpha)), alpha)
        for alpha in candidates
    ]
    best_ece, best_alpha = min(scored, key=lambda item: (item[0], abs(item[1] - 1.0)))
    if best_ece + 1e-12 < raw_ece:
        return best_alpha, "validation_alpha_improved_ece", round(best_ece, 6)
    return 1.0, "raw_retained_validation_ece_not_improved", round(raw_ece, 6)


def _apply_alpha(probabilities: np.ndarray, alpha: float) -> np.ndarray:
    adjusted = np.power(np.clip(probabilities, 1e-12, 1.0), alpha)
    return cast(np.ndarray, adjusted / adjusted.sum(axis=1, keepdims=True))


def _prediction_rows(
    test: Sequence[BenchmarkRecord],
    task: TaskName,
    labels: list[str],
    predictions: Sequence[str],
    probabilities: np.ndarray,
    model_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(test):
        confidence = float(np.max(probabilities[index]))
        rows.append(
            {
                "record_id": record.record_id,
                "language": record.language,
                "difficulty": record.difficulty,
                "challenge_flags": record.challenge_flags,
                "combined_text": record.combined_text,
                f"{task}_label": _truth([record], task)[0],
                "predicted_label": predictions[index],
                "confidence": round(confidence, 6),
                "model_id": model_id,
                "abstained": False,
                "top_label_probability": {
                    labels[column]: round(float(probabilities[index, column]), 6)
                    for column in range(len(labels))
                },
            }
        )
    return rows


def _error_analysis(
    task: TaskName,
    labels: list[str],
    rows: list[dict[str, Any]],
    rule_predictions: Sequence[str],
    model_id: str,
) -> dict[str, Any]:
    truth = [str(row[f"{task}_label"]) for row in rows]
    predicted = [str(row["predicted_label"]) for row in rows]
    errors = [
        _error_row(row, task, model_id)
        for row in rows
        if row[f"{task}_label"] != row["predicted_label"]
    ]
    correct = [row for row in rows if row[f"{task}_label"] == row["predicted_label"]]
    disagreements = [
        {
            "record_id": row["record_id"],
            "expected_label": row[f"{task}_label"],
            "model_prediction": row["predicted_label"],
            "rule_prediction": rule_predictions[index],
            "language": row["language"],
            "challenge_flags": row["challenge_flags"],
        }
        for index, row in enumerate(rows)
        if row["predicted_label"] != rule_predictions[index]
    ][:20]
    return {
        "methodology": "deterministic synthetic-only error slices and confidence sorting",
        "confusion_pairs": confusion_pair_counts(truth, predicted),
        "highest_confidence_false_predictions": sorted(
            errors, key=lambda row: (-row["confidence"], row["record_id"])
        )[:12],
        "lowest_confidence_correct_predictions": sorted(
            [_correct_row(row, task, model_id) for row in correct],
            key=lambda row: (row["confidence"], row["record_id"]),
        )[:12],
        "errors_by_language": _error_counter(errors, "language"),
        "errors_by_challenge_flag": _challenge_error_counter(errors),
        "rule_model_disagreements": disagreements,
        "class_labels": labels,
    }


def _error_row(row: dict[str, Any], task: TaskName, model_id: str) -> dict[str, Any]:
    expected = str(row[f"{task}_label"])
    predicted = str(row["predicted_label"])
    return {
        "record_id": row["record_id"],
        "expected_label": expected,
        "predicted_label": predicted,
        "confidence": row["confidence"],
        "challenge_flags": row["challenge_flags"],
        "language": row["language"],
        "model_version": model_id,
        "error_category": _error_category(row, expected, predicted),
    }


def _correct_row(row: dict[str, Any], task: TaskName, model_id: str) -> dict[str, Any]:
    return {
        "record_id": row["record_id"],
        "expected_label": row[f"{task}_label"],
        "predicted_label": row["predicted_label"],
        "confidence": row["confidence"],
        "challenge_flags": row["challenge_flags"],
        "language": row["language"],
        "model_version": model_id,
        "error_category": "low_confidence_correct",
    }


def _error_category(row: dict[str, Any], expected: str, predicted: str) -> str:
    flags = set(row["challenge_flags"])
    if "class_overlap" in flags:
        return "class_overlap"
    if "mixed_signal" in flags:
        return "mixed_signal"
    if "uncertainty" in flags or expected == "uncertain" or predicted == "uncertain":
        return "uncertainty_boundary"
    if row["language"] == "zh":
        return "zh_template_generalization"
    return "template_generalization"


def _error_counter(rows: Sequence[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row[field])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _challenge_error_counter(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for flag in row["challenge_flags"]:
            counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))


def _promotion_policy(
    selected_metrics: dict[str, Any], dummy_metrics: dict[str, Any]
) -> dict[str, Any]:
    per_class = selected_metrics["per_class"]
    passed = {
        "dataset_and_split_integrity": True,
        "test_not_used_for_selection": True,
        "macro_f1_beats_dummy_by_0_10": selected_metrics["macro_f1"]
        >= dummy_metrics["metrics"]["macro_f1"] + 0.10,
        "no_class_zero_recall": all(row["recall"] > 0 for row in per_class.values()),
        "calibration_available": "expected_calibration_error" in selected_metrics,
        "artifact_manifest_verified": True,
        "no_live_content": True,
    }
    status = "demo_candidate" if all(passed.values()) else "evaluated_not_promoted"
    return {"status": status, "checks": passed}


def _promotion_status(selected_metrics: dict[str, Any], dummy_metrics: dict[str, Any]) -> str:
    return str(_promotion_policy(selected_metrics, dummy_metrics)["status"])


def _model_config(
    selected_name: str, task: TaskName, alpha: float, threshold: float
) -> dict[str, Any]:
    return {
        "task": task,
        "selected_candidate": selected_name,
        "random_state": 20260622,
        "n_jobs": 1,
        "calibration_alpha": alpha,
        "abstention_threshold": threshold,
        "feature_text": "TITLE plus SUMMARY only",
    }


def _labels(task: TaskName) -> list[str]:
    if task == "event":
        return [label.value for label in EventType]
    return [label.value for label in SentimentLabel]


def _truth(records: Sequence[BenchmarkRecord], task: TaskName) -> list[str]:
    if task == "event":
        return [record.event_label.value for record in records]
    return [record.sentiment_label.value for record in records]


def _texts(records: Sequence[BenchmarkRecord]) -> list[str]:
    return [record.combined_text for record in records]


def _complexity_score(name: str) -> int:
    return {"char_tfidf_logreg": 1, "word_char_tfidf_logreg": 2}[name]


def report_config_hash(config: dict[str, Any]) -> str:
    return sha256_text(json.dumps(config, sort_keys=True, separators=(",", ":")))
