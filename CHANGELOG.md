# Changelog

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
