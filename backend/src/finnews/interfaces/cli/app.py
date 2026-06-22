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
from finnews.bootstrap import (
    FIXTURE_DIR,
    build_memory_repository,
    create_postgres_session,
    load_default_records,
    load_source_registry_into_repository,
)
from finnews.infrastructure.http.client import BoundedSourceHttpClient
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.persistence.postgres.repository import PostgresNewsRepository
from finnews.infrastructure.sources.fixtures import JsonlFixtureSource
from finnews.infrastructure.sources.local_feed import LocalFeedSource
from finnews.infrastructure.sources.registry import (
    SourceConfigError,
    validate_source_definitions,
)
from finnews.settings import Settings, get_settings

app = typer.Typer(help="Finnews local CLI")
ingest_app = typer.Typer(help="Ingest local synthetic data")
db_app = typer.Typer(help="Database helpers")
source_app = typer.Typer(help="Source registry and run-once ingestion")
app.add_typer(ingest_app, name="ingest")
app.add_typer(db_app, name="db")
app.add_typer(source_app, name="source")


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
    except SourceConfigError as exc:
        typer.echo(f"source_config_error={exc}", err=True)
        raise typer.Exit(4) from exc
    typer.echo(json.dumps({"valid": True, "source_ids": source_ids}, sort_keys=True))


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
        [source for source in sources if source.fetch_allowed]
        if all_approved
        else [source for source in sources if source.source_id == source_id]
    )
    if not selected:
        _commit_and_close(session)
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


if __name__ == "__main__":
    app()
