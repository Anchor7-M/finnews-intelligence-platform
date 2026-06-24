# Milestone 3C Release Audit

## Scope

Milestone 3C adds offline market-reaction validation for the existing
cross-asset research-signal layer. The release includes the
`finnews-market-bars-v1` local CSV/JSONL import contract, deterministic
synthetic market scenarios, point-in-time event studies, abnormal-return
research labels, signal-quality metrics, leakage diagnostics, negative
controls, read-only API/CLI/static-demo surfaces, and PostgreSQL migration
`0007_market_reaction`.

## Release Evidence

| Evidence | Status | SHA-256 |
| --- | --- | --- |
| `reports/market-reaction/m3c-release-ledger.json` | PASS | `c85c8b556403bbb3fccb6363bd83d78d284852c357540eaf97e7b88450100747` |
| `reports/market-reaction/m3c-scenario-audit.json` | PASS | `7dcddef1040f74f0e1a240091688f64768e4fba6677e9a58244f82716aba4370` |
| `reports/market-reaction/m3c-point-in-time-audit.json` | PASS | `1dacbd362c316fac8a57ace771ac03825e3301b5fd78ee023dbea7765c4df7f2` |

The release-audit CLI regenerated these files twice and confirmed
byte-identical rebuilds for all three reports.

## Dataset Accounting

- Synthetic scenarios: 3.
- Assets per scenario: 24.
- Sessions per scenario: 90.
- Bars per scenario: 2,160.
- Generated bars across scenarios: 6,480.
- Event-study rows: 645.
- Reaction labels: 645.
- Signal-quality metric rows: 132.
- Error-analysis cases: 72.
- Static demo market-data files: 11.
- Full bar static export: false; only bounded bar samples are committed.

Scenario accounting:

| Scenario | Bars | Market states | One-week consistency | One-week opposite |
| --- | ---: | --- | ---: | ---: |
| `synthetic-null-reaction-v1` | 2,160 | 432 each across calm, commodity shock, crypto stress, high volatility, risk off | 0.000000 | 0.000000 |
| `synthetic-planted-reaction-v1` | 2,160 | 432 each across calm, commodity shock, crypto stress, high volatility, risk off | 0.139535 | 0.023256 |
| `synthetic-regime-shift-v1` | 2,160 | 432 each across calm, commodity shock, crypto stress, high volatility, risk off | 0.139535 | 0.023256 |

The synthetic market scenarios are not real prices.

## Contract And Storage

- Contract name: `finnews-market-bars-v1`.
- Contract version: `1.0.0`.
- Schema hash: `8dd39680de15032aac6fd6278371c00e139470061e9c55efca9d00a5238beba9`.
- Validation rules: 21.
- Forbidden import field hash: `54b267b1b998ccba62d9c0b79b9de386a58a2bc97ddeb56cba6d9486c5de50bc`.
- New PostgreSQL tables: 9.
- Alembic head: `0007_market_reaction`.
- PostgreSQL first-run idempotency, repeated-run idempotency, schema, and rollback checks: PASS.

Local imports require user-owned or properly licensed data. Import validation
rejects future-return sentinel fields and account, credential, position, and
order-like fields.

## Point-In-Time Controls

- Checked market bar sample: 100.
- Checked event studies: 645.
- Checked reaction labels: 645.
- Availability policy: daily `available_at` equals `bar_end_at` plus 5 minutes.
- Signal cutoff is at or before decision time: true.
- Reaction windows are after decision time: true.
- File modified time used: false.
- Boundary checks passed for exact availability, one microsecond before/after,
  missing availability, future bars, late backfills, current-clock mutation,
  input-order mutation, and timezone conversion.
- Append-only revisions use new `market_bar_revisions` rows and move the
  current-revision pointer.

## Research Interpretation

Market-reaction labels are research labels, not trade labels. Event studies do
not prove causality. The negative-control checks passed for label permutation,
timestamp mutation, future-price mutation, input-order invariance,
current-clock invariance, future-return sentinel rejection, and missing-data
behavior.

## Safety Boundary

- No live market data is downloaded.
- No MT5 connection.
- No orders or position sizing.
- No broker API.
- No credentials, account identifiers, positions, or order fields.
- No paid data provider.
- No investment advice.
- Not investment advice.

## Verification

All required verification wrappers passed locally with exit code 0:

| Command | Duration seconds |
| --- | ---: |
| `python scripts/dev.py verify-lite` | 817.557 |
| `python scripts/dev.py verify-sources` | 31.341 |
| `python scripts/dev.py verify-source-reviews` | 16.159 |
| `python scripts/dev.py verify-ml` | 127.393 |
| `python scripts/dev.py verify-research-export` | 49.562 |
| `python scripts/dev.py verify-cross-asset` | 67.747 |
| `python scripts/dev.py verify-official-data` | 41.406 |
| `python scripts/dev.py verify-market-reaction` | 116.269 |
| `python scripts/dev.py verify-postgres` | 183.773 |

Additional final checks passed:

- `python -m pytest tests/unit/test_market_reaction.py tests/contract/test_market_reaction_api_cli.py -q`
- `python -m pytest --cov=finnews --cov-report=term-missing --cov-fail-under=80`
- `ruff check .`
- `ruff format --check .`
- `mypy src tests`
- `git diff --check`

Backend coverage from the full wrapper run was 85%, above the 80% threshold.
Frontend Vitest passed with 3 files and 17 tests, and the Vue production build
passed. PostgreSQL verification used the project-scoped Compose project
`finnews_m3c_verify`, official `postgres:16`, localhost-only
`127.0.0.1:55432`, disposable volume/network, and cleanup after the run.
