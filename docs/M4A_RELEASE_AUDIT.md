# Milestone 4A Release Audit

## Scope

Implemented M4A only: optional local MT5 read-only bridge, symbol-map
validation, gated local historical-bar export to `finnews-market-bars-v1`,
read-only readiness surfaces, PostgreSQL metadata, and execution-surface audit.

## Safety Result

- `MetaTrader5` is optional and dynamically imported only after CLI gates pass.
- API and frontend cannot initialize a terminal or export bars.
- CI and default tests do not require MT5 or a terminal.
- Credentials, terminal paths, account data, orders, positions, history,
  margin/profit checks, order checks, and order sends are not implemented.
- Local symbol maps and local exports are ignored and not tracked.

## Verification Snapshot

- `python scripts/dev.py verify-mt5-readonly`: passed
- MT5 read-only backend/API/CLI tests: 12 passed
- Frontend Vitest during wrapper: 17 passed
- Trading-surface report: PASS with 0 forbidden production matches

Full release verification is recorded in the final handoff for this branch.

## PostgreSQL

Migration `0008_mt5_readonly` adds metadata-only tables:

- `mt5_readonly_profiles`
- `mt5_readonly_symbol_mappings`
- `mt5_readonly_runs`
- `mt5_bar_export_manifests`

The schema stores safe metadata and counts only. It has no credential, account,
order, position, stop-loss, take-profit, or margin-required columns.

## Deferred

M4B demo execution and M4C optional live execution remain separate future work
requiring separate review. This release is not investment advice.
