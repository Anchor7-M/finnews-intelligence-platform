# Live Source Security

Milestone 1A implements safe ingestion infrastructure only. Automated tests use
local mocks, and the committed example sources are disabled by default.

## Controls

- Fetch URLs come from repository-owned YAML source definitions.
- Unreviewed, rejected, suspended, or disabled sources are blocked.
- HTTPS is required for live network sources.
- Approved hostnames are enforced before requests and after redirects.
- Loopback, private, link-local, multicast, and unspecified IP destinations are
  blocked in live mode.
- Maximum redirects: 3.
- Default maximum decompressed response size: 2 MB; Milestone 1A ceiling: 5 MB.
- Content type is validated before parsing.
- XML with DTD or entity declarations is rejected.
- Cookies are not persisted, browser automation is not used, JavaScript is not
  executed, and authentication/login support is out of scope.
- Raw response bodies and stack traces are not exposed through API, CLI, logs, or
  persisted user-facing fields.

## Live Smoke Tests

Live source verification is `NOT RUN` unless a source has explicit approval
metadata and the user separately authorizes a smoke test. Real source selection
and terms evidence are deferred to Milestone 1B.
