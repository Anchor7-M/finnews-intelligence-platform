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
finnews source review list
finnews source review validate
```

The Vue Source Health page displays validator availability as booleans and never
shows raw ETag, Last-Modified, response body, local file path, secret, or stack
trace values.

Milestone 1B extends the page into a Source Catalog by showing safe review
metadata such as official owner, engineering-review decision, access cost,
authentication category, live-smoke status, and limitations. It does not expose
personal contact metadata, raw User-Agent values, local override contents, raw
headers, or live response text.
