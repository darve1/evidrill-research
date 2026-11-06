# Codex and Claude Code

The six skill packages share the same `SKILL.md`, references and Python helper. `agents/openai.yaml` supplies Codex UI metadata; Claude Code reads `SKILL.md` without that metadata. No host-specific tool allowlist, shell substitution, API key, hook or global configuration is installed.

## Installation

From the repository root, with Python 3.10+:

```text
python -X utf8 scripts/install_skills.py --target both --dry-run
python -X utf8 scripts/install_skills.py --target both
```

Use `--target codex` or `--target claude` to install one host. All six folders stay together because each scope entry reads the sibling `deep-research` package.

| Host | Default personal directory | Project directory | Invocation |
| --- | --- | --- | --- |
| Codex | `~/.agents/skills` | `.agents/skills` | `$deep-research` |
| Claude Code | `~/.claude/skills` | `.claude/skills` | `/deep-research` |

These locations and invocation forms follow the [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skill documentation](https://code.claude.com/docs/en/skills), checked on 2026-11-06. In a ChatGPT app that provides skill selection through `@`, select the skill there. This installer targets local Codex and Claude Code; it does not upload skills to claude.ai or Cowork.

Custom paths, including host configuration-directory overrides, are explicit:

```text
python -X utf8 scripts/install_skills.py --target codex --skills-dir "~/.codex/skills"
python -X utf8 scripts/install_skills.py --target claude --skills-dir "/path/to/project/.claude/skills"
python -X utf8 scripts/install_skills.py --target codex --skills-dir "/path/to/project/.agents/skills"
```

`--skills-dir` accepts one host at a time. An existing Codex installation in `~/.codex/skills` can stay there; use the first command and install Claude separately. Do not also install duplicate names into `~/.agents/skills`. The installer does not migrate old installations or infer custom configuration paths. Alternatively, manually copy the six folders from `skills/` into one host's skill directory.

## Existing installations

Matching files are skipped. Different existing files, incomplete source bundles and linked package paths fail preflight before copying anything. Unrelated skills and extra files are preserved. A write-time disk or permission failure can leave a partial installation; fix the cause and rerun. Matching files are skipped, while an incomplete file is treated as a conflict to compare and back up first.

For an update, compare the installed package with the new source, preserve customizations in a backup **outside all skill discovery directories**, and remove only the old files you intend to replace. Then rerun the installer. It deliberately has no force-overwrite option. The helper hash comparison can be run against either host:

```text
python -X utf8 scripts/verify_project.py --installed-skill "~/.agents/skills/deep-research"
python -X utf8 scripts/verify_project.py --installed-skill "~/.claude/skills/deep-research"
```

If a new entry does not appear, start a fresh host session and check its skill selector. File installation does not change the host's existing permissions or search-tool availability.

## Shared behavior

| Request | Scope in either host |
| --- | --- |
| `deep-research` | Scholarly literature (default) |
| `deep-research -tech` or `deep-research-tech` | Literature + technical/open-source |
| `deep-research -tech-only` or `deep-research-tech-only` | Technical/open-source only |
| `deep-research -comu` or `deep-research-comu` | Literature + community |
| `deep-research -comu-only` or `deep-research-comu-only` | Community only |
| `deep-research -tech -comu` | Literature + technical + community |
| `deep-research -all` or `deep-research-all` | Literature + technical + general web + community |

Add `$` for Codex or `/` for Claude Code, followed by the topic. The shared instructions use ordinary user arguments; no Claude-specific placeholder is required. Relative links resolve from the selected `SKILL.md`, and helper calls use the common package's absolute path. Research output goes in the user's working project, outside the installed skill folders.

## Verification scope

Local tests install both layouts in temporary directories, resolve all entrypoint links, exercise conflict handling and idempotence, and run all seven scope combinations through each installed helper from another working directory with spaces and Korean characters in the paths. Existing evidence-ledger and synthetic-demo checks remain in the test suite.

These checks cover packaging, paths and helper behavior. They do not certify live model research quality, web access, tool permissions or picker refresh behavior. See the [publication notes](PUBLICATION.md) for evidence and truth-certification limits.

On 2026-11-06, local verification ran 87 tests: 86 passed and one symlink test was skipped because Windows did not grant symlink creation. The project verifier and all six skill-format checks passed. Codex CLI 0.159.0 (`skills/list`) and Claude Code 2.1.292 (initialization command list) each discovered all six entries without sending a model turn. Installed files were compared with the source by SHA-256 for both hosts; this is a discovery and packaging check, not an end-to-end research run.
