# Routes

Read the sections for the selected routes. One study folder covers all of them: record `route` on every query and source, and never count the same study or announcement twice because it appeared in two routes. If a selected route cannot be searched, record the failure and report the gap.

## literature (default)

Papers, journals, proceedings, scholarly books and research-institute reports. Distinguish peer-reviewed articles, preprints, theses and reports; a DOI or a famous venue is not support.

- Choose databases that fit the field and your tools (for example PubMed, ACM/IEEE proceedings, arXiv, OpenAlex or Crossref). If no scholarly search tool exists, use site-restricted web searches and record that limit.
- Set inclusion and exclusion criteria and the period before searching. Search synonyms, older terms and contrary results; follow references and citing papers of key studies.
- Read methods, tables and footnotes: population, design, sample, comparator, dataset, measurement, effect and uncertainty, denominators. Record them on the origin (`design`, `n`, `effect`, `ci`).
- Separate search records, publications and studies. A preprint, its journal version and commentary share one origin. A paper with two studies gets two origins. Separate experiments on one dataset are different origins with a shared dependency.
- Check corrections, retractions and later replications. When newer results come from a different population or method, explain the difference instead of declaring a winner.
- An abstract is `abstract`, not read text. "No candidate found" is not "no study exists".
- A scoped literature review is not a systematic review or meta-analysis; if one is requested, list the required steps that were not met.

## technical

Official documentation, versioned release notes, the relevant code and configuration in the original repository, maintainer answers, reproducible benchmarks.

- Fix the date and the commit or release. Do not carry an older version's support status forward.
- Separate README claims, static code reading, synthetic tests, your own execution and production observations. Without running it, do not claim runtime success.
- Check platform, license, model/search/API dependencies, cost and failure conditions. Local inference does not mean the search or API calls are local.
- Compare performance only under matching inputs, versions, hardware, budget and metric. Many posts repeating a vendor benchmark are one origin.

## general

Primary records from governments and institutions, direct observations, news and industry material. Community posts belong to the community route.

- Trace each claim to its original source and its event and publication dates. Article → article → press release is one origin.
- Check that period, unit, denominator and sample match. Do not confuse count growth with share growth, or observation with cause.
- Compare scope and interests of conflicting claims; the number of outlets is not evidence.

## community

Forums, Q&A sites, discussion boards, public user reviews, user reports in issue trackers.

- Search problem phrasing, aliases, versions, environments, and both fix and failure phrasing. Look for contrary experiences, failed reproductions and follow-up comments, not only popular posts. Record dates, edits and deletions.
- Keep who observed what: the writer's own observation, a relayed report, a guess, or an official reply. Do not infer identities or results.
- Cross-posts, quoted reviews and identical logs are one origin. Different nicknames or domains do not make a source independent; unclear relations stay `unknown`.
- Upvotes and comment counts are not rates or representative samples. Watch for advertising, affiliate links and version differences.
- With `-community-only`, phrase findings as "a user reported this in this environment" and list official confirmation as a next check instead of adding other routes without permission.
