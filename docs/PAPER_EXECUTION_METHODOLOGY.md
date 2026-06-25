# Paper Execution Methodology

Paper execution uses deterministic synthetic/local market bars. It is not real
execution, not a broker integration, and not investment advice.

Fill assumptions:

- only manually approved paper order intents can produce simulated fills;
- default fill price is the next available bar open after the decision time;
- missing bars, expired orders, pending review, review rejection, and absent
  paper exposure produce typed failed-fill reasons;
- slippage and commission are deterministic and bounded;
- no leverage is used;
- shorting is disabled by default;
- `flat` and `reduce` only close existing paper exposure;
- repeated runs are deterministic.

Outputs include paper fills, failed-fill reasons, paper positions, paper cash
ledger effects, NAV, costs, drawdown, exposure, and reconciliation status.

No MT5 terminal is contacted. No `MetaTrader5` package is required. No account,
broker, or real order data is accepted or stored.
