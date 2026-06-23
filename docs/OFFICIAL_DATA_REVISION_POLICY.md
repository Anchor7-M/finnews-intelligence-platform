# Official Data Revision Policy

Official numeric observations use append-only revisions.

For each observation business key:

- first value creates revision `1`;
- identical repeated value is idempotent and creates no new revision;
- changed value appends revision `n + 1`;
- the current observation row points to the latest revision;
- previous revisions remain queryable;
- revision rows retain provenance and quality flags.

The policy supports synthetic fixtures, mocked adapters, memory repositories,
and PostgreSQL. It does not infer forecast surprises, market reactions, or
investment signals.
