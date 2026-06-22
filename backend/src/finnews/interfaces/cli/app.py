from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from finnews.application.ports.repositories import NewsRepository
from finnews.application.services.deduplication_accounting import build_deduplication_accounting
from finnews.application.services.export_static import export_static
from finnews.application.services.pipeline import NewsPipeline
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
    validate_source_definitions,
)
from finnews.infrastructure.sources.reviews import (
    SourceReviewError,
    load_source_reviews,
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
app.add_typer(ingest_app, name="ingest")
app.add_typer(db_app, name="db")
app.add_typer(source_app, name="source")
source_app.add_typer(source_review_app, name="review")
app.add_typer(nlp_app, name="nlp")
nlp_app.add_typer(nlp_dataset_app, name="dataset")


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
