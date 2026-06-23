# FinNews Market Signal Contract v1

Contract name: `finnews-market-signal-v1`

Semantic version: `1.0.0`

This contract exports deterministic synthetic cross-asset research signal
candidates. Signal candidates are information products, not orders, position
sizes, account instructions, or investment advice.

Required package files:

- `manifest.json`
- `assets.json`
- `event_impacts.jsonl`
- `signals.jsonl`

The package is UTF-8, sorted deterministically, and contains only synthetic
metadata. It does not include live prices, account data, credentials, MT5
terminal paths, order types, volume, stop loss, take profit, tickets, or
position data.

Future MT5 work must consume this contract through a separate local bridge with
manual approval, risk checks, and demo-account validation first.
