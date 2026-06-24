# finnews-market-bars-v1

`finnews-market-bars-v1` is a local-only import contract for user-owned or
properly licensed OHLCV market-bar exports.

The contract is intentionally not a live data connector. It does not describe
MT5 exports yet, does not accept broker credentials, and does not contain order,
account, position, or execution fields. A future read-only MT5 bridge may emit
this same contract after separate validation.

Tracked examples are synthetic only:

- `examples/synthetic-bars.csv`
- `examples/synthetic-bars.jsonl`

Required rows include `asset_id`, `provider_symbol`, timezone-aware
`bar_start_at`, `bar_end_at`, `first_seen_at`, `available_at`, positive OHLC,
non-negative volume, `source_profile`, `synthetic_data`, and `schema_version`.

Market-reaction labels produced from this contract are research labels, not
trade labels, and are not investment advice.
