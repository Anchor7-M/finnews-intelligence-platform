# Event Study Methodology

M3C evaluates cross-asset event-impact hypotheses and signal candidates as
research objects:

```text
information event -> impact hypothesis -> signal candidate -> reaction label
```

Daily-bar windows:

- intraday proxy `[0, 1]`, explicitly labeled as a daily proxy;
- `one_day` `[0, 1]`;
- `three_day` `[0, 3]`;
- `one_week` `[0, 5]`;
- `one_month` `[0, 20]`;
- `pre_event_control` `[-5, -1]`.

Each study stores event/study IDs, signal/impact IDs, asset ID, event family,
event timestamp, decision time, reaction window, baseline/control window,
coverage, raw return, benchmark return, abnormal return, magnitude bucket,
quality flags, excluded reason, scenario ID, provider, and version.

No trade order, portfolio, position, execution request, or recommendation is
produced. Event studies do not prove causality.
