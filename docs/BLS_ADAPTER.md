# BLS Adapter

Source ID: `bls-public-data`

The BLS adapter parses Public Data API series payloads into
`OfficialObservationRecord` rows. The default tracked profile is disabled and
uses synthetic fixtures and mocked HTTP tests.

Supported fields:

- series ID;
- year and `M01`-style period;
- numeric value;
- footnote/provenance metadata.

Access policy:

- BLS v1 no-key access is the default live-smoke posture.
- Optional v2 key usage is local-only through `FINNEWS_BLS_API_KEY`.
- API key values are never persisted, logged, printed, exported, or committed.
- Automated tests do not use live network.
