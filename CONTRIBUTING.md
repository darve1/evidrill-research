# Contributing to Evidrill Research

The canonical skill is [skills/deep-research](skills/deep-research/SKILL.md). The other five skill folders select a source scope and reuse its workflow. Helpers require Python 3.10+ and the standard library.

Keep source discovery, actual reading, exact-quote checks, semantic support and real-world execution distinct. Preserve counterevidence and unresolved conclusions. Never change a claim to supported just to pass a check.

Run local checks before proposing a change:

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

For research behavior changes, include a bounded, reproducible example using self-authored or appropriately licensed inputs. Describe what ran, what passed and what remains unverified. The [synthetic examples](examples/README.md) demonstrate the expected evidence handling.

Record user-visible changes in [CHANGELOG.md](CHANGELOG.md). Keep credentials, private research, personal paths and third-party full-text snapshots out of commits. See the [publication boundary](docs/PUBLICATION.md).

GitHub Actions are disabled for this repository. Use local verification; do not add workflows without the maintainer's explicit authorization. Open issues for bugs or ideas and pull requests for concrete changes.

Send changes through a topic branch and a pull request. The active default-branch ruleset requires a PR, resolved review threads and linear history; it blocks force pushes and branch deletion, with no bypass actors. Only squash merging is enabled, and auto-merge is disabled. Agents must wait for the user's explicit instruction for that PR before merging, and must not disable or bypass these protections. The repository currently has one maintainer, so a second reviewer's approval is not required; this is a workflow requirement, not a GitHub-enforced distinction between a person and an agent using the same account.
