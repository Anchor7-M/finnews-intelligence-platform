# MT5 Read-Only Surface Audit

Milestone 4A updates the trading-surface audit from "no MT5 strings anywhere"
to a narrower rule:

- `MetaTrader5` and read-only terminal/bar functions are allowed only in the
  optional read-only adapter, docs, and tests.
- Account, order, position, history, margin/profit, order-check, and order-send
  functions remain forbidden in production paths.
- API, frontend, and static demo surfaces are status-only and cannot trigger
  terminal access.

## Current Report

Machine-readable evidence:
`reports/cross-asset/revised-m3a-trading-surface-audit.json`.

Current status:

- Status: PASS
- Forbidden production matches: 0
- Matched files: 49
- Matched pattern instances: 870
- Dependency matches: 0
- Required `MetaTrader5` dependency: absent

## Explicit Exclusions

The audit excludes exact generated evidence paths only:

- `reports/cross-asset/revised-m3a-trading-surface-audit.json`
- `reports/verification/revised-m3a-timings.json`
- `reports/market-reaction/m3c-release-ledger.json`
- `reports/market-reaction/m3c-scenario-audit.json`
- `reports/market-reaction/m3c-point-in-time-audit.json`

It does not broadly allow `reports/`.

## Regression Guarantees

Tests prove the generated audit does not scan itself, the tracked report returns
PASS, the self-report path does not appear in matches or forbidden rows,
documentation and tests remain classified correctly, and a real production
`order_send(` path still fails.

M4A remains read-only research tooling and not investment advice.
