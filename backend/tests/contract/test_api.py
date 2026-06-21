from __future__ import annotations

from fastapi.testclient import TestClient

from finnews.interfaces.api.app import create_app
from finnews.settings import Settings


def client() -> TestClient:
    return TestClient(create_app(Settings(profile="memory")))


def test_health_endpoints_and_request_id() -> None:
    api = client()
    response = api.get("/health/live", headers={"x-request-id": "test-request"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request"
    assert api.get("/health/ready").json()["status"] == "ready"


def test_article_listing_filters_and_pagination() -> None:
    api = client()
    response = api.get("/api/v1/articles", params={"ticker": "ALP", "limit": 2})
    data = response.json()
    assert response.status_code == 200
    assert data["limit"] == 2
    assert data["total"] >= 1
    assert all("ALP" in item["tickers"] for item in data["items"])


def test_article_detail_not_found_uses_error_envelope() -> None:
    api = client()
    response = api.get("/api/v1/articles/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_companies_digest_signals_and_overview() -> None:
    api = client()
    companies = api.get("/api/v1/companies").json()
    assert len(companies) == 4
    assert api.get("/api/v1/companies/ALP/articles").status_code == 200
    assert api.get("/api/v1/digests/2026-06-20").status_code == 200
    assert api.get("/api/v1/signals/daily").json()
    overview = api.get("/api/v1/stats/overview").json()
    assert overview["synthetic"] is True
    assert overview["not_investment_advice"] is True
