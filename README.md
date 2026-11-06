# Evidrill Research

**Trace the evidence. Challenge the conclusion.**

A research skill for **Codex and Claude Code** that links claims to preserved source passages, searches for counterevidence, and shows what remains when a decisive evidence origin is removed.

[한국어](README.ko.md) · [Synthetic example](examples/README.md) · [MIT License](LICENSE)

## Choose a research scope

The project is called Evidrill Research. Its installable skills use the `deep-research` names below.

| Select this skill | Source scope |
| --- | --- |
| `deep-research` | **Default:** papers, journals, conferences and scholarly literature |
| `deep-research-tech` | Academic literature + technical/open-source sources |
| `deep-research-tech-only` | Technical/open-source sources only |
| `deep-research-comu` | Academic literature + community reports |
| `deep-research-comu-only` | Community discussions, Q&A and user reports only |
| `deep-research-all` | Academic + technical + general web + community |

Select a skill and ask your question normally. The base skill also accepts `-tech`, `-tech-only`, `-comu`, `-comu-only` and `-all`. Combine `-tech -comu` for academic + technical + community. Exclusive `-only` options cannot be combined with other scope flags. See the [scope rules](docs/COMMUNITY_MODES.md).

```text
$deep-research Research this topic using scholarly literature and counterevidence.
$deep-research-tech Include implementation details and open-source projects.
$deep-research-comu-only Investigate community experiences with this approach.
$deep-research-all Explore the topic across all supported source routes.
```

These examples use Codex's `$` invocation. In Claude Code, use `/deep-research` or the corresponding `/deep-research-*` entry. In apps with a skill picker, select the name there. All-source research reports access limits and missing routes; it does not promise exhaustive internet coverage.

## What you get

- Conclusion cards with supporting and opposing passages, exact source locations and versions.
- Separate records for publications and underlying evidence origins, including shared dependencies.
- Origin-removal scenarios showing which recorded evidence remains, alongside actual reviewer judgments.
- Explicit scope, unresolved issues and the next useful check.

For example, two papers can describe the same experiment. Removing that experiment removes both records together. A different experiment that reports a contrary result remains visible. The [fictional example](examples/README.md) makes this behavior reproducible.

## Install

```text
git clone https://github.com/darve1/evidrill-research.git
cd evidrill-research
python -X utf8 scripts/install_skills.py --target both
```

Choose `--target codex`, `--target claude` or `--target both`. Defaults are `~/.agents/skills` for Codex and `~/.claude/skills` for Claude Code. The installer copies all **six sibling folders**, checks their hashes and preserves unrelated files. `--dry-run` previews without writing. Existing files with different contents stop the entire preflight; they are never overwritten.

If you already use `~/.codex/skills`, keep that installation in place with `--target codex --skills-dir "~/.codex/skills"` and install Claude separately. Avoid duplicate names in both Codex locations. Custom and project directories, updating an existing install, and verification limits are covered in [compatibility and installation](docs/COMPATIBILITY.md).

Start a new session if the skill does not appear, then try:

| Host | Example prompt |
| --- | --- |
| Codex | `$deep-research -all Research this topic and its counterevidence.` |
| Claude Code | `/deep-research -all Research this topic and its counterevidence.` |

Helpers require Python 3.10+ and its standard library. The skill uses your agent's existing search/file tools and does not require an additional API key. Model and search-service costs depend on your environment. Local file tests do not verify the app's picker refresh behavior.

## Local helpers

```text
python -X utf8 skills/deep-research/scripts/research_ledger.py init --root research/my-study --question "Research question"
python -X utf8 skills/deep-research/scripts/research_ledger.py snapshot --root research/my-study --input source.txt --source-id s1 --format text
python -X utf8 skills/deep-research/scripts/research_ledger.py check --root research/my-study
python -X utf8 skills/deep-research/scripts/research_ledger.py stress --root research/my-study
python -X utf8 skills/deep-research/scripts/research_ledger.py render --root research/my-study
```

An initialized study is empty. The agent must perform research and write the [source, evidence and review records](skills/deep-research/references/records.md); the helper itself is not a web crawler or semantic judge.

`check`, `stress` and `render` return 0 for recorded review completion, 1 for integrity errors, and 2 for unresolved or unreviewed evidence. A well-supported partial conclusion can still have exit 2.

**Every result retains `truth_certified:false`.** File hashes, exact quotes and recorded judgments do not certify semantic truth, source independence or real-world execution success.

## Develop and verify

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

The public checks use self-authored examples and need no API key or private research archive. GitHub Actions are disabled; verification runs locally.

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), [publication boundaries](docs/PUBLICATION.md) and [design provenance](skills/deep-research/references/provenance.md).
