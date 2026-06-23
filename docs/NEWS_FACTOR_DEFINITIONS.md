# News Factor Definitions

Milestone 3A features are news metadata factors only. They do not include prices, returns, volume, labels, strategy signals, or investment recommendations.

Default windows are `1`, `3`, `5`, and `10` sessions. For session sequence `n` and window `w`, the row uses observations assigned to sessions `[n - w + 1, n]`.

Coverage/count features include `news_count`, `unique_article_count`, `unique_source_count`, `has_news`, `missing_published_time_count`, and `abstained_prediction_count`.

Sentiment features include positive/neutral/negative/uncertain counts and shares, mean score, confidence-weighted score, standard deviation, min, and max. Missing confidence is not fabricated.

Event features include count/share for every current event enum plus `event_type_count` and zero-safe entropy.

Novelty fields are nullable in Milestone 3A when no explicit novelty input is available. Source diversity is `unique_source_count / news_count` when news exists.

Recency and decay use information-availability timestamps. Decay uses a half-life of `24 * window_sessions` hours.

Quality flags record low coverage, missing timestamps, abstentions, multi-company articles, and backfilled information. Zero-news rows remain present in the dense panel with count fields at zero and undefined statistics as null.
