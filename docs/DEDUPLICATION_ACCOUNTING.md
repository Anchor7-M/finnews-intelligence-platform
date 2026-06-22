# Deduplication Accounting

Milestone 0 uses observation-level accounting. An observation is one input item read from a configured source adapter before validation or persistence. Counts are derived from `ObservationDisposition` records, not from text reports.

## Metric Definitions

- `raw_observation_count`: every input observation read from all configured fixture adapters, including malformed observations.
- `rejected_observation_count`: input observations rejected before canonical persistence.
- `valid_observation_count`: successfully validated observations.
- `canonical_article_count`: valid observations that became canonical articles.
- `exact_duplicate_observation_count`: unique valid observations classified as non-canonical exact duplicates.
- `near_duplicate_observation_count`: unique valid observations classified as non-canonical near duplicates.
- `duplicate_observation_count`: exact duplicate observations plus near duplicate observations.
- `exact_duplicate_pair_count`: exact duplicate relationships discovered.
- `near_duplicate_pair_count`: near-duplicate relationships discovered.
- `duplicate_cluster_count`: canonical clusters containing two or more observations.

## Classification Precedence

Each observation receives exactly one disposition:

1. `rejected`
2. `canonical`
3. `exact_duplicate`
4. `near_duplicate`

An observation cannot be both an exact duplicate observation and a near-duplicate observation. Exact duplicate checks run before near-duplicate checks.

## Canonical Selection

The first valid observation for a normalized content hash becomes canonical. Exact duplicates reference that canonical observation. Near duplicates are compared only against canonical processed articles within the configured time window and reference the best canonical match above the threshold.

## Pairs, Observations, And Clusters

Duplicate observations count unique non-canonical inputs. Pair counts count relationships from duplicate observation to canonical article. In the current fixture each duplicate observation has one canonical relationship, so duplicate observation counts and pair counts match by type. Clusters count canonical groups with at least one duplicate observation.

## Accounting Invariants

```text
raw_observation_count = rejected_observation_count + valid_observation_count
valid_observation_count = canonical_article_count + exact_duplicate_observation_count + near_duplicate_observation_count
duplicate_observation_count = exact_duplicate_observation_count + near_duplicate_observation_count
```

Every non-canonical valid observation references exactly one canonical observation/article. Every canonical observation references itself.

## Final Verified Counts

```text
raw_observation_count = 68
rejected_observation_count = 4
valid_observation_count = 64
canonical_article_count = 46
exact_duplicate_observation_count = 8
near_duplicate_observation_count = 10
duplicate_observation_count = 18
exact_duplicate_pair_count = 8
near_duplicate_pair_count = 10
duplicate_cluster_count = 18
```

Arithmetic:

```text
68 = 4 + 64
64 = 46 + 8 + 10
18 = 8 + 10
```

## Worked Synthetic Example

If five observations are read, one malformed item is rejected, two unique items become canonical articles, one item has the same normalized title/summary/language as the first canonical article, and one item is a near duplicate of the second canonical article:

```text
raw_observation_count = 5
rejected_observation_count = 1
valid_observation_count = 4
canonical_article_count = 2
exact_duplicate_observation_count = 1
near_duplicate_observation_count = 1
duplicate_observation_count = 2
exact_duplicate_pair_count = 1
near_duplicate_pair_count = 1
duplicate_cluster_count = 2
```
