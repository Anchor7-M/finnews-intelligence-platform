from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from finnews.infrastructure.nlp.benchmark.models import DATASET_ID


def default_nlp_report_dir(repo_root: Path) -> Path:
    return repo_root / "reports" / "nlp" / DATASET_ID


def load_nlp_evaluation_report(repo_root: Path) -> dict[str, Any]:
    path = default_nlp_report_dir(repo_root) / "evaluation.json"
    if not path.is_file():
        return {}
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_nlp_error_report(repo_root: Path) -> dict[str, Any]:
    path = default_nlp_report_dir(repo_root) / "error_analysis.json"
    if not path.is_file():
        return {}
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def nlp_static_payload(repo_root: Path) -> dict[str, Any]:
    report = load_nlp_evaluation_report(repo_root)
    errors = load_nlp_error_report(repo_root)
    if not report:
        return {
            "nlp-overview": _empty_overview(),
            "nlp-models": [],
            "nlp-evaluations": [],
            "nlp-error-analysis": [],
            "nlp-dataset-card": _dataset_card(None),
        }
    tasks = report["tasks"]
    models = [
        {
            **task_report["artifact"],
            "task": task,
            "selected_candidate": task_report["selected_candidate"],
            "promotion_policy": task_report["promotion_policy"],
            "calibration": task_report["calibration"],
            "abstention": task_report["abstention"],
        }
        for task, task_report in tasks.items()
    ]
    evaluations = [
        {
            "evaluation_id": f"{task_report['selected_model_id']}-test",
            "model_id": task_report["selected_model_id"],
            "task": task,
            "split": "test",
            "dataset": report["dataset"],
            "test_metrics": task_report["test_metrics"],
            "slices": task_report["slices"],
            "calibration": task_report["calibration"],
            "disclaimer": report["disclaimer"],
        }
        for task, task_report in tasks.items()
    ]
    return {
        "nlp-overview": {
            "disclaimer": report["disclaimer"],
            "dataset": report["dataset"],
            "record_count": 1296,
            "split_counts": {"train": 648, "validation": 324, "test": 324},
            "language_counts": {"zh": 864, "en": 432},
            "selected_models": {
                task: task_report["selected_model_id"] for task, task_report in tasks.items()
            },
            "benchmark_claim": "synthetic benchmark only, not real-world accuracy",
            "not_investment_advice": True,
        },
        "nlp-models": models,
        "nlp-evaluations": evaluations,
        "nlp-error-analysis": [
            {"task": task, **task_errors} for task, task_errors in errors.get("tasks", {}).items()
        ],
        "nlp-dataset-card": _dataset_card(report),
    }


def _empty_overview() -> dict[str, Any]:
    return {
        "disclaimer": "NLP benchmark report has not been generated.",
        "dataset": None,
        "record_count": 0,
        "split_counts": {},
        "language_counts": {},
        "selected_models": {},
        "not_investment_advice": True,
    }


def _dataset_card(report: dict[str, Any] | None) -> dict[str, Any]:
    dataset = report["dataset"] if report else {}
    return {
        "dataset_id": dataset.get("dataset_id", DATASET_ID),
        "synthetic_only": True,
        "label_source": "generator_defined_synthetic_gold",
        "human_labeled": False,
        "live_source_content_used": False,
        "copyrighted_news_used": False,
        "investment_advice": False,
        "real_world_metrics_deferred_to": "Milestone 2B",
        "dataset_sha256": dataset.get("dataset_sha256"),
        "split_hashes": dataset.get("split_hashes", {}),
    }
