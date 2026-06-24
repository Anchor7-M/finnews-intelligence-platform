# MT5 Integration Boundary

Revised Milestone 3A implemented an MT5-ready architecture boundary. Milestone
4A adds an optional local read-only adapter boundary, but keeps FinNews outside
the trading system category.

## Official Facts Preserved

Based on the official MQL5 Python integration documentation:

- the Python integration communicates with a locally running MetaTrader 5 terminal through interprocess communication;
- `initialize()` establishes the terminal connection;
- the integration exposes symbol, tick, bar, order, position, and history information;
- `order_check()` validates a proposed request and funding sufficiency, but a successful check does not guarantee execution;
- `order_send()` submits a request to the trade server;
- bar and tick timestamps are UTC and future adapters must normalize time explicitly.

Official references:

- https://www.mql5.com/en/docs/python_metatrader5
- https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py

## Current Implementation

- `MetaTrader5` is not a required dependency and is never imported at normal
  package import time, API startup, frontend build, or CI collection.
- The optional adapter dynamically imports `MetaTrader5` only inside
  `finnews mt5 readonly export-bars` after all local CLI gates pass.
- API and frontend readiness endpoints are read-only status surfaces. They
  cannot initialize a terminal, accept local paths, load local symbol maps, or
  export bars.
- Local symbol-map validation rejects credentials, terminal paths, account
  identifiers, order fields, price/order-sizing fields, and execution flags.
- Historical bar exports are written only under ignored
  `.finnews-mt5-readonly-exports/` paths and normalized to
  `finnews-market-bars-v1`.
- PostgreSQL stores metadata only: profiles, mappings, run summaries, and
  manifest summaries. It does not store credentials, account data, terminal
  paths, orders, positions, trade history, or raw bar file bytes.
- Order execution, order checking, account access, open-order reading,
  position reading, and history/deal reading are not implemented.

## Future Milestones

Demo execution belongs to a later milestone after read-only validation, manual
approval, risk controls, stale-signal rejection, reconciliation, and audit
logging. Live execution remains separately deferred and separately reviewed.
