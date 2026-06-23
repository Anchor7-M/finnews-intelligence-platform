# Market Signal Contract

`finnews-market-signal-v1` is the revised Milestone 3A local research handoff contract.

## Package Files

- `manifest.json`
- `assets.json`
- `event_impacts.jsonl`
- `signals.jsonl`

The committed example package lives under `contracts/finnews-market-signal/v1/examples/synthetic-demo`.

## Validation

The package validator checks:

- contract name and version;
- declared synthetic-data and no-execution flags;
- file names;
- file sizes;
- per-file SHA-256 hashes;
- package content hash;
- strict JSON schemas with `additionalProperties: false`;
- UTC/RFC 3339 timestamp ordering;
- asset, event, impact, and signal references;
- confidence and bounded-strength ranges;
- absence of prohibited execution fields.

Local generated packages must be written under `.finnews-market-signals/`, which is ignored by Git.

## Boundary

The contract is designed for downstream local research consumers. A signal candidate is not an order. It contains no broker credentials, account identifiers, position sizing, protective levels, action fields, route instructions, account data, terminal path, live price, or execution request. It is research tooling, not investment advice.
