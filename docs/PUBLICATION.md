# Publication boundary

Evidrill Research is published at [darve1/evidrill-research](https://github.com/darve1/evidrill-research). The installable skill names remain `deep-research` and its five scope entries; use the names in the [README](../README.md).

The public package contains the independently authored skills, Python helpers, tests, documentation and fictional examples. They are distributed under the [MIT License](../LICENSE). External references in the [design provenance](../skills/deep-research/references/provenance.md) retain their original authorship and terms; links do not bring their contents under this project's license.

Private working materials are intentionally excluded by `.gitignore`: `research/`, `verification/`, local project migration records, local agent instructions, and historical design/research notes. Maintainers preserve them locally without rewriting the original evidence. Generated studies also belong outside commits unless explicitly prepared as safe, licensed examples.

## Verification

The public checks require only this repository, Python 3.10+ and the standard library:

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

The verifier checks the six skill packages, local documentation links and the synthetic demo's unresolved state. It writes a local report under ignored `verification/`. A clean public checkout does not require private historical cases.

Maintainers who have those preserved cases can additionally run:

```text
python -X utf8 scripts/verify_project.py --include-private-evidence
```

Requesting private evidence checks when those files are absent fails; absence is not reported as a successful historical check. Optional `--installed-skill PATH` compares the six sibling installed packages with the source files.

The demo intentionally returns exit 2 from `check`, `stress` and `render`: its broader conclusion is unresolved. Exact text, file hashes, recorded reviews and automated removal scenarios do not establish semantic truth or source independence. All helper outputs retain `truth_certified:false`.

## Repository settings

The initial setup uses public visibility, `main` as the default branch, issues enabled, wiki/projects disabled, squash merging and automatic deletion of merged branches. GitHub Actions are disabled, and no workflow files are shipped. All release verification runs locally. Settings on GitHub can change independently of this document.

On 2026-11-06, after publication, the [Protect main ruleset](https://github.com/darve1/evidrill-research/rules/26689918) was activated for `main` and the default branch with no bypass actors. It requires pull requests, resolution of review threads and linear history, and blocks force pushes and deletion. Auto-merge remains disabled; squash is the only enabled merge method. Required external approvals are zero to support the single-maintainer repository, and there are no required CI status checks while Actions are disabled.

Agents must present a PR and wait for an explicit instruction to merge that PR. GitHub cannot distinguish the human from an agent authenticated as the same owner, and an administrator can edit repository rules; the no-merge-without-instruction requirement is also recorded in local agent instructions. The maintainer's current checkout additionally rejects implicit `git push` and has a local pre-push guard against `main`/`master` targets. These local safeguards are not automatically installed by cloning this repository.
