# Evidrill Research

**Trace the evidence. Challenge the conclusion.**

A research skill for **Claude Code and Codex**. For the few claims an answer depends on, it keeps a copy of the source and the exact passage it read. It also runs at least two counterevidence searches per key claim, and shows what is left when one evidence origin is removed.

[한국어](README.ko.md) · [Evaluation](evals/results.md) · [Synthetic example](examples/README.md) · [MIT License](LICENSE)

## Install

**Claude Code:**

```text
/plugin marketplace add darve1/evidrill-research
/plugin install evidrill@evidrill
```

**Codex, or Claude Code without plugins** (Python 3.10+):

```text
git clone https://github.com/darve1/evidrill-research.git
cd evidrill-research
python -X utf8 scripts/install_skills.py --target both
```

Upgrading from 0.1.x, which installed `deep-research*` folders: add `--remove-legacy`. The old name collided with Claude Code's built-in `deep-research` skill. Only unmodified 0.1.x files are removed; details are in [compatibility](docs/COMPATIBILITY.md).

## Use

```text
/evidrill Does time-restricted eating beat plain calorie restriction for weight loss?
/evidrill -tech-only Is uv really 10-100x faster than pip?
$evidrill -all Should we adopt this method now?
```

Use `/` in Claude Code and `$` in Codex. With no option, the skill searches scholarly literature. `-tech` adds official docs, releases and code, `-community` adds forums and user reports, and `-all` adds the general web too. `-tech-only` and `-community-only` search one route only. Answers come in your language.

The answer starts with three lines: the answer, how much confidence the records allow, and the largest weakness. After that come claim cards, what was not done, and the search coverage with denominators. From a real trial (Korean prompt, translated):

> **Conclusion:** No evidence that time-restricted eating beats equal calorie restriction for weight loss; the two direct-comparison RCTs read found no significant difference.
> **Confidence:** low to moderate. Only the abstracts of the two key RCTs were read, and both trials are small.
> **Largest weakness:** the direct comparisons are small and unblinded; the confidence intervals cannot rule out a difference of several kilograms.

## Does it help?

Every cell is one Claude Code run with Sonnet. The real-topic answers were graded blind: answers shuffled, primary sources checked. Full method, numbers and caveats: [evals/results.md](evals/results.md).

| | No skill | 0.1.1 | 0.2.0 |
| --- | --- | --- | --- |
| Easy fictional corpus (rubric, /13) | 12.5 | 13 | 12.5 |
| Hard fictional corpus (rubric, /13) | 9 | 9 | 10.5 (rerun with the final answer format: 11.5) |
| Real topic: time-restricted eating (blind rank) | 3rd | 2nd | 1st |
| Real topic: uv vs pip (blind rank) | 2nd | 3rd | 1st |
| Checked real-topic claims fully correct | 3/10 | 8/10 | 9/10 |
| Misattributed sources or mixed-up numbers found | 2 | 3 | 0 |
| Cost per run | $0.10–0.16 | $0.31–0.68 | $0.57–1.18 |

Compared with answering without it, the skill costs about 6–8× as much and takes 2.5–7× as long. On the easy corpus it adds nothing. One run per cell is not enough to settle small differences.

## What it records

Each study is a folder in your project with these records:
- the searches actually run, including failed ones
- preserved source copies, which the helper downloads itself with `snapshot --url`
- quoted passages, checked against the preserved text and shown with their surrounding context
- claims, and a judgment for each claim–passage pair
- the counterevidence searches for each key claim
- origin-removal reviews

The helper validates every change and refuses one that would introduce an error. It does not judge meaning: `check` returns 0 when the recorded reviews are complete, 1 for record errors and 2 when review remains, and **every output keeps `truth_certified:false`**. See the [record fields](skills/evidrill/references/records.md) and the [synthetic example](examples/README.md).

## Develop

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), the [evaluation harness](evals/README.md), the [publication boundary](docs/PUBLICATION.md) and the [design provenance](docs/PROVENANCE.md).
