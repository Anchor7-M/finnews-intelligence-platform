from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

CONFIDENCE_THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.90)


def classification_report_dict(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
    *,
    probabilities: Any | None = None,
    duration_ms: int = 0,
) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(labels), zero_division=0
    )
    report: dict[str, Any] = {
        "record_count": len(y_true),
        "accuracy": _round(accuracy_score(y_true, y_pred)),
        "macro_precision": _round(float(np.mean(precision))),
        "macro_recall": _round(float(np.mean(recall))),
        "macro_f1": _round(f1_score(y_true, y_pred, labels=list(labels), average="macro")),
        "weighted_f1": _round(
            f1_score(y_true, y_pred, labels=list(labels), average="weighted", zero_division=0)
        ),
        "per_class": {
            label: {
                "precision": _round(float(precision[index])),
                "recall": _round(float(recall[index])),
                "f1": _round(float(f1[index])),
                "support": int(support[index]),
            }
            for index, label in enumerate(labels)
        },
        "confusion_matrix": {
            "labels": list(labels),
            "matrix": confusion_matrix(y_true, y_pred, labels=list(labels)).tolist(),
        },
        "inference_duration_ms": duration_ms,
    }
    if probabilities is not None:
        probability_array = np.asarray(probabilities, dtype=float)
        log_loss_labels, log_loss_probabilities = _lexicographic_probabilities(
            labels, probability_array
        )
        report["log_loss"] = _round(
            log_loss(y_true, log_loss_probabilities, labels=log_loss_labels)
        )
        report["brier_score"] = _round(multiclass_brier_score(y_true, probability_array, labels))
        report["expected_calibration_error"] = _round(
            expected_calibration_error(y_true, y_pred, probability_array)
        )
        report["reliability_bins"] = reliability_bins(y_true, y_pred, probability_array)
        report["confidence_coverage"] = confidence_coverage(
            y_true, y_pred, probability_array, labels
        )
    return report


def multiclass_brier_score(
    y_true: Sequence[str], probabilities: np.ndarray, labels: Sequence[str]
) -> float:
    label_index = {label: index for index, label in enumerate(labels)}
    one_hot = np.zeros_like(probabilities)
    for row, label in enumerate(y_true):
        one_hot[row, label_index[label]] = 1.0
    return float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1)))


def expected_calibration_error(
    y_true: Sequence[str], y_pred: Sequence[str], probabilities: np.ndarray, bins: int = 10
) -> float:
    confidences = probabilities.max(axis=1)
    correct = np.asarray([truth == pred for truth, pred in zip(y_true, y_pred, strict=True)])
    total = len(y_true)
    ece = 0.0
    for lower, upper in _bin_edges(bins):
        if upper == 1.0:
            mask = (confidences >= lower) & (confidences <= upper)
        else:
            mask = (confidences >= lower) & (confidences < upper)
        if not np.any(mask):
            continue
        accuracy = float(np.mean(correct[mask]))
        confidence = float(np.mean(confidences[mask]))
        ece += float(np.sum(mask)) / total * abs(accuracy - confidence)
    return ece


def reliability_bins(
    y_true: Sequence[str], y_pred: Sequence[str], probabilities: np.ndarray, bins: int = 10
) -> list[dict[str, Any]]:
    confidences = probabilities.max(axis=1)
    correct = np.asarray([truth == pred for truth, pred in zip(y_true, y_pred, strict=True)])
    rows: list[dict[str, Any]] = []
    for index, (lower, upper) in enumerate(_bin_edges(bins)):
        if upper == 1.0:
            mask = (confidences >= lower) & (confidences <= upper)
        else:
            mask = (confidences >= lower) & (confidences < upper)
        count = int(np.sum(mask))
        rows.append(
            {
                "bin": index,
                "lower": _round(lower),
                "upper": _round(upper),
                "count": count,
                "accuracy": _round(float(np.mean(correct[mask]))) if count else None,
                "mean_confidence": _round(float(np.mean(confidences[mask]))) if count else None,
            }
        )
    return rows


def confidence_coverage(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    probabilities: np.ndarray,
    labels: Sequence[str],
    thresholds: Sequence[float] = CONFIDENCE_THRESHOLDS,
) -> list[dict[str, Any]]:
    confidences = probabilities.max(axis=1)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        mask = confidences >= threshold
        covered = int(np.sum(mask))
        if covered:
            covered_true = [label for label, keep in zip(y_true, mask, strict=True) if keep]
            covered_pred = [label for label, keep in zip(y_pred, mask, strict=True) if keep]
            accuracy = accuracy_score(covered_true, covered_pred)
            macro_f1 = f1_score(
                covered_true, covered_pred, labels=list(labels), average="macro", zero_division=0
            )
        else:
            accuracy = None
            macro_f1 = None
        rows.append(
            {
                "threshold": _round(threshold),
                "coverage": _round(covered / len(y_true)),
                "covered_count": covered,
                "abstained_count": len(y_true) - covered,
                "covered_accuracy": _round(float(accuracy)) if accuracy is not None else None,
                "covered_macro_f1": _round(float(macro_f1)) if macro_f1 is not None else None,
            }
        )
    return rows


def select_abstention_threshold(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    probabilities: np.ndarray,
    labels: Sequence[str],
) -> float:
    rows = confidence_coverage(y_true, y_pred, probabilities, labels)
    candidates = [
        row for row in rows if row["coverage"] >= 0.5 and row["covered_macro_f1"] is not None
    ]
    if not candidates:
        return 0.5
    selected = max(candidates, key=lambda row: (row["covered_macro_f1"], row["coverage"]))
    return float(selected["threshold"])


def slice_metrics(
    records: Sequence[dict[str, Any]],
    labels: Sequence[str],
    *,
    task: str,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "language": _slice_group(records, labels, task, "language"),
        "difficulty": _slice_group(records, labels, task, "difficulty"),
        "challenge_flag": _challenge_slices(records, labels, task),
        "text_length": _length_slices(records, labels, task),
    }


def _slice_group(
    records: Sequence[dict[str, Any]], labels: Sequence[str], task: str, field: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value in sorted({str(record[field]) for record in records}):
        selected = [record for record in records if record[field] == value]
        rows.append(_slice_row(value, selected, labels, task))
    return rows


def _challenge_slices(
    records: Sequence[dict[str, Any]], labels: Sequence[str], task: str
) -> list[dict[str, Any]]:
    flags = sorted({flag for record in records for flag in record["challenge_flags"]})
    return [
        _slice_row(
            flag,
            [record for record in records if flag in record["challenge_flags"]],
            labels,
            task,
        )
        for flag in flags
    ]


def _length_slices(
    records: Sequence[dict[str, Any]], labels: Sequence[str], task: str
) -> list[dict[str, Any]]:
    lengths = [len(str(record["combined_text"])) for record in records]
    median = sorted(lengths)[len(lengths) // 2]
    return [
        _slice_row(
            "short_or_equal_median",
            [record for record in records if len(str(record["combined_text"])) <= median],
            labels,
            task,
        ),
        _slice_row(
            "long_above_median",
            [record for record in records if len(str(record["combined_text"])) > median],
            labels,
            task,
        ),
    ]


def _slice_row(
    name: str, records: Sequence[dict[str, Any]], labels: Sequence[str], task: str
) -> dict[str, Any]:
    truth_key = f"{task}_label"
    if not records:
        return {"name": name, "record_count": 0}
    y_true = [str(record[truth_key]) for record in records]
    y_pred = [str(record["predicted_label"]) for record in records]
    return {
        "name": name,
        "record_count": len(records),
        "accuracy": _round(accuracy_score(y_true, y_pred)),
        "macro_f1": _round(
            f1_score(y_true, y_pred, labels=list(labels), average="macro", zero_division=0)
        ),
    }


def confusion_pair_counts(y_true: Sequence[str], y_pred: Sequence[str]) -> list[dict[str, Any]]:
    counter = Counter(
        (truth, pred) for truth, pred in zip(y_true, y_pred, strict=True) if truth != pred
    )
    return [
        {"expected": expected, "predicted": predicted, "count": count}
        for (expected, predicted), count in sorted(
            counter.items(), key=lambda item: (-item[1], item[0])
        )
    ]


def _bin_edges(bins: int) -> list[tuple[float, float]]:
    return [(index / bins, (index + 1) / bins) for index in range(bins)]


def _lexicographic_probabilities(
    labels: Sequence[str], probabilities: np.ndarray
) -> tuple[list[str], np.ndarray]:
    sorted_labels = sorted(labels)
    source_index = {label: index for index, label in enumerate(labels)}
    order = [source_index[label] for label in sorted_labels]
    return sorted_labels, probabilities[:, order]


def _round(value: float) -> float:
    return round(float(value), 6)
