# Paper Risk Policy

Milestone 4B-0 risk controls are paper-only. They do not approve live trading,
do not connect to MT5, do not inspect accounts or positions, and do not provide
investment advice.

The default policy `paper-risk-m4b0-default-v1` evaluates synthetic research
signal candidates before a paper order intent can be generated. A passing
decision means only `approved_for_paper`, never live approval.

Risk gates:

- signal status must be `research` or allowed informational mode;
- expired, rejected, abstained, and uncertain signals are blocked;
- confidence must meet the threshold or enter manual review;
- asset and asset class must be in the paper universe;
- source data must not be stale;
- idempotency keys must be unique;
- per-day, per-asset, asset-class, and total exposure caps are enforced;
- drawdown stop blocks new paper orders;
- market-bar coverage and missing-data ratios are checked;
- market-reaction quality flags can reject candidates;
- manual review is required before any simulated fill;
- emergency kill switch blocks all new paper order intents.

Decision statuses are `approved_for_paper`, `requires_manual_review`,
`rejected`, `expired`, `duplicate`, and `kill_switch_active`.

The policy stores no broker server, account ID, login, password, terminal path,
ticket, leverage, margin, stop-loss, take-profit, or real order field.
