# CFTC COT PRE Review

Source ID: `cftc-cot-pre`

## Decision

Engineering usage-policy review: approved for a disabled-by-default public COT
PRE observations pilot. This is not legal advice and does not certify
redistribution rights.

## Official Owner And Purpose

- Official owner: U.S. Commodity Futures Trading Commission.
- Purpose: ingest selected official public reporting observations for
  positioning-related research fixtures and mocked adapters.
- Official documentation:
  <https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm>

## Access And Credentials

No token is stored or required for the configured public COT PRE profile.

## Storage Policy

Store report date, market identifiers, CFTC contract market code where present,
normalized dimensions, numeric positioning values, provenance, and revision
metadata. Do not assume a universal primary key across all COT datasets and do
not commit live smoke values.

## Request Limits

The tracked config is disabled. Local live smoke is bounded to one CFTC request,
at most five parsed rows, no persistence, and a 2 MB decoded response limit.
Automated tests use fixtures and mocked transports only.

## Limitations

COT row identity differs across formats and report families. Logical keys must
be constructed conservatively from source, dataset, report date, market code,
and normalized dimensions.
