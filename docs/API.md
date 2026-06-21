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

Article filters: `query`, `source`, `ticker`, `event_type`, `sentiment_label`, `language`, `published_from`, `published_to`, `limit`, and `offset`.

Milestone 0 API contract tests verify all required endpoints, success responses, response shapes, filters, bounded pagination, request IDs, error envelopes, readiness behavior, and timezone-aware timestamps in the memory profile.

Errors use:

```json
{"error": {"code": "not_found", "message": "article ... not found"}}
```
