# NLP Evaluation

Milestone 2A evaluates event and sentiment tasks independently.

Systems:

- Dummy baseline: scikit-learn `DummyClassifier(strategy="most_frequent")`.
- Rule baseline: existing deterministic keyword event/sentiment code.
- ML candidates: character TF-IDF logistic regression and word/character TF-IDF logistic regression.

Selection uses validation macro F1, with lower calibration error and lower
complexity as tie-breakers. Test metrics are generated after selection and
thresholds are frozen.

Reports live under `reports/nlp/synthetic-finnews-nlp-v1/` and include
synthetic-only metrics, calibration, coverage, slices, and deterministic error
analysis. Metrics describe this benchmark only.
