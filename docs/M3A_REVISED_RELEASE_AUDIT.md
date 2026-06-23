# Revised Milestone 3A Release Audit

## Status

Revised Milestone 3A is release-ready for local use. It implements cross-asset information and event intelligence with synthetic demo data only. Event-to-asset outputs are hypotheses, not proven causal effects. A signal candidate is not an order. MT5 connection is not implemented, order execution is disabled, and no credentials or account data are accepted.

Future MT5 work is local, demo-first, risk-gated, and separately reviewed. Optional A-share export remains an integration path, not the primary product. This is research tooling, not investment advice.

## Evidence Table

| Requirement | Implementation evidence | Command/test evidence | Exact result | Status | Limitation |
| --- | --- | --- | --- | --- | --- |
| Product positioning | README/docs/API/frontend describe a local-first cross-asset event-intelligence platform | `verify-lite`, frontend compliance tests | A-share export appears only as optional integration | PASS | None |
| Deterministic release ledger | `reports/cross-asset/revised-m3a-release-ledger.json` | `finnews cross-asset release-audit` inside `verify-cross-asset` | SHA-256 `7025475d2904f55e1c5da84589a93a902645b794b9f007562eff28c576c23568` | PASS | Durations excluded from content hashes |
| Asset registry | `cross_asset.py`, asset schemas, registry tests | `tests/unit/test_cross_asset.py` | 40 assets, 10 relationships, 0 alias uniqueness violations | PASS | Synthetic demo universe |
| Alias and symbol map | Strict MT5 symbol-map validator | `test_mt5_symbol_map_validation_rejects_each_forbidden_category` | 211 aliases; forbidden account/order/risk fields rejected | PASS | No real broker profile shipped |
| Event taxonomy | Revised event-family enum and fixtures | Release ledger and rule coverage report | 100 events across 18 families | PASS | Deterministic baseline taxonomy |
| Impact engine | Rule coverage and lifecycle reports | `revised-m3a-rule-coverage.json` | 240 impacts; 2-3 impacts per event; no all-to-all mapping | PASS | Hypotheses only |
| Signal contract | Strict schemas and package validator | `signal export`, `signal validate`, schema tests | 80 candidates; no execution fields; package hash stable | PASS | Local research handoff only |
| Lifecycle/idempotency | Stable hashes and cutoff/expiry checks | `revised-m3a-lifecycle-audit.json` | Byte-identical rebuild and idempotency match | PASS | Fixed synthetic generation time |
| Trading surface | Repository-wide text scan | `revised-m3a-trading-surface-audit.json` | 202 matches, 43 files, 0 forbidden production matches | PASS | Docs mention future MT5 function names |
| MT5 readiness | CLI/API/static readiness reports disabled status | `finnews mt5 readiness` | Terminal not implemented; execution disabled | PASS | Future milestones deferred |
| CLI/API/frontend | Read-only routes and command groups | contract/API/frontend tests | No connect/login/order/account route, command, or UI control | PASS | No live trading UI by design |
| PostgreSQL migration | Alembic revision `0005_cross_asset_signal` | `python scripts/dev.py verify-postgres` | 9 PostgreSQL tests passed; downgrade/re-upgrade passed | PASS | Uses disposable local Docker PostgreSQL |
| Timeout remediation | Split coverage and split Postgres nodeids | `reports/verification/revised-m3a-timings.json` | `verify-lite` 524.579s; `verify-postgres` 147.517s | PASS | Local-machine timings vary |
| Full offline verification | Dev wrappers | `verify-lite`, `verify-sources`, `verify-source-reviews`, `verify-ml`, `verify-cross-asset`, `verify-postgres` | All passed | PASS | Starlette/httpx deprecation warning only |
| Safety/cost | No paid APIs, no live prices, no cloud DB, no model weights | repo scan and wrapper tests | Synthetic data only; zero-cost local stack | PASS | Live data deferred |

## Release Ledger

Assets:

- Total: 40
- Class composition: `us_equity` 8, `etf` 5, `equity_index` 3, `fx` 5, `precious_metal` 3, `commodity` 3, `futures_root` 2, `futures_contract` 2, `crypto_asset` 4, `macro_indicator` 3, `interest_rate` 2
- Active: 40; synthetic: 40
- Venues: 11
- Regions: `US` 25, `Global` 15
- Base currency coverage: 40 assets, 11 unique values
- Quote currency coverage: 12 assets, 3 unique values
- Futures roots/contracts: 2 roots, 2 contracts, 2 valid root links
- Asset relationships: 10

Aliases:

- Total: 211
- Namespaces: `canonical` 40, `news_source` 43, `sec_cik_or_issuer` 8, `market_data` 40, `research` 40, `mt5_broker_local` 40
- Active/inactive: 210 active, 1 inactive
- Ambiguous fixture: 1
- Unresolved fixture: 1
- Active alias uniqueness violations: 0

Events:

- Total: 100
- Families: `monetary_policy` 6, `inflation` 6, `labor_market` 6, `economic_growth` 6, `liquidity_funding` 6, `fiscal_policy` 6, `regulation_enforcement` 6, `corporate_earnings_guidance` 6, `mergers_corporate_actions` 6, `commodity_supply` 6, `inventory_demand` 5, `geopolitical_risk` 5, `derivatives_positioning` 5, `exchange_market_infrastructure` 5, `crypto_protocol_ecosystem` 5, `crypto_regulation` 5, `idiosyncratic_company_event` 5, `other_uncertain` 5

Impacts:

- Total: 240
- Relationship types: 12 types, 20 each
- Direction: `mixed` 62, `negative` 59, `positive` 59, `uncertain` 60
- Horizon: `intraday` 60, `one_day` 60, `one_week` 60, `one_month` 60
- Status: `active` 231, `expired` 3, `rejected` 6
- Confidence: 232 non-null, 8 null

Signals:

- Total: 80
- Status: `research` 16, `informational` 16, `abstained` 14, `rejected` 18, `expired` 16
- Direction: `mixed` 20, `negative` 20, `positive` 20, `uncertain` 20
- Horizon: `intraday` 20, `one_day` 20, `one_week` 20, `one_month` 20
- Asset class: `us_equity` 16, `equity_index` 11, `interest_rate` 10, `etf` 9, `fx` 9, `commodity` 7, `crypto_asset` 7, `precious_metal` 5, `futures_contract` 3, `futures_root` 2, `macro_indicator` 1
- Idempotency keys: 80 unique

## Contract Hashes

Contract: `finnews-market-signal-v1`, version `1.0.0`; fixture `cross-asset-demo-v1`; asset schema `cross-asset-v1`; signal schema `market-signal-v1`.

Package hash: `003f6523b5930942a0122fe27e940431deef8673928de08f0469176517595950`

Dataset hash: `663e54e0adb5fd0680ddac5274dc6bf23108f1dbe194fdf9c6f306a0c5beff72`

Files:

- `assets.json`: 21,562 bytes, `80df36474b6e8ee94e63b6b8d3e449fbe8b7fa2643a7356a0460ec17b1c402c3`
- `event_impacts.jsonl`: 144,933 bytes, `c208695f88680c73502273f346652776bfb4c0a4d5b6fe5a87cd232d6e8d8411`
- `manifest.json`: 794 bytes, `d2291c2897b7851727254047209c445fd0aac17b43028ad619dbd0479a783824`
- `signals.jsonl`: 66,757 bytes, `5c6cb42a193c66b3d45be8f4987224e50cbdfb77164b5020ab2b9e5ba78d6b5a`

Schemas:

- `asset.schema.json`: 1,348 bytes, `635b0823e80a5bf54dd1d1e71f1005eaa9d7d8a5ab841f012397333cc04b1974`
- `impact.schema.json`: 1,466 bytes, `1c152386fd0230df13e5ca259c161bb236d45a7b31cb7c73dc7e7fca5ae99640`
- `manifest.schema.json`: 1,446 bytes, `461b461997c0fd9471223c75448679492f4227418284cd16da322fbcf6512fec`
- `signal.schema.json`: 1,989 bytes, `99557c8fdcc859c30853543ebc26142725df9079055652b82a38d4bebaff5345`

## PostgreSQL Results

Migration head: `0005_cross_asset_signal`.

Cross-asset persistence test: 40 assets, 211 aliases, 10 relationships, 100 events, 240 impact hypotheses, 80 signal candidates; repeated persistence did not duplicate business rows.

Pipeline first-run counts: `sources` 5, `raw_articles` 64, `articles` 56, `article_duplicates` 10, `observation_dispositions` 68, `companies` 12, `article_company_links` 46, `daily_digests` 7, `daily_company_signals` 46, `pipeline_runs` 1, `ingestion_runs` 68.

Pipeline second-run counts: same business rows, `pipeline_runs` 2, `ingestion_runs` 136.

Docker cleanup proof: `docker compose -p finnews_m3r_verify ps` returned no services after verification.

## Test Counts And Coverage

Backend collection: 142 cases total.

- Unit: 111 cases
- Contract: 22 cases
- PostgreSQL integration: 9 cases
- Focused cross-asset: 15 cases, from 12 unit and 3 contract cases
- Frontend Vitest: 13 cases across 3 files

Coverage: 83% total backend coverage with `coverage report --fail-under=80 --show-missing`.

## Verification Timings

Exact per-step durations are tracked in `reports/verification/revised-m3a-timings.json` with stable command names, monotonic start/end offsets, exit codes, and bounded timeouts. Report SHA-256: `882a650722c5109dca7f0fa0b5c65315570c1190eecee59a5c6e65cd9fa72a48`.

Wrapper totals:

- `verify-lite`: 524.579s
- `verify-sources`: 20.797s
- `verify-source-reviews`: 9.843s
- `verify-ml`: 119.671s
- `verify-cross-asset`: 46.531s
- `verify-postgres`: 147.517s

Slowest steps: NLP release audit under coverage 62.938s; API compliance under coverage 48.594s; research export under coverage 42.000s; cross-asset contract under coverage 37.297s; NLP benchmark command 34.844s.

Timeout root cause: prior monolithic coverage and PostgreSQL commands hid slow steps and exceeded local command limits. The remediation splits backend coverage by test file, combines coverage once, runs PostgreSQL marked tests by collected nodeid, and records bounded per-step timings. It does not start Docker in `verify-lite`, does not invoke watch modes, does not install dependencies, and does not recursively call other verification wrappers.

## Full Verification Commands

All commands passed:

- `python scripts/dev.py verify-lite`
- `python scripts/dev.py verify-sources`
- `python scripts/dev.py verify-source-reviews`
- `python scripts/dev.py verify-ml`
- `python scripts/dev.py verify-cross-asset`
- `python scripts/dev.py verify-postgres`
- `python scripts/dev.py verify-research-export`
- `python -m pytest tests/unit/test_cross_asset.py tests/contract/test_cross_asset_api_cli.py -q`
- `pytest --collect-only -q`
- `pytest --collect-only -q -m postgres`
- `npm run test:unit -- --run`
- `git diff --check`

## Limitations And Deferrals

- All assets, events, news, market signals, and source records are synthetic.
- The NLP and impact logic are deterministic baselines, not trained production models.
- No live prices, paid APIs, cloud services, account connections, broker terminals, or model weights are used.
- M3B/M3C/M4 work is deferred: read-only local MT5 metadata, demo terminal integration, risk controls, reconciliation, and any execution research require separate review.
