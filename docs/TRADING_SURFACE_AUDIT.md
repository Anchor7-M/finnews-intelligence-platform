# Trading Surface Audit

Milestone 4A adds an optional local MT5 read-only bridge. It still does not
implement account access, order checking, order sending, position management,
trade history reading, or execution.

## Commands

- `python scripts/dev.py verify-cross-asset`
- `python scripts/dev.py verify-mt5-readonly`
- `git diff --check`
- `docker compose -p finnews_m4a_verify ps`

The detailed machine-readable report is `reports/cross-asset/revised-m3a-trading-surface-audit.json`.

## Search Scope

Tracked source, configuration, contracts, workflows, CLI, API, frontend, docs, and dependency files were scanned for:

`MetaTrader5`, `metatrader5`, `initialize(`, `login(`, `order_check(`,
`order_send(`, `TRADE_ACTION`, `ORDER_TYPE`, `account_info(`,
`positions_get(`, `orders_get(`, `history_deals_get(`,
`history_orders_get(`, `order_calc_margin(`, `order_calc_profit(`,
`copy_rates_range(`, `symbol_info`, `symbols_get`, `terminal_info(`,
`lot`, `volume`, `stop_loss`, `take_profit`, `buy`, `sell`, `execute`.

## Result

| Metric | Value |
| --- | ---: |
| Matched files | 49 |
| Matched pattern instances | 871 |
| Forbidden production matches | 0 |
| `MetaTrader5` dependency declarations | 0 |
| Normal-import `MetaTrader5` usage | 0 |
| Terminal/contact/order routes | 0 |
| Account credential models | 0 |
| Public trading endpoints/commands/UI controls | 0 |

No dependency-file matches are present.

Generated evidence exclusions are exact-path only:

- `reports/cross-asset/revised-m3a-trading-surface-audit.json`
- `reports/verification/revised-m3a-timings.json`
- `reports/market-reaction/m3c-release-ledger.json`
- `reports/market-reaction/m3c-scenario-audit.json`
- `reports/market-reaction/m3c-point-in-time-audit.json`

These files are excluded so generated evidence does not scan its own prior output or other generated evidence artifacts. The audit does not broadly allow `reports/`.

## Classifications

Permitted matches are limited to architecture documentation, future-risk
documentation, schema-denylist fields, static safety notices, tests proving
rejection of execution-like fields, market-bar `volume` fields, and the isolated
MT5 read-only adapter allowlist.

Forbidden production categories all returned zero:

- required MT5 dependency declarations or normal application imports;
- subprocess, COM, terminal launch, or terminal path;
- credential, login, account, order, position, or execution models;
- mutation route or CLI command for connect/login/buy/sell/trade/order/position;
- UI button or static-demo data that can execute or imply execution.

Allowed M4A adapter functions are limited to local read-only package/session,
terminal status, symbol metadata, and historical-bar calls such as
`initialize(`, `terminal_info(`, `symbol_info`, `symbols_get`, and
`copy_rates_range(`. The audit continues to fail on `login(`, `account_info(`,
`orders_get(`, `positions_get(`, `history_orders_get(`,
`history_deals_get(`, `order_calc_margin(`, `order_calc_profit(`,
`order_check(`, and `order_send(` in production paths.

## Status

PASS. Signal candidates are hypotheses for local research. They are not orders, not recommendations, and not executable instructions.
