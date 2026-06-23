# A-Share Research Handoff

The future `ashare-research-platform` should consume FinNews packages as files, not through FinNews internal modules or database access.

Consumer responsibilities:

- Negotiate contract version and reject unsupported major versions.
- Validate `manifest.json`, file hashes, package hash, and leakage status.
- Verify calendar identity, timezone, and session sequence before joining market data.
- Map `company_id` and `ticker` into its own research universe.
- Interpret `decision_cutoff_at` as the earliest legal decision time for joins.
- Preserve dense panel semantics, zero/null semantics, and session-count windows.
- Use lineage for audit only, without depending on article text.
- Reject packages with article text, price/return fields, failed hashes, or leakage failures.

The consumer owns prices, corporate actions, universes, returns, IC/Rank IC, walk-forward tests, portfolio construction, transaction costs, and performance attribution. FinNews owns news provenance, point-in-time availability, event/sentiment metadata, factors, lineage, and the export contract.

Example pseudocode:

```text
manifest = read_json("manifest.json")
verify_contract(manifest.contract_version)
verify_hashes(manifest.files)
calendar = read_calendar("calendar.csv")
features = read_feature_rows("feature_rows.csv")
assert all(features.information_cutoff_at <= features.decision_cutoff_at)
market_panel = consumer_load_prices_and_returns()
joined = join_on(ticker, session_date, decision_cutoff_at)
```

Planned next work belongs in the second repository and is not implemented here.
