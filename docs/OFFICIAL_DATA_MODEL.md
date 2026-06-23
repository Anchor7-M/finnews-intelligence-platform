# Official Data Model

Milestone 3B adds a revision-aware official-data layer for synthetic and
locally mocked BLS, EIA, CFTC COT, and Federal Register profiles.

The model is separate from news articles and market-signal candidates:

- `OfficialDataset` describes the reviewed official source/dataset family.
- `OfficialSeriesProfile` describes a bounded query or series profile.
- `OfficialObservation` stores the current value for a business key.
- `OfficialObservationRevision` stores append-only point-in-time revisions.
- `RegulatoryDocument` stores Federal Register metadata and source-provided
  abstracts only.
- `SeriesAssetAssociation` maps official data profiles to canonical asset IDs
  as research relevance hypotheses.
- `OfficialReleaseEvent` exposes transparent derived release events.

The observation business key is:

`source + dataset + profile + period_start + period_end + normalized dimensions`

Numeric values use `Decimal` semantics in Python and `Numeric(24, 6)` in
PostgreSQL. JSONB is confined to PostgreSQL persistence for provenance,
query metadata, dimensions, and quality flags.

All committed official-data records are synthetic demo data.
