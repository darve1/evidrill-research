# Behavioral evaluation

These trials run a real agent with and without the skill and compare what it does and what it answers. Results and caveats are in [results.md](results.md).

## Tasks

| Task | Kind | What it tests |
| --- | --- | --- |
| `fixture-lumen` | fictional corpus, [examples/fixtures/research-corpus](../examples/fixtures/research-corpus/README.md) | 13 known traps; the files annotate their own dependencies, so this one is easy |
| `fixture-corvid` | fictional corpus, [fixtures/hard-corpus](fixtures/hard-corpus/README.md) | the same kinds of traps without the annotations, plus an embedded instruction aimed at AI summarizers |
| `real-trf` | live web, literature scope | time-restricted eating versus calorie restriction |
| `real-uv` | live web, `-tech-only` | whether uv is 10–100× faster than pip |

Each task file sets the prompt (Korean, as users write it), the allowed tools and, for fixtures, the materials copied into the workspace. Fixture rubrics (`tasks/*.rubric.md`) are never copied into a trial workspace.

## Running a trial

Requires the Claude Code CLI, signed in. Each trial costs model usage (roughly $0.10–$1.20 per run with Sonnet in our runs).

```text
python -X utf8 evals/run_eval.py --task fixture-corvid --variant worktree --invoke "evidrill -all" --label my-run
python -X utf8 evals/run_eval.py --task fixture-corvid --variant none --label my-baseline
python -X utf8 evals/run_eval.py --task real-uv --variant d1a97d4 --invoke "deep-research-tech-only" --label old-uv
```

- `--variant`: `none` (no skill), `worktree` (current files) or any git ref.
- `--invoke`: the skill and its options, without the leading slash; Git Bash rewrites `/name` into a file path.

The harness copies the variant into a fresh temporary workspace's `.claude/skills/`, so nothing is installed into your own skill folders. It runs `claude -p` with `--setting-sources project` and `--strict-mcp-config`, so your settings, hooks and MCP servers are not loaded.

Output goes to `evals/runs/<label>/`, which is ignored by git because live runs contain third-party page snapshots. It holds `transcript.jsonl`, `answer.md`, `metrics.json` and a copy of the workspace. `--resummarize <label>` recomputes the metrics from a transcript.

## Metrics

`metrics.json` records:
- cost, time, turns and tool calls
- helper commands by subcommand and their exit codes
- characters of files the agent wrote itself, and permission denials
- web searches and fetches, and helper downloads
- the trial's own final `check` of each study folder

These describe behavior, not truth.

## Grading

Quality is graded blind. Answers for one task are copied to `A.md`/`B.md`/`C.md` in random order, and the key is kept apart. A grader agent that is told not to open the run folders then grades them:
- **Fixtures:** each rubric item is scored 1 / 0.5 / 0.
- **Real topics:** the grader checks five decision-relevant claims per answer against the primary sources, and ranks the answers on directness, counterevidence, calibration and coverage.
