"""Preserve research sources and check records. Never classify semantic truth.

No network, model calls, dependencies, or changes outside the specified study.
Exit codes for check: 0 recorded reviews complete, 1 invalid records,
2 review remains. All results explicitly set truth_certified to false.
"""
import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

TABLES = {'queries': 'query_id', 'sources': 'source_id', 'evidence': 'evidence_id', 'claims': 'claim_id'}
READ_LEVELS = ('discovered', 'snippet', 'abstract', 'relevant_sections', 'full_text', 'unavailable')
JUDGMENTS = ('supports', 'partial', 'contradicts', 'irrelevant', 'unresolved')
MODES = ('literature', 'technical', 'general', 'community')
ADDITIVE_ROUTES = (['literature', 'technical'], ['literature', 'community'],
                   ['literature', 'technical', 'community'],
                   ['literature', 'technical', 'general'], list(MODES))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inside(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Snapshot paths must be relative to the study')
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Snapshot path escapes the study')
    return target


def select_routes(mode=None, tech=False, all_sources=False, *, comu=False, tech_only=False, comu_only=False):
    if mode is not None:
        if mode not in MODES or any((tech, all_sources, comu, tech_only, comu_only)):
            raise ValueError('Choose an explicit --mode OR scope flags')
        return mode, [mode]
    if tech_only or comu_only:
        if (tech_only and comu_only) or any((tech, comu, all_sources)):
            raise ValueError('An -only option cannot be combined with another scope flag')
        only = 'technical' if tech_only else 'community'
        return only, [only]
    if all_sources:
        return 'literature', list(MODES)
    routes = ['literature']
    if tech:
        routes.append('technical')
    if comu:
        routes.append('community')
    return 'literature', routes


def initialize(root, mode=None, tech=False, all_sources=False, question='', *, comu=False, tech_only=False, comu_only=False):
    mode, routes = select_routes(mode, tech, all_sources, comu=comu, tech_only=tech_only, comu_only=comu_only)
    root = Path(root).resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Study must be new or empty; existing records are never overwritten')
    root.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        (root / f'{table}.jsonl').write_text('', encoding='utf-8')
    (root / 'study.json').write_text(json.dumps({'schema_version': 2, 'mode': mode,
        'routes': routes, 'question': question, 'origins': []}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (root / 'brief.md').write_text(
        '# Research brief\n\nDecision/question:\n\nScope, date, versions:\n\n'
        'Subquestions and search routes:\n\nExclusions and access limits:\n\n'
        'Stopping conditions and unresolved gaps:\n', encoding='utf-8')
    return {'root': str(root), 'mode': mode, 'routes': routes,
            'created': [f'{t}.jsonl' for t in TABLES] + ['brief.md', 'study.json']}


def capture(root, input_path, source_id, media_format):
    root = Path(root).resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', source_id):
        raise ValueError('source_id must be 1-80 ASCII letters/digits/underscores/hyphens')
    if media_format not in {'text', 'binary'}:
        raise ValueError('format must be text or binary')
    raw = Path(input_path).read_bytes()
    if media_format == 'text':
        raw.decode('utf-8-sig')
    sha = digest(raw)
    extension = 'txt' if media_format == 'text' else 'bin'
    relative = f'snapshots/{source_id}/{sha}.{extension}'
    target = inside(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise ValueError('Existing content-addressed snapshot is damaged; refusing overwrite')
    else:
        with target.open('xb') as handle:
            handle.write(raw)
    return {'snapshot_path': relative, 'sha256': sha, 'format': media_format, 'bytes': len(raw)}


def inspect_study(root):
    root = Path(root).resolve()
    errors, pending = [], []
    data = {}

    def text_fields(row, fields, label):
        for field in fields:
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f'{label}: missing/non-text {field}')

    def id_list(value, label):
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(f'{label}: expected a list of nonempty IDs')
            return []
        if len(set(value)) != len(value):
            errors.append(f'{label}: duplicate IDs')
        return value

    for table, key in TABLES.items():
        records = {}
        try:
            lines = (root / f'{table}.jsonl').read_text(encoding='utf-8-sig').splitlines()
        except (OSError, UnicodeError) as error:
            errors.append(f'{table}: cannot read: {error}')
            lines = []
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            label = f'{table}:{line_number}'
            try:
                row = json.loads(line)
            except ValueError as error:
                errors.append(f'{label}: invalid JSON: {error}')
                continue
            if not isinstance(row, dict):
                errors.append(f'{label}: expected an object')
                continue
            identity = row.get(key)
            if not isinstance(identity, str) or not identity.strip() or identity in records:
                errors.append(f'{label}: missing/duplicate {key}')
                continue
            records[identity] = row
        data[table] = records

    metadata = read_metadata(root, data, errors)
    coverage = {}
    if metadata is not None and not errors:
        for route in metadata['routes']:
            completed = sum(q.get('route') == route and q.get('status') == 'completed' for q in data['queries'].values())
            coverage[route] = {'completed_queries': completed,
                'failed_queries': sum(q.get('route') == route and q.get('status') == 'failed' for q in data['queries'].values()),
                'discovered_sources': sum(s.get('route') == route for s in data['sources'].values()),
                'read_sources': sum(s.get('route') == route and s.get('read_level') in ('relevant_sections', 'full_text') for s in data['sources'].values()),
                'abstract_only_sources': sum(s.get('route') == route and s.get('read_level') == 'abstract' for s in data['sources'].values())}
            if not completed:
                pending.append(f'{route}: selected route has no completed search; disclose access or scope gap')

    source_text = {}
    for sid, source in data['sources'].items():
        text_fields(source, ['url', 'title', 'family_id', 'retrieved_at', 'extraction_method'], sid)
        if source.get('read_level') not in READ_LEVELS:
            errors.append(f'{sid}: invalid read_level')
        if not source.get('snapshot_path'):
            if source.get('read_level') not in ('discovered', 'snippet', 'unavailable'):
                pending.append(f'{sid}: read source has no preserved snapshot')
            continue
        if source.get('format') not in ('text', 'binary'):
            errors.append(f'{sid}: snapshot format must be text or binary')
        for path_key, hash_key, is_text in [('snapshot_path', 'sha256', source.get('format') == 'text'),
                                           ('text_path', 'text_sha256', True)]:
            if path_key not in source:
                continue
            try:
                raw = inside(root, source[path_key]).read_bytes()
                if digest(raw) != source.get(hash_key):
                    errors.append(f'{sid}: {path_key} hash mismatch')
                if is_text:
                    source_text[sid] = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
            except (OSError, ValueError) as error:
                errors.append(f'{sid}: {path_key}: {error}')

    for qid, query in data['queries'].items():
        text_fields(query, ['question_id', 'query', 'provider', 'searched_at'], qid)
        if query.get('purpose') not in ('discovery', 'counterevidence'):
            errors.append(f'{qid}: invalid purpose')
        if query.get('status') not in ('completed', 'failed'):
            errors.append(f'{qid}: invalid status')
        for sid in id_list(query.get('result_source_ids'), qid):
            if sid not in data['sources']:
                errors.append(f'{qid}: unknown source {sid}')

    checked_quotes = 0
    for eid, evidence in data['evidence'].items():
        text_fields(evidence, ['source_id', 'locator'], eid)
        sid = evidence.get('source_id')
        if not isinstance(sid, str) or sid not in data['sources']:
            errors.append(f'{eid}: unknown source')
            continue
        if evidence.get('kind') == 'text':
            text_fields(evidence, ['quote'], eid)
            quote = evidence.get('quote')
            if sid not in source_text:
                pending.append(f'{eid}: no preserved UTF-8 text for exact quote check')
            elif isinstance(quote, str) and quote.strip():
                quote = quote.replace('\r\n', '\n').replace('\r', '\n')
                if quote not in source_text[sid]:
                    errors.append(f'{eid}: exact quote absent from snapshot')
                else:
                    checked_quotes += 1
        elif evidence.get('kind') == 'visual':
            observation = evidence.get('visual_review')
            if not isinstance(observation, dict) or not all(isinstance(observation.get(k), str)
                    and observation[k].strip() for k in ['reviewer', 'checked_at', 'observation']):
                pending.append(f'{eid}: visual evidence has no explicit inspection record')
        else:
            errors.append(f'{eid}: kind must be text or visual')

    reviewed_pairs = 0
    supported_pairs = 0
    total_pairs = 0
    for cid, claim in data['claims'].items():
        text_fields(claim, ['text'], cid)
        if claim.get('kind') not in ('fact', 'inference', 'proposal'):
            errors.append(f'{cid}: invalid kind')
        if claim.get('importance') not in ('key', 'context'):
            errors.append(f'{cid}: invalid importance')
        if claim.get('status') not in ('supported', 'partial', 'contradicted', 'unresolved', 'proposed'):
            errors.append(f'{cid}: invalid status')
        if (claim.get('kind') == 'proposal') != (claim.get('status') == 'proposed'):
            errors.append(f'{cid}: only proposals use proposed status')
        ids = id_list(claim.get('evidence_ids'), cid)
        total_pairs += len(ids)
        reviews = claim.get('reviews', [])
        if not isinstance(reviews, list) or any(not isinstance(r, dict) for r in reviews):
            errors.append(f'{cid}: reviews must be a list of objects')
            reviews = []
        mapped = {}
        for review in reviews:
            rid = review.get('evidence_id')
            if not isinstance(rid, str) or rid not in ids or rid in mapped:
                errors.append(f'{cid}: invalid/duplicate review evidence_id')
                continue
            mapped[rid] = review
            text_fields(review, ['reviewer', 'checked_at', 'rationale'], f'{cid}/{rid}')
            if review.get('judgment') not in JUDGMENTS:
                errors.append(f'{cid}/{rid}: invalid judgment')
        for eid in ids:
            evidence = data['evidence'].get(eid)
            if evidence is None:
                errors.append(f'{cid}: unknown evidence {eid}')
                continue
            sid = evidence.get('source_id')
            source = data['sources'].get(sid, {}) if isinstance(sid, str) else {}
            if metadata is None and source.get('family_id') == 'unknown':
                pending.append(f'{cid}/{eid}: source independence is unreviewed')
            if metadata is not None and evidence.get('origin_id') == 'unknown':
                pending.append(f'{cid}/{eid}: evidence origin is unreviewed')
            if metadata is not None and isinstance(metadata.get('routes'), list) and source.get('route') not in metadata['routes']:
                pending.append(f'{cid}/{eid}: evidence route is outside selected scope')
            if source.get('read_level') in ('snippet', 'discovered', 'unavailable'):
                pending.append(f'{cid}/{eid}: underlying source not read')
            judgment = mapped.get(eid, {}).get('judgment')
            if judgment in ('supports', 'partial', 'contradicts', 'irrelevant'):
                reviewed_pairs += 1
                supported_pairs += judgment == 'supports'
            else:
                pending.append(f'{cid}/{eid}: semantic review missing or unresolved')
        judgments = {r.get('judgment') for r in mapped.values() if isinstance(r.get('judgment'), str)}
        if claim.get('kind') != 'proposal' and not ids:
            pending.append(f'{cid}: no evidence linked')
        if claim.get('status') in ('partial', 'unresolved'):
            pending.append(f'{cid}: claim remains {claim["status"]}')
        if claim.get('status') == 'supported' and ('supports' not in judgments or
                ('contradicts' in judgments and not claim.get('resolution'))):
            pending.append(f'{cid}: supported label lacks support or contradiction resolution')
        if claim.get('status') == 'contradicted' and 'contradicts' not in judgments:
            pending.append(f'{cid}: contradicted label lacks reviewed counterevidence')
        if claim.get('kind') != 'proposal' and claim.get('importance') == 'key':
            counter = claim.get('counter_search')
            if not isinstance(counter, dict):
                pending.append(f'{cid}: counterevidence search missing')
                continue
            qids = id_list(counter.get('query_ids', []), f'{cid}:counter_search')
            outcome = counter.get('outcome')
            if outcome == 'not_applicable':
                if not counter.get('rationale'):
                    pending.append(f'{cid}: counter search exemption needs a specific reason')
            elif outcome in ('found', 'not_found'):
                if not qids or not counter.get('rationale') or any(
                        data['queries'].get(q, {}).get('status') != 'completed' or
                        data['queries'].get(q, {}).get('purpose') != 'counterevidence' for q in qids):
                    pending.append(f'{cid}: counter search needs completed query records and scope')
                if outcome == 'found':
                    counter_ids = id_list(counter.get('evidence_ids', []), f'{cid}:counter_evidence')
                    if not counter_ids or any(e not in ids for e in counter_ids) or not claim.get('resolution'):
                        pending.append(f'{cid}: found counterevidence needs linked reviews and resolution')
            else:
                pending.append(f'{cid}: counterevidence search not completed')

    if not data['claims']:
        pending.append('No claims recorded; an empty study is not ready')
    if metadata is not None and not errors:
        for claim in data['claims'].values():
            if claim.get('importance') == 'key' and claim.get('kind') != 'proposal':
                validate_stress_review(claim, analyze_claim(data, metadata, claim), errors, pending)
    families = {s.get('family_id') for s in data['sources'].values()
                if isinstance(s.get('family_id'), str) and s['family_id'] != 'unknown'}
    report = {'integrity': 'fail' if errors else 'pass',
            'review_readiness': 'needs_review' if errors or pending else 'ready',
            'truth_certified': False,
            'semantic_validation': 'reviewer-recorded judgments only; not independently verified by this script',
            'errors': errors, 'pending': pending,
            'route_coverage': coverage,
            'metrics': {'sources': len(data['sources']), 'source_families': len(families),
                        'unclassified_sources': sum(s.get('family_id') == 'unknown' for s in data['sources'].values()),
                        'claims': len(data['claims']), 'exact_quotes_found': checked_quotes,
                        'claim_evidence_pairs': total_pairs, 'reviewed_pairs': reviewed_pairs,
                        'recorded_supporting_pairs': supported_pairs,
                        'recorded_support_fraction': supported_pairs / reviewed_pairs if reviewed_pairs else None}}
    return report, data, metadata


def check(root):
    return inspect_study(root)[0]


def read_metadata(root, data, errors):
    """Absent metadata alone denotes legacy; malformed metadata never does."""
    path = root / 'study.json'
    if not path.exists():
        return None
    try:
        metadata = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        errors.append(f'study.json: {error}')
        return {}
    if not isinstance(metadata, dict):
        errors.append('study.json: expected an object')
        return {}
    if type(metadata.get('schema_version')) is not int or metadata['schema_version'] != 2:
        errors.append('study.json: unsupported schema_version; expected 2')
    mode, routes = metadata.get('mode'), metadata.get('routes')
    if mode not in MODES or not isinstance(routes, list) or routes not in (
            [mode], *ADDITIVE_ROUTES) or (
            isinstance(routes, list) and len(routes) > 1 and mode != 'literature'):
        errors.append('study.json: invalid mode/routes combination')
    if not isinstance(metadata.get('question'), str):
        errors.append('study.json: question must be text')
    for table in ('queries', 'sources'):
        for identity, record in data[table].items():
            if record.get('route') not in MODES:
                errors.append(f'{identity}: route must be literature, technical, general or community')
    origins = metadata.get('origins')
    if not isinstance(origins, list) or any(not isinstance(o, dict) for o in origins):
        errors.append('study.json: origins must be a list of objects')
        return metadata
    mapped = {}
    for origin in origins:
        oid = origin.get('origin_id')
        if not isinstance(oid, str) or not oid.strip() or oid == 'unknown' or oid in mapped:
            errors.append('study.json: invalid/duplicate/reserved origin_id')
            continue
        mapped[oid] = origin
        for key in ('kind', 'label', 'rationale', 'reviewer', 'checked_at'):
            if not isinstance(origin.get(key), str) or not origin[key].strip():
                errors.append(f'{oid}: missing/non-text {key}')
        sids = origin.get('source_ids')
        if not isinstance(sids, list) or not sids or any(
                not isinstance(s, str) or s not in data['sources'] for s in sids):
            errors.append(f'{oid}: source_ids must reference existing sources')
        elif len(set(sids)) != len(sids):
            errors.append(f'{oid}: duplicate source_ids')
        deps = origin.get('shared_dependencies', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) or not d.strip() for d in deps):
            errors.append(f'{oid}: shared_dependencies must be a list of text labels')
    for eid, evidence in data['evidence'].items():
        oid = evidence.get('origin_id')
        if oid == 'unknown':
            continue
        if not isinstance(oid, str) or oid not in mapped:
            errors.append(f'{eid}: missing/unknown origin_id (use "unknown" if unclassified)')
        else:
            sids = mapped[oid].get('source_ids')
            if isinstance(sids, list) and evidence.get('source_id') not in sids:
                errors.append(f'{eid}: origin does not include this source')
    return metadata


def analyze_claim(data, metadata, claim):
    """Compute only recorded relations; never infer independence or support."""
    ids = claim['evidence_ids']
    judgments = {r['evidence_id']: r['judgment'] for r in claim.get('reviews', [])}
    origins = {o['origin_id']: o for o in metadata['origins']} if metadata is not None else {}
    groups, unknown = {}, []
    for eid in ids:
        evidence = data['evidence'][eid]
        oid = evidence.get('origin_id') if metadata is not None else data['sources'][evidence['source_id']]['family_id']
        if oid == 'unknown':
            unknown.append(eid)
        else:
            groups.setdefault(oid, []).append(eid)
    support = [eid for eid in ids if judgments.get(eid) == 'supports']
    support_origins = [oid for oid, eids in groups.items() if any(e in support for e in eids)]
    structure = ('no_recorded_support' if not support else 'independence_unknown' if unknown else
                 'single_origin' if len(support_origins) == 1 else 'multiple_origins')
    basis = {'claim': {k: v for k, v in claim.items() if k != 'stress_test'},
             'evidence': [data['evidence'][e] for e in ids],
             'sources': [data['sources'][sid] for sid in sorted({data['evidence'][e]['source_id'] for e in ids})],
             'origins': [origins[o] for o in sorted(groups)] if metadata is not None else None,
             'scope': {k: metadata[k] for k in ('mode', 'routes', 'question')} if metadata is not None else None}
    basis_sha = digest(json.dumps(basis, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    dependencies = {}
    for oid in sorted(groups):
        for dep in origins.get(oid, {}).get('shared_dependencies', []):
            dependencies.setdefault(dep, []).append(oid)
    scenarios = []
    for oid, removed in sorted(groups.items()):
        remaining = [e for e in support if e not in removed]
        scenarios.append({'excluded_origin_id': oid, 'removed_evidence_ids': removed,
                          'remaining_support_ids': remaining,
                          'remaining_counter_ids': [e for e in ids if e not in removed and judgments.get(e) == 'contradicts'],
                          'requires_review': not remaining})
    return {'claim_id': claim['claim_id'], 'structure': structure, 'basis_sha256': basis_sha,
            'support_ids': support, 'counter_ids': [e for e in ids if judgments.get(e) == 'contradicts'],
            'partial_ids': [e for e in ids if judgments.get(e) == 'partial'],
            'unreviewed_ids': [e for e in ids if judgments.get(e) in (None, 'unresolved')],
            'unknown_origin_evidence_ids': unknown, 'shared_dependencies': dependencies,
            'scenarios': scenarios}


def validate_stress_review(claim, analysis, errors, pending):
    cid = claim['claim_id']
    recorded = claim.get('stress_test')
    if recorded is None:
        pending.append(f'{cid}: stress review missing')
        return
    if not isinstance(recorded, dict):
        errors.append(f'{cid}: stress_test must be an object')
        return
    reviews = recorded.get('reviews')
    if not isinstance(reviews, list) or any(not isinstance(r, dict) for r in reviews):
        errors.append(f'{cid}: stress reviews must be a list of objects')
        return
    reason = recorded.get('selection_rationale')
    if not isinstance(reason, str) or not reason.strip():
        pending.append(f'{cid}: stress selection rationale missing')
    scenario_ids = {s['excluded_origin_id'] for s in analysis['scenarios']}
    reviewed, exemption = set(), False
    for review in reviews:
        oid, judgment = review.get('excluded_origin_id'), review.get('judgment')
        if judgment not in ('retained', 'narrowed', 'unresolved', 'not_applicable'):
            errors.append(f'{cid}: invalid stress judgment')
        if judgment == 'not_applicable':
            if 'excluded_origin_id' not in review or oid is not None or len(reviews) != 1:
                errors.append(f'{cid}: stress exemption must be a single null-origin review')
            exemption = True
        elif not isinstance(oid, str) or oid not in scenario_ids or oid in reviewed:
            errors.append(f'{cid}: invalid/duplicate excluded_origin_id')
        else:
            reviewed.add(oid)
        for key in ('reviewer', 'checked_at', 'rationale', 'basis_sha256'):
            if not isinstance(review.get(key), str) or not review[key].strip():
                errors.append(f'{cid}: stress review missing/non-text {key}')
        if review.get('basis_sha256') != analysis['basis_sha256']:
            pending.append(f'{cid}: stale stress review; current claim/evidence/scope differs')
        if judgment == 'unresolved':
            pending.append(f'{cid}: stress judgment remains unresolved')
    if not exemption:
        if not reviewed:
            pending.append(f'{cid}: stress review needs a selected scenario or justified exemption')
        for scenario in analysis['scenarios']:
            if scenario['requires_review'] and scenario['excluded_origin_id'] not in reviewed:
                pending.append(f'{cid}: stress review required for {scenario["excluded_origin_id"]}')


def stress(root):
    validation, data, metadata = inspect_study(root)
    analyses = []
    if validation['integrity'] == 'pass':
        for claim in data['claims'].values():
            if claim['importance'] == 'key' and claim['kind'] != 'proposal':
                analyses.append(analyze_claim(data, metadata, claim))
    return dict(validation, origin_basis='evidence_origin' if metadata is not None else 'legacy_source_family',
                scope=({k: metadata.get(k) for k in ('mode', 'routes', 'question')} if metadata is not None else None),
                analysis_limits='Recorded relations only. Origin labels do not prove independence. Shared dependencies are not transitively removed.',
                claims=analyses)


def safe_text(value):
    text = str(value).replace('\r', ' ').replace('\n', ' ')
    text = html.escape(text, quote=False)
    return re.sub(r'([\\`*_{\[\]}()#!|])', r'\\\1', text)


def source_link(source):
    """Only http(s) URLs become clickable; local/fixture/unsafe URLs stay text."""
    url = source['url']
    try:
        parsed = urlsplit(url)
        if parsed.scheme in ('http', 'https') and parsed.hostname and not any(ord(c) < 32 for c in url):
            return '[' + safe_text(source['title']) + '](' + quote(url, safe=':/?&=%#@+;,~!$*-._') + ')'
    except ValueError:
        pass
    return safe_text(source['title']) + ' — ' + safe_text(url)


def render(root):
    validation, data, metadata = inspect_study(root)
    if validation['integrity'] != 'pass':
        raise ValueError('Cannot render invalid records: ' + '; '.join(validation['errors']))
    lines = ['# Research evidence cards', '', 'truth_certified: false', '',
             'Recorded evidence and reviewer judgments; no automatic truth or independence certification.', '',
             'Review state: ' + validation['review_readiness'],
             'Routes: ' + (', '.join(metadata['routes']) if metadata is not None else 'legacy / unspecified'),
             'Question: ' + safe_text(metadata.get('question', '')) if metadata is not None else 'Question: see brief.md', '']
    if metadata is not None:
        lines.extend(['## Source route coverage', ''])
        for route, counts in validation['route_coverage'].items():
            lines.append('- ' + route + ': ' + safe_text(json.dumps(counts, ensure_ascii=False)))
        lines.append('')
    for cid, claim in data['claims'].items():
        lines.extend(['## ' + safe_text(cid) + ' — ' + safe_text(claim['text']), '',
                      '- Status: ' + safe_text(claim['status']),
                      '- Scope: ' + safe_text(claim.get('scope', 'not recorded')),
                      '- Resolution: ' + safe_text(claim.get('resolution', 'not recorded')),
                      '- Next action: ' + safe_text(claim.get('next_action', 'not recorded')), '', '### Evidence', ''])
        reviews = {r['evidence_id']: r for r in claim.get('reviews', [])}
        for eid in claim['evidence_ids']:
            evidence = data['evidence'][eid]
            source = data['sources'][evidence['source_id']]
            review = reviews.get(eid, {})
            observation = evidence.get('quote', '') if evidence['kind'] == 'text' else (
                evidence['visual_review'].get('observation', 'not reviewed') if isinstance(evidence.get('visual_review'), dict) else 'not reviewed')
            lines.extend(['- ' + safe_text(eid) + ' [' + safe_text(review.get('judgment', 'unreviewed')) + ']: ' + source_link(source),
                          '  - Location: ' + safe_text(evidence['locator']) + '; version: ' + safe_text(source.get('version', 'unknown')) + '; read: ' + safe_text(source['read_level']),
                          '  - Passage/observation: ' + safe_text(observation),
                          '  - Review: ' + safe_text(review.get('rationale', 'not recorded'))])
            if source.get('snapshot_path'):
                lines.append('  - Preserved: [' + safe_text(evidence['source_id']) + ' snapshot](' + quote(source['snapshot_path'], safe='/.-_') + ')')
        if claim['importance'] == 'key' and claim['kind'] != 'proposal':
            analysis = analyze_claim(data, metadata, claim)
            lines.extend(['', '### Origin removal (recorded relations)', '', '- Structure: ' + analysis['structure'],
                          '- Unknown origins: ' + safe_text(', '.join(analysis['unknown_origin_evidence_ids']) or 'none'),
                          '- Shared dependencies: ' + safe_text(json.dumps(analysis['shared_dependencies'], ensure_ascii=False)),
                          '- Basis SHA-256: ' + analysis['basis_sha256']])
            recorded = (claim.get('stress_test') or {}) if metadata is not None else {}
            lines.append('- Review selection: ' + safe_text(recorded.get('selection_rationale', 'not recorded')))
            for scenario in analysis['scenarios']:
                oid = scenario['excluded_origin_id']
                lines.append('- Exclude ' + safe_text(oid) + '; remaining supports: ' + safe_text(', '.join(scenario['remaining_support_ids']) or 'none') +
                             '; remaining counterevidence: ' + safe_text(', '.join(scenario['remaining_counter_ids']) or 'none'))
                found = [r for r in recorded.get('reviews', []) if r['excluded_origin_id'] == oid]
                if not found:
                    lines.append('  - Human/agent review: not reviewed (automatic scenario only)')
                else:
                    r = found[0]
                    freshness = 'current' if r['basis_sha256'] == analysis['basis_sha256'] else 'STALE'
                    lines.append('  - Recorded judgment: ' + safe_text(r['judgment']) + ' (' + freshness + '); ' + safe_text(r['rationale']))
            for review in recorded.get('reviews', []):
                if review['judgment'] == 'not_applicable':
                    lines.append('- Exemption: ' + safe_text(review['rationale']))
        lines.append('')
    lines.extend(['## Pending review and access limits', ''])
    lines.extend('- ' + safe_text(item) for item in validation['pending'])
    if not validation['pending']:
        lines.append('- None recorded in the checked scope; this is not a truth certificate.')
    for sid, source in data['sources'].items():
        if source['read_level'] in ('snippet', 'abstract', 'discovered', 'unavailable') or source.get('access_limit'):
            lines.append('- ' + safe_text(sid) + ': ' + safe_text(source['read_level']) + '; ' + safe_text(source.get('access_limit', 'limited source access')))
    if metadata is None:
        lines.extend(['', 'Legacy analysis groups by source family; per-evidence study identity was not recorded.'])
    return '\n'.join(lines) + '\n'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--root', type=Path, required=True)
    init.add_argument('--mode', choices=MODES)
    init.add_argument('-tech', action='store_true')
    init.add_argument('-tech-only', action='store_true')
    init.add_argument('-comu', action='store_true')
    init.add_argument('-comu-only', action='store_true')
    init.add_argument('-all', dest='all_sources', action='store_true')
    init.add_argument('--question', default='')
    snapshot = commands.add_parser('snapshot')
    snapshot.add_argument('--root', type=Path, required=True)
    snapshot.add_argument('--input', type=Path, required=True)
    snapshot.add_argument('--source-id', required=True)
    snapshot.add_argument('--format', choices=['text', 'binary'], required=True)
    for command in ('check', 'stress', 'render'):
        validate = commands.add_parser(command)
        validate.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            result, code = initialize(args.root, args.mode, args.tech, args.all_sources, args.question,
                                     comu=args.comu, tech_only=args.tech_only, comu_only=args.comu_only), 0
        elif args.command == 'snapshot':
            result, code = capture(args.root, args.input, args.source_id, args.format), 0
        else:
            result = stress(args.root) if args.command == 'stress' else check(args.root)
            code = 1 if result['integrity'] == 'fail' else 2 if result['review_readiness'] != 'ready' else 0
            if args.command == 'render' and code != 1:
                print(render(args.root), end='')
                return code
    except (OSError, ValueError) as error:
        result, code = {'error': str(error), 'truth_certified': False}, 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
