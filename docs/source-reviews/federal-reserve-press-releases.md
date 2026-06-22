# Federal Reserve Board RSS Review

Source ID: `federal-reserve-press-releases`

## Decision

Engineering usage-policy review: approved for a disabled-by-default metadata
pilot. This is not legal advice and does not certify redistribution rights.

## Official Owner And Purpose

- Official owner: Board of Governors of the Federal Reserve System.
- Purpose: collect official press-release RSS metadata, official links,
  timestamps, source IDs, and feed-provided summaries.
- Official documentation: <https://www.federalreserve.gov/feeds/feeds.htm>

## Evidence Summary

The Federal Reserve RSS page publishes feed URLs for Board content, including a
press-release feed. No authentication, API key, or payment requirement was
identified for the RSS feed page during this engineering review on 2026-06-22.

## Request Limits

The tracked source remains disabled. The smoke command is limited to a manual
local no-persist run, one initial GET, one optional conditional follow-up, at
most five parsed items, and a 2 MB decoded response limit. No linked
press-release pages are requested.

## Storage Policy

Store only title, official URL, source-provided ID, publication timestamp,
brief feed summary where present, provenance, hashes, and derived features.
Do not store linked page bodies, raw RSS responses, cookies, or complete
headers.

## Attribution And Limitations

Metadata should attribute the Federal Reserve Board as official owner and keep
official links. Feed availability, validators, and policy pages may change.
Review approval does not mean production readiness.

## Live Test Status

Guarded local smoke status: `passed` on 2026-06-22.

Safe metadata recorded:

- source ID: `federal-reserve-press-releases`
- host: `www.federalreserve.gov`
- request count: 2
- initial HTTP status: 200
- conditional behavior: `not_modified`
- decoded response bytes: 15042
- parsed item count: 5
- persistence mode: `no_persist`
- validators offered: ETag yes, Last-Modified yes

No raw response, item titles, item summaries, raw validators, complete headers,
or linked press-release page content are committed.
