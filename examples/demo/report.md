# Research evidence cards

truth_certified: false. Recorded evidence and reviewer judgments; no automatic truth or independence certification.

- Review state: needs_review
- Routes: literature
- Question: Does the fictional Lumen method outperform Baseline?

## Search and screening

- literature: 3 completed and 0 failed searches; 3 sources, 3 read in full or relevant sections, 0 abstract only
- Evidence reviews by method: self 4

## c1 — On Small-X, LX-01 reports Lumen at 90% and Baseline at 80% \(18/20 vs 16/20\).

- Status: supported
- Scope: Fictional LX-01 Small-X experiment only.
- Resolution: not recorded
- Next action: Look for an independent same-condition replication.

### Evidence

- e1 [supports, self]: LX-01 journal article — fixture:paper-a-journal.txt
  - Location: line 4; version: fixture-v1; read: full\_text; capture: user\_supplied
  - Passage/observation: Lumen succeeded on 18/20 items, which is 90%, not 95%.
  - Context: … experiment and same 20 test items as preprint v1, not a new study. Correction:  **[passage]**  Baseline succeeded on 16/20 items \(80%\). The correction supersedes the percenta…
  - Review: Corrected figure for the same experiment.
  - Preserved: [s1 snapshot](snapshots/s1/27107967343fe5df66c985b3bebc3c0249d53601cd9b6748cfd0f4489d8aaf10.txt)
- e2 [supports, self]: LX-01 journal article — fixture:paper-a-journal.txt
  - Location: line 4; version: fixture-v1; read: full\_text; capture: user\_supplied
  - Passage/observation: Baseline succeeded on 16/20 items \(80%\).
  - Context: …a new study. Correction: Lumen succeeded on 18/20 items, which is 90%, not 95%.  **[passage]**  The correction supersedes the percentage printed in v1. Generalization beyond S…
  - Review: Comparator figure in the same sentence group.
  - Preserved: [s1 snapshot](snapshots/s1/27107967343fe5df66c985b3bebc3c0249d53601cd9b6748cfd0f4489d8aaf10.txt)

### Origin removal (recorded relations)

- Structure: single_origin
- Unknown origins: none
- Shared dependencies: none
- Basis SHA-256: 819eb791f101c5156c470a89c996064788e4dc2244333583433d5f902b9fe621
- Review selection: Removing the only origin leaves no support.
- Exclude lx01 (study; design: benchmark; n=20); remaining supports: none; remaining counterevidence: none
  - Recorded judgment: narrowed (current, self); Only LX-01 supports the Small-X result.

## c2 — Lumen generally outperforms Baseline.

- Status: unresolved
- Scope: Cross-benchmark generalization.
- Resolution: The two benchmarks disagree and differ in size and items; general superiority is not established.
- Next action: Seek comparable independent studies.

### Evidence

- e1 [partial, self]: LX-01 journal article — fixture:paper-a-journal.txt
  - Location: line 4; version: fixture-v1; read: full\_text; capture: user\_supplied
  - Passage/observation: Lumen succeeded on 18/20 items, which is 90%, not 95%.
  - Context: … experiment and same 20 test items as preprint v1, not a new study. Correction:  **[passage]**  Baseline succeeded on 16/20 items \(80%\). The correction supersedes the percenta…
  - Review: One 20-item benchmark cannot establish generality.
  - Preserved: [s1 snapshot](snapshots/s1/27107967343fe5df66c985b3bebc3c0249d53601cd9b6748cfd0f4489d8aaf10.txt)
- e3 [contradicts, self]: LY-02 conference paper — fixture:paper-b-conference.txt
  - Location: line 4; version: fixture-v1; read: full\_text; capture: user\_supplied
  - Passage/observation: Lumen succeeded on 70/100 items; Baseline succeeded on 75/100 items.
  - Context: …Different investigators tested dataset Large-Y with budget 1 unit on 100 items.  **[passage]**  These results concern Large-Y and do not directly invalidate the reported Small…
  - Review: The larger benchmark favors Baseline.
  - Preserved: [s2 snapshot](snapshots/s2/5eb364873b5810ad8a8ba35c7c4999b3651407307a7d0ade2f063c025053a3a7.txt)

### Origin removal (recorded relations)

- Structure: no_recorded_support
- Unknown origins: none
- Shared dependencies: none
- Basis SHA-256: 31eea7aedf4fe4aab02511f7c21ce2be3d505707abd63be2d24742bded823539
- Review selection: Removing the contrary origin still leaves no full support.
- Exclude lx01 (study; design: benchmark; n=20); remaining supports: none; remaining counterevidence: e3
  - Recorded judgment: unresolved (current, self); Only the contrary LY-02 result remains.
- Exclude ly02 (study; design: benchmark; n=100); remaining supports: none; remaining counterevidence: none
  - Recorded judgment: unresolved (current, self); Only the 20-item Small-X result remains; it is partial.

## Pending review and access limits

- c2: claim remains unresolved
- c2: stress judgment remains unresolved
