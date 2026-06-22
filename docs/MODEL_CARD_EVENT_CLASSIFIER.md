# Model Card: Event Classifier

- Model ID: `m2a-event-word_char_tfidf_logreg`
- Task: event classification
- Provider: local scikit-learn
- Candidate: word/character TF-IDF feature union plus one-vs-rest logistic regression
- Dataset: `synthetic-finnews-nlp-v1`
- Status: `demo_candidate`
- Test macro F1: 1.000000 on the synthetic test split
- Test accuracy: 1.000000 on the synthetic test split
- Calibration: validation-selected probability power scaling, alpha `1.5`
- Abstention threshold: `0.50`, selected on validation

This model is a synthetic benchmark demo candidate only. It is not production
validated, not human-labeled, and not investment advice. It must not be used to
claim real-world financial-news accuracy.
