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
- Copyright and provenance mistakes.

## Mitigations

- File-size checks for fixture inputs.
- Absolute HTTP(S) URL validation and tracking-parameter removal.
- XML parsed from local fixtures only.
- Vue template escaping.
- SQLAlchemy parameterization.
- `.env` ignored and `.env.example` safe.
- No full article bodies stored in Milestone 0.
