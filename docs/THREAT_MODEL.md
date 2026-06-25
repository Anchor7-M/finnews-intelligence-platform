# Threat Model

## M4A Local MT5 Read-Only Bridge

The MT5 bridge is a local-only optional integration. Primary risks are
accidental credential capture, accidental account/order/position access,
terminal metadata leakage, local path leakage, and accidental evolution into an
execution surface.

Controls:

- `MetaTrader5` is not a required dependency and is dynamically imported only
  inside gated local CLI execution.
- API and frontend routes cannot load local symbol maps, initialize terminals,
  or export bars.
- Symbol-map validation rejects credentials, account identifiers, terminal
  paths, order fields, trade sizing, price/order fields, and execution flags.
- CI is blocked from terminal access.
- Exports must stay under ignored `.finnews-mt5-readonly-exports/`.
- Trading-surface audit fails on forbidden account, order, position, history,
  margin/profit, order-check, and order-send functions in production paths.

## Research Export

Research-export risks include lookahead leakage, backfill leakage, accidental article-text export, local-path leakage, false official-calendar claims, and market-data scope creep. Mitigations include explicit information-availability timestamps, cutoff timestamps, leakage audit, no-text lineage, synthetic flags, local ignored exports, and a documented boundary with the future A-share research repository.

## Risks

- Untrusted metadata in local imports.
- Malicious URLs and tracking parameters.
- Oversized files.
- Malformed XML/JSON.
- Log injection.
- HTML/script text in titles or snippets.
- Dependency supply-chain issues.
- Secret commits.
- Path traversal in CLI import/export.
- SQL injection.
- Future SSRF from live adapters.
- Live-source SSRF, redirect, oversized response, unsafe XML, and response-body leakage.
- Stale or missing source-review evidence.
- Accidental commit of local live-source override, smoke report, or personal SEC contact.
- Browser-side live-source fetches.
- Copyright and provenance mistakes.
- Untrusted model artifact loading.
- Synthetic benchmark leakage into train/validation/test splits.
- Misrepresenting synthetic NLP metrics as real-world performance.
- Cross-asset scope creep into live prices, broker credentials, account access,
  or execution behavior.
- Provider-symbol confusion causing incorrect downstream mapping assumptions.
- Accidental commit of local broker-symbol maps.
- Lookahead leakage from future bars, future-return sentinel columns, local
  import path exposure, and overclaiming synthetic market-reaction diagnostics.

## Mitigations

- File-size checks for fixture inputs.
- Absolute HTTP(S) URL validation and tracking-parameter removal.
- XML parsed from local fixtures only.
- Vue template escaping.
- SQLAlchemy parameterization.
- `.env` ignored and `.env.example` safe.
- No full article bodies stored in Milestone 0.
- Deterministic malformed fixture records verify invalid URL, language, timestamp, missing title, and malformed JSONL handling.
- Milestone 1A validates approved hostnames, enforces HTTPS for live sources,
  blocks private/loopback/link-local/multicast/unspecified IP destinations,
  revalidates redirects, caps decompressed responses, rejects DTD/entity XML,
  persists only validators/metadata/snippets, and exposes no public mutation or
  arbitrary URL fetch API.
- Milestone 1B requires typed source-review evidence, source config digests,
  ignored local overrides, explicit live env and confirmation gates, no-persist
  smoke-test defaults, SEC contact redaction, and read-only API review
  summaries.
- Milestone 2A keeps model binaries under ignored `.finnews-artifacts/`, loads
  only hash-verified local artifacts under that root, commits only synthetic
  benchmark/report data, validates split leakage, and labels every metric as
  synthetic-only.
- Revised Milestone 3A uses canonical asset IDs, namespace-specific aliases,
  offline symbol-map validation, read-only API/CLI surfaces, ignored
  `.finnews-market-signals/`, ignored local symbol maps, readiness checks, and a
  trading-surface audit. The current codebase contains no terminal adapter, no
  credentials, no account access, and no execution path.
- Milestone 3C validates local market-bar files with strict schemas, UTC
  timestamps, monotonic/duplicate checks, size bounds, forbidden-field checks,
  point-in-time `available_at` logic, null/planted/regime synthetic scenarios,
  leakage diagnostics, read-only API routes, and bounded static bar samples.
  Local import paths and raw user market-data files are not committed.
- Milestone 4B-0 keeps paper execution independent from MT5 and broker systems.
  Paper order intents reject broker/account/credential/terminal/order-ticket
  fields, manual approval is simulated with synthetic local actors only, fills
  use synthetic/local bars, API routes are read-only, and the surface audit
  checks that no real order, account, position, `order_check`, or `order_send`
  path is introduced.
