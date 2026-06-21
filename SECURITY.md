# Security Policy

This is a local-first portfolio project. Milestone 0 uses synthetic fixtures only and has no public write API.

## Threats Covered

- Untrusted source metadata and malformed JSON/XML.
- Malicious URLs and tracking parameters.
- Oversized input files.
- Log injection through source-provided text.
- HTML/script content in titles or snippets.
- Accidental secret commits.
- Path traversal in import/export commands.
- SQL injection risks, mitigated through SQLAlchemy parameterization.
- Future SSRF risks in network adapters.
- Copyright and provenance risks.

## Reporting

Do not include secrets or proprietary article text in reports. Open a private issue or contact the maintainer before sharing sensitive details publicly.
