# Market Data Import Contract

`finnews-market-bars-v1` is a local-only contract for user-owned or properly
licensed OHLCV/tick-derived bar exports. It is not a live market-data connector
and it is not a trading interface.

Required fields are `bar_id` or deterministic business key, `asset_id`,
`provider_symbol`, optional `session_date`, timezone-aware `bar_start_at` and
`bar_end_at`, `timezone`, `open`, `high`, `low`, `close`, `volume`, optional
`quote_volume`, `source_profile`, `first_seen_at`, `available_at`,
`synthetic_data`, and `schema_version`.

Validation rejects non-UTF-8 files, unknown fields, duplicate business keys,
naive timestamps, non-UTC rows, non-finite numbers, non-positive OHLC values,
OHLC inconsistencies, negative volume, missing availability, oversized files,
future-return sentinel columns, credentials, account fields, order fields,
execution fields, and live-fetch metadata.

Local user imports are private local inputs. They are not copied into tracked
paths automatically. Synthetic tracked examples live under
`contracts/finnews-market-bars/v1/examples/`.

Market-reaction labels built from this contract are research labels, not trade
labels. No live market data is downloaded by default, no orders or position
sizing are produced, and this is not investment advice.

## MT5 Read-Only Export

Milestone 4A can export locally available historical bars from a user-operated
MetaTrader 5 terminal into this contract through
`finnews mt5 readonly export-bars`. The command is CLI-only, disabled by
default, requires `FINNEWS_ALLOW_LOCAL_MT5_READONLY=1`, requires
`--confirm-local-terminal`, rejects CI, requires a validated local symbol map,
requires bounded UTC ranges, and writes only under ignored
`.finnews-mt5-readonly-exports/` paths.

The MT5 read-only bridge does not accept credentials, read account/order/
position/history data, check orders, send orders, or persist local terminal
metadata in public API/static-demo output.
