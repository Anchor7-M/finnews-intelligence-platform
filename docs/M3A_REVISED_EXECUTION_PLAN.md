# Revised Milestone 3A Execution Plan

## Current-State Audit

The branch `feat/cross-asset-mt5-foundation` was created from updated `main` at
`b75a156 Complete Milestone 3A release audit`. The previous A-share-style
research export milestone is merged into `main`.

Current positioning that needs correction:

- `README.md` still opens with a generic financial-news demo statement and then
  highlights the A-share-style research export as Milestone 3A.
- `docs/ROADMAP.md` treats the A-share export as Milestone 3A rather than an
  optional integration.
- `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/DEVELOPMENT.md`,
  `docs/COST_AND_RESOURCE_GUARDRAILS.md`, and `docs/THREAT_MODEL.md` describe
  research export as the current primary Milestone 3A concern.
- Frontend navigation exposes `Research Export` as a primary top-level item.
- Static demo data includes the research export package as a first-class demo
  surface.

The existing A-share implementation is useful and should remain intact, but it
must be reclassified as:

`Optional Research Integration: A-share point-in-time feature export`

## Corrected Product Statement

FinNews Intelligence Platform is a local-first cross-asset financial
information and event-intelligence platform for U.S. equities, ETFs, indices,
FX, gold, commodities, futures, crypto assets, and macroeconomic policy.

The platform transforms source-attributed financial information into normalized
events, asset associations, impact hypotheses, point-in-time research signal
candidates, timelines, and cross-asset monitoring views. It does not provide
investment advice, guarantee causal market impact, place orders, manage a
brokerage account, or operate as a live trading system.

## Target Asset Classes

- `us_equity`
- `etf`
- `equity_index`
- `fx`
- `precious_metal`
- `commodity`
- `futures_root`
- `futures_contract`
- `crypto_asset`
- `macro_indicator`
- `interest_rate`

The deterministic demo fixture will contain exactly 40 synthetic assets with
the requested per-class counts.

## Domain Model

Add framework-free domain entities and enums for assets, aliases, provider and
broker symbol mappings, asset relationships, cross-asset events, impact
hypotheses, market signal candidates, signal publication runs, and MT5 readiness
reports. Keep SQLAlchemy, FastAPI, Typer, and settings outside the domain layer.

## Migration Plan

Add Alembic migration `0005_cross_asset_signal_foundation` with tables for:

- assets;
- asset aliases;
- provider/broker mappings;
- asset relationships;
- cross-asset events;
- asset impact hypotheses;
- market signal candidates;
- signal publication runs.

Tables must use UUID keys, timezone-aware timestamps, JSONB only in PostgreSQL
adapters, uniqueness/idempotency constraints, useful indexes, synthetic flags,
and no credential/account/order fields.

## Signal Contract Plan

Create `contracts/finnews-market-signal/v1/` at semantic version `1.0.0`. The
contract will include README, JSON Schemas, feature catalog, deterministic
synthetic example package, manifest/file hashes, and validation that rejects
execution, credential, account, and position-size fields.

Generated local exports will go only under ignored `.finnews-market-signals/`.

## MT5 Integration Boundary

This milestone implements documentation, schema validation, readiness reporting,
and symbol-map validation only. It will not import `MetaTrader5`, connect to a
terminal, accept credentials, query account data, call `initialize`, `login`,
`order_check`, `order_send`, or create executable order requests.

Future architecture documentation will preserve official MT5 facts:

- the Python package communicates with a local MT5 terminal through IPC;
- `initialize()` establishes the terminal connection;
- market, symbol, order, position, and history information are exposed through
  the Python integration;
- `order_check()` validates a request and funding sufficiency, but a successful
  check does not guarantee execution;
- `order_send()` submits a request to the trade server;
- tick/bar timestamps are UTC and require explicit normalization.

## No-Trading Safety Model

The repository must expose no public trade/order endpoint and no CLI command
equivalent to connect/login/buy/sell/close/order. Signal candidates are research
metadata only. Documentation must use association/hypothesis language and avoid
investment recommendations.

`config/integrations/mt5-symbol-map.example.yaml` will contain synthetic,
disabled examples. `config/integrations/mt5-symbol-map.local.yaml` will be
ignored and validated offline for a narrow allowlist of safe fields.

## Frontend Plan

Reposition primary navigation around:

- overview;
- cross-asset overview;
- assets;
- event impacts;
- signal candidates;
- integration readiness;
- methodology;
- optional integrations.

The existing A-share research export page will move under optional integrations
without deleting its code or data.

## Test Plan

Add offline tests for:

- corrected positioning;
- exact asset fixture counts and stable IDs;
- alias uniqueness, ambiguity, inactive aliases, and provider namespaces;
- MT5 local symbol-map validation and forbidden fields;
- event-family mapping and backward compatibility;
- baseline impact rules and contradiction/stale/idempotency behavior;
- market-signal contract validation and deterministic repeated export;
- read-only API endpoints and forbidden trading routes;
- CLI commands and forbidden MT5 commands;
- frontend navigation/readiness/disclaimer behavior;
- PostgreSQL migration and memory/PostgreSQL parity;
- trading-surface audit.

Maintain at least 80% backend coverage.

## Resource Budget

All automated tests remain offline, CPU-only, and sequential. No paid APIs,
live prices, model downloads, browser binaries, schedulers, queues, or new
infrastructure services will be added. Optional PostgreSQL verification may use
one project-scoped `postgres:16` service with Compose project
`finnews_m3r_verify`, localhost binding, 512 MB memory, and 0.50 CPU, then clean
all task-owned resources.

## Definition Of Done

- Product positioning is corrected across docs, API/static/frontend surfaces.
- Exactly 40 assets, 100 events, 240 impact hypotheses, and 80 signal
  candidates are generated deterministically.
- Signal contract `finnews-market-signal-v1` `1.0.0` validates and exports
  offline with stable hashes.
- MT5 readiness reports terminal connection not implemented and execution
  disabled.
- No MT5 package, credentials, account data, order fields, or trading endpoints
  exist.
- API/CLI/frontend/static demo expose cross-asset intelligence as the primary
  product.
- A-share export remains optional.
- Verification commands pass or failures are reported precisely.

## Deferred Milestones

- Milestone 3B: broader official-source reviews for macro, commodities,
  derivatives, crypto, issuers, and central banks.
- Milestone 3C: event-study methodology with user-owned/licensed market data
  and walk-forward validation.
- Milestone 4A: read-only local MT5 bridge.
- Milestone 4B: demo execution only after risk-engine/manual-approval gates.
- Milestone 4C: optional live execution only after separate security, legal,
  broker, and risk audits.
