# Synthetic Market Scenarios

M3C uses three deterministic synthetic scenarios:

- `synthetic-null-reaction-v1`
- `synthetic-planted-reaction-v1`
- `synthetic-regime-shift-v1`

Each scenario uses 24 canonical assets, 90 pseudo daily sessions, UTC bar
timestamps, and 2,160 bars. The complete synthetic set contains 6,480 bars.
The pseudo calendar is deterministic and does not claim official exchange
calendar accuracy.

Market states are `calm`, `risk_off`, `high_volatility`, `commodity_shock`,
and `crypto_stress`.

The null scenario is a negative control. The planted scenario has a weak,
documented synthetic lagged relationship after selected point-in-time signal
candidates. The regime-shift scenario weakens or reverses that relationship in
the second half. These scenarios are synthetic diagnostics, not real prices and
not real-world alpha evidence.
