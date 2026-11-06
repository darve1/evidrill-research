# Reproducible, synthetic examples

The [raw corpus](fixtures/research-corpus/README.md) is fictional and written for this project. It includes repeated publications, a corrected percentage, different study populations, two studies in one paper, abstract-only access, version differences, circular news citations, and a survey denominator change.

The [evaluation rubric](fixtures/expected.md) distinguishes structural checks from semantic review. Keep it hidden from an agent performing a behavioral trial; review its actual output afterward.

Build a small illustrative ledger once (an existing output is never overwritten):

```text
python -X utf8 examples/build_demo.py --root examples/demo
python -X utf8 skills/deep-research/scripts/research_ledger.py stress --root examples/demo
python -X utf8 skills/deep-research/scripts/research_ledger.py render --root examples/demo
```

The demo is authored fixture data, not an independent agent evaluation. It intentionally returns exit 2 because general superiority remains unresolved. Its narrow observed claim can still be supported. All outputs retain `truth_certified:false`.

Expected user-facing interpretation: Lumen was reported at 90% versus Baseline's 80% on Small-X. The preprint and journal paper describe one experiment. A different Large-Y study reports 70% versus 75%. Removing the Small-X origin removes the recorded support for Small-X superiority; this does not prove that the claim is false. General superiority is not established by these records.
