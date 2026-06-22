# Model Registry

Milestone 2A stores safe model/evaluation metadata in memory and PostgreSQL:

- `nlp_model_registry`
- `nlp_evaluation_runs`

Stored fields include logical IDs, task, provider, model kind, status, dataset
hashes, split hashes, label sets, metrics, calibration summaries, slice
summaries, artifact hashes, artifact sizes, config hashes, and timestamps.

The registry does not store model binaries, sparse matrices, full vocabularies,
raw live text, absolute local paths, secrets, or user inference input. Model
binaries and local manifests are under ignored `.finnews-artifacts/`.
