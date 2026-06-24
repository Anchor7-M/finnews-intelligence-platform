# MT5 Read-Only Local Setup

This setup is optional. CI, default tests, API startup, frontend build, and
static demo do not require MetaTrader 5 or the Python package.

## Symbol Map

Copy the example only if you intend to run a local export:

```text
copy config\integrations\mt5-symbol-map.example.yaml config\integrations\mt5-symbol-map.local.yaml
```

`config/integrations/mt5-symbol-map.local.yaml` is ignored. Keep it local.
Allowed fields are `profile_id`, `canonical_asset_id`, `mt5_symbol`, `enabled`,
`display_name`, `notes`, and `timezone`.

Do not put credentials, account numbers, server names, terminal paths, order
fields, price fields, volume/lot sizing, stop loss, take profit, margin fields,
or execution flags in the file. Validation rejects them.

## Validate

```text
cd backend
python -m finnews.interfaces.cli.app mt5 readonly status
python -m finnews.interfaces.cli.app mt5 readonly validate-symbol-map --path ../config/integrations/mt5-symbol-map.local.yaml
```

Validation does not import `MetaTrader5` and does not contact a terminal.

## Export Bars

Run only when you have a local terminal open and you explicitly choose to allow
read-only local access:

```text
cd backend
set FINNEWS_ALLOW_LOCAL_MT5_READONLY=1
python -m finnews.interfaces.cli.app mt5 readonly export-bars ^
  --symbol-map ../config/integrations/mt5-symbol-map.local.yaml ^
  --timeframe M5 ^
  --from 2026-06-01T00:00:00Z ^
  --to 2026-06-02T00:00:00Z ^
  --output ../.finnews-mt5-readonly-exports/local-run ^
  --confirm-local-terminal
```

The command is blocked in CI, requires UTC-aware times, enforces bounded ranges,
and writes only below `.finnews-mt5-readonly-exports/`.

No API route or frontend action can trigger this export. M4A does not read
accounts, orders, positions, or history; it does not check or send orders.
