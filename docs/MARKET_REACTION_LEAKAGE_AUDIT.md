# Market Reaction Leakage Audit

M3C runs deterministic leakage and negative-control diagnostics:

- null-scenario negative control;
- planted-scenario sanity recovery;
- regime-shift deterioration reporting;
- fixed-seed label permutation;
- timestamp mutation exclusion;
- future-price mutation invariance;
- input-order invariance;
- current-clock invariance;
- future-return sentinel rejection;
- missing-data unavailable labels.

The audit reports hashes and PASS/PARTIAL/FAIL-style diagnostics. Null,
planted, and regime-shift scenarios are synthetic diagnostics. They do not
prove causality, real-world alpha, investment suitability, or trading
profitability.
