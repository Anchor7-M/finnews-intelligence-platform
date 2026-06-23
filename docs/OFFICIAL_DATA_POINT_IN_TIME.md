# Official Data Point-In-Time Policy

Official observations are aligned by information availability, not by the
economic period date.

Rules:

- `period_start` and `period_end` describe what the observation measures.
- `first_seen_at` records when the platform first saw the observation.
- `source_updated_at` is used only when the source provides a reliable
  timezone-aware timestamp.
- `information_available_at = max(first_seen_at, source_updated_at)` when the
  source timestamp is usable.
- Missing source timestamps fall back to `first_seen_at` and receive a quality
  flag.
- Future-dated source timestamps are not trusted for availability; the
  observation falls back to `first_seen_at` and receives a quality flag.
- Naive timestamps are rejected.

Live smoke data is no-persist and cannot create point-in-time rows.
