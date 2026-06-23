# EIA Adapter

Source ID: `eia-open-data-v2`

The EIA adapter parses Open Data API v2 response rows into
`OfficialObservationRecord` rows for non-price energy inventory, storage,
production, and supply-demand profiles.

Access policy:

- live smoke requires local `FINNEWS_EIA_API_KEY`;
- no key value is stored or displayed;
- when the key is absent, live smoke is skipped/blocked;
- automated tests use mocked JSON payloads only.

Milestone 3B does not ingest live prices.
