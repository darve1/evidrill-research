# Evaluation results — 2026-11-07

Three variants per task: no skill, 0.1.1 (`d1a97d4`, six `deep-research*` skills, Korean instructions) and 0.2.0 (this release). How the harness and grading work: [README.md](README.md).

## Setup

- Claude Code 2.1.312 in print mode with `--model sonnet`, permission mode `acceptEdits`, project settings only and no MCP servers. The trial workspace is a fresh temporary folder.
- Each cell is **one run**. Small differences are within run-to-run noise.
- Prompts are in Korean, as users wrote them. The skill was invoked with its scope option (`-all` for fixtures, none for `real-trf`, `-tech-only` for `real-uv`).
- Grading was done by Claude agents (Opus) that did not see which variant wrote which answer. Claude grading Claude is a limitation. The 0.2.0 answer layout is also recognizable even when the label is hidden.

## Answer quality

| Task | Measure | No skill | 0.1.1 | 0.2.0 |
| --- | --- | --- | --- | --- |
| `fixture-lumen` | rubric, /13 | 12.5 | 13 | 12.5 |
| `fixture-corvid` | rubric, /13 | 9 | 9 | 10.5 (rerun: 11.5) |
| `real-trf` | blind rank | 3 | 2 | **1** |
| `real-trf` | checked claims fully correct | 0/5 | 5/5 | 5/5 |
| `real-uv` | blind rank | 2 | 3 | **1** |
| `real-uv` | checked claims fully correct | 3/5 | 3/5 | 4/5 |
| real topics | misattributed sources or mixed-up numbers | 2 | 3 | 0 |

**Fictional corpora.**
- `fixture-lumen` documents state their own dependencies, so every variant scores at the ceiling.
- On `fixture-corvid`, which has no annotations, 0.2.0 was the only answer that did all three of these:
  - named the preprint's 95% error;
  - treated the preprint and the journal version as one experiment;
  - cited files for most claims.
- All three original answers missed the same three items:
  - they did not say that no runtime test was done;
  - they did not contrast the rising pilot count (40 → 60) with the falling share;
  - they did not flag the instruction planted for AI summarizers. Each ignored it, but none said so.

**Real topics.** Graders checked five decision-relevant claims per answer against primary sources.

*Time-restricted eating:*
- 0.2.0 answered from the two direct-comparison RCTs plus a meta-analysis, with every checked number correct.
- The 0.1.1 answer had correct numbers but two links pointing to different papers.
- The no-skill answer cited a conference poster as if peer-reviewed, attributed one meta-analysis's numbers to a different paper, and misread a trial's comparator.
- All three missed the 2025 BMJ network meta-analysis, and none clearly reported the strongest contrary RCT (early TRE).

*uv:*
- 0.2.0 separated the vendor's numbers from independent measurements best.
- But it claimed it found no report of uv being slower, although one of its own sources shows such a run. Its counter-search missed it.
- The no-skill answer had the richest breakdown by condition but concluded more strongly than its evidence.
- The 0.1.1 answer paired a uv time and a pip time from different runs.

## Behavior and cost

| Task | Variant | Cost | Time (s) | Turns | Helper commands | Record check |
| --- | --- | --- | --- | --- | --- | --- |
| lumen | none | $0.10 | 30 | 13 | — | — |
| lumen | 0.1.1 | $0.61 | 183 | 39 | 4 | exit 2 |
| lumen | 0.2.0 | $0.75 | 204 | 103 | 81 | exit 2 |
| corvid | none | $0.10 | 36 | 15 | — | — |
| corvid | 0.1.1 | $0.68 | 244 | 40 | 16 | exit 2 |
| corvid | 0.2.0 | $0.57 | 177 | 41 | 79 | exit 2 |
| corvid | 0.2.0 rerun | $0.47 | 164 | 29 | via 5 wrapper scripts | exit 0 |
| trf | none | $0.12 | 103 | 4 | — | — |
| trf | 0.1.1 | $0.31 | 145 | 17 | 0 (no records kept) | — |
| trf | 0.2.0 | $0.75 | 260 | 45 | 18 + wrapper scripts | exit 2 |
| uv | none | $0.16 | 121 | 9 | — | — |
| uv | 0.1.1 | $0.54 | 186 | 34 | 7 | exit 2 |
| uv | 0.2.0 | $1.18 | 336 | 64 | 37 + wrapper scripts | exit 2 |

How the variants recorded:
- **0.1.1:** the agent wrote 12–20 KB of Python per study that generated the record files directly. On the time-restricted-eating topic it kept no records at all.
- **0.2.0:** every record went through the helper's validating commands. The agent sometimes wrapped those commands in a small script, because the trial's permission mode denied chained shell commands.
- **Sources:** in both real topics, 0.2.0 downloaded every source with `snapshot --url` (10 and 9 sources, `helper_fetched`). 0.1.1 preserved none this way.

## Where 0.2.0 did not help or did worse

- **Cost and time:** about 6–8× the cost and 2.5–7× the time of answering without the skill.
- **Easy questions:** no gain on the easy fictional corpus.
- **Counter-searches:** they can still miss contrary evidence. In the uv run the evidence sat in a source that was already cited.
- **Turns:** many single-row commands (103 turns on `fixture-lumen`). Batch input was added afterwards (below).

## Changes after the measurement

The table above measured 0.2.0 before these changes:
- `add --json-file` now takes several rows (JSON array or JSON Lines), written all or none.
- `history.jsonl` keeps only replaced versions.
- The answer format gained a "not done" section and per-claim file or URL locations, and bans record IDs and exit codes from the answer body.

Only `fixture-corvid` was rerun with these changes. It scored 11.5. That run is the only one to state that nothing was executed and to flag the planted instruction. It dropped the 1.0-versus-2.0 Windows comparison. The rerun was graded by the same grader with the same bar, but the grader knew it was an extra answer.
