# Milestone 2A Final Release Audit

Date: 2026-06-23
Branch: `feat/nlp-evaluation-lab`
Audit commit baseline: `688874a Complete Milestone 2A verification`

Milestone 2A implements a synthetic NLP evaluation lab only. Labels are
synthetic generator-defined labels, not human annotations. Metrics are
benchmark-only metrics, not real-world accuracy. No model is production-ready.
The rule provider remains the default for ordinary ingestion. Milestone 2B
licensed or human-reviewed real-world evaluation is deferred. The platform is
research tooling and not investment advice.

## Evidence Table

| Requirement | Implementation evidence | Test/command evidence | Actual result | Status | Limitation |
| --- | --- | --- | --- | --- | --- |
| Repository ancestry | Branch `feat/nlp-evaluation-lab`; `origin/main` ancestor of `HEAD` | `git status --short --branch`; `git merge-base --is-ancestor origin/main HEAD` | Clean except untracked local prompt files before audit | PASS | Not pushed |
| Benchmark ledger | `reports/nlp/synthetic-finnews-nlp-v1/benchmark-ledger.json` | `finnews nlp release-audit` | 1,296 records; 1,772,778 bytes | PASS | Synthetic only |
| Split integrity | Template-family split policy; test lock | `leakage-audit.json`; `validate_benchmark_dir` | IDs, families, story groups, paraphrases disjoint across splits | PASS | Template-generated text shares boilerplate |
| Cross-split near duplicates | Character 5-gram Jaccard audit | `leakage-audit.json` | No pair at or above 0.92 warning threshold | PASS | Threshold is a release guard, not semantic proof |
| Feature leakage | Production pipeline uses `combined_text` only | `feature-audit.json`; unit tests | Hidden metadata sentinel changes do not change feature text | PASS | Visible synthetic company/ticker tokens remain in article text |
| Selection integrity | Train fit, validation selection/calibration/threshold, locked test evaluation | `selection-trace.json` | Test set marked unused for selection | PASS | Code can be rerun; test lock guards mutation |
| Baselines and candidates | Dummy, rule, char TF-IDF LR, word/char TF-IDF LR | `evaluation.json` | Both selected candidates are `word_char_tfidf_logreg` | PASS | Baselines are classical/local only |
| Calibration and abstention | Validation-only probability power scaling; thresholds 0.50-0.90 | `evaluation.json`; metric tests | Alpha 1.5 accepted for both tasks by validation ECE | PASS | No external calibration corpus |
| Promotion policy | Registry status allowlist | `evaluation.json`; model cards | Both models `demo_candidate`; none `production_ready` | PASS | Synthetic benchmark cannot justify production |
| Artifact security | Hash-verified local `.joblib` under ignored root | artifact audit and tests | 0 tracked binaries; local artifacts total 444,688 bytes | PASS | joblib safe only for trusted local artifacts |
| PostgreSQL registry | Migration `0003_nlp_model_registry` | `verify-postgres` | Upgrade, downgrade, re-upgrade and 7 integration tests passed | PASS | Remote CI not run |
| CLI/API/frontend | Typer NLP commands, read-only API, Vue route/static demo | NLP contract and frontend tests | CLI/API/static paths verified offline | PASS | No public train/upload/infer API |
| Cost/resource policy | CPU, `n_jobs=1`, ignored artifacts, no downloads | workflow/script inspection and verification | No paid API, GPU, cloud DB, model download, or live corpus | PASS | Uses local scikit-learn only |
| Release safety | No prompt, `.env`, secret, model binary, or live corpus tracked | `git ls-files`; `git diff --check`; artifact audit | Safety checks passed | PASS | Local prompt files remain untracked |

## Benchmark Ledger

- Dataset ID: `synthetic-finnews-nlp-v1`
- Dataset version: `1.0.0`
- Generator version: `m2a-v1`
- Total records: 1,296
- Languages: `zh` 864, `en` 432
- Splits: train 648, validation 324, test 324
- Event enum values: `earnings`, `merger_acquisition`, `policy_regulation`,
  `operations_product`, `financing_capital`, `litigation_penalty`,
  `governance_personnel`, `macro_market`, `other`
- Sentiment enum values: `positive`, `neutral`, `negative`, `uncertain`
- Event counts: each event label has 144 records
- Sentiment counts: each sentiment label has 324 records
- Event/sentiment combinations: each of 36 combinations has 36 records
- Template families: 12 families, 108 records each
- Story groups: 432 groups, 3 paraphrases each
- Difficulty: easy 432, medium 432, hard 432
- Challenge records: 432 total; train 216, validation 108, test 108
- Challenge flags: each of the 12 challenge flags appears 42 times
- Fictional companies: 36
- Fictional industries: 72 language-specific industry strings
- Fictional source types: 3
- Committed `records.jsonl` size: 1,772,778 bytes
- Dataset SHA-256:
  `5eba057ef83198c5a35d29da2c821a5624d813885806cab4f48ecb22dbda67aa`
- Split SHA-256:
  - train `78c03f095f38b7f40408e63c76924544659a3bbac1c34710f66a67cf5039fb7b`
  - validation `8dfe819e5dd65118175f400e99bc863c9bb162d5ce0cd717e3db693cdf97791c`
  - test `2f0b409caa29a341e122d1ff28b4f34b09208d0b6f2f0dff323b5d469657172b`
- Schema/config hash:
  `6b3af577cb07b90e24247e387316b8206b2c260ce768aa765cbf01bf75814903`

## Leakage And Determinism

- Deterministic regeneration: two clean temporary benchmark generations were
  byte-for-byte identical.
- Stable dataset and split hashes: PASS.
- Stable selected candidate, metrics, test predictions, and artifact hashes:
  PASS.
- Exact duplicate normalized text count: 0.
- Cross-split exact overlaps: none.
- Maximum cross-split near-duplicate similarities:
  - train/validation: 0.897281
  - train/test: 0.850374
  - validation/test: 0.819242
- Pairs at or above warning threshold 0.92: none.

Feature-leakage diagnostics:

- Hidden metadata sentinel test: PASS; changing `company_id`,
  `fictional_ticker`, `source_type`, `template_family_id`, `story_group_id`,
  `challenge_flags`, and `generator_version` did not change production feature
  text.
- Label-permutation negative control: event validation macro F1 0.101447;
  sentiment validation macro F1 0.168185.
- Metadata-only negative control: event validation macro F1 0.000000;
  sentiment validation macro F1 0.150887. This diagnostic is not the production
  feature path.
- Top-feature inspection found event/sentiment lexical cue tokens from the
  synthetic templates, but no exact label names, generator markers, split IDs,
  record IDs, or template/story IDs in the top positive features.
- Train+validation GroupKFold diagnostic by template family: event mean macro F1
  0.996912, std 0.004367; sentiment mean macro F1 1.000000, std 0.000000. The
  locked test set was not used.

## Model Metrics

Event task:

- Dummy baseline test: accuracy 0.111111, macro F1 0.022222.
- Rule baseline test: accuracy 0.777778, macro F1 0.755556.
- Candidate validation:
  - `char_tfidf_logreg`: macro F1 0.993822, ECE 0.597495
  - `word_char_tfidf_logreg`: macro F1 1.000000, ECE 0.534369
- Selected candidate: `word_char_tfidf_logreg`, by highest validation macro F1.
- Calibration: `probability_power_scaling`, alpha 1.5,
  `validation_alpha_improved_ece`; validation ECE 0.332359, test ECE 0.329020.
- Abstention threshold: 0.50, selected on validation.
- Locked test selected ML: accuracy 1.000000, macro precision 1.000000, macro
  recall 1.000000, macro F1 1.000000, weighted F1 1.000000, log loss 0.415803,
  Brier score 0.147753.
- Language slices: English 108 records, macro F1 1.000000; Chinese 216 records,
  macro F1 1.000000.
- Weakest class: all classes tie at F1 1.000000.
- Weakest difficulty: all difficulties tie at F1 1.000000.
- Weakest challenge slice by macro F1: `low_information` 0.333333 because
  slice macro F1 is computed over the full label set while the slice has support
  for only a subset of labels; accuracy is 1.000000.

Sentiment task:

- Dummy baseline test: accuracy 0.250000, macro F1 0.100000.
- Rule baseline test: accuracy 0.759259, macro F1 0.770784.
- Candidate validation:
  - `char_tfidf_logreg`: macro F1 1.000000, ECE 0.392800
  - `word_char_tfidf_logreg`: macro F1 1.000000, ECE 0.256287
- Selected candidate: `word_char_tfidf_logreg`, by validation macro F1 tie and
  lower validation ECE.
- Calibration: `probability_power_scaling`, alpha 1.5,
  `validation_alpha_improved_ece`; validation ECE 0.110114, test ECE 0.157792.
- Abstention threshold: 0.50, selected on validation. Sentiment `uncertain`
  remains a label, not abstention.
- Locked test selected ML: accuracy 1.000000, macro precision 1.000000, macro
  recall 1.000000, macro F1 1.000000, weighted F1 1.000000, log loss 0.180604,
  Brier score 0.050744.
- Language slices: English 108 records, macro F1 1.000000; Chinese 216 records,
  macro F1 1.000000.
- Weakest class: all classes tie at F1 1.000000.
- Weakest difficulty: all difficulties tie at F1 1.000000.
- Weakest challenge slice by macro F1: `alias_or_ticker` 0.750000 because slice
  macro F1 is computed over the full label set while the slice has subset
  support; accuracy is 1.000000.

## Promotion And Artifacts

- Event model: `m2a-event-word_char_tfidf_logreg`
  - Status: `demo_candidate`
  - Artifact size: 284,034 bytes
  - Artifact SHA-256:
    `59ff51deb0d5e70377bbeba980724ab4ed79c773aabd4da48cb56cce8adc7a99`
  - Manifest SHA-256:
    `5b8ce127c6d3cb096bc8bd11855cda60909f565165f9d5faff7bbb3b8c5a1561`
- Sentiment model: `m2a-sentiment-word_char_tfidf_logreg`
  - Status: `demo_candidate`
  - Artifact size: 160,654 bytes
  - Artifact SHA-256:
    `c0e6ae82fe2e51aabe03407732e776c4863a913e7e61032f11f90756ef3e79e1`
  - Manifest SHA-256:
    `3b94369825f1b4013f928fd9363712c72054cc31932cdb6c865d0fd2c0cb9899`
- Local artifacts: 2 artifacts, 444,688 bytes total.
- Tracked model binaries: 0.
- PostgreSQL stores metadata only; no artifact bytes or absolute artifact paths.
- API/frontend expose logical hashes, sizes, metrics, and statuses only.

Promotion gates:

- Dataset integrity passed: PASS
- Split/leakage checks passed: PASS
- No test-set selection: PASS
- Test macro F1 exceeds dummy by required margin: PASS
- No class has zero recall: PASS
- Chinese and English support/metrics present: PASS
- Artifact hash valid: PASS
- Model cards present: PASS
- Calibration/coverage report present: PASS
- No live content, secret, or binary tracked: PASS
- Final status: `demo_candidate` for both tasks; `production_ready` is forbidden
  and not used in Milestone 2A.

## Registry, CLI, API, And Frontend

- Migration `0003_nlp_model_registry` adds `nlp_model_registry` and
  `nlp_evaluation_runs` with primary keys, foreign key from evaluation to
  model, useful indexes, JSONB metadata fields, and timezone-aware timestamps.
- Memory and PostgreSQL repositories implement the same registry contract.
- Registration is idempotent for model and evaluation business keys.
- Default pipeline event/sentiment predictions remain rule-based; API startup
  and ordinary ingestion do not train models.
- CLI command tree includes dataset build/validate/summary, train, benchmark,
  evaluate, compare, registry list/show, infer, release-audit, and
  export-static.
- The public API exposes read-only NLP overview/model/evaluation/error-analysis
  endpoints. There is no public endpoint to train, upload, download artifacts,
  activate, delete, edit thresholds, edit benchmark records, or infer arbitrary
  text.
- The Vue `/nlp-evaluation` page displays benchmark counts, synthetic
  disclaimer, validation/test distinction, dummy/rule/ML comparison, per-class
  metrics, confusion matrices, reliability/coverage, language/challenge slices,
  bounded error examples, artifact hashes/sizes, limitations, loading/error
  states, static/API modes, and no production-ready claim.

## Verification

Final verification commands run after audit corrections:

- `python scripts/dev.py verify-lite`: PASS.
- `python scripts/dev.py verify-sources`: PASS.
- `python scripts/dev.py verify-source-reviews`: PASS.
- `python scripts/dev.py verify-ml`: PASS.
- `python scripts/dev.py verify-postgres`: PASS.
- `git diff --check`: PASS.

Final verification results:

- Backend lightweight tests: 102 passed, 7 PostgreSQL tests skipped, 1
  Starlette TestClient warning.
- Backend coverage: 84.52%, above the 80% gate.
- Ruff check, Ruff format check, and mypy: PASS.
- Frontend ESLint, Prettier check, TypeScript check, Vitest, and production
  build: PASS.
- Frontend Vitest: 3 files, 10 tests passed.
- Memory-profile demo: PASS with 46 articles, 12 companies, 7 digests, and 46
  daily company signals.
- Source verification: source config validation PASS, 37 source tests passed,
  and frontend Vitest 10 passed.
- Source-review verification: review validation PASS and 17 source-review tests
  passed.
- ML verification: benchmark build/validate PASS, 13 NLP-focused tests passed,
  benchmark run PASS, release-audit generation PASS, static NLP export PASS.
- PostgreSQL verification: Alembic head `0003_nlp_model_registry`, downgrade and
  re-upgrade PASS, 7 PostgreSQL integration tests passed.

Latest collected test inventory:

- Total backend test cases collected: 109.
- PostgreSQL-marked test cases: 7.
- NLP-focused test cases: 13.
- Benchmark-generation test cases: 3.
- Rule NLP baseline test cases: 4.
- Metric/calibration/artifact test cases: 2.
- Registry test cases: 1.
- Release-audit/leakage/artifact-security test cases: 2.
- CLI/API NLP contract test cases: 1.
- Frontend test cases: 10.

Docker cleanup:

- PostgreSQL verification uses Compose project `finnews_m2a_verify`, service
  `postgres`, image `postgres:16`, and localhost-only port `127.0.0.1:55432`.
- Verification removes task-created container, volume, and network with
  `docker compose -p finnews_m2a_verify down --volumes --remove-orphans`.

## Safety And Limitations

- No live Federal Reserve, SEC, A-share, or other external source data is used
  for training or evaluation.
- No copyrighted news corpus, paid API, cloud database, model download, GPU
  dependency, PyTorch, TensorFlow, transformers, or embedding stack is added.
- All included benchmark examples are original synthetic content.
- Synthetic templates intentionally contain lexical cues; the benchmark proves
  local evaluation plumbing and leakage controls, not production generalization.
- GitHub Actions are configured locally but were not executed remotely.
- No push or pull request has been attempted.
- Deferred work:
  - Milestone 2B: licensed or user-owned real-world corpus and human-reviewed
    evaluation.
  - Milestone 3: market/factor research with leakage-safe calendars.
  - Milestone 4: optional LLM extraction evaluation with explicit cost controls.
