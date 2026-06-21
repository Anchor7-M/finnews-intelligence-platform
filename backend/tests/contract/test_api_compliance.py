from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from finnews.interfaces.api.app import create_app
from finnews.settings import Settings


def client() -> TestClient:
    return TestClient(create_app(Settings(profile="memory")))


def test_all_required_read_endpoints_success_and_no_write_ingestion_endpoint() -> None:
    api = client()
    article = api.get("/api/v1/articles").json()["items"][0]
    endpoints = [
        "/health/live",
        "/health/ready",
        "/api/v1/articles",
        f"/api/v1/articles/{article['id']}",
        "/api/v1/companies",
        "/api/v1/companies/ALP/articles",
        "/api/v1/events",
        "/api/v1/digests/2026-06-18",
        "/api/v1/signals/daily",
        "/api/v1/pipeline-runs",
        "/api/v1/stats/overview",
    ]
    for endpoint in endpoints:
        assert api.get(endpoint).status_code == 200
    assert api.post("/api/v1/articles").status_code == 405


def test_article_filters_pagination_errors_and_timezone_timestamps() -> None:
    api = client()
    assert api.get("/api/v1/articles", params={"query": "earnings"}).json()["total"] >= 1
    assert (
        api.get("/api/v1/articles", params={"source": "synthetic-jsonl-desk"}).json()["total"] >= 1
    )
    assert api.get("/api/v1/articles", params={"ticker": "ALP"}).json()["total"] >= 1
    assert api.get("/api/v1/articles", params={"event_type": "earnings"}).json()["total"] >= 1
    assert api.get("/api/v1/articles", params={"sentiment_label": "positive"}).json()["total"] >= 1
    assert api.get("/api/v1/articles", params={"language": "zh"}).json()["total"] >= 1
    ranged = api.get(
        "/api/v1/articles",
        params={"published_from": "2026-06-18", "published_to": "2026-06-19", "limit": 5},
    ).json()
    assert ranged["limit"] == 5
    assert ranged["total"] >= 1
    assert api.get("/api/v1/articles", params={"limit": 101}).status_code == 422
    first = api.get("/api/v1/articles", params={"limit": 1}).json()["items"][0]
    assert datetime.fromisoformat(first["published_at"]).tzinfo is not None


def test_error_envelope_request_id_and_not_found_cases() -> None:
    api = client()
    response = api.get(
        "/api/v1/articles/00000000-0000-0000-0000-000000000000", headers={"x-request-id": "audit"}
    )
    assert response.status_code == 404
    assert response.headers["x-request-id"] == "audit"
    assert response.json()["error"]["code"] == "not_found"
    digest = api.get("/api/v1/digests/2030-01-01")
    assert digest.status_code == 404
    assert digest.json()["error"]["code"] == "not_found"


def test_response_shapes_for_companies_events_signals_pipeline_and_overview() -> None:
    api = client()
    company = api.get("/api/v1/companies").json()[0]
    event = api.get("/api/v1/events").json()[0]
    signal = api.get("/api/v1/signals/daily").json()[0]
    run = api.get("/api/v1/pipeline-runs").json()[0]
    overview = api.get("/api/v1/stats/overview").json()
    assert {"ticker", "legal_name", "short_name", "sector"}.issubset(company)
    assert {"article_id", "event_type", "confidence", "evidence"}.issubset(event)
    assert {"signal_date", "ticker", "weighted_sentiment_score", "schema_version"}.issubset(signal)
    assert {"status", "counts", "timings"}.issubset(run)
    assert overview["synthetic"] is True
    assert overview["not_investment_advice"] is True
