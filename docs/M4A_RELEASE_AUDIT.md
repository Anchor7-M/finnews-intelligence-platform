# Milestone 4A Release Audit

M4A is read-only only, local CLI only, and not investment advice. It adds an
optional MT5 read-only bridge for local historical bar export, but it does not
add account access, order execution, order check, position reading, credential
storage, public API terminal triggers, or live execution.

M4B demo execution is separate. Live execution is not implemented and remains
separately reviewed.

## Evidence Table

| Requirement | Implementation Evidence | Command/Test Evidence | Exact Result | Status | Limitation |
| --- | --- | --- | --- | --- | --- |
| Release ledger is deterministic | `reports/mt5-readonly/m4a-release-ledger.json` | `finnews mt5 readonly release-audit` | byte-identical rebuild true, SHA256 `7d743cec2e072f83df6b6895a0790859907088009abad716cdfa7b43999a96a5` | PASS | Ledger is local generated evidence, not remote CI evidence. |
| Default public readiness is safe | `mt5_readonly_readiness()` and static demo JSON | API/CLI/static tests | MT5 terminal connection: not attempted; Order execution: disabled; Account access: not supported | PASS | Real local terminal status is not exposed publicly. |
| `MetaTrader5` remains optional | dynamic import isolated in `mt5_readonly.py` | dependency grep and execution-surface audit | no required dependency declaration; API/import/test collection do not require package | PASS | A user may install the package locally for manual export. |
| Local gates block terminal access | `evaluate_mt5_readonly_gates()` | unit tests and `m4a-bar-export-audit.json` | missing env, missing flag, CI, invalid map, bad output, bad time/range/timeframe all blocked | PASS | Gate audit uses fake adapter only. |
| Symbol-map policy is strict | `config/integrations/mt5-symbol-map.example.yaml` and validator | `m4a-symbol-map-audit.json` | tracked example valid; local map ignored; forbidden fields rejected | PASS | Local user map contents are private and not reported. |
| Fake adapter covers read-only export | `_AuditFakeBridge` audit and MT5 read-only tests | `m4a-fake-adapter-audit.json` and pytest | package missing, init failure, terminal unavailable, symbol metadata, bars, empty bars, duplicate/invalid bars covered | PASS | No real terminal is contacted. |
| Bar export matches market-bars contract | `export_mt5_bars_readonly()` | `m4a-bar-export-audit.json` and market-bar validator | exported fake bar validates against `finnews-market-bars-v1` | PASS | Export output remains local ignored data. |
| API is read-only and private | FastAPI `/api/v1/integrations/mt5/readonly/*` | contract tests | GET status/schema/runs only; POST returns 405; no local paths or credentials accepted | PASS | API exposes static/safe readiness only. |
| CLI contract is bounded | Typer `mt5 readonly` commands | CLI contract tests | help/status/validate/export/audit commands exist; forbidden subcommands absent | PASS | Real export requires manual local gates. |
| Vue/static demo is non-executable | Integration Readiness page and static JSON | Vitest and static validation | account access not supported, order execution disabled, API trigger disabled | PASS | No real terminal metadata shown. |
| Execution surface has zero forbidden production paths | `m4a-execution-surface-audit.json` and cross-asset trading audit | `finnews mt5 readonly release-audit`; `finnews cross-asset release-audit` | PASS, 0 forbidden production matches, no MT5 dependency | PASS | Generated evidence paths are exact-path excluded, not broad `reports/`. |
| PostgreSQL metadata is safe | migration `0008_mt5_readonly` | `python scripts/dev.py verify-postgres` | head `0008_mt5_readonly`; metadata tables verified; no forbidden columns | PASS | Tables store metadata only, not raw bars. |
| Full local verification | developer wrappers | `verify-lite`, `verify-sources`, `verify-source-reviews`, `verify-ml`, `verify-research-export`, `verify-cross-asset`, `verify-official-data`, `verify-market-reaction`, `verify-mt5-readonly`, `verify-postgres` | all passed locally | PASS | GitHub Actions were not run remotely. |

## PostgreSQL Metadata Tables

- `mt5_readonly_profiles`
- `mt5_readonly_symbol_mappings`
- `mt5_readonly_runs`
- `mt5_bar_export_manifests`

These tables are metadata-only. They do not store credentials, account IDs,
broker servers, terminal paths, orders, positions, trade history, margin data,
order checks, order sends, or raw bar file bytes.

## Deferred

M4B demo execution and M4C optional live execution remain future work requiring
separate review, separate risk controls, and separate opt-in. M4A does not
provide investment advice.
