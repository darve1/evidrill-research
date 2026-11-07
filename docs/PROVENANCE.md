# Design provenance

The skill was written independently from principles observed in public research skills and reporting standards, surveyed on 2026-11-06. No skill text or validation code was copied, and nothing here depends on a particular provider or another skill. The links are design references, not instructions.

- daymade's [research notes format](https://github.com/daymade/claude-code-skills/blob/4f8573228c43e328b03c032f525ec40fad53977e/deep-research/references/research_notes_format.md) and [quality gates](https://github.com/daymade/claude-code-skills/blob/4f8573228c43e328b03c032f525ec40fad53977e/deep-research/references/quality_gates.md): evidence grouped per question, re-reading the original, source families, counterevidence and gaps.
- stevenirby's [deep-research skill](https://github.com/stevenirby/deep-research-skill/blob/605a59eccdbe6b7369f312af322e374c6eb5c2b9/SKILL.md): a quote existing is separate from the quote supporting a claim; counter-searches for key claims.
- K-Dense's [literature-review workflow](https://github.com/K-Dense-AI/scientific-agent-skills/blob/a25cf9ec00e2745d03f8704acf6f6919694ccd9a/skills/literature-review/references/core_workflow.md): reproducible scholarly searches, full-text screening, and keeping search records, publications and studies apart.
- [PRISMA-S](https://link.springer.com/article/10.1186/s13643-020-01542-z): report sources, queries, dates, filters and de-duplication. [PRESS](https://pubmed.ncbi.nlm.nih.gov/27005575/): review search concepts, logic, synonyms and filters.
- [SIFT](https://hapgood.us/2019/06/19/sift-the-four-moves/): trace claims to their original context. [ALCE](https://aclanthology.org/2023.emnlp-main.398/): separate citation support from citation relevance.

Not adopted: large parallel agent fan-out, fixed source quotas, uncertainty scores, and word-overlap truth judgments. Hash and quote checks are mechanical; support is a recorded reviewer judgment. The helper has no automatic semantic judgment, because an early prototype that had one labeled unsupported claims as supported in independent counterexamples.

The skill guides general research. It does not certify a systematic review, and it is not a security audit, legal opinion or substitute for running the software in question.
