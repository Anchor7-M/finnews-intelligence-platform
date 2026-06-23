# Roadmap

FinNews is a local-first cross-asset financial information and event-intelligence platform. It is not primarily an A-share research-data producer. The previous A-share export remains an optional downstream adapter.

## Completed Foundations

### Milestone 0

Implemented: deterministic synthetic news ingestion, normalization, deduplication, provenance, fictional company linking, event and sentiment baselines, memory profile, PostgreSQL adapter, FastAPI, Typer CLI, Vue dashboard, static demo, CI files, and verification tooling.

### Milestone 1A

Implemented: safe source registry, bounded HTTP client, disabled-by-default source definitions, mocked source adapters, conditional request state, retries, source health, API/CLI/static/frontend surfaces, and offline verification.

### Milestone 1B

Implemented: source-review evidence, disabled Federal Reserve RSS and SEC EDGAR pilot configs, local-only overrides, guarded smoke-test command, review API/frontend visibility, and source-boundary documentation.

### Milestone 2A

Implemented: synthetic bilingual NLP benchmark, leakage-safe splits, deterministic baselines, scikit-learn evaluation, calibration, abstention, error analysis, model registry metadata, API/CLI/static/frontend surfaces, and release audit documentation.

### Milestone 3A

Implemented as an optional integration: point-in-time synthetic A-share-style research export contract, calendar, dense rolling news-factor panel, safe lineage, leakage audit, API/CLI/static/frontend surfaces, and PostgreSQL metadata. It does not include official calendars, prices, returns, backtests, portfolios, or recommendations.

### Revised Milestone 3A

Implemented in this branch: cross-asset product repositioning, canonical asset registry, provider and broker symbol aliases, event-to-asset impact hypotheses, point-in-time research signal candidates, versioned local market-signal contract, MT5 readiness checks, API/CLI/static/frontend surfaces, and PostgreSQL metadata.

This milestone does not connect to MT5, accept credentials, read account data, or execute trades.

## Revised Future Roadmap

### Milestone 3B

Cross-asset official-source expansion for macroeconomic releases, energy and commodity information, derivatives and positioning metadata, crypto regulation and exchange-status information, issuer communications, and central-bank communications. Every source remains subject to terms review, rate limits, provenance controls, copyright policy, and disabled-by-default configuration.

### Milestone 3C

Signal research and validation: event-study methodology, market-reaction labels from user-owned or properly licensed data, walk-forward evaluation, false-positive analysis, asset-class slices, regime slices, confidence, and coverage. No automatic execution.

### Milestone 4A

MT5 read-only local bridge, as a separate future milestone: local terminal connection, terminal/account/symbol metadata reads, canonical asset to local broker-symbol mapping, UTC tick/bar normalization, demo environment first, no credentials stored in FinNews, and no trading commands.

### Milestone 4B

MT5 demo execution, only after read-only validation: demo account, manual approval, strict risk engine, idempotent requests, stale-signal rejection, preflight checks, kill switch, reconciliation, and full audit trail.

### Milestone 4C

Optional live execution is explicitly deferred. It may be considered only after prolonged demo validation, separate security and risk audit, applicable legal/broker/jurisdiction eligibility, and independent opt-in configuration.
