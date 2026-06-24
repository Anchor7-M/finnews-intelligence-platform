# Milestone 3C Execution Plan

## Current-State Audit

FinNews is on `feat/market-reaction-validation`, branched from updated
`main` at `c30c1a9 Complete Milestone 3B release audit`. The repository already
contains the revised M3A cross-asset registry, event-to-asset impact
hypotheses, `finnews-market-signal-v1`, MT5 readiness boundary checks, M3B
official-data source reviews, revision-aware official observations, API/CLI
surfaces, static demo exports, and PostgreSQL migration `0006_official_data`.

The current implementation has no market-reaction labels, no market-data bar
contract, no event-study results, and no signal-quality evaluation against
subsequent synthetic or local user-owned market data.

## Scope

Milestone 3C adds an offline market-reaction validation lab:

- versioned local market-bar import contract `finnews-market-bars-v1`;
- deterministic synthetic market-bar scenarios;
- event-study windows over point-in-time research signal candidates;
- abnormal-return and reaction-label generation;
- signal-quality metrics and deterministic error analysis;
- leakage and negative-control diagnostics;
- read-only API, Typer CLI, Vue/static-demo surfaces, documentation, tests, and
  PostgreSQL metadata.

## Non-Goals

- No live market-data download.
- No paid data providers.
- No broker API.
- No `MetaTrader5` dependency, terminal connection, account data, credentials,
  order checking, order sending, position sizing, or execution path.
- No real-world alpha, causality, investment suitability, portfolio, or trading
  recommendation claim.

## Market-Data Import Boundary

The import contract accepts only local CSV or JSONL files explicitly passed to
CLI validation/import commands. Files must contain user-owned or properly
licensed bar data, strict UTF-8 schemas, timezone-aware timestamps, finite
positive OHLC values, non-negative volumes, deterministic business keys, and no
credentials, account fields, order fields, live-fetch metadata, or future-return
sentinel columns. Local imports are not copied into tracked paths by default.

## Synthetic Scenario Design

Three deterministic scenarios will be generated from 24 canonical assets:

- `synthetic-null-reaction-v1`: returns are independent of signal direction;
- `synthetic-planted-reaction-v1`: weak lagged synthetic relationship after
  selected signals;
- `synthetic-regime-shift-v1`: planted relationship weakens or reverses after
  the midpoint.

Each scenario has 90 daily UTC sessions, producing `90 x 24 = 2,160` bars and
`6,480` total synthetic bars. Market states are deterministic labels: calm,
risk-off, high-volatility, commodity shock, and crypto stress.

## Market Timestamp Policy

`available_at` is the first time a bar may be used. Daily synthetic bars default
to `bar_end_at + 5 minutes`. Signal `information_cutoff_at` must be at or
before decision time. Event-study windows use bars after the signal decision
time; pre-event baselines use only bars available before decision time. Current
wall-clock time and local file modified time are never used as market
availability.

## Event-Study Methodology

Required windows:

- intraday proxy `[0, 1]` daily session window;
- `one_day` `[0, 1]`;
- `three_day` `[0, 3]`;
- `one_week` `[0, 5]`;
- `one_month` `[0, 20]`;
- `pre_event_control` `[-5, -1]`.

Each event-study record stores signal/impact IDs, asset, event family,
decision time, horizon, control coverage, reaction coverage, raw return,
benchmark return, abnormal return, label inputs, quality flags, excluded reason,
scenario ID, and provider/version. No order or position is produced.

## Return And Reaction Labels

Raw return is close-to-close cumulative return over the reaction window.
Benchmark modes are asset-class equal weight, scenario-wide equal weight, and
asset-specific pre-event mean. Abnormal return is raw return minus the selected
benchmark, with optional standardized abnormal return when pre-event volatility
coverage is sufficient.

Allowed labels are `consistent_positive`, `consistent_negative`, `opposite`,
`muted`, `mixed`, and `unavailable`. Labels are research labels, not trade
labels or recommendations.

## Signal-Evaluation Metrics

Metrics are grouped by scenario, horizon, asset class, event family, signal
status, confidence bucket, source/provider, and market regime. Required
metrics include coverage, consistency/opposite/muted rates, mean/median
abnormal return, abnormal-return volatility, signed-score IC, Spearman rank IC,
false positives, false negatives, high-confidence wrong cases, and
low-confidence right cases.

`signed_score = direction_sign x strength x confidence`, with missing
confidence reported and treated by a documented neutral policy.

## Leakage Checks

Diagnostics cover null negative control, planted sanity recovery, regime shift,
label permutation, timestamp mutation, future-price mutation, input-order
invariance, current-clock invariance, future-return sentinel rejection, and
missing-data behavior.

## PostgreSQL Migration Plan

Add one migration after `0006_official_data` for:

- `market_data_packages`;
- `market_bar_series`;
- `market_bars`;
- `market_bar_revisions`;
- `market_reaction_studies`;
- `market_reaction_labels`;
- `signal_quality_runs`;
- `signal_quality_metrics`;
- `signal_error_cases`.

Use UUID primary keys, stable unique business keys, Numeric/Decimal fields,
timezone-aware timestamps, JSONB metadata/flags, append-only bar revisions, and
no raw file bytes, credentials, account, order, or MT5 fields.

## API, CLI, And Frontend Plan

CLI groups:

- `market-data contract validate`;
- `market-data import-local --dry-run`;
- `market-data build-demo`;
- `market-data summary`;
- `reaction study build`;
- `reaction study validate`;
- `reaction labels`;
- `reaction evaluate`;
- `reaction compare`;
- `reaction error-analysis`;
- `reaction export-static`.

Read-only API endpoints will expose overview, scenarios, studies, labels,
metrics, error analysis, packages, and bars. Vue will add `/market-reaction`
with static-demo and API modes, scenario selector, metrics, slices, leakage
status, point-in-time methodology, and permanent synthetic/no-advice notices.

## Test Matrix

Tests will cover contract validation, synthetic scenario counts and
determinism, point-in-time boundaries, event-study arithmetic, benchmark modes,
reaction-label policy, signal-quality metrics, false-positive/false-negative
records, leakage diagnostics, memory/PostgreSQL parity, CLI/API contracts,
frontend rendering, static export, and trading-surface regression.

## Resource Budget

All default tests run offline and sequentially. Synthetic data stays bounded.
No large files over 50 MB, model downloads, browsers, schedulers, queues, or
new infrastructure are introduced. Optional PostgreSQL verification may start
one disposable `postgres:16` service under Compose project
`finnews_m3c_verify`, localhost-only, 512 MB memory, 0.50 CPU, `restart: "no"`.

## CI And Offline Plan

CI remains offline, uses only synthetic market data, requires no API keys, and
must not fetch prices, connect to MT5, or upload local user imports. Workflows
will run the market-reaction tests and preserve the existing checks.

## Definition Of Done

M3C is done when the contract validates, exactly three scenarios and 6,480
synthetic bars exist, event-study windows and abnormal returns are implemented,
reaction labels are leakage-safe, signal-quality/error/leakage reports exist,
PostgreSQL parity passes, API is read-only, Vue/static demo passes, trading
surface remains absent, coverage stays at least 80%, wrappers pass, Docker
resources are cleaned, and local commits exist.

## Deferred M4 Work

M4A read-only MT5 bridge, M4B demo execution, M4C optional live execution,
broker risk controls, account reconciliation, and any real trading workflow are
deferred to later milestones with separate review.
