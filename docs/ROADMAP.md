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

### Milestone 3B

Implemented: cross-asset official-source expansion for macroeconomic releases,
energy and commodity information, derivatives and positioning metadata, crypto
regulation and exchange-status information, issuer communications, and
central-bank communications. It added source reviews, synthetic point-in-time
official observations, revisions, release events, regulatory metadata,
asset-series associations, API/CLI/static/frontend surfaces, and PostgreSQL
metadata. Every real source remains subject to terms review, rate limits,
provenance controls, copyright policy, and disabled-by-default configuration.

### Milestone 3C

Implemented: offline signal research and validation with a versioned local
market-bar import contract, deterministic synthetic market scenarios,
point-in-time event studies, abnormal-return labels, signal-quality metrics,
false-positive/false-negative analysis, asset-class slices, regime slices,
confidence buckets, coverage, leakage diagnostics, API/CLI/static/frontend
surfaces, and PostgreSQL metadata. No live prices, broker APIs, account access,
positions, or recommendations are included.

### Milestone 4A

Implemented: optional local MT5 read-only bridge boundary, dynamic package
import only behind explicit local CLI gates, symbol-map validation, bounded UTC
historical bar export into `finnews-market-bars-v1`, read-only readiness
API/CLI/static/frontend surfaces, PostgreSQL metadata tables, and
execution-surface audit coverage.

This milestone does not read account data, read orders, read positions, read
trading history, check orders, send orders, store credentials, launch a
terminal, or provide investment advice.

## Revised Future Roadmap

### Milestone 4B

MT5 demo execution, only after read-only validation: demo account, manual approval, strict risk engine, idempotent requests, stale-signal rejection, preflight checks, kill switch, reconciliation, and full audit trail.

### Milestone 4C

Optional live execution is explicitly deferred. It may be considered only after prolonged demo validation, separate security and risk audit, applicable legal/broker/jurisdiction eligibility, and independent opt-in configuration.
