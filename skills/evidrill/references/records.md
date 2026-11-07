# Records

A study folder holds `study.json`, `brief.md`, four JSONL tables, `snapshots/` and, after changes, `history.jsonl`. Write them through the helper commands; each command validates the whole study before writing, and refuses to write while `study.json` itself is invalid (fix it by hand first). IDs are 1–80 characters of letters, digits and `_ . : -` (source IDs: letters, digits, `_ -`), unique per table.

## study.json

`{schema_version: 3, mode, routes, question, origins: [...]}`, created by `init`. Each origin (added with `origin`):

| Field | Meaning |
| --- | --- |
| `origin_id`, `kind`, `label` | One study, disclosure, implementation, dataset release or event. `unknown` is reserved. |
| `source_ids` | Every source that reports this origin (preprint and journal version together). |
| `rationale`, `reviewer`, `checked_at` | Why these sources share an origin. |
| `shared_dependencies` | Optional labels such as `dataset W` when separate origins share an input. |
| `design`, `population`, `n`, `effect`, `ci` | Optional study details; shown next to removal scenarios so a 20-item test is not mistaken for a 10,000-person trial. |

## queries.jsonl

Required: `query_id`, `question_id`, `query`, `provider`, `purpose` (`discovery` or `counterevidence`), `status` (`completed` or `failed`), `result_source_ids`, `route`. `searched_at` defaults to now. Optional: `result_count` (integer), filters, errors. Record only searches that ran; a planned search is not a search.

## sources.jsonl

Usually created by `snapshot --title ...`. Required: `source_id`, `url`, `title`, `route`, `family_id` (`unknown` if unsure), `retrieved_at`, `read_level`, `extraction_method`, `capture`.

- `read_level`: `discovered`, `snippet`, `abstract`, `relevant_sections`, `full_text`, `unavailable`. Downloading a file is not reading it.
- `capture`: `helper_fetched` (helper downloaded the URL; `fetch` metadata required), `downloaded` (original bytes saved by another tool), `user_supplied`, `agent_written` (text you typed or a tool summary). Quotes against `agent_written` text stay pending.
- Snapshot fields from the helper: `snapshot_path`, `sha256`, `format`, and for HTML, PDF or non-UTF-8 text `text_path`, `text_sha256`, `text_extraction`.
- Optional: `publication_date`, `version` (DOI version, commit, release), `upstream_source_ids`, `access_limit`, `notes`, `screening: {decision: included|excluded, reason}` (reason required for exclusions). Leave unknown dates out rather than guessing; never invent URLs or DOIs.

## evidence.jsonl

Required: `evidence_id`, `source_id`, `origin_id` (`unknown` until classified), `kind`, `locator`.

- `kind: text` needs `quote`: an exact passage. Matching ignores only whitespace, line-break hyphens, soft hyphens, curly quotes and ligatures. When a source has `text_path`, quotes are matched against that extracted text only, never against markup, comments or scripts. Quotes under 20 characters (10 for CJK) need `short_quote_reason`. Put translations or summaries in other fields.
- `kind: visual` needs `visual_review: {reviewer, checked_at, observation}` from actually viewing the figure, table or frame.
- `locator`: page, table, section, paragraph, commit and line, or timestamp.

## claims.jsonl

Required: `claim_id`, `text`, `kind` (`fact`, `inference`, `proposal`), `importance` (`key`, `context`), `status`, `evidence_ids`. Key fact and inference claims also need `scope` and `next_action`.

- `status`: `supported`, `partial`, `contradicted`, `unresolved`; proposals use `proposed`. A source's untested performance claim is phrased as what the authors reported.
- `reviews` (via `review`): one per linked evidence, `{evidence_id, judgment, reviewer, method, checked_at, rationale, evidence_sha256}`. The helper fills `evidence_sha256`; replacing that evidence row makes the review stale. `judgment`: `supports`, `partial`, `contradicts`, `irrelevant`, `unresolved`. `method`: `self`, `fresh_agent`, `human`.
- `counter_search` (via `counter`): `{query_ids, outcome, rationale, evidence_ids}`. `outcome`: `found`, `not_found`, `not_applicable` (a definition or narrow specification check), `not_searched`. `found` and `not_found` need at least two distinct completed counterevidence queries; `found` also needs the counterevidence linked and a `resolution`.
- `stress_test` (via `stress-review`): `{selection_rationale, reviews: [{excluded_origin_id, judgment, rationale, reviewer, method, checked_at, basis_sha256}]}`. `judgment`: `retained`, `narrowed`, `unresolved`, or `not_applicable` as a single review with a null origin. The helper fills `basis_sha256`; it changes when the claim, its evidence, sources, origins or scope change, which marks the review stale.

## What check reports

- **errors** (exit 1): broken files, references, hashes, missing quotes, invalid values.
- **pending** (exit 2): missing reviews, partial or unresolved claims, unread or abstract-only support for key claims, short quotes, agent-written snapshots, too few counter-searches, missing or stale stress reviews, reviews of evidence that changed afterwards, selected routes without a completed search.
- **metrics**: sources, families, capture types, quotes found, reviewed pairs, `recorded_support_fraction` (supports / reviewed pairs; not an accuracy score), review methods.

The helper is for one writer. Parallel researchers use separate study folders; the final writer merges them and resolves ID and origin overlaps.
