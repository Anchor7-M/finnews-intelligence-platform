# Live Source Security

Milestone 1A implements safe ingestion infrastructure. Milestone 1B adds
source-review evidence and guarded manual smoke testing. Automated tests use
local mocks, and committed real source definitions are disabled by default.

## Controls

- Fetch URLs come from repository-owned YAML source definitions.
- Unreviewed, rejected, suspended, or disabled sources are blocked.
- HTTPS is required for live network sources.
- Approved hostnames are enforced before requests and after redirects.
- Hostnames are resolved before each request and redirect, and every returned
  IPv4 or IPv6 address must pass destination policy checks.
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
- Approved network sources require typed review evidence and config/review
  integrity checks.
- Manual smoke tests require an ignored local override,
  `FINNEWS_ALLOW_LIVE_NETWORK=1`, and `--confirm-live`.
- SEC smoke tests additionally require local-only `FINNEWS_SEC_CONTACT` and
  `FINNEWS_SEC_TEST_CIK`; these values are not printed, persisted, or committed.

## Live Smoke Tests

Live source verification is `NOT RUN` unless a source has valid review evidence,
is enabled by ignored local override, and the user explicitly authorizes a
bounded no-persist smoke test. A passing smoke test is not production readiness.

## Known Limitations

- DNS rebinding cannot be fully eliminated in Milestone 1A because the HTTP
  connection is not pinned to the pre-validated address. Mitigations are limited
  to repository-owned URLs, host allowlists, pre-request and post-redirect
  address checks, no credentials or cookies, bounded response size, and no
  arbitrary URL input.
