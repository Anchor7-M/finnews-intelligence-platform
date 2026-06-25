# Milestone 4B-0 Execution Plan

## Current State Audit

FinNews is on `feat/paper-execution-risk-simulator`, branched from `main` after
Milestone 4A. The existing platform has synthetic news/event pipelines, market
reaction validation, cross-asset research exports, official data fixtures, and a
local MT5 read-only boundary. M4A includes `docs/M4A_RELEASE_AUDIT.md`,
`docs/MT5_READONLY_BRIDGE.md`, Alembic migration `0008_mt5_readonly_bridge.py`,
read-only MT5 API/CLI/static/frontend surfaces, and a CI-safe fake export gate.

M4A does not provide account access, position reading, order checks, order
sending, or executable broker requests. M4B-0 starts from that boundary and adds
paper-only simulation.

## Scope

M4B-0 implements a deterministic paper-execution simulator and independent
risk-control engine. The feature evaluates research signal candidates, creates
paper order intents, simulates manual approval states, produces paper fills from
synthetic/local market bars, and reconciles a hypothetical paper portfolio.

The milestone delivers a versioned paper-order contract, backend services,
read-only API routes, Typer commands, static demo payloads, a Vue Paper Execution
Lab, PostgreSQL metadata tables, tests, release-audit evidence, and local
verification tooling.

## Non-Goals

M4B-0 does not connect to MT5, does not import or require `MetaTrader5`, does
not launch a terminal, does not read account or position data, does not call
`order_check` or `order_send`, and does not build broker order requests. It does
not claim real-world profitability and does not provide investment advice.

M4B demo-account execution and M4C live execution review remain deferred.

## Why Paper-Only

Paper execution is a safety layer between research signals and any future broker
integration. It lets the platform test idempotency, risk controls, approval
workflow, fill assumptions, accounting, and auditability using synthetic/local
data before any real account, terminal, or broker system exists.

## Risk-Control Architecture

The risk engine is independent from execution simulation. It consumes immutable
signal candidates, deterministic market-bar coverage summaries, portfolio state,
and a versioned `PaperRiskPolicy`. It returns a typed `PaperRiskDecision` with
status, reason codes, and an idempotency key. The fill simulator only accepts
paper order intents that already passed risk evaluation and manual review.

Required gates include signal status, TTL, confidence, asset universe, asset
class, direction, stale data, duplicate idempotency key, daily order limits,
per-asset and per-class notional caps, total exposure, drawdown stop, missing
data ratio, bar coverage, market-reaction quality flags, manual review, and an
emergency kill switch.

## Paper-Order Schema

The contract name is `finnews-paper-execution-v1`. It allows only paper-order
intent fields such as `paper_order_id`, `signal_id`, `asset_id`, `paper_side`,
`paper_quantity_units`, `paper_notional`, `risk_decision`,
`manual_approval_state`, `idempotency_key`, and `payload_hash`. Unknown fields
and broker/account/order-ticket fields are rejected.

Allowed paper sides are `long`, `flat`, and `reduce`. These are paper-only
states and are never broker order instructions.

## Paper-Fill Model

Default fills use the next available synthetic/local market bar open after the
decision time. Missing bars, expired intents, rejected risk decisions, pending
reviews, and disabled approval states produce typed failed-fill reasons.
Slippage and commission are deterministic and bounded. No leverage and no
shorting are allowed by default.

## Paper-Portfolio Accounting Model

The accounting model tracks cash, positions, average cost, realized and
unrealized PnL, transaction costs, gross and net exposure, asset-class exposure,
turnover, NAV, drawdown, maximum drawdown, and reconciliation status. Cash,
positions, fills, and NAV must reconcile after repeated deterministic runs.

## Idempotency And TTL Policy

Paper order intents carry stable idempotency keys derived from scenario, signal,
asset, decision time, side, and policy. Repeated runs reuse the same keys and
counts. Expired signals or expired manual reviews cannot be approved or filled.

Generated local experiment outputs remain ignored and are not committed.

## Manual-Approval Simulation Policy

Manual approval is local and deterministic. States are `pending_review`,
`approved`, `rejected`, and `expired`. Approval applies only to paper orders,
uses synthetic/local actor labels, does not store identity credentials, and does
not bypass risk rejections.

## No-Broker Safety Model

No API, CLI, frontend route, contract, migration, or static payload accepts
broker server, account ID, login, password, terminal path, MT5 symbol, ticket,
position ID, lot size, leverage, margin, stop loss, take profit, order type,
execution flag, `order_check`, or `order_send`.

## PostgreSQL Migration Plan

Add migration `0009_paper_execution.py` after `0008_mt5_readonly_bridge.py` with
UUID primary keys, stable business keys, idempotency constraints, JSONB metadata,
numeric money/exposure fields, timezone-aware timestamps, and no broker,
credential, MT5 terminal, account, ticket, or real-order columns.

Tables: `paper_risk_policies`, `paper_risk_decisions`, `paper_order_intents`,
`paper_manual_reviews`, `paper_fills`, `paper_positions`, `paper_nav`, and
`paper_execution_runs`.

## API, CLI, And Frontend Plan

The API is read-only under `/api/v1/paper/*`. CLI commands run local,
deterministic simulations only. The Vue Paper Execution Lab reads static demo or
API payloads and displays scenario counts, decisions, paper orders, fills,
positions, NAV, exposure, costs, drawdown, rejection reasons, and a persistent
synthetic-only disclaimer.

## Test Matrix

Tests cover the contract, strict unknown-field rejection, forbidden fields,
payload hash/idempotency, risk gates, manual approval, fill assumptions,
portfolio reconciliation, scenarios, PostgreSQL migration/parity, CLI commands,
API endpoints, frontend rendering, static demo exports, and execution-surface
audit.

Backend coverage must stay above 80%.

## Resource Budget

All default tests run offline with synthetic/static data. PostgreSQL verification
may start one project-scoped PostgreSQL 16 service. No paid API, browser binary,
large model, live market data, or files over 50 MB are used.

## CI And Offline Plan

CI remains broker-free and MT5-free. The `verify-paper-execution` wrapper runs
offline and terminates. Existing wrappers continue to pass.

## Definition Of Done

M4B-0 is complete when the paper contract exists, risk engine works, fills and
portfolio accounting reconcile, three synthetic scenarios run, API is read-only,
frontend/static demo pass, PostgreSQL parity passes, execution-surface audit has
zero forbidden production matches, all required wrappers pass, local commits
exist, and no push or PR has been attempted.
