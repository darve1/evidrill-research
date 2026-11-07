# Codex and Claude Code

One skill folder, `skills/evidrill`, serves both hosts. `SKILL.md`, the references and the Python helper are shared; `agents/openai.yaml` adds Codex UI metadata that Claude Code ignores. Nothing installs hooks, tool allowlists, API keys or global configuration.

## Install

**Claude Code plugin** (recommended for Claude Code):

```text
/plugin marketplace add darve1/evidrill-research
/plugin install evidrill@evidrill
```

The plugin registers the skill as `evidrill:evidrill`; typing `/evidrill` also resolves to it.

**Skill folder** (Codex, or Claude Code without plugins). From a checkout, with Python 3.10+:

```text
python -X utf8 scripts/install_skills.py --target both --dry-run
python -X utf8 scripts/install_skills.py --target both
```

| Host | Personal directory | Project directory | Invocation |
| --- | --- | --- | --- |
| Codex | `~/.agents/skills` | `.agents/skills` | `$evidrill` |
| Claude Code | `~/.claude/skills` | `.claude/skills` | `/evidrill` |

Use `--target codex` or `--target claude` for one host, and `--skills-dir PATH` (one host at a time) for another location such as an existing `~/.codex/skills` or a project directory. Locations follow the [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills) and the [Claude Code skill documentation](https://code.claude.com/docs/en/skills).

## Upgrading from 0.1.x

0.1.x installed six folders named `deep-research*`. Claude Code now ships a built-in `deep-research` skill, so the old name collided with it. The installer warns when it finds the old folders; to remove them:

```text
python -X utf8 scripts/install_skills.py --target both --remove-legacy --dry-run
python -X utf8 scripts/install_skills.py --target both --remove-legacy
```

Only files whose SHA-256 matches a released 0.1.x file are deleted. Files you edited or added are kept and listed, and linked folders (symlinks, junctions) are never entered; move what remains out of the skill directory yourself. Studies recorded with 0.1.x (schema 2) are not migrated; the 0.2.0 helper reads schema 3 only.

## Existing installations

Matching files are skipped. A different existing file, a missing source file or a linked path stops the installer before it copies anything, so customizations are never overwritten; there is no force option. Unrelated skills and extra files are preserved. A disk or permission failure during writing can leave a partial install; fix the cause and rerun. To compare an installed copy with the source:

```text
python -X utf8 scripts/verify_project.py --installed-skill "~/.claude/skills/evidrill"
```

If the skill does not appear, start a new host session. Installing files does not change the host's permissions or which search tools are available.

## Scope options

The same options work in both hosts: `-tech`, `-community`, `-tech -community`, `-all`, `-tech-only`, `-community-only`; no option means scholarly literature. The scope table is in [SKILL.md](../skills/evidrill/SKILL.md). 0.1.x's `-comu` spelling was renamed to `-community`.

## What the checks cover

The tests install both layouts into temporary directories whose paths contain spaces and Korean characters. They check conflict handling, idempotence and legacy removal, and run every scope combination through each installed helper. `claude plugin validate . --strict` checks the plugin manifests. None of this certifies research quality, web access or tool permissions; for measured behavior see the [evaluation results](../evals/results.md).
