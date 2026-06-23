# Federal Register API Review

Source ID: `federal-register-api`

## Decision

Engineering usage-policy review: approved for a disabled-by-default regulatory
metadata and abstract pilot. This is not legal advice and does not certify
redistribution rights.

## Official Owner And Purpose

- Official owner: Office of the Federal Register and U.S. Government Publishing
  Office.
- Purpose: ingest selected FederalRegister.gov API document metadata and
  source-provided abstracts for synthetic research fixtures and mocked
  adapters.
- Official documentation:
  <https://www.federalregister.gov/developers/documentation/api/v1>

## Access And Credentials

No API key is required for the configured metadata profile.

## Storage Policy

Store document number, title, source-provided abstract, publication date,
document type, agency/CFR/RIN metadata, official HTML/PDF URLs, provenance, and
derived event metadata. Do not download PDFs or store full Federal Register
document bodies.

## Request Limits

The tracked config is disabled. Local live smoke is bounded to one Federal
Register request, at most five metadata records, no persistence, and a 2 MB
decoded response limit. Automated tests use fixtures and mocked transports only.

## Limitations

FederalRegister.gov is informational and is not the official legal edition.
Point-in-time provenance must be retained because regulatory metadata can
change.
