from __future__ import annotations

from datetime import datetime
from typing import Any

from finnews.application.ports.repositories import NewsRepository
from finnews.domain.entities import NlpEvaluationRun, NlpModelRegistryEntry


def register_nlp_report(repository: NewsRepository, report: dict[str, Any]) -> dict[str, int]:
    counts = {"models": 0, "evaluations": 0}
    dataset = report["dataset"]
    selection = report["selection_procedure"]
    for task, task_report in report["tasks"].items():
        artifact = task_report["artifact"]
        model = NlpModelRegistryEntry(
            model_id=artifact["model_id"],
            task=task,
            provider=artifact["provider"],
            model_kind=artifact["model_kind"],
            status=artifact["status"],
            dataset_id=dataset["dataset_id"],
            dataset_version=dataset["dataset_version"],
            dataset_sha256=dataset["dataset_sha256"],
            split_hashes=dict(dataset["split_hashes"]),
            label_set=list(task_report["label_set"]),
            metrics=dict(task_report["test_metrics"]["selected_ml"]),
            calibration=dict(task_report["calibration"]),
            artifact_uri=None,
            artifact_sha256=artifact["artifact_sha256"],
            artifact_size_bytes=int(artifact["artifact_size_bytes"]),
            manifest_sha256=artifact["manifest_sha256"],
            config_sha256=artifact["config_sha256"],
            created_at=datetime.fromisoformat(artifact["created_at"]),
            updated_at=datetime.fromisoformat(artifact["created_at"]),
        )
        repository.upsert_nlp_model(model)
        counts["models"] += 1
        evaluation = NlpEvaluationRun(
            evaluation_id=f"{artifact['model_id']}-test",
            model_id=artifact["model_id"],
            task=task,
            dataset_id=dataset["dataset_id"],
            dataset_version=dataset["dataset_version"],
            dataset_sha256=dataset["dataset_sha256"],
            split_name="test",
            metrics=dict(task_report["test_metrics"]),
            slice_metrics=dict(task_report["slices"]),
            calibration=dict(task_report["calibration"]),
            error_analysis=dict(task_report["error_analysis"]),
            selection_procedure=dict(selection),
            evaluated_at=datetime.fromisoformat(report["created_at"]),
        )
        repository.upsert_nlp_evaluation(evaluation)
        counts["evaluations"] += 1
    return counts
