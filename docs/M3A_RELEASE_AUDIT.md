# Milestone 3A Release Audit

Status: local implementation in progress on `feat/research-export-contract`.

Milestone 3A adds a synthetic, deterministic, point-in-time research export contract. The implementation uses only local synthetic news/company data and a synthetic A-share-style calendar. It does not fetch live calendars, announcements, prices, returns, or market data.

Expected release checks:

- Contract version `finnews-research-export-v1` `1.0.0`.
- Demo calendar: 60 synthetic sessions.
- Companies: 12 fictional companies.
- Windows: 1, 3, 5, 10 sessions.
- Dense feature rows: 2,880.
- Local exports ignored under `.finnews-research-exports/`.
- PostgreSQL verification project: `finnews_m3a_verify`.
- No push, PR, GitHub API call, real market data, or investment recommendation.
