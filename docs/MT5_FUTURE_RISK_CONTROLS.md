# MT5 Future Risk Controls

This document is forward-looking. None of these controls imply execution is implemented now. Milestone 4A supplies a read-only bridge foundation only; it cannot be reused as a demo or live execution surface without a separate milestone and audit.

## Required Before Demo Execution

- Separate read-only bridge validation.
- Demo account first.
- Manual approval before any submitted request.
- Strict local risk engine.
- Idempotency keys and duplicate-request prevention.
- Stale-signal rejection.
- Symbol and contract metadata introspection from the local terminal.
- UTC timestamp normalization.
- Kill switch.
- Reconciliation against terminal state.
- Full audit trail.

## Required Before Any Live Consideration

- Prolonged demo validation.
- Separate security and risk audit.
- Broker and jurisdiction eligibility review.
- Independent opt-in configuration.
- Clear user ownership of data, credentials, and decisions.

Live execution is explicitly deferred.
