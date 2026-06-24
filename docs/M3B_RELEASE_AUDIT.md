# Milestone 3B Release Audit

## Status

Milestone 3B implements official cross-asset source expansion for BLS, EIA,
CFTC COT PRE, and Federal Register API profiles. Tracked demo values are
synthetic. Official observations may be revised. Period date is not information
availability. This project is research tooling, not investment advice.

No consensus-surprise model exists. EIA pilot data excludes price data. COT
data does not prove individual trader intent. FederalRegister.gov is
informational and not the official legal edition. Live smoke data is not
persisted or published. Source approval is engineering review, not legal
certification. No MT5 connection or execution exists.

Machine-readable evidence:

- `reports/official-data/m3b-release-ledger.json`
- `reports/official-data/m3b-source-review-audit.json`
- `reports/verification/revised-m3a-timings.json`

## Terminology

| Term | Meaning | Count |
| --- | --- | --- |
| Official source definition | Reviewed disabled source config for BLS, EIA, CFTC, or Federal Register | 4 |
| Dataset definition | Physical `official_datasets` rows | 4 |
| Series definition | BLS/EIA `OfficialSeriesProfile` rows | 8 |
| Query profile | CFTC/Federal Register `OfficialSeriesProfile` rows | 8 |
| Definition count total | Logical series/query definition total, not physical dataset table count | 16 |
| Observation business key | Source + dataset + series/query + period + normalized dimensions | 144 |
| Observation revision row | Append-only revision row, including revision 1 and changed values | 168 |
| Current observation | One current row per observation business key | 144 |
| Superseded revision | Changed-value historical row retained for point-in-time access | 24 |
| Regulatory document | Federal Register-style metadata/abstract record, no full body or PDF | 32 |
| Association | Series/query-to-canonical-asset relevance hypothesis | 80 |
| Derived release event | Synthetic official release event preserving source provenance | 48 |

## Count Reconciliation

The previous summary reported `4 datasets`, `10 series`, `24 observations`,
`28 revisions`, and `32 release events`. That summary was not the acceptance
ledger. It mixed old preview/static counters with full-fixture terminology.

| Prior value | Source of mismatch | Correct result | Status |
| --- | --- | --- | --- |
| 4 datasets | Physical dataset table count; still valid only for `official_datasets` | Logical definitions are 16: 4 BLS, 4 EIA, 4 CFTC, 4 Federal Register | PASS |
| 10 series | Earlier profile fixture omitted 6 required profiles | `_profiles()` now emits 16 definitions | PASS |
| 24 observations | Earlier numeric fixture had 6 profiles x 4 periods | 12 numeric/position profiles x 12 periods = 144 business keys | PASS |
| 28 revisions | Earlier model had 24 first revisions + 4 changed revisions | 144 first revisions + 24 changed revisions = 168 physical rows | PASS |
| 32 release events | Earlier implementation only created document/preview events | 48 events: 12 initial observation, 24 revision, 12 regulatory document | PASS |

The storage model is explicit: `official_observations` stores one current row
per business key, while `official_observation_revisions` stores revision 1 plus
changed-value revisions. Therefore:

```text
144 observation business keys = 144 current observation rows
168 physical revision rows = 144 first revisions + 24 changed-value revisions
24 superseded revision rows = changed-value revisions
```

## Release Ledger

| Requirement | Implementation evidence | Test/command evidence | Exact result | Status | Limitation |
| --- | --- | --- | --- | --- | --- |
| Deterministic ledger | `build_official_data_release_ledger()` | `finnews official-data release-audit` | schema `m3b-release-ledger-v1`, generator `official-data-synthetic-v1` | PASS | None |
| Byte-identical regeneration | SHA-256 before/after command rerun | PowerShell `Get-FileHash` around two generation calls | ledger file hash `C774805CF32A42AA5B5EB8B3D1A8A4A1D95C4E73F57D0D91EE97C206DB01B708` unchanged | PASS | Internal `ledger_sha256` excludes its own field |
| Source definitions | Source registry + source audit | `official-data source-audit` | 4, all disabled, all reviews current | PASS | Engineering review only |
| Definitions | Synthetic official-data fixture | Unit/contract/Postgres tests | 4 datasets, 8 series, 8 query profiles, total 16 | PASS | Synthetic profiles |
| Observations | Numeric/position fixture generator | `validate-fixtures` | BLS 48, EIA 48, CFTC 48, total 144 | PASS | No live values |
| Revisions | Append-only revision service | Unit/as-of/Postgres tests | 168 rows, 24 changed-value revisions | PASS | Baseline fixture only |
| Documents | Federal Register fixture | Unit/API/static tests | 32, 8 per query profile | PASS | Metadata and source abstract only |
| Associations | Cross-asset asset mapping | Unit/static/API tests | 80, 20 per source | PASS | Relevance hypotheses, not direction |
| Derived events | Official-data event fixture | Ledger/API/static tests | 48, 12 per source | PASS | No market reaction labels |
| Static export | `official_data_static_payload()` | `verify-official-data` | static counts match ledger | PASS | Static demo only |
| PostgreSQL parity | `PostgresNewsRepository` + Alembic `0006_official_data` | `verify-postgres` and focused Postgres test | official-data counts match memory ledger | PASS | Disposable local Postgres only |

Deterministic ledger hashes:

- ledger content field: `dc9d27a571172f38e7e7e56708439844fc81e5818f4d5398f51a7903b80d0bb5`
- datasets: `ef226a5b4b12ef21701e5bff37eca9b8c96bb299641dcc724f67a12fcedba1b6`
- profiles: `f3ab9da69a215117f5a57365c2da200891b7f0e50a47ea30097309ba05cb19d4`
- observations: `482230ab5b5915d69c979f6d75173f6962974821d9b8860ac62f9c95aa3bddf3`
- revisions: `01c322401027515691f986c67b32bafd63a4145755908a681f8f32899a097103`
- documents: `07d6b1dddc2808df8aee209d05f1c0b07a05c96367395c9ffbf594854908b7cb`
- associations: `3690e3f6d8081ace8458ffb47e253b2f7e0d27c50db629e765f359cce823808b`
- events: `3f742c586d0377d54ca2054b15980fcae09d0797f644d530d113d449bfa80530`

## Source Review Audit

| Source | Decision | Enabled | Auth/cost | Methods | Digest | Live smoke | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bls-public-data` | approved | false | no-key v1, optional local `FINNEWS_BLS_API_KEY`; free | GET/POST/HEAD | current | NOT RUN | PASS |
| `eia-open-data-v2` | approved | false | local `FINNEWS_EIA_API_KEY`; free with key | GET/HEAD | current | NOT RUN, key-gated | PASS |
| `cftc-cot-pre` | approved | false | no token; free | GET/HEAD | current | NOT RUN | PASS |
| `federal-register-api` | approved | false | no key; free | GET/HEAD | current | NOT RUN | PASS |

The source audit reports approved hosts, endpoint patterns, request limits,
storage policy, known risks, evidence dates, and review/config digests. Unknown
fields, duplicate source/review IDs, stale digests, host mismatch, endpoint
mismatch, inline secret-like fields, and local override misuse are covered by
source registry/review tests. `FINNEWS_BLS_API_KEY` and `FINNEWS_EIA_API_KEY`
appear only as names; values are never stored.

## Adapter Audit

| Area | Implementation evidence | Test evidence | Status | Limitation |
| --- | --- | --- | --- | --- |
| BLS | POST JSON, v1 no-key path, optional local key, bounded series/year inputs, BLS-level error parsing, Decimal values, missing/footnote handling | `test_source_adapters.py`, official-data revision tests | PASS | No forecast surprise |
| EIA | API v2 route/facet/data parsing, local key gate, key redaction, non-price allowlist, row limits, Decimal parsing | `test_source_adapters.py`, `test_source_smoke.py` | PASS | Live use blocked without local key |
| CFTC | Reviewed dataset IDs, strict column/query allowlist, bounded limit/offset, schema-drift and duplicate handling, deterministic business keys | `test_source_adapters.py` | PASS | No trader-intent claim |
| Federal Register | No key, GET metadata profile, approved filters, document-number identity, title/abstract/links/CFR/RIN metadata, no PDF/body persistence | `test_source_adapters.py`, API/static tests | PASS | FederalRegister.gov is informational |

## Revision And Point-In-Time Audit

| Requirement | Evidence | Status |
| --- | --- | --- |
| First value creates revision 1 | `ingest_official_observation_records()` tests | PASS |
| Identical repeat creates no new revision | Unit replay and Postgres idempotency tests | PASS |
| Changed value appends one revision | 24 changed-value revisions in fixture | PASS |
| Historical value replay does not append | `test_observation_ingestion_order_does_not_change_point_in_time_history` | PASS |
| Prior revisions remain available | revisions API and repository tests | PASS |
| One current revision per business key | memory/Postgres repository constraints | PASS |
| Monotonic revision numbers and deterministic value hash | unit and integration tests | PASS |
| Period is not availability | API as-of test uses `information_available_at` | PASS |
| Source timestamp does not backdate availability | service timestamp policy tests | PASS |
| Naive/future timestamps rejected or handled by policy | official-data service tests | PASS |
| Input order is deterministic | records are sorted before ingestion; order-invariance test | PASS |
| As-of queries return historical value | API contract as-of assertion | PASS |

## Static, API, CLI, And Frontend

| Surface | Evidence | Exact result | Status |
| --- | --- | --- | --- |
| CLI | `summary`, `validate-fixtures`, `export-static`, `release-audit`, `source-audit`, `live-smoke` blocked by default | official-data contract tests pass | PASS |
| API | Read-only `/api/v1/official-data/*` endpoints | overview, datasets, series, observations, revisions, docs, associations, events tested | PASS |
| Static demo | `frontend/public/demo-data/official-*.json` | 4/16/144/168/32/80/48 counts | PASS |
| Frontend | Official Data Monitor route | Vitest 15 frontend tests pass | PASS |
| Public mutation/fetch | No official-data API mutation endpoint | contract review and route inspection | PASS |

Frontend notices include synthetic static demo, not investment advice, official
observations may be revised, period date is not availability, EIA price data is
excluded, COT intent caveat, Federal Register informational caveat, no live
smoke content, and no MT5/trading.

## PostgreSQL Audit

Alembic head is `0006_official_data`. `verify-postgres` upgraded from empty DB,
confirmed one head, downgraded, re-upgraded, checked schema types/constraints,
then ran all Postgres-marked tests under Compose project `finnews_m3b_verify`
with service `postgres` and image `postgres:16`.

Official-data first-run and repeated-run counts:

```text
official_datasets: 4 -> 4
official_series_profiles: 16 -> 16
official_observations: 144 -> 144
official_observation_revisions: 168 -> 168
regulatory_documents: 32 -> 32
series_asset_associations: 80 -> 80
official_release_events: 48 -> 48
official_data_release_runs: 4 -> 4
changed_value_revision_count: 24 -> 24
```

The generic M0 pipeline idempotency test remains unchanged:

```text
articles: 56 -> 56
canonical articles: 46
observation_dispositions: 68 -> 68
raw_articles: 64 -> 64
ingestion_runs: 68 -> 136
pipeline_runs: 1 -> 2
```

Append-only audit/run tables may increase where documented; official-data
business rows and revisions remain stable on replay. Docker cleanup was
verified with no `finnews_m3b_verify` containers, volumes, or networks
remaining.

## Verification

| Command | Result | Duration |
| --- | --- | --- |
| `python scripts/dev.py verify-lite` | PASS, backend coverage 84%, frontend build PASS | 634.0s |
| `python scripts/dev.py verify-sources` | PASS, source tests 38 passed | 22.5s |
| `python scripts/dev.py verify-source-reviews` | PASS, source-review tests 18 passed | 11.4s |
| `python scripts/dev.py verify-ml` | PASS, NLP tests 13 passed | 120.1s |
| `python scripts/dev.py verify-research-export` | PASS, research tests 16 passed | 45.7s |
| `python scripts/dev.py verify-cross-asset` | PASS, cross-asset tests 19 passed | 52.5s |
| `python scripts/dev.py verify-official-data` | PASS, official-data tests 11 passed, frontend 15 passed | 30.8s |
| `python scripts/dev.py verify-postgres` | PASS, 10 Postgres tests passed | 159.7s |
| Focused official-data backend tests | PASS, 11 passed | 15.9s |
| Focused Postgres official-data test | PASS, 1 passed with `FINNEWS_RUN_POSTGRES_TESTS=1` | 19.2s |

Backend test collection:

```text
160 backend tests collected
126 unit tests
24 contract tests
10 PostgreSQL integration tests
```

Official-data category coverage:

```text
fixture/accounting/revision/as-of unit tests: 9
CLI/API official-data contract tests: 2
PostgreSQL official-data integration case: 1
source/review/config/adapters/smoke tests: 37
frontend official-data/static mode assertions: covered inside 15 Vitest cases
```

Critical uncovered modules from the coverage report remain CLI branches,
selected API error paths, memory repository branches, and benchmark validation
edge cases. Total backend coverage is 84.29%, above the 80% gate.

## Secret, Live-Data, And Trading Surface

| Check | Evidence | Status |
| --- | --- | --- |
| No live data committed | Static files and reports are synthetic; no live smoke report tracked | PASS |
| No API key value tracked | `.env.example` uses names/placeholders; configs store env var names only | PASS |
| No local override tracked | `config/sources.local.yaml` is ignored and untracked | PASS |
| No prompt tracked | prompt files remain untracked | PASS |
| No full raw response/body/PDF | official-data rows store metadata, values, provenance, hashes only | PASS |
| Trading surface | revised M3A audit PASS, MT5 readiness not implemented, execution disabled | PASS |
| Cost | zero-cost local-first: no paid API, cloud DB, model download, live price, account, or order path | PASS |

## Limitations And Deferred Work

Known limitations:

- Live smoke remains manual, no-persist, and not run in this audit.
- Source approval is engineering review, not legal certification.
- The official-data fixture is deterministic synthetic data, not live official
  data.
- NLP and event logic remain deterministic baselines.
- GitHub Actions configuration is local evidence only until run remotely.

Deferred to M3C/M4 or later:

- market-reaction labels and event studies;
- consensus forecast/surprise modeling;
- licensed/live official data persistence policies;
- live price ingestion;
- read-only MT5 terminal bridge;
- demo execution, orders, accounts, risk controls, and any trading workflow.
