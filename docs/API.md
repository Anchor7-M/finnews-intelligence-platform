# API

Routes are read-only and mounted under `/api/v1` except health checks.

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/articles`
- `GET /api/v1/articles/{article_id}`
- `GET /api/v1/companies`
- `GET /api/v1/companies/{ticker}/articles`
- `GET /api/v1/events`
- `GET /api/v1/digests/{date}`
- `GET /api/v1/signals/daily`
- `GET /api/v1/pipeline-runs`
- `GET /api/v1/stats/overview`
- `GET /api/v1/sources`
- `GET /api/v1/source-reviews`
- `GET /api/v1/source-fetch-attempts`
- `GET /api/v1/nlp/overview`
- `GET /api/v1/nlp/models`
- `GET /api/v1/nlp/evaluations`
- `GET /api/v1/research/overview`
- `GET /api/v1/research/exports`
- `GET /api/v1/cross-asset/overview`
- `GET /api/v1/assets`
- `GET /api/v1/assets/{asset_id}`
- `GET /api/v1/assets/{asset_id}/aliases`
- `GET /api/v1/assets/{asset_id}/events`
- `GET /api/v1/asset-relationships`
- `GET /api/v1/cross-asset/events`
- `GET /api/v1/event-impacts`
- `GET /api/v1/signals`
- `GET /api/v1/signals/{signal_id}`
- `GET /api/v1/integrations/mt5/readiness`
- `GET /api/v1/market-reaction/overview`
- `GET /api/v1/market-reaction/scenarios`
- `GET /api/v1/market-reaction/studies`
- `GET /api/v1/market-reaction/labels`
- `GET /api/v1/market-reaction/metrics`
- `GET /api/v1/market-reaction/error-analysis`
- `GET /api/v1/market-data/packages`
- `GET /api/v1/market-data/bars`

Article filters: `query`, `source`, `ticker`, `event_type`, `sentiment_label`, `language`, `published_from`, `published_to`, `limit`, and `offset`.

Milestone 0 API contract tests verify all required endpoints, success responses, response shapes, filters, bounded pagination, request IDs, error envelopes, readiness behavior, and timezone-aware timestamps in the memory profile.

Revised Milestone 3A cross-asset routes are read-only. Asset, event-impact, and
signal listings support bounded pagination and deterministic synthetic data.
The MT5 readiness route reports only offline capability status; it does not
contact a terminal or expose broker/account fields.

Milestone 3C market-reaction routes are read-only. Studies, labels, metrics,
errors, and bars support bounded pagination plus scenario, asset, event-family,
horizon, label, regime, provider, and date filters where relevant. The bars
route serves deterministic local synthetic data in the memory profile and does
not fetch live prices.

Errors use:

```json
{"error": {"code": "not_found", "message": "article ... not found"}}
```
