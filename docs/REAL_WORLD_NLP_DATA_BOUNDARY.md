# Real-World NLP Data Boundary

Milestone 2A downloads no external corpus and assumes no license from public
availability. Federal Reserve, SEC, A-share, and other live-source output is not
a training corpus and is not used in the benchmark.

Future local adapters may accept user-owned or licensed JSONL/CSV labeled data,
but such data must remain explicit local input, include provenance and license
metadata, avoid tracked paths by default, and never access the network.

External dataset license review, annotation policy, and human-reviewed
benchmarks are deferred to Milestone 2B. Synthetic benchmark metrics must never
be used to infer real-world production accuracy.
