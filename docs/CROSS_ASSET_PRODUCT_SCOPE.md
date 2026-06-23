# Cross-Asset Product Scope

FinNews is a cross-asset financial information and event-intelligence platform.

## Primary Scope

- U.S. equities and ETFs.
- U.S. equity indices.
- Foreign exchange.
- Gold and other precious metals.
- Energy and commodity markets.
- Futures roots and contracts.
- Crypto assets.
- Macroeconomic indicators, central-bank policy, rates, and regulation.

The platform stores metadata, provenance, hashes, synthetic fixtures, and derived research features. It does not store copied article bodies.

## Current Revised Milestone 3A Surface

- 40 synthetic canonical assets.
- 211 aliases across canonical, news-source, research, provider, and local broker namespaces.
- 100 synthetic cross-asset events.
- 240 event-to-asset impact hypotheses.
- 80 research signal candidates.
- `finnews-market-signal-v1` local package contract.
- Read-only API, CLI, Vue, static demo, and PostgreSQL persistence.

## Optional Integrations

The A-share research export is retained as an optional downstream adapter. It must not define the homepage, primary architecture, main navigation, or future roadmap.

## Explicit Non-Goals

- No live prices or official market data.
- No automatic execution.
- No broker credentials.
- No account access.
- No recommendations, portfolios, backtests, or investment advice.
