# SEC EDGAR Submissions API Review

Source ID: `sec-edgar-submissions`

## Decision

Engineering usage-policy review: approved for a disabled-by-default metadata
pilot with local SEC contact metadata and one local test CIK required before
any live request. This is not legal advice and does not certify redistribution
rights.

## Official Owner And Purpose

- Official owner: U.S. Securities and Exchange Commission.
- Purpose: collect official filing metadata from the SEC EDGAR Submissions API
  for one locally supplied CIK at a time.
- Official API documentation:
  <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>
- Policy reference: <https://www.sec.gov/privacy.htm>

## Evidence Summary

The SEC API documentation identifies programmatic access to EDGAR submission
data. This milestone uses the documented submissions endpoint template only:
`https://data.sec.gov/submissions/CIK##########.json`. No API key or paid plan
is used. A declared User-Agent with locally supplied contact metadata is
required by this project before any SEC smoke request.

## Request Limits

The tracked source remains disabled. A live smoke request is allowed only when
`FINNEWS_SEC_CONTACT` and `FINNEWS_SEC_TEST_CIK` exist locally. The command uses
no-persist mode, one CIK, one GET request, at most five filings, a 2 MB decoded
response limit, and at least five seconds between SEC requests.

## Storage Policy

Store only filer/CIK metadata, form type, accession number, filing and
acceptance dates, primary document identifier, derived official filing URL,
provenance, hashes, and derived features. Do not store filing document bodies,
exhibits, HTML pages, raw JSON responses, complete headers, or personal contact
metadata.

## Attribution And Limitations

Metadata should attribute SEC EDGAR as the official source and keep official
links. SEC schemas and access expectations may change. Review approval and a
passing smoke test do not mean production readiness.

## Live Test Status

Status before prerequisite check: `not_run`.
