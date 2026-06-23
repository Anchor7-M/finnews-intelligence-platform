# Milestone 3A Release Audit

Status: local release audit completed on `feat/research-export-contract`.

Milestone 3A implements a deterministic, synthetic, point-in-time research export contract for downstream research consumers. It does not fetch market data, prices, returns, real exchange calendars, paid APIs, cloud resources, model weights, or copyrighted article bodies.

## Release Ledger

The tracked deterministic ledger is:

`contracts/finnews-research-export/v1/examples/synthetic-demo/release-ledger.json`

Exact ledger summary:

- Contract: `finnews-research-export-v1` version `1.0.0`
- Feature schema: `news-factor-v1`
- Export id: `synthetic-news-factor-demo-v1`
- Calendar: `synthetic-ashare-demo-calendar` version `2026-demo-v1`
- Calendar timezone: `Asia/Shanghai`
- Calendar hash: `404cb8a3bc356d40b308eaf870469a6653be264995d39c819d286947e54290d4`
- Synthetic holidays excluded from the 60-session span: `2026-05-12`, `2026-05-15`, `2026-06-19`, `2026-07-06`
- Session span: `2026-05-11` to `2026-08-06`
- Package content hash: `c5269bbabed8afec2cf014a48d53b4a7515dc4c51a80926539084a5cc06a21c5`
- Manifest sha256: `2719d54cea1d2055fd54eca6696e038b384d6221eb6212d3cac796dfc85b222a`
- File count: 7 content files plus `manifest.json`

Package hash construction is SHA-256 over the newline-joined ordered string:

`calendar.csv:{sha256}\ncompanies.csv:{sha256}\nfeature_rows.csv:{sha256}\nfeature_rows.jsonl:{sha256}\nlineage.jsonl:{sha256}\nquality_report.json:{sha256}\nleakage_audit.json:{sha256}`

The validator independently recomputes this value from manifest-declared file hashes and rejects mismatches.

## Dataset Accounting

- Sessions: 60
- Companies: 12 fictional companies
- Windows: 1, 3, 5, 10 sessions
- Dense feature rows: 2,880
- Expected dense rows: `60 * 12 * 4 = 2,880`
- Rows with news: 349
- Rows without news: 2,531
- Lineage rows: 874
- Excluded observations: 0
- Event provider/version: `keyword_event_classifier:1`
- Sentiment provider/version: `keyword_sentiment_analyzer:1`

Rows by window:

| Window | Feature Rows | Rows With News | Lineage Rows |
| --- | ---: | ---: | ---: |
| 1 | 720 | 28 | 46 |
| 3 | 720 | 64 | 138 |
| 5 | 720 | 96 | 230 |
| 10 | 720 | 161 | 460 |

Source ingestion accounting remains unchanged from Milestone 2A:

- Raw observations: 68
- Rejected observations: 4
- Valid observations: 64
- Canonical articles: 46
- Exact duplicate observations: 8
- Near-duplicate observations: 10
- Duplicate observations: 18
- PostgreSQL `articles`: 56 records, retaining 46 canonical and 10 near-duplicate article records

## Evidence Table

| Area | Status | Evidence |
| --- | --- | --- |
| Branch ancestry | PASS | Branch `feat/research-export-contract` remains based on `origin/main` from Milestone 2A. |
| Prompt files | PASS | Milestone prompt files remain untracked and unchanged. |
| Contract files | PASS | Versioned contract is under `contracts/finnews-research-export/v1/`. |
| Schema coverage | PASS | Manifest, calendar, company, feature-row, and lineage-row schema examples are tested. Calendar/company schema omissions found during audit were fixed. |
| UTF-8 package files | PASS | Writer emits deterministic UTF-8 CSV, JSON, and JSONL files. |
| Timestamp policy | PASS | Calendar imports reject naive timestamps; package timestamps are RFC3339 timezone-aware. |
| Calendar size/encoding limits | PASS | Local import rejects non-UTF-8 and oversized calendar files. |
| Calendar ordering | PASS | Duplicate dates, nonmonotonic sequence, invalid timezone, missing fields, and invalid open/break/close ordering are tested. |
| Synthetic calendar | PASS | 60 sessions, Asia/Shanghai, four explicit synthetic holidays in range, no official-calendar claim. |
| Cutoff boundary | PASS | Exactly `2026-05-11T09:15:00+08:00` assigns to `2026-05-11`; one microsecond after assigns to `2026-05-13`. |
| Availability formula | PASS | Manifest records `max(source_published_at, first_seen_at)`; tests confirm `generated_at` is not used in feature or lineage rows. |
| Dense panel | PASS | `60 * 12 * 4 = 2,880`; feature-row keys are unique. |
| Feature formulas | PASS | Unit proof covers counts, shares, entropy, mean/std, confidence-weighted score, and half-life decay. |
| CSV/JSONL equivalence | PASS | Package validator compares normalized `feature_rows.csv` and `feature_rows.jsonl`. |
| Package hash | PASS | Validator recomputes ordered content hash and rejects mismatches. |
| Manifest path safety | PASS | Manifest file paths must be exact package filenames; traversal and unexpected paths are rejected. |
| Missing package files | PASS | Validator rejects missing declared package files. |
| Atomic writer | PASS | Writer uses temp directory replacement and rejects non-empty output directories. |
| Article text policy | PASS | Exported feature/lineage files omit title, body, summary, URL, raw response, and source response fields. |
| Lineage reconciliation | PASS | Included lineage rows link to dense feature rows by `feature_row_key`; all included information timestamps are at or before decision cutoff. |
| Leakage audit | PASS | `leakage_audit.json` status is `passed`, 2,880 rows checked, 874 links checked, 0 violations. |
| Static demo | PASS | Research static JSON regenerated with the same calendar/package hashes as the contract example. |
| API/CLI | PASS | Research API/CLI contract tests run in `verify-research-export` and full `verify-lite`. |
| Frontend | PASS | ESLint, Prettier check, TypeScript, Vitest, and production build passed. |
| PostgreSQL migrations | PASS | Alembic upgraded through `0004_research_export_metadata`; downgrade and re-upgrade paths passed. |
| PostgreSQL research parity | PASS | Integration test persists 60 sessions, 2,880 feature rows, 874 lineage rows, then repeats persistence idempotently. |
| Docker cleanup | PASS | `finnews_m3a_verify` container, volume, and network were removed after verification. |
| CI workflows | NOT RUN | GitHub Actions are configured locally but were not executed remotely. |
| Push/PR | NOT RUN | No push or pull request was created. |

## Verification Commands

Completed locally:

- `.\.venv\Scripts\python scripts/dev.py verify-lite`
- `.\.venv\Scripts\python scripts/dev.py verify-research-export`
- `.\.venv\Scripts\python scripts/dev.py verify-postgres`
- `git diff --check`

Verification results:

- Backend lightweight suite: 118 passed, 8 skipped, 1 warning
- Backend coverage: 83.12%, above the 80% threshold
- Research export focused suite: 16 passed, 1 warning
- PostgreSQL integration suite: 8 passed, 118 deselected, 15 warnings
- Ruff check: passed
- Ruff format check: passed
- mypy: passed, 74 source files
- Frontend ESLint: passed
- Frontend Prettier check: passed
- Frontend TypeScript check: passed
- Vitest: 11 passed across 3 files
- Vue production build: passed
- Memory demo command: passed
- `git diff --check`: passed, with Git EOL warnings only

## PostgreSQL Notes

`verify-postgres` used the local `postgres:16` image with project name `finnews_m3a_verify` and localhost port `127.0.0.1:55432`. The standard pipeline-count printout before the research metadata test showed 56 persisted `articles`, 68 `observation_dispositions`, 46 `article_events`, 46 `article_sentiments`, 7 `daily_digests`, and 46 `daily_company_signals`. The dedicated research export metadata parity test then persisted and checked the research tables.

After verification, Docker reported no remaining `finnews_m3a_verify` containers, volumes, or networks.

## Known Limits

- The calendar is synthetic and not an official exchange calendar.
- Features are deterministic metadata features from synthetic news, not prices, returns, labels, recommendations, or backtest inputs.
- GitHub Actions were not run remotely.
- The platform remains research tooling and does not provide investment advice.
