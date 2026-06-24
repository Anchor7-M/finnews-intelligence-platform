# Signal Quality Metrics

M3C computes synthetic signal-quality diagnostics by scenario, horizon,
asset class, event family, regime, signal status, source provider, and
confidence bucket.

Metrics include evaluated count, unavailable count, coverage, directional
consistency rate, opposite rate, muted rate, mean raw return, mean and median
abnormal return, abnormal-return volatility, hit rate by direction,
information coefficient, Spearman rank IC, false positives, false negatives,
high-confidence wrong cases, low-confidence right cases, and missing-confidence
support.

Signed score:

```text
signed_score = direction_sign x strength x confidence
```

Missing confidence uses a neutral documented policy for scoring and is reported
as support. Metrics are research diagnostics and must not be described as live
trading profitability.
