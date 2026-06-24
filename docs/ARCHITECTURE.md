# Architecture

Milestone 0 is a modular monolith with ports and adapters.

Milestone 3A adds a research-export application service that reads existing news metadata through repository ports and writes deterministic packages plus safe metadata. FinNews owns news provenance, information availability, event/sentiment metadata, feature lineage, and the export contract. The future `ashare-research-platform` owns prices, returns, backtests, and portfolio logic.

Revised Milestone 3A makes cross-asset information intelligence the primary architecture path. The A-share research export remains an optional downstream adapter.

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

## Milestone 2A NLP Evaluation Lab

```mermaid
flowchart LR
  Generator[Synthetic benchmark generator] --> Checks[Schema and leakage checks]
  Checks --> Train[Dummy, rule, and scikit-learn baselines]
  Train --> Reports[Evaluation and error reports]
  Train --> Artifacts[Ignored local model artifacts]
  Reports --> Registry[Safe model registry metadata]
  Reports --> API[Read-only NLP API]
  Reports --> Static[Static demo JSON]
  API --> Vue[NLP Evaluation page]
  Static --> Vue
```

Model binaries stay under ignored `.finnews-artifacts/`. The committed
benchmark and reports contain only original synthetic records and safe metadata.
The default news pipeline remains rule-based; Milestone 2A adds evaluation
tooling rather than production model activation.

## Revised Milestone 3A Cross-Asset Foundation

```mermaid
flowchart LR
  News[Normalized news metadata] --> Events[Cross-asset event families]
  Assets[Canonical asset registry] --> Impact[Impact hypotheses]
  Events --> Impact
  Impact --> Signals[Research signal candidates]
  Signals --> Contract[finnews-market-signal-v1]
  Contract --> Future[Future local bridge boundary]
```

The cross-asset layer adds domain entities for assets, aliases, provider symbols,
local broker-symbol mappings, relationships, events, impact hypotheses, signal
candidates, and publication runs. It keeps the dependency direction unchanged:
domain remains framework-free, application owns deterministic builders and
validators, infrastructure persists memory/PostgreSQL state, and interfaces
expose read-only API/CLI surfaces.

The MT5 boundary is documentation, validation, and readiness metadata only. The
repository contains no terminal adapter, no credentials, no account access, and
no execution path.

## Milestone 3C Market-Reaction Validation

```mermaid
flowchart LR
  Signals[Research signal candidates] --> Study[Point-in-time event studies]
  Bars[Synthetic or local validated bars] --> Study
  Study --> Labels[Reaction labels]
  Labels --> Metrics[Signal-quality metrics]
  Metrics --> API[Read-only API and CLI]
  API --> Vue[Market Reaction Lab]
```

M3C adds an application service for `finnews-market-bars-v1`, synthetic market
scenarios, event-study windows, reaction labels, signal-quality metrics, and
leakage diagnostics. Static demo output contains bounded samples for bars while
the API can generate the full deterministic in-memory synthetic bar set. The
new PostgreSQL migration stores metadata, revisions, labels, and metrics; it
does not store raw user files, credentials, account identifiers, or local import
paths.
