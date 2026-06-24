# Milestone 4A Execution Plan

## Current-State Audit

FinNews is on `main` at the M3C release line, with revised M3A, M3B, and
M3C present. The repository already has a cross-asset registry, local broker
symbol-map example, `finnews-market-signal-v1`, `finnews-market-bars-v1`,
market-reaction validation, MT5 boundary documentation, read-only API/CLI/Vue
surfaces, PostgreSQL migrations through `0007_market_reaction`, and a
trading-surface audit that blocks executable MT5/order paths.

Existing MT5 behavior is boundary-only: no `MetaTrader5` import, no terminal
connection, no account access, no credentials, and no execution path. Existing
market-bar behavior validates local CSV/JSONL only and treats market-reaction
labels as research labels.

## Scope

Milestone 4A will add an optional local read-only MT5 bridge boundary for
terminal readiness, symbol metadata, and historical bar export into
`finnews-market-bars-v1`. The bridge is local CLI-only, disabled by default,
mocked in CI, and never required for API startup, test collection, frontend
builds, or static-demo generation.

## Non-Goals

M4A does not implement M4B demo execution, order sizing, order requests,
`order_check`, `order_send`, account reads, open-order reads, position reads,
history reads, credential storage, broker APIs, live internet market data,
public terminal access, schedulers, daemons, recommendations, or investment
advice.

## Official MT5 Documentation Assumptions

The official MetaTrader 5 Python integration communicates with a locally
running terminal through interprocess communication. It exposes both read
functions and trading/account functions. M4A may use only the read-only subset
and only after local CLI gates pass.

## Read-Only Function Allowlist

The optional adapter may dynamically access only:

- `initialize`
- `shutdown`
- `version`
- `last_error`
- `terminal_info`
- `symbols_total`
- `symbols_get`
- `symbol_info`
- `symbol_info_tick`
- `copy_rates_range`

## Forbidden Function List

The adapter and production code must not call or wrap `login`, `account_info`,
`orders_total`, `orders_get`, `positions_total`, `positions_get`,
`history_orders_total`, `history_orders_get`, `history_deals_total`,
`history_deals_get`, `order_calc_margin`, `order_calc_profit`, `order_check`,
`order_send`, `TRADE_ACTION`, `ORDER_TYPE`, `MqlTradeRequest`, or any trade
request/order model.

## Dynamic-Import Design

Domain and application ports will not import `MetaTrader5`. The real adapter
will dynamically import the package only inside an explicitly invoked local CLI
path after gate validation. Missing package produces a typed `not_installed`
or `package_missing` readiness state, not an import-time failure.

## Local Gating Model

Any real terminal access requires:

- `FINNEWS_ALLOW_LOCAL_MT5_READONLY=1`
- explicit `--confirm-local-terminal`
- not running in CI
- CLI-only invocation
- valid local symbol-map path
- no credentials or secret-like values in input/config/environment scan
- read-only operation
- bounded bar range
- output under ignored local export root

If any gate fails, the operation returns a typed safe failure and no terminal
access occurs.

## Symbol-Map Model

The local ignored file remains `config/integrations/mt5-symbol-map.local.yaml`.
The tracked example remains `config/integrations/mt5-symbol-map.example.yaml`.
M4A will support `profile_id`, `canonical_asset_id`, `mt5_symbol`, `enabled`,
optional `display_name`, optional `notes`, and optional local timezone display
preference. Unknown fields, credentials, account fields, terminal paths,
execution fields, sizing fields, protective levels, margins, duplicate active
symbols, conflicting active asset mappings, unknown canonical assets, and
unsupported asset classes will be rejected.

## Bar-Export Model

The CLI will export historical bars to a local ignored package under
`.finnews-mt5-readonly-exports/`. Exports will be CSV/JSONL-compatible with
`finnews-market-bars-v1`, validate OHLC and timestamp invariants, reject
duplicates, normalize historical bar volume as market-data metadata only, set
`available_at = bar_end_at + 5 minutes` by default, and keep `first_seen_at` as
the export time.

## UTC Timestamp Model

Inputs must be timezone-aware UTC datetimes. Naive timestamps and non-UTC
inputs are rejected. MT5 timestamps are normalized to UTC before contract
conversion. `from` must be strictly earlier than `to`.

## No-Account/No-Order Safety Model

No API, CLI, data model, migration, or frontend surface will accept account
credentials, account identifiers, server names, terminal paths, order fields,
position fields, or execution controls. Public readiness will always say order
execution is disabled and account access is not supported.

## API, CLI, And Frontend Plan

CLI:

- `finnews mt5 readonly status`
- `finnews mt5 readonly validate-symbol-map --path <local-file>`
- `finnews mt5 readonly export-bars ... --confirm-local-terminal`

API:

- `GET /api/v1/integrations/mt5/readonly/overview`
- `GET /api/v1/integrations/mt5/readonly/readiness`
- `GET /api/v1/integrations/mt5/readonly/symbol-map/schema`
- `GET /api/v1/integrations/mt5/readonly/runs`

Frontend/static demo will display safe readiness and local CLI-only workflow
information without connect/login/order controls and without local terminal
metadata.

## PostgreSQL Plan

Add a migration after `0007_market_reaction` for metadata-only tables:
`mt5_readonly_profiles`, `mt5_readonly_symbol_mappings`,
`mt5_readonly_runs`, and `mt5_bar_export_manifests`. The schema will use UUID
primary keys, timezone-aware timestamps, safe JSONB metadata/counts, unique
business keys, no credentials, no account/server/terminal path columns, and no
order/position/trade columns.

## Test Matrix

Tests will cover gates, symbol-map validation, fake adapter behavior, bar
export conversion, API read-only endpoints, CLI status/validation/export,
frontend/static readiness, PostgreSQL migration/schema metadata, and
execution-surface audit. CI tests remain offline and terminal-free.

## Resource Budget

No paid APIs, no model downloads, no browser binary downloads, no permanent
services, no files over 50 MB, and no tracked local exports. PostgreSQL final
verification may use one project-scoped `postgres:16` service with 512 MB and
0.50 CPU limits, localhost binding, and disposable cleanup.

## CI And Offline Plan

Default tests use fake adapters and synthetic/static data. The `MetaTrader5`
package and a local terminal are never required for CI, import, API startup, or
frontend builds. `python scripts/dev.py verify-mt5-readonly` will run offline.

## Definition Of Done

M4A is done when the read-only bridge architecture exists, real MT5 is optional
and dynamically imported only behind CLI gates, symbol maps validate, mocked
bar export writes valid `finnews-market-bars-v1`, API/frontend are read-only,
PostgreSQL metadata parity passes, execution-surface audit passes, wrappers
pass, no exports/secrets/prompts are tracked, and local commits exist.

## Deferred Work

M4B demo execution, order preflight, risk engine, reconciliation, and manual
approval are deferred. M4C live execution remains separately reviewed and is
not implemented.
