# MT5 Integration Boundary

Revised Milestone 3A implements only an MT5-ready architecture boundary. It does not implement an MT5 adapter.

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

- No `MetaTrader5` package import.
- No terminal connection.
- No credential fields.
- No account data access.
- No order route.
- Offline symbol-map schema validation only.
- Readiness endpoint and CLI report disabled status.

## Future Milestones

Read-only local terminal metadata belongs to a future milestone. Demo execution belongs to a later milestone after read-only validation, manual approval, risk controls, stale-signal rejection, reconciliation, and audit logging.
