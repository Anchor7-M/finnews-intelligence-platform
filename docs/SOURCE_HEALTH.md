# Source Health

Milestone 1A stores one fetch state per source and append-only fetch attempts.

Fetch state tracks:

- ETag and Last-Modified availability
- cursor/checkpoint
- last attempted and successful timestamps
- next allowed timestamp
- last HTTP status
- last response hash and byte count
- last item count
- consecutive failure count
- sanitized error category and summary
- health status
- adapter version

Health is exposed through:

```text
GET /api/v1/sources
GET /api/v1/sources/{source_id}/health
GET /api/v1/source-fetch-attempts
finnews source health
```

The Vue Source Health page displays validator availability as booleans and never
shows raw ETag, Last-Modified, response body, local file path, secret, or stack
trace values.
