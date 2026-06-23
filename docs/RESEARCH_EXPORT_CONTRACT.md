# Research Export Contract

Milestone 3A adds `finnews-research-export-v1` at contract version `1.0.0`.

The contract lives in `contracts/finnews-research-export/v1/` and defines a deterministic, UTF-8, point-in-time package for a future `ashare-research-platform` consumer. Required files are `manifest.json`, `calendar.csv`, `companies.csv`, `feature_rows.csv`, `feature_rows.jsonl`, `lineage.jsonl`, `quality_report.json`, and `leakage_audit.json`.

Feature rows are keyed by contract version, calendar ID/version, session date, decision cutoff, ticker, company ID, rolling window, and feature schema version. CSV columns have stable ordering and JSONL rows are byte-stable with sorted keys. Hashes use SHA-256.

The export intentionally excludes article title, summary, body, raw source response, local file path, market price, volume, return, benchmark, universe, portfolio, backtest, and recommendation fields.

Null means the statistic is undefined. Zero means counted absence for count fields or numeric zero for numeric features. Consumers must verify manifest hashes, reject leakage failures, respect timezone-aware timestamps, and treat synthetic demo packages as non-official research examples.
