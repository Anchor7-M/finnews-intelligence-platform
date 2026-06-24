# Milestone 3C Release Audit

## Scope

Milestone 3C adds offline market-reaction validation for the existing
cross-asset research-signal layer. The release includes:

- `finnews-market-bars-v1` local CSV/JSONL import contract;
- deterministic synthetic market scenarios;
- point-in-time event studies and abnormal-return labels;
- signal-quality metrics and deterministic error analysis;
- leakage diagnostics and negative controls;
- read-only FastAPI, Typer CLI, Vue/static-demo surfaces;
- PostgreSQL metadata migration `0007_market_reaction`.

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

Static demo files commit bounded samples for market bars. The full 6,480-bar
synthetic set is generated locally by backend services and is not committed as
a large static JSON dump.

## Safety Boundary

- No live market-data download.
- No paid data provider.
- No broker API.
- No MT5 package import or terminal connection.
- No credentials, account identifiers, positions, or order fields.
- No investment advice, strategy recommendation, or causality claim.
- Local import validation rejects future-return sentinel columns and
  credential/account/order-like fields.

## Verification Evidence

Targeted M3C verification passed locally:

- `python scripts/dev.py verify-market-reaction`
- `cd backend && python -m pytest tests/unit/test_market_reaction.py tests/contract/test_market_reaction_api_cli.py -q`
- `cd frontend && npm run test:unit -- --run`

Full-suite verification also passed locally:

- `python scripts/dev.py verify-lite`
- Backend coverage: 84%, above the 80% threshold.
- Backend Ruff check, Ruff format check, and mypy passed.
- Frontend ESLint, Prettier check, TypeScript check, Vitest, and production
  build passed.
- Memory-profile demo and `git diff --check` passed.
- `python scripts/dev.py verify-postgres` passed with Compose project
  `finnews_m3c_verify`, official `postgres:16`, localhost-only
  `127.0.0.1:55432`, disposable volume/network, and cleanup verified.
