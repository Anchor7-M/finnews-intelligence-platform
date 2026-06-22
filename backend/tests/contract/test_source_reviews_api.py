from __future__ import annotations

from fastapi.testclient import TestClient

from finnews.interfaces.api.app import create_app
from finnews.settings import Settings


def test_source_review_api_safe_fields_and_filters() -> None:
    api = TestClient(create_app(Settings(profile="memory")))
    response = api.get("/api/v1/source-reviews", headers={"x-request-id": "reviews"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "reviews"
    body = response.json()
    assert body["total"] >= 2
    ids = {item["source_id"] for item in body["items"]}
    assert "federal-reserve-press-releases" in ids
    fed = api.get("/api/v1/source-reviews/federal-reserve-press-releases").json()
    assert fed["review_decision"] == "approved"
    assert fed["enabled"] is False
    assert "documentation_url" in fed
    assert "terms_or_policy_url" in fed
    assert "FINNEWS_SEC_CONTACT" not in str(fed)
    assert "etag" not in str(fed).lower()

    filtered = api.get("/api/v1/source-reviews?review_decision=approved&limit=1")
    assert filtered.status_code == 200
    assert filtered.json()["limit"] == 1
    assert filtered.json()["items"][0]["review_decision"] == "approved"
    not_found = api.get("/api/v1/source-reviews/missing")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"
