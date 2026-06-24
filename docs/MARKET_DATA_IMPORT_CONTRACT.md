# Market Data Import Contract

`finnews-market-bars-v1` is a local-only contract for user-owned or properly
licensed OHLCV/tick-derived bar exports. It is not a live market-data connector
and it does not define an MT5 export format yet.

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
labels. No live market data is downloaded, no MT5 connection is made, no orders
or position sizing are produced, and this is not investment advice.
