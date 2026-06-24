from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from finnews.application.ports.repositories import NewsRepository
from finnews.application.services.cross_asset import (
    CrossAssetError,
    build_cross_asset_demo,
    cross_asset_overview,
    mt5_readiness,
    persist_cross_asset_demo,
    resolve_asset_alias,
    validate_mt5_symbol_map,
    validate_signal_package,
    write_signal_package,
)
from finnews.application.services.cross_asset_release_audit import (
    write_revised_m3a_release_reports,
)
from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.application.services.export_static import build_static_payload, export_static
from finnews.application.services.nlp_artifacts import ArtifactError, load_trusted_artifact
from finnews.application.services.nlp_evaluation import run_nlp_benchmark
from finnews.application.services.nlp_registry import register_nlp_report
from finnews.application.services.nlp_release_audit import write_release_audit_reports
from finnews.application.services.nlp_reporting import (
    load_nlp_evaluation_report,
    nlp_static_payload,
)
from finnews.application.services.official_data import (
    build_official_data_release_ledger,
    official_data_overview,
    official_data_static_payload,
    persist_official_data_demo,
)
from finnews.application.services.pipeline import NewsPipeline
from finnews.application.services.research_export import (
    DEFAULT_CUTOFF_POLICY,
    DEFAULT_WINDOWS,
    ResearchExportError,
    build_demo_calendar,
    build_research_export,
    compare_research_export_packages,
    feature_catalog,
    load_local_calendar,
    load_research_export_package,
    validate_calendar_path,
    validate_research_export_package,
    write_research_export_package,
)
from finnews.application.services.source_ingestion import SourceIngestionService
from finnews.application.services.source_smoke import (
    SMOKE_EXIT_CODES,
    SmokeOptions,
    SourceSmokeService,
)
from finnews.bootstrap import (
    FIXTURE_DIR,
    build_memory_repository,
    create_postgres_session,
    load_default_records,
    load_source_registry_into_repository,
)
from finnews.domain.enums import SourceType
from finnews.infrastructure.http.client import BoundedSourceHttpClient
from finnews.infrastructure.nlp.benchmark.generator import benchmark_dir, write_benchmark
from finnews.infrastructure.nlp.benchmark.validation import (
    BenchmarkValidationError,
    validate_benchmark_dir,
)
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.persistence.postgres.repository import PostgresNewsRepository
from finnews.infrastructure.sources.fixtures import JsonlFixtureSource
from finnews.infrastructure.sources.local_feed import LocalFeedSource
from finnews.infrastructure.sources.registry import (
    SourceConfigError,
    load_source_definitions,
    validate_source_definitions,
)
from finnews.infrastructure.sources.reviews import (
    SourceReviewError,
    load_source_reviews,
    source_config_digest,
    validate_source_review_integrity,
    validate_source_reviews,
)
from finnews.settings import Settings, get_settings

app = typer.Typer(help="Finnews local CLI")
ingest_app = typer.Typer(help="Ingest local synthetic data")
db_app = typer.Typer(help="Database helpers")
source_app = typer.Typer(help="Source registry and run-once ingestion")
source_review_app = typer.Typer(help="Source review evidence")
nlp_app = typer.Typer(help="Synthetic NLP benchmark and evaluation")
nlp_dataset_app = typer.Typer(help="Synthetic NLP dataset commands")
research_app = typer.Typer(help="Point-in-time research export commands")
research_calendar_app = typer.Typer(help="Research calendar commands")
research_export_app = typer.Typer(help="Research package commands")
asset_app = typer.Typer(help="Canonical cross-asset registry commands")
cross_asset_app = typer.Typer(help="Cross-asset event intelligence commands")
signal_app = typer.Typer(help="Versioned market signal contract commands")
mt5_app = typer.Typer(help="Offline MT5 readiness and symbol-map validation")
official_data_app = typer.Typer(help="Official-data fixtures and point-in-time metadata")
app.add_typer(ingest_app, name="ingest")
app.add_typer(db_app, name="db")
app.add_typer(source_app, name="source")
source_app.add_typer(source_review_app, name="review")
app.add_typer(nlp_app, name="nlp")
nlp_app.add_typer(nlp_dataset_app, name="dataset")
app.add_typer(research_app, name="research")
research_app.add_typer(research_calendar_app, name="calendar")
research_app.add_typer(research_export_app, name="export")
app.add_typer(asset_app, name="asset")
app.add_typer(cross_asset_app, name="cross-asset")
app.add_typer(signal_app, name="signal")
app.add_typer(mt5_app, name="mt5")
app.add_typer(official_data_app, name="official-data")


@app.command()
def doctor() -> None:
    settings = get_settings()
    typer.echo(f"Python profile: {settings.profile}")
    typer.echo(f"Environment: {settings.env}")
    typer.echo(f"Fixture directory exists: {FIXTURE_DIR.exists()}")
    typer.echo(f"Database URL configured: {'yes' if settings.database_url else 'no'}")


@db_app.command("upgrade")
def db_upgrade() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    typer.echo("database_upgraded=head")


@source_app.command("list")
def source_list() -> None:
    settings = get_settings()
    repo, session = _repository(settings)
    rows = [
        {
            "source_id": source.source_id,
            "display_name": source.display_name,
            "source_type": source.source_type.value,
            "review_status": source.review_status.value,
            "enabled": source.enabled,
            "risk_classification": source.risk_classification,
        }
        for source in repo.list_source_definitions()
    ]
    _commit_and_close(session)
    typer.echo(json.dumps(rows, sort_keys=True))


@source_app.command("validate-config")
def source_validate_config() -> None:
    try:
        source_ids = validate_source_definitions()
        repo, session = _repository(get_settings())
        review_ids = validate_source_reviews()
        validated_review_sources = validate_source_review_integrity(
            repo.list_source_definitions(), load_source_reviews()
        )
        _commit_and_close(session)
    except SourceConfigError as exc:
        typer.echo(f"source_config_error={exc}", err=True)
        raise typer.Exit(4) from exc
    except SourceReviewError as exc:
        typer.echo(f"source_review_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(
        json.dumps(
            {
                "valid": True,
                "source_ids": source_ids,
                "review_ids": review_ids,
                "review_validated_source_ids": validated_review_sources,
            },
            sort_keys=True,
        )
    )


@source_review_app.command("list")
def source_review_list() -> None:
    try:
        reviews = load_source_reviews()
    except SourceReviewError as exc:
        typer.echo(f"source_review_error={exc}", err=True)
        raise typer.Exit(4) from exc
    rows = [
        {
            "source_id": review.source_id,
            "review_decision": review.review_decision,
            "official_owner": review.official_owner,
            "access_cost": review.access_cost,
            "live_smoke_status": review.live_smoke_status,
        }
        for review in reviews
    ]
    typer.echo(json.dumps(rows, sort_keys=True))


@source_review_app.command("validate")
def source_review_validate() -> None:
    try:
        repo, session = _repository(get_settings())
        review_ids = validate_source_reviews()
        validated_sources = validate_source_review_integrity(
            repo.list_source_definitions(), load_source_reviews()
        )
        _commit_and_close(session)
    except (SourceConfigError, SourceReviewError) as exc:
        typer.echo(f"source_review_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(
        json.dumps(
            {
                "valid": True,
                "review_ids": review_ids,
                "review_validated_source_ids": validated_sources,
            },
            sort_keys=True,
        )
    )


@source_review_app.command("show")
def source_review_show(source_id: Annotated[str, typer.Option("--source")]) -> None:
    try:
        for review in load_source_reviews():
            if review.source_id == source_id:
                typer.echo(json.dumps(review.safe_summary(), default=str, sort_keys=True))
                return
    except SourceReviewError as exc:
        typer.echo(f"source_review_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo("source_review_not_found", err=True)
    raise typer.Exit(4)


@source_app.command("health")
def source_health() -> None:
    settings = get_settings()
    repo, session = _repository(settings)
    states = {state.source_id: state for state in repo.list_source_fetch_states()}
    rows = []
    for source in repo.list_source_definitions():
        state = states.get(source.source_id)
        rows.append(
            {
                "source_id": source.source_id,
                "health": state.health_status.value if state else "disabled",
                "last_attempted_at": state.last_attempted_at if state else None,
                "last_successful_at": state.last_successful_at if state else None,
                "last_error_category": state.last_error_category.value if state else "none",
                "consecutive_failure_count": state.consecutive_failure_count if state else 0,
            }
        )
    _commit_and_close(session)
    typer.echo(json.dumps(rows, default=str, sort_keys=True))


@source_app.command("fetch")
def source_fetch(
    source_id: Annotated[str | None, typer.Option("--source")] = None,
    all_approved: Annotated[bool, typer.Option("--all-approved")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings()
    repo, session = _repository(settings)
    service = SourceIngestionService(
        repo,
        settings,
        http_client_factory=lambda source: BoundedSourceHttpClient(source),
    )
    sources = repo.list_source_definitions()
    selected = (
        [
            source
            for source in sources
            if source.fetch_allowed
            and source.source_type
            in {SourceType.RSS, SourceType.ATOM, SourceType.DOCUMENTED_JSON_API}
        ]
        if all_approved
        else [source for source in sources if source.source_id == source_id]
    )
    if not selected:
        _commit_and_close(session)
        if all_approved:
            typer.echo(
                json.dumps(
                    {
                        "status": "no_work",
                        "reason": "no approved enabled network sources",
                    },
                    sort_keys=True,
                )
            )
            return
        typer.echo("source_selection_empty", err=True)
        raise typer.Exit(4)
    results = []
    try:
        for source in selected:
            result = service.fetch_source(source.source_id, dry_run=dry_run)
            results.append(result.__dict__)
    except ValueError as exc:
        _commit_and_close(session)
        typer.echo(f"source_policy_error={exc}", err=True)
        raise typer.Exit(4) from exc
    _commit_and_close(session)
    typer.echo(json.dumps(results, default=str, sort_keys=True))


@source_app.command("import-announcements")
def source_import_announcements(
    source_id: Annotated[str, typer.Option("--source")],
    path: Annotated[Path, typer.Option("--path")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings()
    repo, session = _repository(settings)
    service = SourceIngestionService(repo, settings)
    try:
        result = service.import_announcements(source_id, path, dry_run=dry_run)
    except ValueError as exc:
        _commit_and_close(session)
        typer.echo(f"source_policy_error={exc}", err=True)
        raise typer.Exit(4) from exc
    _commit_and_close(session)
    typer.echo(json.dumps(result.__dict__, default=str, sort_keys=True))


@source_app.command("smoke-test")
def source_smoke_test(
    source_id: Annotated[str, typer.Option("--source")],
    max_items: Annotated[int, typer.Option("--max-items", min=1, max=5)] = 5,
    conditional_check: Annotated[bool, typer.Option("--conditional-check")] = False,
    persist: Annotated[bool, typer.Option("--persist/--no-persist")] = False,
    profile: Annotated[str, typer.Option("--profile")] = "memory",
    report_path: Annotated[Path | None, typer.Option("--report-path")] = None,
    confirm_live: Annotated[bool, typer.Option("--confirm-live")] = False,
) -> None:
    settings = Settings(profile=profile)
    repo, session = _repository(settings)
    reviews = load_source_reviews()
    result = SourceSmokeService(repo.list_source_definitions(), reviews).run(
        SmokeOptions(
            source_id=source_id,
            max_items=max_items,
            conditional_check=conditional_check,
            persist=persist,
            confirm_live=confirm_live,
            report_path=report_path,
        )
    )
    _commit_and_close(session)
    typer.echo(json.dumps(result.safe_dict(), sort_keys=True))
    exit_code = SMOKE_EXIT_CODES[result.exit_kind]
    if exit_code:
        raise typer.Exit(exit_code)


@nlp_dataset_app.command("build")
def nlp_dataset_build() -> None:
    manifest = write_benchmark(benchmark_dir(_repo_root()))
    typer.echo(json.dumps(manifest, sort_keys=True))


@nlp_dataset_app.command("validate")
def nlp_dataset_validate() -> None:
    try:
        result = validate_benchmark_dir(benchmark_dir(_repo_root()))
    except BenchmarkValidationError as exc:
        typer.echo(f"nlp_dataset_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(json.dumps(result, sort_keys=True))


@nlp_dataset_app.command("summary")
def nlp_dataset_summary() -> None:
    nlp_dataset_validate()


@nlp_app.command("train")
def nlp_train(task: Annotated[str, typer.Option("--task")]) -> None:
    if task not in {"event", "sentiment"}:
        typer.echo("nlp_task_error=task must be event or sentiment", err=True)
        raise typer.Exit(4)
    report = run_nlp_benchmark(
        benchmark_dir(_repo_root()),
        _repo_root() / "reports" / "nlp" / "synthetic-finnews-nlp-v1",
        _repo_root() / ".finnews-artifacts" / "nlp",
        task=task,  # type: ignore[arg-type]
    )
    task_report = report["tasks"][task]
    typer.echo(
        json.dumps(
            {
                "task": task,
                "model_id": task_report["selected_model_id"],
                "status": task_report["artifact"]["status"],
                "dataset_sha256": report["dataset"]["dataset_sha256"],
                "disclaimer": report["disclaimer"],
            },
            sort_keys=True,
        )
    )


@nlp_app.command("benchmark")
def nlp_benchmark(task: Annotated[str, typer.Option("--task")] = "all") -> None:
    if task not in {"all", "event", "sentiment"}:
        typer.echo("nlp_task_error=task must be all, event, or sentiment", err=True)
        raise typer.Exit(4)
    report = run_nlp_benchmark(
        benchmark_dir(_repo_root()),
        _repo_root() / "reports" / "nlp" / "synthetic-finnews-nlp-v1",
        _repo_root() / ".finnews-artifacts" / "nlp",
        task=task,  # type: ignore[arg-type]
    )
    repo, session = _repository(get_settings())
    registered = register_nlp_report(repo, report)
    _commit_and_close(session)
    typer.echo(
        json.dumps(
            {
                "status": "completed",
                "task": task,
                "registered": registered,
                "dataset_sha256": report["dataset"]["dataset_sha256"],
                "selected_models": {
                    name: item["selected_model_id"] for name, item in report["tasks"].items()
                },
                "disclaimer": report["disclaimer"],
            },
            sort_keys=True,
        )
    )


@nlp_app.command("evaluate")
def nlp_evaluate(
    task: Annotated[str, typer.Option("--task")],
    model_id: Annotated[str, typer.Option("--model-id")],
) -> None:
    report = load_nlp_evaluation_report(_repo_root())
    task_report = report.get("tasks", {}).get(task)
    if not task_report or task_report.get("selected_model_id") != model_id:
        typer.echo("nlp_evaluation_not_found", err=True)
        raise typer.Exit(4)
    typer.echo(json.dumps(task_report["test_metrics"], sort_keys=True))


@nlp_app.command("compare")
def nlp_compare(task: Annotated[str, typer.Option("--task")]) -> None:
    report = load_nlp_evaluation_report(_repo_root())
    task_report = report.get("tasks", {}).get(task)
    if not task_report:
        typer.echo("nlp_task_not_found", err=True)
        raise typer.Exit(4)
    typer.echo(
        json.dumps(
            {
                "task": task,
                "validation_selection": task_report["selected_candidate"],
                "test_metrics": task_report["test_metrics"],
                "calibration": task_report["calibration"],
                "abstention": task_report["abstention"],
            },
            sort_keys=True,
        )
    )


@nlp_app.command("export-static")
def nlp_export_static() -> None:
    output = _repo_root() / "frontend" / "public" / "demo-data"
    for name, payload in nlp_static_payload(_repo_root()).items():
        (output / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    typer.echo(json.dumps({"exported": True, "files": sorted(nlp_static_payload(_repo_root()))}))


@nlp_app.command("release-audit")
def nlp_release_audit() -> None:
    result = write_release_audit_reports(_repo_root())
    typer.echo(json.dumps(result, sort_keys=True))


@nlp_app.command("infer")
def nlp_infer(
    task: Annotated[str, typer.Option("--task")],
    model_id: Annotated[str, typer.Option("--model-id")],
    text: Annotated[str, typer.Option("--text")],
) -> None:
    if task not in {"event", "sentiment"}:
        typer.echo("nlp_task_error=task must be event or sentiment", err=True)
        raise typer.Exit(4)
    manifest_path = _repo_root() / ".finnews-artifacts" / "nlp" / task / model_id / "manifest.json"
    try:
        loaded = cast(
            dict[str, Any],
            load_trusted_artifact(
                _repo_root() / ".finnews-artifacts" / "nlp", manifest_path, task=task
            ),
        )
    except ArtifactError as exc:
        typer.echo(f"nlp_artifact_error={exc}", err=True)
        raise typer.Exit(5) from exc
    model = loaded["model"]
    labels = list(loaded["labels"])
    probabilities = model.predict_proba([text])[0]
    classes = [str(item) for item in model.named_steps["classifier"].classes_]
    by_label = {label: float(probabilities[classes.index(label)]) for label in labels}
    predicted = str(model.predict([text])[0])
    confidence = by_label[predicted]
    typer.echo(
        json.dumps(
            {
                "task": task,
                "model_id": model_id,
                "predicted_label": predicted,
                "abstained": False,
                "confidence": round(confidence, 6),
                "disclaimer": "synthetic benchmark model only; input text was not persisted",
            },
            sort_keys=True,
        )
    )


nlp_registry_app = typer.Typer(help="NLP model registry metadata")
nlp_app.add_typer(nlp_registry_app, name="registry")


@nlp_registry_app.command("list")
def nlp_registry_list() -> None:
    rows = nlp_static_payload(_repo_root())["nlp-models"]
    typer.echo(json.dumps(rows, sort_keys=True))


@nlp_registry_app.command("show")
def nlp_registry_show(model_id: Annotated[str, typer.Option("--model-id")]) -> None:
    for row in nlp_static_payload(_repo_root())["nlp-models"]:
        if row["model_id"] == model_id:
            typer.echo(json.dumps(row, sort_keys=True))
            return
    typer.echo("nlp_model_not_found", err=True)
    raise typer.Exit(4)


@ingest_app.command("fixture")
def ingest_fixture(path: Annotated[Path, typer.Option("--path")]) -> None:
    settings = get_settings()
    repo, session = _empty_repository(settings)
    pipeline = NewsPipeline(repo, settings)
    pipeline.load_companies(FIXTURE_DIR / "companies.json")
    counts = pipeline.ingest_records(
        JsonlFixtureSource(path, settings.max_fixture_bytes).read_records()
    )
    _commit_and_close(session)
    typer.echo(json.dumps(counts, ensure_ascii=False, sort_keys=True))


@ingest_app.command("local-feed")
def ingest_local_feed(path: Annotated[Path, typer.Option("--path")]) -> None:
    settings = get_settings()
    repo, session = _empty_repository(settings)
    pipeline = NewsPipeline(repo, settings)
    pipeline.load_companies(FIXTURE_DIR / "companies.json")
    counts = pipeline.ingest_records(
        LocalFeedSource(path, settings.max_fixture_bytes).read_records()
    )
    _commit_and_close(session)
    typer.echo(json.dumps(counts, ensure_ascii=False, sort_keys=True))


@research_calendar_app.command("build-demo")
def research_calendar_build_demo() -> None:
    calendar, sessions = build_demo_calendar()
    typer.echo(
        json.dumps(
            {
                "calendar_id": calendar.calendar_id,
                "calendar_version": calendar.calendar_version,
                "timezone": calendar.timezone,
                "calendar_hash": calendar.calendar_hash,
                "session_count": len(sessions),
                "synthetic_data": calendar.synthetic,
                "official_market_calendar": False,
            },
            sort_keys=True,
        )
    )


@research_calendar_app.command("validate")
def research_calendar_validate(path: Annotated[Path, typer.Option("--path")]) -> None:
    result = validate_calendar_path(path)
    typer.echo(json.dumps(result.__dict__, sort_keys=True))
    if not result.valid:
        raise typer.Exit(4)


@research_calendar_app.command("summary")
def research_calendar_summary(path: Annotated[Path, typer.Option("--path")]) -> None:
    research_calendar_validate(path)


@research_export_app.command("build")
def research_export_build(
    profile: Annotated[str, typer.Option("--profile")] = "memory",
    calendar_path: Annotated[Path | None, typer.Option("--calendar")] = None,
    cutoff_policy: Annotated[str, typer.Option("--cutoff-policy")] = DEFAULT_CUTOFF_POLICY,
    windows_text: Annotated[str, typer.Option("--windows")] = ",".join(
        str(item) for item in DEFAULT_WINDOWS
    ),
    output: Annotated[Path, typer.Option("--output")] = Path("../.finnews-research-exports/latest"),
    persist_metadata: Annotated[
        bool, typer.Option("--persist-metadata/--no-persist-metadata")
    ] = False,
) -> None:
    try:
        windows = [int(item.strip()) for item in windows_text.split(",") if item.strip()]
        settings = Settings(profile=profile)
        repo, session = _repository(settings)
        calendar = None
        sessions = None
        if calendar_path is not None and str(calendar_path) != "demo":
            calendar, sessions = load_local_calendar(calendar_path)
        package = build_research_export(
            repo,
            calendar=calendar,
            sessions=sessions,
            cutoff_policy=cast(Any, cutoff_policy),
            windows=windows,
            persist_metadata=persist_metadata,
        )
        written = write_research_export_package(package, output)
        _commit_and_close(session)
    except ResearchExportError as exc:
        typer.echo(f"research_export_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(
        json.dumps(
            {
                "export_id": written.export_id,
                "package_content_hash": written.package_hash,
                "feature_row_count": len(written.feature_rows),
                "lineage_row_count": len(written.lineage_rows),
                "output_name": output.name,
            },
            sort_keys=True,
        )
    )


@research_export_app.command("validate")
def research_export_validate(path: Annotated[Path, typer.Option("--path")]) -> None:
    try:
        result = validate_research_export_package(path)
    except ResearchExportError as exc:
        typer.echo(f"research_export_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(json.dumps(result, sort_keys=True))


@research_export_app.command("summary")
def research_export_summary(path: Annotated[Path, typer.Option("--path")]) -> None:
    try:
        package = load_research_export_package(path)
    except ResearchExportError as exc:
        typer.echo(f"research_export_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(
        json.dumps(
            {
                "export_id": package.export_id,
                "package_content_hash": package.package_hash,
                "counts": package.quality_report["counts"],
                "leakage_status": package.leakage_audit["status"],
            },
            sort_keys=True,
        )
    )


@research_export_app.command("compare")
def research_export_compare(
    left: Annotated[Path, typer.Option("--left")],
    right: Annotated[Path, typer.Option("--right")],
) -> None:
    try:
        result = compare_research_export_packages(left, right)
    except ResearchExportError as exc:
        typer.echo(f"research_export_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(json.dumps(result, sort_keys=True))
    if not result["equal"]:
        raise typer.Exit(2)


@research_export_app.command("lineage")
def research_export_lineage(
    path: Annotated[Path, typer.Option("--path")],
    row_id: Annotated[str, typer.Option("--row-id")],
) -> None:
    try:
        package = load_research_export_package(path)
    except ResearchExportError as exc:
        typer.echo(f"research_export_error={exc}", err=True)
        raise typer.Exit(4) from exc
    rows = [row for row in package.lineage_rows if row["lineage_row_id"] == row_id]
    if not rows:
        typer.echo("research_lineage_not_found", err=True)
        raise typer.Exit(4)
    safe_rows = [
        {
            key: row.get(key)
            for key in [
                "lineage_row_id",
                "feature_row_key",
                "canonical_article_id",
                "source_id",
                "company_id",
                "source_published_at",
                "first_seen_at",
                "information_available_at",
                "decision_cutoff_at",
                "event_label",
                "sentiment_label",
                "inclusion_reason",
            ]
        }
        for row in rows
    ]
    typer.echo(json.dumps(safe_rows, sort_keys=True))


@research_export_app.command("feature-catalog")
def research_export_feature_catalog() -> None:
    typer.echo(json.dumps(feature_catalog(), sort_keys=True))


@research_export_app.command("export-static")
def research_export_static() -> None:
    output = _repo_root() / "frontend" / "public" / "demo-data"
    repo = build_memory_repository()
    payload = build_static_payload(repo)
    exported = []
    for name, value in payload.items():
        if name.startswith("research-"):
            (output / f"{name}.json").write_text(
                json.dumps(value, ensure_ascii=False, indent=2, default=str, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            exported.append(name)
    typer.echo(json.dumps({"exported": True, "files": sorted(exported)}, sort_keys=True))


@research_app.command("export-static")
def research_static_command() -> None:
    research_export_static()


@asset_app.command("list")
def asset_list() -> None:
    dataset = build_cross_asset_demo()
    typer.echo(
        json.dumps(
            [
                {
                    "asset_id": asset.asset_id,
                    "display_name": asset.display_name,
                    "asset_class": asset.asset_class.value,
                    "canonical_symbol": asset.canonical_symbol,
                    "region": asset.country_region,
                    "status": asset.status.value,
                }
                for asset in dataset.assets
            ],
            sort_keys=True,
            default=str,
        )
    )


@asset_app.command("show")
def asset_show(asset_id: Annotated[str, typer.Option("--asset-id")]) -> None:
    dataset = build_cross_asset_demo()
    for asset in dataset.assets:
        if asset.asset_id == asset_id:
            typer.echo(json.dumps(asset.__dict__, sort_keys=True, default=str))
            return
    typer.echo("asset_not_found", err=True)
    raise typer.Exit(code=1)


@asset_app.command("validate")
def asset_validate() -> None:
    dataset = build_cross_asset_demo()
    counts: dict[str, int] = {}
    for asset in dataset.assets:
        counts[asset.asset_class.value] = counts.get(asset.asset_class.value, 0) + 1
    ids = [asset.asset_id for asset in dataset.assets]
    result = {
        "valid": len(dataset.assets) == 40 and len(ids) == len(set(ids)),
        "asset_count": len(dataset.assets),
        "asset_class_counts": counts,
        "alias_count": len(dataset.aliases),
        "broker_mapping_count": len(dataset.broker_mappings),
        "synthetic_data": True,
    }
    typer.echo(json.dumps(result, sort_keys=True))


@asset_app.command("resolve")
def asset_resolve(
    namespace: Annotated[str, typer.Option("--namespace")],
    symbol: Annotated[str, typer.Option("--symbol")],
) -> None:
    try:
        result = resolve_asset_alias(namespace, symbol)
    except CrossAssetError as exc:
        typer.echo(f"asset_resolution_error={exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result.__dict__, sort_keys=True))


@cross_asset_app.command("build-demo")
def cross_asset_build_demo() -> None:
    dataset = build_cross_asset_demo()
    typer.echo(
        json.dumps(
            {
                "asset_count": len(dataset.assets),
                "event_count": len(dataset.events),
                "impact_hypothesis_count": len(dataset.impacts),
                "signal_candidate_count": len(dataset.signals),
                "synthetic_data": True,
            },
            sort_keys=True,
        )
    )


@cross_asset_app.command("impacts")
def cross_asset_impacts(event_id: Annotated[str, typer.Option("--event-id")]) -> None:
    dataset = build_cross_asset_demo()
    rows = [row for row in dataset.impacts if row.event_id == event_id]
    if not rows:
        typer.echo("event_impacts_not_found", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        json.dumps(
            [
                {
                    "impact_id": row.impact_id,
                    "event_id": row.event_id,
                    "asset_id": row.asset_id,
                    "direction": row.direction.value,
                    "horizon": row.horizon.value,
                    "confidence": row.confidence,
                    "status": row.status,
                }
                for row in rows
            ],
            sort_keys=True,
            default=str,
        )
    )


@cross_asset_app.command("summary")
def cross_asset_summary() -> None:
    typer.echo(json.dumps(cross_asset_overview(), sort_keys=True, default=str))


@cross_asset_app.command("release-audit")
def cross_asset_release_audit() -> None:
    result = write_revised_m3a_release_reports(_repo_root())
    typer.echo(json.dumps(result, sort_keys=True))


@signal_app.command("generate-demo")
def signal_generate_demo() -> None:
    dataset = build_cross_asset_demo()
    typer.echo(
        json.dumps(
            {
                "contract_name": "finnews-market-signal-v1",
                "contract_version": "1.0.0",
                "signal_candidate_count": len(dataset.signals),
                "synthetic_data": True,
                "no_execution": True,
            },
            sort_keys=True,
        )
    )


@signal_app.command("validate")
def signal_validate(path: Annotated[Path, typer.Option("--path")]) -> None:
    try:
        result = validate_signal_package(path)
    except CrossAssetError as exc:
        typer.echo(f"signal_contract_error={exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, sort_keys=True))


@signal_app.command("export")
def signal_export(
    output: Annotated[Path, typer.Option("--output")] = Path("../.finnews-market-signals/latest"),
) -> None:
    try:
        result = write_signal_package(output, build_cross_asset_demo())
    except CrossAssetError as exc:
        typer.echo(f"signal_export_error={exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps({"exported": True, "output_name": output.name, **result}, sort_keys=True))


@signal_app.command("summary")
def signal_summary(path: Annotated[Path, typer.Option("--path")]) -> None:
    signal_validate(path)


@mt5_app.command("readiness")
def mt5_readiness_command() -> None:
    typer.echo(json.dumps(mt5_readiness(), sort_keys=True, default=str))


@mt5_app.command("validate-symbol-map")
def mt5_validate_symbol_map(path: Annotated[Path, typer.Option("--path")]) -> None:
    try:
        result = validate_mt5_symbol_map(path)
    except CrossAssetError as exc:
        typer.echo(f"mt5_symbol_map_error={exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, sort_keys=True))


@official_data_app.command("summary")
def official_data_summary(profile: Annotated[str, typer.Option("--profile")] = "memory") -> None:
    repo, session = _repository(Settings(profile=profile))
    typer.echo(json.dumps(official_data_overview(repo), sort_keys=True, default=str))
    _commit_and_close(session)


@official_data_app.command("validate-fixtures")
def official_data_validate_fixtures() -> None:
    repo = MemoryNewsRepository()
    counts = persist_official_data_demo(repo)
    overview = official_data_overview(repo)
    expected = {
        "dataset_count": 4,
        "series_profile_count": 16,
        "definition_count_total": 16,
        "observation_count": 144,
        "revision_count": 168,
        "changed_value_revision_count": 24,
        "revised_observation_count": 24,
        "regulatory_document_count": 32,
        "series_asset_association_count": 80,
        "official_release_event_count": 48,
    }
    mismatches = {
        key: {"expected": value, "actual": overview.get(key)}
        for key, value in expected.items()
        if overview.get(key) != value
    }
    result = {
        "valid": not mismatches,
        "counts": counts,
        "overview": overview,
        "mismatches": mismatches,
    }
    typer.echo(json.dumps(result, sort_keys=True, default=str))
    if mismatches:
        raise typer.Exit(code=4)


@official_data_app.command("release-audit")
def official_data_release_audit() -> None:
    output = _repo_root() / "reports" / "official-data" / "m3b-release-ledger.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    repo = build_memory_repository()
    ledger = build_official_data_release_ledger(repo)
    output.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    typer.echo(
        json.dumps(
            {
                "status": "completed",
                "path": str(output.relative_to(_repo_root())).replace("\\", "/"),
                "ledger_sha256": ledger["ledger_sha256"],
            },
            sort_keys=True,
        )
    )


@official_data_app.command("source-audit")
def official_data_source_audit() -> None:
    output = _repo_root() / "reports" / "official-data" / "m3b-source-review-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    official_source_ids = {
        "bls-public-data",
        "eia-open-data-v2",
        "cftc-cot-pre",
        "federal-register-api",
    }
    sources = {
        source.source_id: source
        for source in load_source_definitions()
        if source.source_id in official_source_ids
    }
    reviews = {
        review.source_id: review
        for review in load_source_reviews()
        if review.source_id in official_source_ids
    }
    validated = set(
        validate_source_review_integrity(list(sources.values()), list(reviews.values()))
    )
    rows: list[dict[str, Any]] = []
    for source_id in sorted(official_source_ids):
        source = sources[source_id]
        review = reviews[source_id]
        rows.append(
            {
                "source_id": source_id,
                "review_decision": review.review_decision,
                "enabled": source.enabled,
                "official_owner": review.official_owner,
                "official_source": review.official_source,
                "documentation_url": review.documentation_url,
                "terms_or_policy_url": review.terms_or_policy_url,
                "evidence_checked_at": review.evidence_checked_at,
                "approved_hostnames": sorted(source.approved_hostnames),
                "allowed_hostnames": sorted(review.allowed_hostnames),
                "endpoint_template": source.endpoint_template,
                "documented_endpoint_patterns": review.documented_endpoint_patterns,
                "methods": review.allowed_methods,
                "http_method": source.http_method,
                "api_version": source.dataset_profiles.get("api_version"),
                "authentication_category": review.authentication_requirement,
                "cost": review.access_cost,
                "request_limits": {
                    "max_response_bytes": source.max_response_bytes,
                    "minimum_interval_seconds": source.minimum_interval_seconds,
                    "retry_policy": {
                        "max_retries": source.retry_policy.max_retries,
                        "base_delay_seconds": source.retry_policy.base_delay_seconds,
                        "max_delay_seconds": source.retry_policy.max_delay_seconds,
                    },
                },
                "source_specific_risks": review.known_risks,
                "storage_policy": source.content_storage_policy.value,
                "revision_behavior": source.dataset_profiles.get("revision_behavior"),
                "live_smoke_status": review.live_smoke_status,
                "config_digest": source_config_digest(source),
                "review_config_sha256": review.source_config_sha256,
                "stale_review": source_config_digest(source) != review.source_config_sha256,
                "validated": source_id in validated,
            }
        )
    payload = {
        "schema_version": "m3b-source-review-audit-v1",
        "synthetic_data": True,
        "live_data_persisted": False,
        "source_count": len(rows),
        "all_disabled": all(row["enabled"] is False for row in rows),
        "all_reviews_current": all(row["stale_review"] is False for row in rows),
        "sources": rows,
    }
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    typer.echo(
        json.dumps(
            {
                "status": "completed",
                "path": str(output.relative_to(_repo_root())).replace("\\", "/"),
                "source_count": payload["source_count"],
                "all_disabled": payload["all_disabled"],
                "all_reviews_current": payload["all_reviews_current"],
            },
            sort_keys=True,
        )
    )


@official_data_app.command("export-static")
def official_data_export_static() -> None:
    output = _repo_root() / "frontend" / "public" / "demo-data"
    repo = build_memory_repository()
    persist_official_data_demo(repo)
    payload = official_data_static_payload(repo)
    for name, value in payload.items():
        (output / f"{name}.json").write_text(
            json.dumps(value, ensure_ascii=False, indent=2, default=str, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    typer.echo(json.dumps({"exported": True, "files": sorted(payload)}, sort_keys=True))


@official_data_app.command("live-smoke")
def official_data_live_smoke(
    source_id: Annotated[str, typer.Option("--source")],
    no_persist: Annotated[bool, typer.Option("--no-persist")] = False,
    confirm_live: Annotated[bool, typer.Option("--confirm-live")] = False,
) -> None:
    if not no_persist or not confirm_live:
        typer.echo(
            json.dumps(
                {
                    "status": "policy_blocked",
                    "source_id": source_id,
                    "reason": "--no-persist and --confirm-live are required",
                    "request_count": 0,
                },
                sort_keys=True,
            )
        )
        raise typer.Exit(code=4)
    typer.echo(
        json.dumps(
            {
                "status": "not_run",
                "source_id": source_id,
                "request_count": 0,
                "persistence_mode": "no_persist",
                "note": "M3B live smoke must be run manually through source-specific adapters.",
            },
            sort_keys=True,
        )
    )


@app.command()
def process() -> None:
    settings = get_settings()
    repo, session = _repository(settings)
    counts = NewsPipeline(repo, settings).process_articles()
    _commit_and_close(session)
    typer.echo(json.dumps(counts, sort_keys=True))


@app.command()
def digest(digest_date_text: Annotated[str, typer.Option("--date")]) -> None:
    digest_date = date.fromisoformat(digest_date_text)
    settings = get_settings()
    repo, session = _repository(settings)
    if settings.profile == "postgres":
        NewsPipeline(repo, settings).generate_digest(digest_date)
    item = repo.get_digest(digest_date)
    _commit_and_close(session)
    if item is None:
        raise typer.Exit(1)
    typer.echo(json.dumps(item.digest_payload, ensure_ascii=False, default=str))


@app.command()
def signals(signal_date_text: Annotated[str, typer.Option("--date")]) -> None:
    signal_date = date.fromisoformat(signal_date_text)
    settings = get_settings()
    repo, session = _repository(settings)
    if settings.profile == "postgres":
        NewsPipeline(repo, settings).generate_signals(signal_date)
    rows = [item for item in repo.list_signals() if item.signal_date == signal_date]
    _commit_and_close(session)
    typer.echo(json.dumps([row.__dict__ for row in rows], ensure_ascii=False, default=str))


@app.command("export-static")
def export_static_command(output: Annotated[Path, typer.Option("--output")]) -> None:
    repo = build_memory_repository()
    export_static(repo, output)
    typer.echo(f"exported={output}")


@app.command("evaluate-demo")
def evaluate_demo() -> None:
    repo = build_memory_repository()
    labels = json.loads((FIXTURE_DIR / "expected_labels.json").read_text(encoding="utf-8"))
    accounting = build_deduplication_accounting(repo)
    detected_dispositions = {
        observation_id: disposition
        for disposition, observation_ids in accounting.grouped_observation_ids.items()
        for observation_id in observation_ids
    }
    disposition_total = len(labels)
    disposition_matches = sum(
        1
        for observation_id, label in labels.items()
        if detected_dispositions.get(observation_id) == label.get("disposition")
    )
    event_by_article = {event.article_id: event for event in repo.list_events()}
    sentiment_by_article = {sentiment.article_id: sentiment for sentiment in repo.list_sentiments()}
    links_by_article = {link.article_id: link for link in repo.list_links()}
    company_by_id = {company.id: company for company in repo.list_companies()}
    matched = 0
    total = 0
    for raw in repo.raw_articles.values():
        label = labels.get(raw.source_article_id)
        if not label:
            continue
        if label.get("disposition") not in {"canonical", "exact_duplicate", "near_duplicate"}:
            continue
        article = repo.articles_by_hash.get(raw.normalized_content_hash)
        if (
            article is None
            or article.id not in event_by_article
            or article.id not in sentiment_by_article
        ):
            continue
        link = links_by_article.get(article.id)
        ticker = company_by_id[link.company_id].ticker if link else ""
        total += 1
        matched += int(
            event_by_article[article.id].event_type.value == label["event"]
            and sentiment_by_article[article.id].label.value == label["sentiment"]
            and ticker == label["ticker"]
        )
    typer.echo(f"synthetic_demo_matches={matched} synthetic_demo_total={total}")
    typer.echo(
        f"synthetic_disposition_matches={disposition_matches} "
        f"synthetic_disposition_total={disposition_total}"
    )
    typer.echo("deduplication_metrics=" + json.dumps(accounting.metrics, sort_keys=True))


@app.command()
def demo(profile: Annotated[str, typer.Option("--profile")] = "memory") -> None:
    settings = Settings(profile=profile)
    repo, session = _empty_repository(settings)
    pipeline = NewsPipeline(repo, settings)
    run = pipeline.run_demo(load_default_records(settings), FIXTURE_DIR / "companies.json")
    persist_cross_asset_demo(repo, build_cross_asset_demo())
    persist_official_data_demo(repo)
    if profile == "memory":
        export_static(repo, Path("../frontend/public/demo-data"))
    accounting = build_deduplication_accounting(repo)
    _commit_and_close(session)
    typer.echo(
        json.dumps(
            {
                "status": run.status.value,
                "articles": accounting.metrics["canonical_article_count"],
                "companies": len(repo.list_companies()),
                "digests": len(repo.list_digests()),
                "signals": len(repo.list_signals()),
                "counts": run.per_step_counts,
                "deduplication": accounting.metrics,
            },
            sort_keys=True,
        )
    )


def _empty_repository(settings: Settings) -> tuple[NewsRepository, Session | None]:
    if settings.profile == "postgres":
        session = create_postgres_session(settings)
        postgres_repo = PostgresNewsRepository(session)
        load_source_registry_into_repository(postgres_repo)
        return postgres_repo, session
    memory_repo = MemoryNewsRepository()
    load_source_registry_into_repository(memory_repo)
    return memory_repo, None


def _repository(settings: Settings) -> tuple[NewsRepository, Session | None]:
    if settings.profile == "postgres":
        session = create_postgres_session(settings)
        return PostgresNewsRepository(session), session
    return build_memory_repository(settings), None


def _commit_and_close(session: Session | None) -> None:
    if session is None:
        return
    session.commit()
    session.close()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


if __name__ == "__main__":
    app()
