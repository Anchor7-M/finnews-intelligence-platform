from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from finnews.application.services.export_static import export_static
from finnews.application.services.pipeline import NewsPipeline
from finnews.bootstrap import FIXTURE_DIR, build_memory_repository, load_default_records
from finnews.infrastructure.persistence.memory.repository import MemoryNewsRepository
from finnews.infrastructure.sources.fixtures import JsonlFixtureSource
from finnews.infrastructure.sources.local_feed import LocalFeedSource
from finnews.settings import Settings, get_settings

app = typer.Typer(help="Finnews local CLI")
ingest_app = typer.Typer(help="Ingest local synthetic data")
db_app = typer.Typer(help="Database helpers")
app.add_typer(ingest_app, name="ingest")
app.add_typer(db_app, name="db")


@app.command()
def doctor() -> None:
    settings = get_settings()
    typer.echo(f"Python profile: {settings.profile}")
    typer.echo(f"Environment: {settings.env}")
    typer.echo(f"Fixture directory exists: {FIXTURE_DIR.exists()}")
    typer.echo(f"Database URL configured: {'yes' if settings.database_url else 'no'}")


@db_app.command("upgrade")
def db_upgrade() -> None:
    typer.echo("Run Alembic upgrade with: cd backend && alembic upgrade head")


@ingest_app.command("fixture")
def ingest_fixture(path: Annotated[Path, typer.Option("--path")]) -> None:
    settings = get_settings()
    repo = MemoryNewsRepository()
    pipeline = NewsPipeline(repo, settings)
    pipeline.load_companies(FIXTURE_DIR / "companies.json")
    counts = pipeline.ingest_records(
        JsonlFixtureSource(path, settings.max_fixture_bytes).read_records()
    )
    typer.echo(json.dumps(counts, ensure_ascii=False, sort_keys=True))


@ingest_app.command("local-feed")
def ingest_local_feed(path: Annotated[Path, typer.Option("--path")]) -> None:
    settings = get_settings()
    repo = MemoryNewsRepository()
    pipeline = NewsPipeline(repo, settings)
    pipeline.load_companies(FIXTURE_DIR / "companies.json")
    counts = pipeline.ingest_records(
        LocalFeedSource(path, settings.max_fixture_bytes).read_records()
    )
    typer.echo(json.dumps(counts, ensure_ascii=False, sort_keys=True))


@app.command()
def process() -> None:
    repo = build_memory_repository()
    typer.echo(f"processed={len(repo.list_articles())}")


@app.command()
def digest(digest_date_text: Annotated[str, typer.Option("--date")]) -> None:
    digest_date = date.fromisoformat(digest_date_text)
    repo = build_memory_repository()
    item = repo.get_digest(digest_date)
    if item is None:
        raise typer.Exit(1)
    typer.echo(json.dumps(item.digest_payload, ensure_ascii=False, default=str))


@app.command()
def signals(signal_date_text: Annotated[str, typer.Option("--date")]) -> None:
    signal_date = date.fromisoformat(signal_date_text)
    repo = build_memory_repository()
    rows = [item for item in repo.list_signals() if item.signal_date == signal_date]
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


@app.command()
def demo(profile: Annotated[str, typer.Option("--profile")] = "memory") -> None:
    if profile != "memory":
        typer.echo("Only memory demo is implemented for the default offline path.")
        raise typer.Exit(1)
    settings = Settings(profile=profile)
    repo = MemoryNewsRepository()
    pipeline = NewsPipeline(repo, settings)
    run = pipeline.run_demo(load_default_records(settings), FIXTURE_DIR / "companies.json")
    export_static(repo, Path("../frontend/public/demo-data"))
    typer.echo(
        json.dumps(
            {
                "status": run.status.value,
                "articles": len(repo.list_articles()),
                "companies": len(repo.list_companies()),
                "digests": len(repo.list_digests()),
                "signals": len(repo.list_signals()),
                "counts": run.per_step_counts,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    app()
