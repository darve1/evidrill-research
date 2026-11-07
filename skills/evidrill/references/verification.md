# Judging evidence

## Claim against passage

Open the source again and check, in order:

1. **Identity and time:** author, title, version or commit, publication date, the period the claim is about.
2. **Context:** the surrounding sentences, table titles and footnotes, negations, exceptions and hedges. `add` and `review` print the context around each quote; read it.
3. **Numbers:** units, population, sample, denominator, period and comparator. Recompute: 18/20 is 90%, and 90% versus 80% is not "twice as accurate".
4. **Meaning:** does the passage support all of the claim, part of it, or contradict it? Shared words can describe different things. One "not" reverses a sentence.
5. **Level:** author claim, static reading, your own execution, independent replication, or real-world use. An LLM's agreement is not an experiment.

A quote existing and a quote supporting the claim are separate facts. If a passage supports only part of a sentence, narrow or split the claim. Without support, keep the claim `unresolved`. Never turn DOIs, prestige, recency or source counts into a probability.

## Counterevidence searches

Before searching, write down what finding would change the conclusion, then search for it with at least two distinct queries.

| Claim type | Useful counter-searches |
| --- | --- |
| Accuracy or performance advantage | raw results, denominators, independent evaluations, failure cases, comparison conditions, data leakage |
| Currently supported or installable | release and deprecation notes, current configuration and dependencies, platform issues, execution reports |
| A paper's conclusion | corrections, retractions, later studies, failed replications, contrary results, other publications of the same study |
| Local, independent or free | default network dependencies, provider or API requirements, upstream data, terms of use |

Record only searches that ran. Access failures are their own status. "Not found" is limited to where you searched.

When sources conflict, keep both passages and compare version, population, method and time. Newer is not automatically right and the more authoritative source does not automatically win. Record why the conclusion was rejected, narrowed or made conditional, or that it remains unresolved.

## Origin removal

`stress` removes one recorded origin at a time and lists the support and counterevidence that remain. Losing all support is not proof that a claim is false. Several remaining origins can still share data, measurements or interests, so read what remains before judging `retained` or `narrowed`.

## Reporting

Give denominators: candidates found, sources read in full or relevant sections, abstract-only sources, key claims, reviewed pairs, supports/partial/contradicts/unresolved, origins, and what you actually executed. Partial support and unreviewed pairs are not successes. Duplicate sources and several answers from the same model are not independent evidence.
