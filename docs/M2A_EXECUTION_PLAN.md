# Milestone 2A Execution Plan

## Current-State Audit

Branch setup:

- Starting branch before synchronization: `feat/approved-live-source-pilot`.
- `main` was fast-forwarded to `2adba68 Complete Milestone 1B verification`.
- Working branch for this milestone: `feat/nlp-evaluation-lab`.
- Local prompt files remain untracked and must not be edited, staged, moved, or committed.

Implemented baseline state:

- Milestone 0 provides the offline synthetic news pipeline, memory/PostgreSQL profiles,
  read-only API, CLI, static demo, Vue dashboard, and verification scripts.
- Milestone 1A provides safe source registry, mocked source ingestion, bounded HTTP,
  source health, API/CLI/frontend/static source views, and source-state persistence.
- Milestone 1B provides source-review evidence, disabled Federal Reserve/SEC pilot
  definitions, local-only smoke gates, read-only review API, and Source Catalog UI.
- Existing event and sentiment predictions are deterministic rule baselines.
- Existing event enum has 9 labels: `earnings`, `merger_acquisition`,
  `policy_regulation`, `operations_product`, `financing_capital`,
  `litigation_penalty`, `governance_personnel`, `macro_market`, `other`.
- Existing sentiment enum has 4 labels: `positive`, `neutral`, `negative`,
  `uncertain`.

Current implementation notes:

- `domain` is framework-independent and already stores rule provider names and
  versions on article event/sentiment entities.
- `application` owns pipeline/static export services and repository protocols.
- `infrastructure` contains rule NLP, memory/PostgreSQL repositories, source
  adapters, settings, and migrations.
- `interfaces` contains FastAPI and Typer entrypoints.
- PostgreSQL migrations currently stop at `0002_source_fetch_state`.
- Static demo is generated from memory data under `frontend/public/demo-data`.
- Vue has existing static/API data modes and no charting/UI framework.

## Scope

Milestone 2A implements a reproducible, synthetic-only NLP evaluation lab:

- `synthetic-finnews-nlp-v1` benchmark generation and validation.
- Leakage-safe train/validation/test split by template family and story group.
- Dummy, existing rule, and bounded scikit-learn baseline evaluation for event
  and sentiment tasks.
- Probability metrics, reliability bins, confidence/coverage, and abstention.
- Deterministic error-analysis reports.
- Trusted local artifact manifests under an ignored artifact root.
- Safe model/evaluation metadata registry in memory and PostgreSQL.
- Read-only NLP API endpoints, Typer CLI commands, Vue evaluation page, and
  deterministic static-demo JSON.

## Non-Goals

- No Milestone 2B external corpus acquisition or human annotation.
- No Milestone 3 A-share factor research.
- No Milestone 4 LLM evaluation.
- No live Federal Reserve, SEC, A-share, or copyrighted content for training.
- No public train/upload/infer/mutation API.
- No production-ready accuracy claim.
- No model binary committed to Git.
- No paid API, cloud database, hosted tracker, GPU stack, transformers, model
  weights, or external dataset download.

## Architecture Changes

- Add an NLP benchmark package under `backend/src/finnews/infrastructure/nlp/benchmark`.
- Add ML evaluation services under `backend/src/finnews/application/services`.
- Add registry domain entities for safe model and evaluation metadata only.
- Extend repository contracts with model/evaluation registry methods.
- Implement memory and PostgreSQL registry persistence.
- Add a migration `0003_nlp_model_registry`.
- Keep binary artifacts in an ignored local root, with committed manifests and
  reports containing only safe metadata.
- Keep default article processing behavior rule-based.

Dependency direction remains:

```text
domain -> application -> infrastructure/interfaces
```

The domain layer will not import FastAPI, SQLAlchemy, Typer, settings, pandas,
or scikit-learn.

## Benchmark Schema

Each record will include:

- `record_id`, `dataset_id`, `dataset_version`, `language`.
- `title`, `summary`, `combined_text`.
- `event_label`, `sentiment_label`.
- `company_id`, `fictional_ticker`, `industry`, `source_type`.
- `published_at`, `template_family_id`, `story_group_id`, `paraphrase_id`.
- `split`, `difficulty`, `challenge_flags`.
- `label_source`, `generator_version`.

`combined_text` is derived deterministically from title and summary. Metadata,
labels, split IDs, source IDs, company IDs, and challenge flags are not model
features.

## Benchmark Generation Formula

The benchmark target is exactly:

```text
9 event labels
x 4 sentiment labels
x 12 disjoint global template families
x 3 paraphrases
= 1,296 records
```

Required aggregate counts:

- Total: 1,296 records.
- Chinese: 864 records.
- English: 432 records.
- Train: 648 records from 6 template families.
- Validation: 324 records from 3 template families.
- Test: 324 records from 3 template families.
- Every event label, sentiment label, and event/sentiment combination represented.
- At least 36 fictional companies and 12 fictional industries.
- At least 324 challenge records, with at least 108 in test.

Generation will use stable loops and IDs rather than random row splitting. If a
seed is used, it will be fixed and documented.

## Leakage Controls

Automated checks will assert:

- Disjoint record IDs.
- Disjoint template families by split.
- Disjoint story groups by split.
- Paraphrase colocation within one split.
- Exact normalized text uniqueness and no exact overlap across splits.
- Near-duplicate groups remain in one split.
- Expected counts and label/language distributions.
- Deterministic regeneration and stable dataset/split hashes.
- No maintained real-company denylist hit.
- No label or challenge metadata in model feature text.
- Test-set lock manifest detects accidental post-evaluation mutation.

## Split Policy

Template families are globally assigned:

- Train: 6 families.
- Validation: 3 families.
- Test: 3 families.

Validation may be used for model selection, calibration decisions, and
abstention threshold selection. Test is evaluated after selections are frozen.

## Baselines And Candidates

Required systems for each task:

- `DummyClassifier`, documented strategy.
- Existing deterministic rule baseline.
- Character n-gram TF-IDF plus logistic regression.
- Word/character TF-IDF feature union plus logistic regression.

All scikit-learn candidates use fixed hyperparameters, fixed seeds, bounded
feature counts, and `n_jobs=1`. No grid search, embeddings, Chinese tokenizer
downloads, GPU, or external model weights are used.

Primary validation selection metric is macro F1. Tie-breakers are lower
calibration error, then lower complexity.

## Calibration Strategy

- Evaluate raw probabilities from selected classifiers.
- Fit post-hoc validation-only calibration only if it improves validation ECE.
- Report honest calibration status: retained raw probabilities or calibrated.
- Compute log loss, multiclass Brier score, ECE, reliability bins, and
  confidence/coverage.
- Select abstention threshold on validation only.
- Keep sentiment `uncertain` distinct from model abstention.

Required thresholds: `0.50`, `0.60`, `0.70`, `0.80`, `0.90`.

## Metric Definitions

For each task/system:

- Record count.
- Accuracy.
- Macro precision, recall, F1.
- Weighted F1.
- Per-class precision, recall, F1, support.
- Confusion matrix.
- Log loss and Brier score when probabilities exist.
- ECE and reliability bins when probabilities exist.
- Coverage, covered accuracy, covered macro F1, abstained count.
- Fixed test-set inference duration.
- Artifact size where applicable.

Slice metrics:

- Chinese and English.
- Every class.
- Difficulty levels.
- Every challenge flag.
- Short versus long text.
- High-confidence errors and low-confidence correct predictions.

## Error-Analysis Plan

Reports will include deterministic:

- Confusion-pair counts.
- Highest-confidence false predictions.
- Lowest-confidence correct predictions.
- Representative false positives/false negatives.
- Errors by language, challenge flag, and text length.
- Rule-versus-ML disagreements.
- Model-versus-dummy comparisons.
- Heuristic error categories only, without causal certainty claims.

## Artifact-Trust Model

- Local model binaries are written only under an ignored artifact root.
- Every artifact has a JSON manifest with model ID, task, dataset hash, split
  hashes, config hash, artifact SHA-256, size, created timestamp, and label set.
- Inference loads only registered artifacts whose path remains under the local
  artifact root and whose hash/metadata validate.
- No remote URL, arbitrary joblib path, unsupported format, tampered artifact,
  moved artifact, or task/label mismatch is accepted.
- Committed reports may include hashes and metrics, not binaries, vocabularies,
  sparse matrices, local absolute paths, personal usernames, secrets, or live
  text.

## Registry Schema And Migration Plan

Add safe metadata tables:

- `nlp_model_registry`
- `nlp_evaluation_runs`

Persist:

- Model/evaluation IDs, task, provider kind, status.
- Dataset ID/version/hash and split hashes.
- Safe model config, metric summaries, calibration summaries, slice summaries.
- Artifact hash, size, manifest hash, and relative artifact URI.
- Created/evaluated timestamps.

Do not persist:

- Model binaries.
- Sparse matrices.
- Full feature vocabulary.
- Raw live text.
- Absolute paths.
- Secrets.

Prediction provenance will be extended only as needed to distinguish rule/model
outputs while keeping existing records readable and default rule output
behaviorally equivalent.

## API, CLI, And Frontend Plan

CLI group:

- `finnews nlp dataset build`
- `finnews nlp dataset validate`
- `finnews nlp dataset summary`
- `finnews nlp train --task event|sentiment`
- `finnews nlp benchmark --task all|event|sentiment`
- `finnews nlp evaluate --task <event|sentiment> --model-id <id>`
- `finnews nlp compare --task <event|sentiment>`
- `finnews nlp registry list`
- `finnews nlp registry show --model-id <id>`
- `finnews nlp infer --task <event|sentiment> --model-id <id> --text <text>`
- `finnews nlp export-static`

Read-only API:

- `GET /api/v1/nlp/overview`
- `GET /api/v1/nlp/models`
- `GET /api/v1/nlp/models/{model_id}`
- `GET /api/v1/nlp/evaluations`
- `GET /api/v1/nlp/evaluations/{evaluation_id}`
- `GET /api/v1/nlp/error-analysis`

Frontend:

- Add `/nlp-evaluation`.
- Display synthetic disclaimer, benchmark/split counts, model comparison,
  selected models, per-class metrics, confusion matrices, reliability bins,
  coverage, slices, error examples, artifact metadata, and limitations.
- Support API and static-demo modes.
- No browser-side training, inference, live-source requests, binary links, or
  absolute paths.

## Test Matrix

Backend tests:

- Benchmark generation, deterministic hashes, schema, counts, labels,
  challenge distribution, fictional data checks.
- Split/leakage checks.
- Metric math fixtures.
- Model training/evaluation/candidate selection/calibration/abstention.
- Artifact security and manifest validation.
- Memory/PostgreSQL registry parity.
- CLI commands and safe output.
- Read-only NLP API endpoints and safe fields.
- Regression tests for M0/M1 source behavior and disabled real sources.

Frontend tests:

- NLP route rendering.
- Static/API data mode.
- Loading, empty, and error states.
- Disclaimers.
- Model comparison, per-class table, confusion matrix, calibration bins, slices,
  and error examples.
- No artifact path or production-ready claim.

## CPU, Memory, And Disk Budget

- CPU only.
- `n_jobs=1`.
- No pytest parallel workers.
- No GPU or dense conversion of unbounded sparse matrices.
- Benchmark below 5 MB.
- Each artifact below 25 MB.
- Total deliberate local artifacts below 100 MB.
- `verify-ml` should remain below five minutes when practical.
- Temporary matrices/artifacts from tests are cleaned.
- BLAS/OpenMP single-thread limits are set or documented in scripts.

## CI Plan

CI changes remain local files only:

- Preserve backend, frontend, sources, source-reviews, PostgreSQL, and Pages jobs.
- Add offline benchmark integrity/leakage checks and bounded NLP tests.
- Do not require secrets, live network, external data, model downloads, or model
  binary upload.
- Publish only synthetic static-demo JSON and Vue build artifacts.
- Do not claim remote GitHub Actions have run.

## Definition Of Done

Milestone 2A is done when:

- The 1,296-record benchmark is deterministic, versioned, and validated.
- Splits and test lock hashes pass leakage checks.
- Dummy/rule/ML systems are evaluated honestly.
- Calibration and abstention analysis exists.
- Error analysis, model cards, dataset card, registry docs, and release audit exist.
- Safe local artifacts and manifests validate.
- Memory/PostgreSQL registry parity passes.
- Default pipeline remains rule-based.
- Read-only API, CLI, Vue page, static export, CI files, and docs are updated.
- `verify-lite`, `verify-sources`, `verify-source-reviews`, `verify-ml`,
  `verify-postgres`, `git diff --check`, and final status checks pass.
- Docker resources are cleaned.
- No prompt files, live content, model binaries, `.env`, secrets, or files above
  limits are tracked.
- No push or PR is attempted.

## Deferred Work

- Milestone 2B: licensed or user-owned real-world corpus acquisition,
  provenance/license review, and human-reviewed annotation.
- Milestone 3: A-share factor research, calendar alignment, and leakage-safe
  market studies.
- Milestone 4: optional provider-based LLM extraction evaluation with cost
  controls and citations.
