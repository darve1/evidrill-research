# Publication boundary

Evidrill Research is published at [darve1/evidrill-research](https://github.com/darve1/evidrill-research) under the [MIT License](../LICENSE). The public package contains the skill, the Python helper, the installer, tests, the evaluation harness and fictional fixtures. Works linked from the [design provenance](PROVENANCE.md) keep their own authorship and terms.

Excluded by `.gitignore`: `research/`, `verification/`, `evals/runs/` (trial transcripts and workspaces, which hold third-party page snapshots), local agent instructions and historical design notes. Generated studies belong outside commits unless prepared as safe, licensed examples.

## Verification

Public checks need only this repository, Python 3.10+ and the standard library (`pdftotext` is optional; its test is skipped without it):

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

The verifier checks the skill files, matching versions in the helper, plugin manifests and changelog, local documentation links, and that `examples/demo` is exactly what `examples/build_demo.py` produces and remains unresolved (exit 2). It writes a report under the ignored `verification/` folder.

Maintainers who keep the preserved 0.1.x cases can add `--include-private-evidence`, which checks them with the 0.1.1 helper read from git history. If the cases are missing, that run fails; absence is never reported as a passing historical check.

The [evaluation harness](../evals/README.md) runs real agent sessions and costs model usage; it is run by hand, not in CI.

Exact text, file hashes, recorded reviews and removal scenarios do not establish semantic truth or source independence. Every helper output keeps `truth_certified:false`.

## Repository settings

`main` is the default branch, protected by a ruleset with no bypass actors. The ruleset requires pull requests, resolved review threads and linear history, and blocks force pushes and deletion. Squash is the only merge method and auto-merge is off. The repository has one maintainer, so no second approval is required.

`.github/workflows/tests.yml` runs the unit tests and the verifier on pull requests. It does nothing until GitHub Actions is enabled in the repository settings, and it is not a required status check unless the maintainer adds it to the ruleset.

Agents must open a PR and wait for the maintainer's explicit instruction before merging it. GitHub cannot tell the maintainer from an agent using the same account, so this is a working rule, not something GitHub enforces.
