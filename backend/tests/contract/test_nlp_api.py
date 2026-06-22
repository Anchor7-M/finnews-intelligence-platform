from __future__ import annotations

from fastapi.testclient import TestClient

from finnews.interfaces.api.app import create_app
from finnews.settings import Settings


def test_nlp_api_read_only_safe_metadata_and_filters() -> None:
    api = TestClient(create_app(Settings(profile="memory")))

    overview = api.get("/api/v1/nlp/overview", headers={"x-request-id": "nlp"})
    assert overview.status_code == 200
    assert overview.headers["x-request-id"] == "nlp"
    body = overview.json()
    assert body["record_count"] == 1296
    assert body["dataset"]["synthetic_only"] is True
    assert "not real-world accuracy" in body["benchmark_claim"]

    models = api.get("/api/v1/nlp/models", params={"task": "event"}).json()
    assert models["total"] == 1
    model = models["items"][0]
    assert model["task"] == "event"
    assert "artifact_uri" not in model
    assert "C:\\Users" not in str(model)
    detail = api.get(f"/api/v1/nlp/models/{model['model_id']}").json()
    assert detail["model_id"] == model["model_id"]

    evaluations = api.get("/api/v1/nlp/evaluations", params={"language": "zh"}).json()
    assert evaluations["total"] >= 1
    evaluation_id = evaluations["items"][0]["evaluation_id"]
    assert api.get(f"/api/v1/nlp/evaluations/{evaluation_id}").status_code == 200
    errors = api.get("/api/v1/nlp/error-analysis", params={"task": "sentiment"}).json()
    assert errors["total"] == 1
    assert api.get("/api/v1/nlp/models/missing-model").status_code == 404
    assert api.post("/api/v1/nlp/infer").status_code in {404, 405}
    assert api.post("/api/v1/nlp/models").status_code == 405
