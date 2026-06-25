# Paper Portfolio Accounting

The paper portfolio starts with synthetic cash and applies only simulated fills.
It does not read a real account and does not represent live performance.

Tracked fields:

- cash;
- positions;
- average cost;
- realized and unrealized PnL;
- gross and net exposure;
- asset-class exposure;
- turnover;
- transaction costs;
- NAV;
- drawdown and maximum drawdown;
- reconciliation status.

Rules:

- no negative cash;
- no leverage;
- no short positions by default;
- no broker account data;
- deterministic synthetic/local market bars only;
- current wall-clock time is not used for demo outcomes;
- repeated runs are idempotent.

The accounting result is research tooling only and is not investment advice.
