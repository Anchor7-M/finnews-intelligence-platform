from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from finnews.application.services.nlp_artifacts import ArtifactError, load_trusted_artifact
from finnews.application.services.nlp_evaluation import run_nlp_benchmark
from finnews.application.services.nlp_metrics import (
    classification_report_dict,
    confidence_coverage,
    expected_calibration_error,
    multiclass_brier_score,
)
from finnews.infrastructure.nlp.benchmark.generator import write_benchmark


def test_metric_math_for_probabilities_and_coverage() -> None:
    labels = ["a", "b"]
    y_true = ["a", "b", "a", "b"]
    y_pred = ["a", "b", "b", "b"]
    probabilities = np.asarray(
        [
            [0.8, 0.2],
            [0.1, 0.9],
            [0.4, 0.6],
            [0.3, 0.7],
        ]
    )

    report = classification_report_dict(y_true, y_pred, labels, probabilities=probabilities)
    assert report["record_count"] == 4
    assert report["accuracy"] == 0.75
    assert report["macro_f1"] == 0.733333
    assert multiclass_brier_score(y_true, probabilities, labels) == pytest.approx(0.25)
    assert expected_calibration_error(y_true, y_pred, probabilities) == pytest.approx(0.3)
    coverage = confidence_coverage(y_true, y_pred, probabilities, labels)
    assert coverage[1]["threshold"] == 0.6
    assert coverage[1]["covered_count"] == 4
    empty_coverage = confidence_coverage(y_true, y_pred, probabilities, labels, thresholds=[0.95])
    assert empty_coverage == [
        {
            "threshold": 0.95,
            "coverage": 0.0,
            "covered_count": 0,
            "abstained_count": 4,
            "covered_accuracy": None,
            "covered_macro_f1": None,
        }
    ]


def test_nlp_benchmark_report_artifacts_and_tamper_detection(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    report_dir = tmp_path / "reports"
    artifact_root = tmp_path / "artifacts"
    manifest = write_benchmark(dataset_dir)

    first = run_nlp_benchmark(dataset_dir, report_dir, artifact_root, task="all")
    second = run_nlp_benchmark(dataset_dir, report_dir, artifact_root, task="all")

    assert first["dataset"]["dataset_sha256"] == manifest["dataset_sha256"]
    assert first["tasks"]["event"]["selected_candidate"] == "word_char_tfidf_logreg"
    assert first["tasks"]["sentiment"]["selected_candidate"] == "word_char_tfidf_logreg"
    assert (
        first["tasks"]["event"]["test_metrics"]["selected_ml"]["macro_f1"]
        == second["tasks"]["event"]["test_metrics"]["selected_ml"]["macro_f1"]
    )
    assert (
        first["tasks"]["sentiment"]["test_metrics"]["selected_ml"]["macro_f1"]
        == second["tasks"]["sentiment"]["test_metrics"]["selected_ml"]["macro_f1"]
    )
    event_manifest = (
        artifact_root / "event" / first["tasks"]["event"]["selected_model_id"] / "manifest.json"
    )
    loaded = load_trusted_artifact(artifact_root, event_manifest, task="event")
    assert isinstance(loaded, dict)
    assert loaded["task"] == "event"

    artifact_path = (
        artifact_root / "event" / first["tasks"]["event"]["selected_model_id"] / "model.joblib"
    )
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tamper")
    with pytest.raises(ArtifactError, match="hash mismatch"):
        load_trusted_artifact(artifact_root, event_manifest, task="event")
