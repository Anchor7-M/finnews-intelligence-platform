# FinNews Research Export Contract v1

Contract name: `finnews-research-export-v1`

Semantic contract version: `1.0.0`

This contract defines a deterministic point-in-time news-factor package for a future `ashare-research-platform` consumer. Packages are UTF-8, use RFC 3339 timezone-aware timestamps, ISO `YYYY-MM-DD` session dates, stable CSV column order, SHA-256 hashes, and deterministic sort order.

Required files:

- `manifest.json`
- `calendar.csv`
- `companies.csv`
- `feature_rows.csv`
- `feature_rows.jsonl`
- `lineage.jsonl`
- `quality_report.json`
- `leakage_audit.json`

CSV and JSONL feature rows must be equivalent. Null means an undefined statistic. Zero means a counted absence or numeric zero as defined by the feature catalog. No article title, summary, body, raw source response, local path, price, return, backtest, or recommendation field is allowed.

Breaking changes require a new major contract version. Backward-compatible additive optional fields may use a minor version. Consumers must reject unknown required fields, failed hashes, leakage failures, non-synthetic demo packages that claim to be synthetic, and packages with feature rows that violate `information_available_at <= decision_cutoff_at`.

The included example package is synthetic demo data only and is not an official market calendar or investment advice.
