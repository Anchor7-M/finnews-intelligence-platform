# MT5 Read-Only Bridge

Milestone 4A adds a local, optional, read-only MetaTrader 5 bridge boundary.
It exists to let a user export historical bars from their own local terminal
into `finnews-market-bars-v1` for research workflows.

## Boundary

- `MetaTrader5` is not a required dependency.
- The package is dynamically imported only inside gated local CLI commands.
- FastAPI, Vue, static demo, and CI never initialize a terminal.
- Public readiness output is synthetic/safe and does not expose local symbol-map
  contents, terminal metadata, account data, paths, or broker details.
- Local exports are written under ignored `.finnews-mt5-readonly-exports/`.

## Allowed M4A Functions

The optional adapter may use only read-oriented package/session, terminal,
symbol, tick, and bar functions:

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

## Forbidden Surface

M4A does not implement or wrap account, order, position, history, margin/profit,
or execution functions. It does not accept credentials, terminal paths, account
numbers, order requests, position identifiers, trade sizing, stop loss, take
profit, or execution flags.

## Bar Export

`finnews mt5 readonly export-bars` validates all gates, reads enabled symbol-map
entries, fetches bounded historical bars, normalizes timestamps to UTC, validates
OHLC and duplicate timestamps, and writes `bars.jsonl` plus `manifest.json` in
the market-bars contract shape.

`available_at` is deterministic: bar end time plus a default five-minute export
latency. Tests use a fixed export time for byte-stable output.

This is research tooling and not investment advice.
