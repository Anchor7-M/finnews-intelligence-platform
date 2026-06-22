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

The audited memory-profile vertical slice processes 68 raw observations into 46 canonical articles, 18 duplicate observations, 7 daily digests, and 46 daily company signals. PostgreSQL integration is verified through disposable Docker.

## Milestone 1A Source Ingestion

```mermaid
flowchart LR
  Registry[YAML source registry] --> Gate[Approval and enabled gate]
  Gate --> HTTP[Bounded HTTP client]
  Gate --> Import[User JSON/CSV import]
  HTTP --> Parse[RSS/Atom or JSON mapping]
  Import --> Parse
  Parse --> Pipeline[Existing normalization/dedup pipeline]
  Pipeline --> State[Fetch state and attempts]
  State --> API[Read-only source API]
  State --> Vue[Source Health page]
```

The source layer is run-once and local-first. It introduces no scheduler, queue,
Redis, Kafka, search service, browser automation, or full-body cache.

## Milestone 1B Source Review And Smoke Testing

```mermaid
flowchart LR
  Config[Disabled source config] --> Integrity[Review integrity check]
  Review[Review evidence YAML] --> Integrity
  Override[Ignored local override] --> Gate[Smoke gate]
  Integrity --> Gate
  Gate --> HTTP[Bounded HTTP client]
  HTTP --> Parse[RSS or documented JSON parser]
  Parse --> Report[Sanitized no-persist report]
  Review --> API[Read-only review API]
  API --> Vue[Source Catalog]
```

Milestone 1B keeps approval evidence repository-owned and runtime enablement
local-only. The smoke path is explicit CLI-only, no-persist by default, and does
not introduce API mutation routes, schedulers, or browser-side live requests.
