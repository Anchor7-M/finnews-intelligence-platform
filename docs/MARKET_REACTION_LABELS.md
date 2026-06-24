# Market Reaction Labels

Allowed labels:

- `consistent_positive`;
- `consistent_negative`;
- `opposite`;
- `muted`;
- `mixed`;
- `unavailable`.

Positive signal direction plus positive abnormal return may be
`consistent_positive`. Negative direction plus negative abnormal return may be
`consistent_negative`. Opposite-sign abnormal return is `opposite`. A fixed
threshold around zero produces `muted` to avoid overinterpreting noise. Mixed,
uncertain, abstained, rejected, and expired candidates follow documented
non-trading policy and never mutate the original signal candidate.

Stored label evidence includes threshold/version, abnormal return, raw return,
benchmark return, quality flags, coverage, and point-in-time timestamps.

Market-reaction labels are research labels, not allocation instructions, not order
instructions, and not investment advice.
