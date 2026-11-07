# Contributing to Evidrill Research

The skill lives in [skills/evidrill](skills/evidrill/SKILL.md); the helper is one standard-library Python file (3.10+).

Keep source discovery, actual reading, exact-quote checks, semantic support and real-world execution distinct. Preserve counterevidence and unresolved conclusions. Never relabel a claim as supported to pass a check.

Before proposing a change:

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

If you change the helper, add a test. If you change the instructions, run at least one [behavioral trial](evals/README.md) and state what you ran and what you did not. If you change `examples/build_demo.py`, rebuild `examples/demo`. Bump the version in the helper, both plugin manifests and [CHANGELOG.md](CHANGELOG.md) together; the verifier checks that they match.

Keep credentials, private research, personal paths and third-party full-text snapshots out of commits (see the [publication boundary](docs/PUBLICATION.md)).

Send changes as a pull request from a topic branch. `main` is protected: it requires a PR, resolved review threads and linear history, and only squash merging is enabled. Agents open the PR and wait for the maintainer's explicit instruction before merging.
