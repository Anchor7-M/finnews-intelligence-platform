# Threat Model

## Risks

- Untrusted metadata in local imports.
- Malicious URLs and tracking parameters.
- Oversized files.
- Malformed XML/JSON.
- Log injection.
- HTML/script text in titles or snippets.
- Dependency supply-chain issues.
- Secret commits.
- Path traversal in CLI import/export.
- SQL injection.
- Future SSRF from live adapters.
- Live-source SSRF, redirect, oversized response, unsafe XML, and response-body leakage.
- Stale or missing source-review evidence.
- Accidental commit of local live-source override, smoke report, or personal SEC contact.
- Browser-side live-source fetches.
- Copyright and provenance mistakes.

## Mitigations

- File-size checks for fixture inputs.
- Absolute HTTP(S) URL validation and tracking-parameter removal.
- XML parsed from local fixtures only.
- Vue template escaping.
- SQLAlchemy parameterization.
- `.env` ignored and `.env.example` safe.
- No full article bodies stored in Milestone 0.
- Deterministic malformed fixture records verify invalid URL, language, timestamp, missing title, and malformed JSONL handling.
- Milestone 1A validates approved hostnames, enforces HTTPS for live sources,
  blocks private/loopback/link-local/multicast/unspecified IP destinations,
  revalidates redirects, caps decompressed responses, rejects DTD/entity XML,
  persists only validators/metadata/snippets, and exposes no public mutation or
  arbitrary URL fetch API.
- Milestone 1B requires typed source-review evidence, source config digests,
  ignored local overrides, explicit live env and confirmation gates, no-persist
  smoke-test defaults, SEC contact redaction, and read-only API review
  summaries.
