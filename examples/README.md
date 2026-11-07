# Reproducible, synthetic examples

The [raw corpus](fixtures/research-corpus/README.md) is fictional and written for this project. It has these traps:
- repeated publications and a corrected percentage
- different study populations, and two studies in one paper
- abstract-only access and version differences
- circular news citations
- a survey whose denominator changes

The [community-scope files](fixtures/community-scope) cover reposts and an official reply. Both corpora are also used by the [behavioral evaluation](../evals/README.md).

[`demo/`](demo/report.md) is a study built with the helper's own commands, with fixed timestamps so it rebuilds byte for byte:

```text
python -X utf8 examples/build_demo.py --root my-demo
python -X utf8 skills/evidrill/scripts/research_ledger.py check --root examples/demo
python -X utf8 skills/evidrill/scripts/research_ledger.py render --root examples/demo
```

[build_demo.py](build_demo.py) shows the whole flow in under 90 lines. It initializes a study and snapshots three sources. It then adds queries, origins, evidence and claims in batches. It records reviews, two counter-searches per key claim, and origin-removal reviews.

The demo is authored fixture data, not an agent evaluation. `check` returns 2 on purpose: general superiority stays unresolved. The narrow Small-X claim is supported, and all outputs keep `truth_certified:false`.

The expected reading:
- Lumen was reported at 90% versus Baseline's 80% on Small-X, and the preprint and the journal paper describe one experiment.
- A different Large-Y study reports 70% versus 75%.
- Removing the Small-X origin removes the support for the Small-X result. That does not prove the result false.
- General superiority is not established.
