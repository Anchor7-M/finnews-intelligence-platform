from __future__ import annotations

from collections import Counter

from typer.testing import CliRunner

from finnews.domain.enums import EventType, SentimentLabel
from finnews.infrastructure.nlp.benchmark.generator import build_benchmark, write_benchmark
from finnews.infrastructure.nlp.benchmark.validation import validate_benchmark_dir
from finnews.interfaces.cli.app import app


def test_synthetic_nlp_benchmark_counts_and_splits() -> None:
    records = build_benchmark()

    assert len(records) == 1296
    assert Counter(record.language for record in records) == {"zh": 864, "en": 432}
    assert Counter(record.split for record in records) == {
        "train": 648,
        "validation": 324,
        "test": 324,
    }
    assert Counter(record.event_label for record in records) == {event: 144 for event in EventType}
    assert Counter(record.sentiment_label for record in records) == {
        sentiment: 324 for sentiment in SentimentLabel
    }
    assert len({record.company_id for record in records}) == 36
    assert len({record.industry for record in records}) >= 12
    assert sum(1 for record in records if record.challenge_flags) == 432
    assert sum(1 for record in records if record.split == "test" and record.challenge_flags) == 108


def test_synthetic_nlp_benchmark_leakage_and_determinism(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = write_benchmark(tmp_path)
    first_bytes = tmp_path.joinpath("records.jsonl").read_bytes()
    result = validate_benchmark_dir(tmp_path)
    second = write_benchmark(tmp_path)

    assert first["dataset_sha256"] == result["dataset_sha256"]
    assert first["split_hashes"] == result["split_hashes"]
    assert first == second
    assert first_bytes == tmp_path.joinpath("records.jsonl").read_bytes()


def test_nlp_dataset_cli_build_validate_and_summary(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import finnews.interfaces.cli.app as cli_app_module

    monkeypatch.setattr(cli_app_module, "_repo_root", lambda: tmp_path)
    runner = CliRunner()

    build = runner.invoke(app, ["nlp", "dataset", "build"])
    assert build.exit_code == 0
    assert "synthetic-finnews-nlp-v1" in build.stdout
    validate = runner.invoke(app, ["nlp", "dataset", "validate"])
    assert validate.exit_code == 0
    assert '"record_count": 1296' in validate.stdout
    summary = runner.invoke(app, ["nlp", "dataset", "summary"])
    assert summary.exit_code == 0
    assert '"challenge_test_count": 108' in summary.stdout
