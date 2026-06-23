# Research Export Leakage Checks

Milestone 3A treats leakage as a release blocker.

Required invariants:

- Every included lineage observation satisfies `information_available_at <= decision_cutoff_at`.
- After-cutoff information is deferred to the next eligible session.
- Backfilled information cannot affect rows before `first_seen_at`.
- Future sessions do not affect earlier rolling windows.
- `generated_at` is not used as an information timestamp.
- Sorting changes do not change results.
- Repeated exports are byte-identical.
- Session windows do not use calendar-day arithmetic.

The deterministic leakage audit records rows checked, lineage links checked, violations, boundary cases, future-mutation status, backfill status, and an audit hash. Any violation must fail validation before release.
