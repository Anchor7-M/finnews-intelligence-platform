# Point-In-Time Alignment

For each article/company observation, FinNews distinguishes:

- `source_published_at`: timestamp supplied by the source.
- `first_seen_at`: timestamp when the platform could first observe the record.
- `processed_at`: operational processing timestamp.
- `information_available_at`: timestamp allowed to affect features.
- `decision_cutoff_at`: exact session cutoff stored on every feature row.
- `assigned_session_date`: first session whose cutoff is at or after availability.

Default formula:

```text
information_available_at = max(source_published_at, first_seen_at)
```

If publication time is missing, `first_seen_at` is used and a quality flag is set. If publication time is later than first seen, the anomaly is retained and the export never moves information earlier than safely known. In the deterministic synthetic demo, `first_seen_at` is derived from publication time plus a stable article-ID delay so repeated builds are byte-identical.

Cutoff policies:

- `pre_open_15m`: 15 minutes before session open; default.
- `session_close`: session close timestamp.

Exact cutoff information is included. One microsecond after cutoff is deferred to the next session. Rolling windows count sessions, not calendar days.
