from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import cast
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from finnews.application.services.export_static import build_static_payload
from finnews.bootstrap import build_repository
from finnews.domain.errors import NotFoundError
from finnews.infrastructure.observability.logging import configure_logging
from finnews.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    repository = build_repository(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            session = getattr(repository, "session", None)
            if session is not None:
                session.close()

    app = FastAPI(
        title="Finnews Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.repository = repository
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", str(uuid4()))
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"error": {"code": "not_found", "message": str(exc)}}
        )

    @app.exception_handler(HTTPException)
    async def http_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
        )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok", "profile": settings.profile}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        if settings.profile == "memory" and repository.list_articles():
            return {"status": "ready", "profile": settings.profile}
        if settings.profile == "memory":
            raise HTTPException(status_code=503, detail="memory repository is empty")
        if settings.profile == "postgres" and repository.list_articles():
            return {"status": "ready", "profile": settings.profile}
        raise HTTPException(status_code=503, detail=f"{settings.profile} repository is empty")

    @app.get("/api/v1/articles")
    def list_articles(
        query: str | None = None,
        source: str | None = None,
        ticker: str | None = None,
        event_type: str | None = None,
        sentiment_label: str | None = None,
        language: str | None = None,
        published_from: date | None = None,
        published_to: date | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["articles"])
        filtered: list[dict[str, object]] = []
        for row in rows:
            if query and query.lower() not in f"{row['title']} {row['summary']}".lower():
                continue
            tickers = cast(list[str], row["tickers"])
            if source and row["source_key"] != source:
                continue
            if ticker and ticker.upper() not in tickers:
                continue
            if event_type and row["event"] != event_type:
                continue
            if sentiment_label and row["sentiment"] != sentiment_label:
                continue
            if language and row["language"] != language:
                continue
            market_day = row["market_date"]
            if isinstance(market_day, str):
                market_day = date.fromisoformat(market_day)
            if not isinstance(market_day, date):
                continue
            if published_from and market_day < published_from:
                continue
            if published_to and market_day > published_to:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/articles/{article_id}")
    def get_article(article_id: UUID) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["articles"])
        for row in rows:
            if str(row["id"]) == str(article_id):
                return row
        raise NotFoundError(f"article {article_id} not found")

    @app.get("/api/v1/companies")
    def companies() -> list[dict[str, object]]:
        return cast(list[dict[str, object]], build_static_payload(repository)["companies"])

    @app.get("/api/v1/companies/{ticker}/articles")
    def company_articles(ticker: str) -> dict[str, object]:
        company = repository.get_company_by_ticker(ticker)
        if company is None:
            raise NotFoundError(f"company {ticker} not found")
        article_rows = cast(list[dict[str, object]], build_static_payload(repository)["articles"])
        rows = [row for row in article_rows if company.ticker in cast(list[str], row["tickers"])]
        company_rows = cast(list[dict[str, object]], build_static_payload(repository)["companies"])
        return {"company": company_rows, "items": rows}

    @app.get("/api/v1/events")
    def events() -> list[dict[str, object]]:
        return [
            {
                "article_id": event.article_id,
                "event_type": event.event_type.value,
                "confidence": event.confidence,
                "evidence": event.evidence,
            }
            for event in repository.list_events()
        ]

    @app.get("/api/v1/digests/{digest_date}")
    def digest(digest_date: date) -> dict[str, object]:
        item = repository.get_digest(digest_date)
        if item is None:
            raise NotFoundError(f"digest {digest_date} not found")
        return {
            "digest_date": item.digest_date,
            "timezone": item.timezone,
            "article_count": item.article_count,
            "company_count": item.company_count,
            "event_counts": item.event_counts,
            "sentiment_counts": item.sentiment_counts,
            "payload": item.digest_payload,
        }

    @app.get("/api/v1/signals/daily")
    def signals(signal_date: date | None = None) -> list[dict[str, object]]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["signals"])
        if signal_date:
            rows = [row for row in rows if row["signal_date"] == signal_date]
        return rows

    @app.get("/api/v1/pipeline-runs")
    def pipeline_runs() -> list[dict[str, object]]:
        return [
            {
                "id": run.id,
                "status": run.status.value,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "counts": run.per_step_counts,
                "timings": run.per_step_timings,
                "warnings": run.warnings,
                "errors": run.errors,
            }
            for run in repository.list_pipeline_runs()
        ]

    @app.get("/api/v1/stats/overview")
    def overview() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["overview"])

    @app.get("/api/v1/sources")
    def sources(
        source_kind: str | None = None,
        approval_status: str | None = None,
        enabled: bool | None = None,
        health: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        source_rows = cast(list[dict[str, object]], build_static_payload(repository)["sources"])
        health_rows = {
            str(row["source_id"]): row
            for row in cast(
                list[dict[str, object]], build_static_payload(repository)["source-health"]
            )
        }
        rows: list[dict[str, object]] = []
        for row in source_rows:
            source_id = str(row["source_id"])
            merged = {**row, "health": health_rows.get(source_id, {}).get("health", "disabled")}
            if source_kind and merged["source_type"] != source_kind:
                continue
            if approval_status and merged["approval_status"] != approval_status:
                continue
            if enabled is not None and merged["enabled"] is not enabled:
                continue
            if health and merged["health"] != health:
                continue
            rows.append(merged)
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/sources/{source_id}")
    def source_detail(source_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["sources"])
        for row in rows:
            if row["source_id"] == source_id:
                return row
        raise NotFoundError(f"source {source_id} not found")

    @app.get("/api/v1/sources/{source_id}/health")
    def source_health(source_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["source-health"])
        for row in rows:
            if row["source_id"] == source_id:
                return row
        raise NotFoundError(f"source {source_id} health not found")

    @app.get("/api/v1/source-reviews")
    def source_reviews(
        review_decision: str | None = None,
        live_smoke_status: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["source-reviews"])
        filtered: list[dict[str, object]] = []
        for row in rows:
            if review_decision and row["review_decision"] != review_decision:
                continue
            if live_smoke_status and row["live_smoke_status"] != live_smoke_status:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/source-reviews/{source_id}")
    def source_review_detail(source_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["source-reviews"])
        for row in rows:
            if row["source_id"] == source_id:
                return row
        raise NotFoundError(f"source review {source_id} not found")

    @app.get("/api/v1/source-fetch-attempts")
    def source_fetch_attempts(
        source_id: str | None = None,
        outcome: str | None = None,
        started_from: date | None = None,
        started_to: date | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]], build_static_payload(repository)["source-fetch-attempts"]
        )
        filtered: list[dict[str, object]] = []
        for row in rows:
            if source_id and row["source_id"] != source_id:
                continue
            if outcome and row["outcome"] != outcome:
                continue
            started = row.get("started_at")
            if isinstance(started, str):
                started_day = date.fromisoformat(started[:10])
            elif isinstance(started, datetime):
                started_day = started.date()
            elif isinstance(started, date):
                started_day = started
            else:
                started_day = None
            if started_day and started_from and started_day < started_from:
                continue
            if started_day and started_to and started_day > started_to:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/nlp/overview")
    def nlp_overview() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["nlp-overview"])

    @app.get("/api/v1/nlp/models")
    def nlp_models(
        task: str | None = None,
        provider: str | None = None,
        status: str | None = None,
        dataset_version: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["nlp-models"])
        filtered = [
            row
            for row in rows
            if (not task or row["task"] == task)
            and (not provider or row["provider"] == provider)
            and (not status or row["status"] == status)
            and (not dataset_version or row["dataset_version"] == dataset_version)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/nlp/models/{model_id}")
    def nlp_model_detail(model_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["nlp-models"])
        for row in rows:
            if row["model_id"] == model_id:
                return row
        raise NotFoundError(f"nlp model {model_id} not found")

    @app.get("/api/v1/nlp/evaluations")
    def nlp_evaluations(
        task: str | None = None,
        dataset_version: str | None = None,
        evaluation_split: str | None = None,
        language: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["nlp-evaluations"])
        filtered = []
        for row in rows:
            if task and row["task"] != task:
                continue
            if evaluation_split and row["split"] != evaluation_split:
                continue
            dataset = cast(dict[str, object], row["dataset"])
            if dataset_version and dataset.get("dataset_version") != dataset_version:
                continue
            if language:
                slices = cast(dict[str, object], row["slices"])
                language_rows = cast(list[dict[str, object]], slices.get("language", []))
                if not any(item.get("name") == language for item in language_rows):
                    continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/nlp/evaluations/{evaluation_id}")
    def nlp_evaluation_detail(evaluation_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["nlp-evaluations"])
        for row in rows:
            if row["evaluation_id"] == evaluation_id:
                return row
        raise NotFoundError(f"nlp evaluation {evaluation_id} not found")

    @app.get("/api/v1/nlp/error-analysis")
    def nlp_error_analysis(
        task: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["nlp-error-analysis"])
        filtered = [row for row in rows if not task or row["task"] == task]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    return app


app = create_app(Settings(profile="memory"))
