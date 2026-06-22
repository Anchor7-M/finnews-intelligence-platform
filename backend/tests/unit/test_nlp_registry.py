from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from finnews.application.services.nlp_evaluation import run_nlp_benchmark
from finnews.application.services.nlp_registry import register_nlp_report
from finnews.infrastructure.nlp.benchmark.generator import write_benchmark
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository


def test_memory_nlp_registry_idempotent_filters_and_json_round_trip(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    report_dir = tmp_path / "reports"
    artifact_root = tmp_path / "artifacts"
    write_benchmark(dataset_dir)
    report = run_nlp_benchmark(dataset_dir, report_dir, artifact_root, task="all")
    repo = MemoryNewsRepository()

    first = register_nlp_report(repo, report)
    second = register_nlp_report(repo, report)
    task_reports = cast(dict[str, dict[str, Any]], report["tasks"])

    assert first == {"models": 2, "evaluations": 2}
    assert second == {"models": 2, "evaluations": 2}
    assert len(repo.list_nlp_models()) == 2
    assert len(repo.list_nlp_models(task="event")) == 1
    assert len(repo.list_nlp_models(status="demo_candidate")) == 2
    event_model = repo.get_nlp_model(task_reports["event"]["selected_model_id"])
    assert event_model is not None
    assert event_model.metrics["macro_f1"] == 1.0
    assert event_model.artifact_uri is None
    assert len(repo.list_nlp_evaluations(task="sentiment")) == 1
    evaluation = repo.get_nlp_evaluation(
        f"{task_reports['sentiment']['selected_model_id']}-test"
    )
    assert evaluation is not None
    evaluation_metrics = cast(dict[str, dict[str, Any]], evaluation.metrics)
    assert evaluation_metrics["selected_ml"]["macro_f1"] == 1.0
