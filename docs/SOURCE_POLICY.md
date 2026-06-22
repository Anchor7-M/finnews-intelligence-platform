# Source Policy

Milestone 0 uses local synthetic fixtures. Milestone 1A adds live-source
ingestion infrastructure, but no real source is enabled by default and automated
tests use local mocks only.

Implemented local adapters:

- JSONL fixture adapter with file-size checks and malformed JSONL reporting.
- Local RSS and Atom fixture parser with no network calls.

Future priority:

1. User-supplied JSON/CSV exports.
2. Publisher RSS/Atom feeds after terms review.
3. Official exchange, regulator, or company announcement feeds/APIs after terms review.
4. No-key public research metadata sources when terms and limits permit use.

Source configs must include source ID, display name, kind, base URL or import
format, approved hostnames, terms URL, documentation URL when applicable,
review status, enabled flag defaulting false, content-storage policy, timeout,
maximum response size, bounded retries, rate limit, user agent, field mapping,
and provenance requirements.

Only `approved` and `enabled` sources can be fetched. Unreviewed, rejected, and
suspended sources are listed but blocked. Runtime fetch URLs derive from
repository-owned configuration; the API exposes no public fetch, approve,
enable, reset, or arbitrary URL endpoint.

Do not implement paywall bypass, login/CAPTCHA bypass, search-result scraping, undocumented endpoints, aggressive crawling, full-text republication, paid News API plans, or paid model APIs.

The default storage policy retains title, URL, timestamps, source-provided snippet/summary, provenance, hashes, and derived features rather than copied article bodies.
