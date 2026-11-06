# Research evidence cards

truth_certified: false

Recorded evidence and reviewer judgments; no automatic truth or independence certification.

Review state: needs_review
Routes: literature
Question: Does fictional Lumen outperform Baseline?

## Source route coverage

- literature: \{"completed\_queries": 1, "failed\_queries": 0, "discovered\_sources": 2, "read\_sources": 2, "abstract\_only\_sources": 0\}

## c1 — On Small-X, the journal fixture reports Lumen at 90% and Baseline at 80%.

- Status: supported
- Scope: Fictional LX-01 Small-X experiment only.
- Resolution: not recorded
- Next action: Review independent same-condition replications.

### Evidence

- e1 [supports]: paper-a-journal.txt — fixture:paper-a-journal.txt
  - Location: line 4; version: fixture-v1; read: full\_text
  - Passage/observation: Correction: Lumen succeeded on 18/20 items, which is 90%, not 95%. Baseline succeeded on 16/20 items \(80%\).
  - Review: Same experiment and corrected denominator.
  - Preserved: [s1 snapshot](snapshots/s1/27107967343fe5df66c985b3bebc3c0249d53601cd9b6748cfd0f4489d8aaf10.txt)

### Origin removal (recorded relations)

- Structure: single_origin
- Unknown origins: none
- Shared dependencies: \{\}
- Basis SHA-256: 427b6604a9eca317d27ec2daa5e8708eb9d16e17b235bc67b3694485995d0af9
- Review selection: Demonstrate all recorded origin-removal scenarios.
- Exclude lx01; remaining supports: none; remaining counterevidence: none
  - Recorded judgment: narrowed (current); Source-specific observation only.

## c2 — Lumen generally outperforms Baseline.

- Status: unresolved
- Scope: Fictional cross-dataset generalization.
- Resolution: General superiority remains unresolved; compare populations and methods.
- Next action: Seek comparable independent studies.

### Evidence

- e1 [partial]: paper-a-journal.txt — fixture:paper-a-journal.txt
  - Location: line 4; version: fixture-v1; read: full\_text
  - Passage/observation: Correction: Lumen succeeded on 18/20 items, which is 90%, not 95%. Baseline succeeded on 16/20 items \(80%\).
  - Review: One small dataset cannot establish generality.
  - Preserved: [s1 snapshot](snapshots/s1/27107967343fe5df66c985b3bebc3c0249d53601cd9b6748cfd0f4489d8aaf10.txt)
- e2 [contradicts]: paper-b-conference.txt — fixture:paper-b-conference.txt
  - Location: line 4; version: fixture-v1; read: full\_text
  - Passage/observation: Lumen succeeded on 70/100 items; Baseline succeeded on 75/100 items.
  - Review: The other dataset favors Baseline; conditions differ.
  - Preserved: [s2 snapshot](snapshots/s2/5eb364873b5810ad8a8ba35c7c4999b3651407307a7d0ade2f063c025053a3a7.txt)

### Origin removal (recorded relations)

- Structure: no_recorded_support
- Unknown origins: none
- Shared dependencies: \{\}
- Basis SHA-256: 0135b0fcd6e3fe2532c820f917dfa022bcf9f845486c2d10f1a868612984aa40
- Review selection: Demonstrate all recorded origin-removal scenarios.
- Exclude lx01; remaining supports: none; remaining counterevidence: e2
  - Recorded judgment: unresolved (current); No general conclusion from the remaining conditions.
- Exclude ly02; remaining supports: none; remaining counterevidence: none
  - Recorded judgment: unresolved (current); No general conclusion from the remaining conditions.

## Pending review and access limits

- c2: claim remains unresolved
- c2: stress judgment remains unresolved
- c2: stress judgment remains unresolved
