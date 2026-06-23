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
- absence of prohibited execution fields.

Local generated packages must be written under `.finnews-market-signals/`, which is ignored by Git.

## Boundary

The contract is designed for downstream local research consumers. It contains no broker credentials, account identifiers, position sizing, protective levels, action fields, or route instructions. It is not investment advice.
