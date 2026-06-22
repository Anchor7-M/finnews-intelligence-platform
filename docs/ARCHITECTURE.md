# Architecture

Milestone 0 is a modular monolith with ports and adapters.

```mermaid
flowchart TD
  Domain[Domain entities and rules] --> Application[Application use cases and ports]
  Application --> Infrastructure[Infrastructure adapters]
  Application --> Interfaces[FastAPI and Typer]
  Infrastructure --> Memory[Memory repository]
  Infrastructure --> Postgres[PostgreSQL adapter and Alembic]
  Infrastructure --> Sources[Local JSONL and RSS fixtures]
  Interfaces --> Frontend[Vue dashboard]
```

```mermaid
flowchart LR
  Fixtures[Synthetic fixtures] --> Validate[Validate and normalize]
  Validate --> Exact[Exact duplicate hash]
  Exact --> Near[Bounded TF-IDF near duplicate]
  Near --> Link[Company alias linker]
  Link --> Classify[Event and sentiment baselines]
  Classify --> Persist[Memory or PostgreSQL]
  Persist --> API[FastAPI read API]
  Persist --> Static[Static demo JSON]
  API --> Vue[Vue dashboard]
  Static --> Vue
```

## Boundaries

- `domain` is framework-independent.
- `application` owns use cases and ports.
- `infrastructure` implements adapters.
- `interfaces` exposes HTTP and CLI entrypoints.

No microservices, paid APIs, telemetry, model downloads, or full-text article storage are used in Milestone 0.

The audited memory-profile vertical slice processes 68 raw observations into 46 canonical articles, 18 duplicate observations, 7 daily digests, and 46 daily company signals. PostgreSQL is represented by SQLAlchemy models and Alembic migration, but runtime integration is not verified without Docker.
