# Market Reaction Point-In-Time Policy

Bar `available_at` is the earliest time the bar may be used. For daily
synthetic bars, `available_at = bar_end_at + 5 minutes`.

Rules:

- signal `information_cutoff_at` must be at or before reaction-label decision
  time;
- feature construction may use only bars whose `available_at` is at or before
  decision time;
- reaction windows are measured after decision time;
- no event may use future market bars to define its signal;
- current wall-clock time never enters labels or metrics;
- imported file modified time is not market availability;
- backfilled bars become available only at declared `first_seen_at` or
  `available_at`, whichever is later;
- revised bars create a new vintage rather than silently rewriting history.

These rules protect research labels from leakage. They do not make event
studies causal proof or investment advice.
