# BLS Public Data API Review

Source ID: `bls-public-data`

## Decision

Engineering usage-policy review: approved for a disabled-by-default official
numeric data pilot. This is not legal advice and does not certify
redistribution rights.

## Official Owner And Purpose

- Official owner: U.S. Bureau of Labor Statistics.
- Purpose: ingest selected official economic series observations from synthetic
  fixtures, mocked HTTP tests, or bounded no-persist local smoke runs.
- Official documentation: <https://www.bls.gov/developers/>

## Access And Credentials

BLS Public Data API v1 is treated as the default no-key path. API v2 key usage
is optional and local-only through `FINNEWS_BLS_API_KEY`; the value must never
be stored, logged, committed, or exported.

## Storage Policy

Store series ID, dataset profile, period, normalized dimensions, numeric value,
footnote/provenance metadata, and project-derived revision metadata. Do not
store raw response bodies, unrelated series payloads, or API key values.

## Request Limits

The tracked config is disabled. Local live smoke is bounded to one BLS request,
at most five parsed observations, no persistence, and a 2 MB decoded response
limit. Automated tests use fixtures and mocked transports only.

## Limitations

Series definitions, seasonal-adjustment semantics, and BLS access rules may
change. New series profiles require review before being added.
