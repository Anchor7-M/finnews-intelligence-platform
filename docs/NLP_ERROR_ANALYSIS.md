# NLP Error Analysis

Milestone 2A error analysis is deterministic and synthetic-only. It reports
confusion-pair counts, highest-confidence false predictions, lowest-confidence
correct predictions, language slices, challenge slices, and rule/ML
disagreements.

On the committed synthetic test split, the selected ML event and sentiment
models make no false predictions. This is a property of the generator-defined
benchmark and must not be interpreted as real-world accuracy. Low-confidence
correct predictions are still reported to show calibration and confidence
limitations.
