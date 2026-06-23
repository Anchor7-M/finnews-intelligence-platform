# EIA Open Data API v2 Review

Source ID: `eia-open-data-v2`

## Decision

Engineering usage-policy review: approved for a disabled-by-default non-price
energy data pilot. This is not legal advice and does not certify
redistribution rights.

## Official Owner And Purpose

- Official owner: U.S. Energy Information Administration.
- Purpose: ingest selected official inventory, storage, production, and
  supply-demand observations from synthetic fixtures, mocked HTTP tests, or
  bounded no-persist local smoke runs.
- Official documentation: <https://www.eia.gov/opendata/documentation.php>

## Access And Credentials

Live access requires a local `FINNEWS_EIA_API_KEY`. The tracked repository stores
only the env var name and skips live EIA smoke when the key is absent.

## Storage Policy

Store dataset route, series/query profile, period, normalized dimensions,
numeric value, unit, provenance, and project-derived revision metadata. Do not
store raw response bodies, API key values, or live smoke values in committed
files.

## Request Limits

The tracked config is disabled. Local live smoke is bounded to one EIA request
only when the key exists, at most five parsed observations, no persistence, and
a 2 MB decoded response limit. Automated tests use fixtures and mocked
transports only.

## Limitations

EIA route and facet schemas vary by dataset. Expansion beyond the configured
profile requires route-specific validation and review.
