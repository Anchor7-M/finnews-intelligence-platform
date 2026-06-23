# Trading Surface Audit

Revised Milestone 3A includes a local audit that scans repository text for accidental trading-surface additions.

## Checked Patterns

The audit checks for MT5 package references, terminal connection calls, account-login calls, trading request validation/submission calls, action constants, order-type constants, password phrases, sizing phrases, and protective-level phrases.

Allowed findings are limited to:

- this documentation set;
- the revised execution plan;
- the signal contract schema;
- cross-asset unit and contract tests;
- the self-audit pattern list in `cross_asset.py`.

## Current Result

`python scripts/dev.py verify-cross-asset` runs the cross-asset unit tests, including the trading-surface audit. The expected result is:

- no MT5 package import in production code;
- no terminal contact in production code;
- no execution route in production code.
