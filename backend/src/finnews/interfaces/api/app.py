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
from finnews.application.services.market_reaction import build_market_reaction_demo
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

    @app.get("/api/v1/research/overview")
    def research_overview() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["research-overview"])

    @app.get("/api/v1/research/calendars")
    def research_calendars() -> list[dict[str, object]]:
        return cast(list[dict[str, object]], build_static_payload(repository)["research-calendars"])

    @app.get("/api/v1/research/exports")
    def research_exports(
        export_id: str | None = None,
        calendar_id: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        payload = build_static_payload(repository)
        overview = cast(dict[str, object], payload["research-overview"])
        rows = cast(list[dict[str, object]], payload["research-exports"])
        filtered = [
            row
            for row in rows
            if (not export_id or row["export_id"] == export_id)
            and (not calendar_id or overview["calendar_id"] == calendar_id)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/research/exports/{export_id}")
    def research_export_detail(export_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["research-exports"])
        for row in rows:
            if row["export_id"] == export_id:
                return row
        raise NotFoundError(f"research export {export_id} not found")

    @app.get("/api/v1/research/features")
    def research_features(
        export_id: str | None = None,
        calendar_id: str | None = None,
        session_from: date | None = None,
        session_to: date | None = None,
        ticker: str | None = None,
        company_id: str | None = None,
        window: int | None = Query(default=None, ge=1, le=60),
        has_news: bool | None = None,
        feature_schema_version: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        payload = build_static_payload(repository)
        overview = cast(dict[str, object], payload["research-overview"])
        rows = cast(list[dict[str, object]], payload["research-feature-sample"])
        filtered: list[dict[str, object]] = []
        for row in rows:
            session_date = date.fromisoformat(str(row["session_date"]))
            if export_id and overview["export_id"] != export_id:
                continue
            if calendar_id and row["calendar_id"] != calendar_id:
                continue
            if session_from and session_date < session_from:
                continue
            if session_to and session_date > session_to:
                continue
            if ticker and row["ticker"] != ticker.upper():
                continue
            if company_id and row["company_id"] != company_id:
                continue
            if window and row["window_sessions"] != window:
                continue
            if has_news is not None and row["has_news"] is not has_news:
                continue
            if feature_schema_version and row["feature_schema_version"] != feature_schema_version:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/research/lineage/{lineage_row_id}")
    def research_lineage(lineage_row_id: str) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]],
            build_static_payload(repository)["research-lineage-sample"],
        )
        for row in rows:
            if row["lineage_row_id"] == lineage_row_id:
                return row
        raise NotFoundError(f"research lineage {lineage_row_id} not found")

    @app.get("/api/v1/research/feature-catalog")
    def research_feature_catalog() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["research-feature-catalog"])

    @app.get("/api/v1/assets")
    def assets(
        asset_class: str | None = None,
        region: str | None = None,
        venue: str | None = None,
        currency: str | None = None,
        active: bool | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["assets"])
        filtered: list[dict[str, object]] = []
        for row in rows:
            if asset_class and row["asset_class"] != asset_class:
                continue
            if region and row["country_region"] != region:
                continue
            if venue and row.get("home_venue") != venue:
                continue
            if currency and currency not in {row.get("base_currency"), row.get("quote_currency")}:
                continue
            if active is not None and (row["status"] == "active") is not active:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/assets/{asset_id}")
    def asset_detail(asset_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["assets"])
        for row in rows:
            if row["asset_id"] == asset_id:
                return row
        raise NotFoundError(f"asset {asset_id} not found")

    @app.get("/api/v1/assets/{asset_id}/aliases")
    def asset_aliases(asset_id: str) -> list[dict[str, object]]:
        asset_detail(asset_id)
        rows = cast(list[dict[str, object]], build_static_payload(repository)["asset-aliases"])
        return [row for row in rows if row["asset_id"] == asset_id]

    @app.get("/api/v1/assets/{asset_id}/events")
    def asset_events(asset_id: str) -> dict[str, object]:
        asset_detail(asset_id)
        payload = build_static_payload(repository)
        impacts = [
            row
            for row in cast(list[dict[str, object]], payload["event-impacts"])
            if row["asset_id"] == asset_id
        ]
        events_by_id = {
            str(row["event_id"]): row
            for row in cast(list[dict[str, object]], payload["cross-asset-events"])
        }
        return {
            "asset_id": asset_id,
            "items": [
                {"event": events_by_id.get(str(row["event_id"])), "impact": row} for row in impacts
            ],
        }

    @app.get("/api/v1/asset-relationships")
    def asset_relationships() -> list[dict[str, object]]:
        return cast(
            list[dict[str, object]], build_static_payload(repository)["asset-relationships"]
        )

    @app.get("/api/v1/cross-asset/events")
    def cross_asset_events() -> list[dict[str, object]]:
        return cast(list[dict[str, object]], build_static_payload(repository)["cross-asset-events"])

    @app.get("/api/v1/event-impacts")
    def event_impacts(
        asset_class: str | None = None,
        event_family: str | None = None,
        direction: str | None = None,
        horizon: str | None = None,
        provider: str | None = None,
        status: str | None = None,
        active: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        payload = build_static_payload(repository)
        assets_by_id = {
            str(row["asset_id"]): row for row in cast(list[dict[str, object]], payload["assets"])
        }
        events_by_id = {
            str(row["event_id"]): row
            for row in cast(list[dict[str, object]], payload["cross-asset-events"])
        }
        rows = cast(list[dict[str, object]], payload["event-impacts"])
        filtered: list[dict[str, object]] = []
        for row in rows:
            asset = assets_by_id[str(row["asset_id"])]
            event = events_by_id[str(row["event_id"])]
            cutoff_day = date.fromisoformat(str(row["information_cutoff_at"])[:10])
            is_active = row["status"] == "active"
            if asset_class and asset["asset_class"] != asset_class:
                continue
            if event_family and event["event_family"] != event_family:
                continue
            if direction and row["direction"] != direction:
                continue
            if horizon and row["horizon"] != horizon:
                continue
            if provider and row["provider"] != provider:
                continue
            if status and row["status"] != status:
                continue
            if active is not None and is_active is not active:
                continue
            if date_from and cutoff_day < date_from:
                continue
            if date_to and cutoff_day > date_to:
                continue
            filtered.append(
                {
                    **row,
                    "asset_class": asset["asset_class"],
                    "event_family": event["event_family"],
                }
            )
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/signals")
    def market_signals(
        asset_class: str | None = None,
        direction: str | None = None,
        horizon: str | None = None,
        provider: str | None = None,
        status: str | None = None,
        active: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        payload = build_static_payload(repository)
        assets_by_id = {
            str(row["asset_id"]): row for row in cast(list[dict[str, object]], payload["assets"])
        }
        rows = cast(list[dict[str, object]], payload["market-signals"])
        filtered: list[dict[str, object]] = []
        for row in rows:
            asset = assets_by_id[str(row["asset_id"])]
            cutoff_day = date.fromisoformat(str(row["information_cutoff_at"])[:10])
            is_active = row["status"] not in {"expired", "rejected"}
            if asset_class and asset["asset_class"] != asset_class:
                continue
            if direction and row["direction"] != direction:
                continue
            if horizon and row["horizon"] != horizon:
                continue
            if provider and row["provider"] != provider:
                continue
            if status and row["status"] != status:
                continue
            if active is not None and is_active is not active:
                continue
            if date_from and cutoff_day < date_from:
                continue
            if date_to and cutoff_day > date_to:
                continue
            filtered.append({**row, "asset_class": asset["asset_class"]})
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/signals/{signal_id}")
    def market_signal_detail(signal_id: str) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["market-signals"])
        for row in rows:
            if row["signal_id"] == signal_id:
                return row
        raise NotFoundError(f"signal {signal_id} not found")

    @app.get("/api/v1/cross-asset/overview")
    def cross_asset_overview() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["cross-asset-overview"])

    @app.get("/api/v1/integrations/mt5/readiness")
    def mt5_readiness() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["mt5-readiness"])

    @app.get("/api/v1/market-reaction/overview")
    def market_reaction_overview() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["market-reaction-overview"])

    @app.get("/api/v1/market-reaction/scenarios")
    def market_reaction_scenarios() -> list[dict[str, object]]:
        return cast(
            list[dict[str, object]], build_static_payload(repository)["market-reaction-scenarios"]
        )

    @app.get("/api/v1/market-reaction/studies")
    def market_reaction_studies(
        scenario: str | None = None,
        asset_id: str | None = None,
        asset_class: str | None = None,
        event_family: str | None = None,
        horizon: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]], build_static_payload(repository)["market-reaction-studies"]
        )
        filtered: list[dict[str, object]] = []
        for row in rows:
            decision_day = date.fromisoformat(str(row["decision_time"])[:10])
            if scenario and row["synthetic_scenario_id"] != scenario:
                continue
            if asset_id and row["asset_id"] != asset_id:
                continue
            if asset_class and row["asset_class"] != asset_class:
                continue
            if event_family and row["event_family"] != event_family:
                continue
            if horizon and row["reaction_window"] != horizon:
                continue
            if date_from and decision_day < date_from:
                continue
            if date_to and decision_day > date_to:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/market-reaction/labels")
    def market_reaction_labels(
        scenario: str | None = None,
        asset_id: str | None = None,
        asset_class: str | None = None,
        event_family: str | None = None,
        direction: str | None = None,
        horizon: str | None = None,
        label: str | None = None,
        regime: str | None = None,
        provider: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]], build_static_payload(repository)["market-reaction-labels"]
        )
        filtered = [
            row
            for row in rows
            if (not scenario or row["scenario_id"] == scenario)
            and (not asset_id or row["asset_id"] == asset_id)
            and (not asset_class or row["asset_class"] == asset_class)
            and (not event_family or row["event_family"] == event_family)
            and (not direction or row["signal_direction"] == direction)
            and (not horizon or row["horizon"] == horizon)
            and (not label or row["label"] == label)
            and (not regime or row["market_state"] == regime)
            and (not provider or provider == "finnews-synthetic-market-reaction")
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/market-reaction/metrics")
    def market_reaction_metrics(
        scenario: str | None = None,
        horizon: str | None = None,
        asset_class: str | None = None,
        event_family: str | None = None,
        regime: str | None = None,
        provider: str | None = None,
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]], build_static_payload(repository)["market-reaction-metrics"]
        )
        filtered = [
            row
            for row in rows
            if (not scenario or row["scenario_id"] == scenario)
            and (not horizon or (row["slice_type"] == "horizon" and row["slice_value"] == horizon))
            and (
                not asset_class
                or (row["slice_type"] == "asset_class" and row["slice_value"] == asset_class)
            )
            and (
                not event_family
                or (row["slice_type"] == "event_family" and row["slice_value"] == event_family)
            )
            and (not regime or (row["slice_type"] == "regime" and row["slice_value"] == regime))
            and (
                not provider
                or (row["slice_type"] == "source_provider" and row["slice_value"] == provider)
            )
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/market-reaction/error-analysis")
    def market_reaction_error_analysis(
        scenario: str | None = None,
        asset_id: str | None = None,
        asset_class: str | None = None,
        event_family: str | None = None,
        horizon: str | None = None,
        regime: str | None = None,
        label: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]],
            build_static_payload(repository)["market-reaction-error-analysis"],
        )
        filtered = [
            row
            for row in rows
            if (not scenario or row["scenario_id"] == scenario)
            and (not asset_id or row["asset_id"] == asset_id)
            and (not asset_class or row["asset_class"] == asset_class)
            and (not event_family or row["event_family"] == event_family)
            and (not horizon or row["horizon"] == horizon)
            and (not regime or row["regime"] == regime)
            and (not label or row["observed_label"] == label)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/market-data/packages")
    def market_data_packages(
        scenario: str | None = None,
        provider: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]], build_static_payload(repository)["market-data-packages"]
        )
        filtered = [
            row
            for row in rows
            if (not scenario or row["scenario_id"] == scenario)
            and (not provider or row["provider"] == provider)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/market-data/bars")
    def market_data_bars(
        scenario: str | None = None,
        asset_id: str | None = None,
        asset_class: str | None = None,
        regime: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_market_reaction_demo().bars)
        filtered: list[dict[str, object]] = []
        for row in rows:
            session_day = date.fromisoformat(str(row["session_date"]))
            if scenario and row["scenario_id"] != scenario:
                continue
            if asset_id and row["asset_id"] != asset_id:
                continue
            if asset_class and row["asset_class"] != asset_class:
                continue
            if regime and row["market_state"] != regime:
                continue
            if date_from and session_day < date_from:
                continue
            if date_to and session_day > date_to:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/official-data/overview")
    def official_data_overview() -> dict[str, object]:
        return cast(dict[str, object], build_static_payload(repository)["official-data-overview"])

    @app.get("/api/v1/official-data/datasets")
    def official_data_datasets(
        source_id: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["official-datasets"])
        filtered = [row for row in rows if not source_id or row["source_id"] == source_id]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/official-data/series")
    def official_data_series(
        source_id: str | None = None,
        dataset_id: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(list[dict[str, object]], build_static_payload(repository)["official-series"])
        filtered = [
            row
            for row in rows
            if (not source_id or row["source_id"] == source_id)
            and (not dataset_id or row["dataset_id"] == dataset_id)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/official-data/observations")
    def official_data_observations(
        dataset_id: str | None = None,
        profile_id: str | None = None,
        as_of: datetime | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        payload = build_static_payload(repository)
        rows = cast(list[dict[str, object]], payload["official-observations"])
        revisions = cast(list[dict[str, object]], payload["official-observation-revisions"])
        revisions_by_key: dict[str, list[dict[str, object]]] = {}
        for revision in revisions:
            revisions_by_key.setdefault(str(revision["observation_key"]), []).append(revision)
        filtered: list[dict[str, object]] = []
        for row in rows:
            if dataset_id and row["dataset_id"] != dataset_id:
                continue
            if profile_id and row["profile_id"] != profile_id:
                continue
            if as_of:
                visible_revisions = [
                    revision
                    for revision in revisions_by_key.get(str(row["observation_key"]), [])
                    if datetime.fromisoformat(str(revision["information_available_at"])) <= as_of
                ]
                if not visible_revisions:
                    continue
                visible = sorted(
                    visible_revisions,
                    key=lambda revision: (
                        str(revision["information_available_at"]),
                        int(str(revision["revision_number"])),
                    ),
                )[-1]
                filtered.append(
                    {
                        **row,
                        "current_revision": visible["revision_number"],
                        "current_value": visible["value"],
                        "information_available_at": visible["information_available_at"],
                    }
                )
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/official-data/observations/{observation_key}/revisions")
    def official_data_observation_revisions(observation_key: str) -> list[dict[str, object]]:
        rows = cast(
            list[dict[str, object]],
            build_static_payload(repository)["official-observation-revisions"],
        )
        matches = [row for row in rows if row["observation_key"] == observation_key]
        if not matches:
            raise NotFoundError(f"official observation {observation_key} not found")
        return matches

    @app.get("/api/v1/official-data/regulatory-documents")
    def official_data_regulatory_documents(
        agency: str | None = None,
        document_type: str | None = None,
        published_from: date | None = None,
        published_to: date | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]],
            build_static_payload(repository)["official-regulatory-documents"],
        )
        filtered: list[dict[str, object]] = []
        for row in rows:
            publication_date = date.fromisoformat(str(row["publication_date"]))
            agencies = cast(list[str], row["agencies"])
            if agency and not any(agency.lower() in item.lower() for item in agencies):
                continue
            if document_type and row["document_type"] != document_type:
                continue
            if published_from and publication_date < published_from:
                continue
            if published_to and publication_date > published_to:
                continue
            filtered.append(row)
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/official-data/series-asset-associations")
    def official_data_associations(
        profile_id: str | None = None,
        asset_id: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]],
            build_static_payload(repository)["official-series-asset-associations"],
        )
        filtered = [
            row
            for row in rows
            if (not profile_id or row["profile_id"] == profile_id)
            and (not asset_id or row["asset_id"] == asset_id)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/official-data/release-events")
    def official_data_release_events(
        source_id: str | None = None,
        event_family: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        rows = cast(
            list[dict[str, object]], build_static_payload(repository)["official-release-events"]
        )
        filtered = [
            row
            for row in rows
            if (not source_id or row["source_id"] == source_id)
            and (not event_family or row["event_family"] == event_family)
        ]
        return {
            "items": filtered[offset : offset + limit],
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
        }

    return app


app = create_app(Settings(profile="memory"))
