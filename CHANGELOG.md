# Changelog

## 0.2.0 — 2026-11-07

**Breaking:** the six `deep-research*` skills are now one skill, `evidrill`. The old name collided with Claude Code's built-in `deep-research` skill. `-comu` is now `-community`, and studies use record schema 3; 0.1.x studies are not migrated.

- Install from Claude Code with `/plugin marketplace add darve1/evidrill-research`, then `/plugin install evidrill@evidrill`. The Python installer still covers Codex. `--remove-legacy` deletes unmodified 0.1.x files and keeps anything you changed.
- `snapshot --url` downloads the source itself, records it as `helper_fetched`, and extracts text from HTML (and from PDF when `pdftotext` is available). A tool summary is recorded as `agent_written`, not as the source.
- Quote checks fold only layout differences (whitespace, line-break hyphens, curly quotes, ligatures). Quotes need at least 20 characters (10 for CJK) unless a reason is given, and the surrounding context is shown with every quote.
- Every key claim needs at least two distinct counterevidence searches. Abstract-only support for a key claim stays pending.
- Record commands (`add`, `set-claim`, `review`, `counter`, `origin`, `stress-review`) validate the whole study and refuse a change that would introduce an error. `add --json-file` accepts a JSON array or JSON Lines and writes all rows or none. Only replaced versions go to `history.jsonl`.
- Reviews record their method (`self`, `fresh_agent`, `human`). Origins can carry design, population, n, effect and CI; sources can carry screening decisions and queries a result count.
- The instructions are rewritten in English at half their former size (39 KB to 20 KB). Answers now open with the answer, the confidence and the largest weakness, and say what was not done.
- Add a behavioral evaluation harness with fictional and real-topic tasks and blind grading; see `evals/results.md`.
- Add a pull-request workflow for unit tests (it runs once Actions is enabled).

## 0.1.1 — 2026-11-06

- Support Codex and Claude Code using the same six skill packages; document `$` and `/` invocation with the same default literature scope and all existing scope options.
- Add a Python installer for either host or both, with custom directories, dry runs, hash verification and preflight conflict detection. Existing customizations are never overwritten.
- Resolve shared references from the skill file location and keep study outputs in the user's working project.
- Add installation and installed-helper checks for both directory layouts, including Unicode/spaced paths, conflict preservation and every scope combination. Local checks do not certify model behavior or web research quality.
- Document current and legacy Codex installation paths and Claude Code's local installation boundary. GitHub Actions remain disabled.

Validation: 86 tests passed; one Windows symlink-permission test skipped. Project and six skill-format checks passed. Codex CLI 0.159.0 and Claude Code 2.1.292 each listed all six installed entries through initialization/discovery only, with no model turn. See [compatibility notes](docs/COMPATIBILITY.md) for scope and limitations.

## 0.1.0 — 2026-11-06

Initial public package of **Evidrill Research**, with six installable `deep-research` skill entries.

- Default to scholarly literature; add technical/open-source, general-web and community routes through explicit scope options.
- Support `-tech`, `-tech-only`, `-comu`, `-comu-only`, `-tech -comu` and `-all`.
- Preserve source passages and record claim-level support, counterevidence, review judgments and unresolved questions.
- Group repeated publications by evidence origin and generate origin-removal scenarios with stale-review detection.
- Provide Python standard-library helpers, fictional reproducible examples and local tests. Automated checks always retain `truth_certified:false`.
- Publish independently authored materials under MIT. Keep third-party source snapshots and personal working records outside the public package.
- Make project verification work without the private historical archive. Maintainers can explicitly include those preserved cases with `--include-private-evidence`.
- Configure local verification and document the publication boundary; GitHub Actions remain disabled.

The project brand is Evidrill Research; installed skill names remain `deep-research` and its scope entries. Historical development logs and their original evidence are preserved locally. See [publication notes](docs/PUBLICATION.md) for scope and limitations.
