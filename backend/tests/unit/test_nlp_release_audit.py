from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from finnews.application.services.nlp_artifacts import ArtifactError, load_trusted_artifact
from finnews.application.services.nlp_evaluation import run_nlp_benchmark
from finnews.application.services.nlp_release_audit import write_release_audit_reports
from finnews.infrastructure.nlp.benchmark.generator import write_benchmark


def test_release_audit_reports_ledger_leakage_and_controls(tmp_path: Path) -> None:
    repo_root = tmp_path
    dataset_dir = repo_root / "data" / "evaluation" / "synthetic-finnews-nlp-v1"
    report_dir = repo_root / "reports" / "nlp" / "synthetic-finnews-nlp-v1"
    artifact_root = repo_root / ".finnews-artifacts" / "nlp"
    write_benchmark(dataset_dir)
    run_nlp_benchmark(dataset_dir, report_dir, artifact_root, task="all")
    result = write_release_audit_reports(repo_root)

    assert result["status"] == "completed"
    ledger = _read(report_dir / "benchmark-ledger.json")
    assert ledger["record_count"] == 1296
    assert ledger["language_counts"] == {"en": 432, "zh": 864}
    assert ledger["split_counts"] == {"test": 324, "train": 648, "validation": 324}
    assert ledger["story_group_count"] == 432
    assert ledger["story_group_size_counts"] == {"3": 432}

    leakage = _read(report_dir / "leakage-audit.json")
    assert leakage["record_ids_disjoint"] is True
    assert leakage["template_families_disjoint"] is True
    assert leakage["story_groups_disjoint"] is True
    assert leakage["prohibited_pair_found"] is False
    assert leakage["pairs_at_or_above_warning_threshold"]["train_vs_test"] == []

    selection = _read(report_dir / "selection-trace.json")
    assert selection["test_set_used_for_selection"] is False
    assert selection["tasks"]["event"]["selected_candidate"] == "word_char_tfidf_logreg"
    assert selection["tasks"]["sentiment"]["selected_candidate"] == "word_char_tfidf_logreg"

    feature = _read(report_dir / "feature-audit.json")
    assert feature["forbidden_metadata_sentinel_test"]["feature_text_unchanged"] is True
    assert feature["tasks"]["event"]["label_permutation_negative_control"]["macro_f1"] < 0.3
    assert feature["tasks"]["sentiment"]["label_permutation_negative_control"]["macro_f1"] < 0.3

    determinism = _read(report_dir / "determinism-audit.json")
    assert determinism["records_byte_identical"] is True
    assert determinism["test_predictions_identical"] is True
    assert determinism["artifact_hashes_identical"] == {"event": True, "sentiment": True}


def test_artifact_loader_rejects_unsafe_manifest_and_artifact_paths(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    report_dir = tmp_path / "reports"
    artifact_root = tmp_path / "artifacts"
    write_benchmark(dataset_dir)
    report = run_nlp_benchmark(dataset_dir, report_dir, artifact_root, task="event")
    model_id = report["tasks"]["event"]["selected_model_id"]
    manifest_path = artifact_root / "event" / model_id / "manifest.json"
    manifest = _read(manifest_path)

    with pytest.raises(ArtifactError, match="outside artifact root"):
        load_trusted_artifact(artifact_root, tmp_path / "outside-manifest.json", task="event")

    remote_manifest = artifact_root / "event" / model_id / "remote-manifest.json"
    remote_payload = {**manifest, "artifact_uri": "https://example.invalid/model.joblib"}
    remote_manifest.write_text(json.dumps(remote_payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="manifest validation failed"):
        load_trusted_artifact(artifact_root, remote_manifest, task="event")

    traversal_manifest = artifact_root / "event" / model_id / "traversal-manifest.json"
    traversal_payload = {**manifest, "artifact_uri": "../model.joblib"}
    traversal_manifest.write_text(json.dumps(traversal_payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="manifest validation failed"):
        load_trusted_artifact(artifact_root, traversal_manifest, task="event")

    wrong_task_manifest = artifact_root / "event" / model_id / "wrong-task-manifest.json"
    wrong_task_payload = {**manifest, "task": "sentiment"}
    wrong_task_manifest.write_text(json.dumps(wrong_task_payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="task mismatch"):
        load_trusted_artifact(artifact_root, wrong_task_manifest, task="event")

    unsupported_manifest = artifact_root / "event" / model_id / "unsupported-manifest.json"
    unsupported_payload = {**manifest, "artifact_uri": "event/model/model.txt"}
    unsupported_manifest.write_text(json.dumps(unsupported_payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="manifest validation failed"):
        load_trusted_artifact(artifact_root, unsupported_manifest, task="event")


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
