# Changelog

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
