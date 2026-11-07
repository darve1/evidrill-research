"""Evidrill research ledger: preserve sources, record evidence and reviews, check the records.

It never classifies semantic truth. Standard library only. The only network access is
`snapshot --url`, which downloads exactly the requested http(s) URL. Every write stays
inside the study folder. Exit codes for check/stress/render: 0 recorded reviews complete,
1 invalid records, 2 review remains. Outputs keep truth_certified:false.
"""
import argparse
import copy
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

VERSION = '0.2.0'
SCHEMA_VERSION = 3
TABLES = {'queries': 'query_id', 'sources': 'source_id', 'evidence': 'evidence_id', 'claims': 'claim_id'}
READ_LEVELS = ('discovered', 'snippet', 'abstract', 'relevant_sections', 'full_text', 'unavailable')
JUDGMENTS = ('supports', 'partial', 'contradicts', 'irrelevant', 'unresolved')
CLAIM_STATUSES = ('supported', 'partial', 'contradicted', 'unresolved', 'proposed')
STRESS_JUDGMENTS = ('retained', 'narrowed', 'unresolved', 'not_applicable')
COUNTER_OUTCOMES = ('found', 'not_found', 'not_applicable', 'not_searched')
MODES = ('literature', 'technical', 'general', 'community')
VALID_ROUTES = (['literature'], ['technical'], ['general'], ['community'],
                ['literature', 'technical'], ['literature', 'community'],
                ['literature', 'technical', 'community'], list(MODES))
CAPTURES = ('helper_fetched', 'downloaded', 'user_supplied', 'agent_written')
REVIEW_METHODS = ('self', 'fresh_agent', 'human')
SCREENING = ('included', 'excluded')
ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}')
SOURCE_ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')
MIN_QUOTE_CHARS, MIN_QUOTE_CHARS_CJK = 20, 10
MIN_COUNTER_QUERIES = 2
CONTEXT_CHARS = 80
MAX_FETCH_BYTES = 25 * 1024 * 1024
USER_AGENT = f'evidrill-research/{VERSION} (+https://github.com/darve1/evidrill-research)'
CJK = re.compile(r'[぀-ヿ㐀-鿿가-힯]')
FOLD = str.maketrans({'‘': "'", '’': "'", '‚': "'", '‛': "'", '“': '"', '”': '"',
                      '„': '"', '‟': '"', '­': None, '​': None, '﻿': None,
                      'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl'})


# ---------------------------------------------------------------- small helpers

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def evidence_digest(evidence):
    """Fingerprint of the evidence row a review judged; replacing the row makes the review stale."""
    return digest(json.dumps(evidence, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def inside(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Snapshot paths must be relative to the study')
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Snapshot path escapes the study')
    return target


LINE_BREAK_HYPHEN = r'(\w)([-‐])[ \t]*\r?\n[ \t]*(\w)'


def normalize(text, hyphens=None):
    """Fold only layout differences: whitespace, line-break hyphens, curly quotes, ligatures.

    Letters, digits, negations and other punctuation are compared exactly. `hyphens` handles a
    hyphen at a line end: 'join' drops it (hyphen-/nation), 'keep' keeps it (state-of-the-/art).
    Soft hyphens are invisible and always dropped.
    """
    text = re.sub(r'­[ \t]*\r?\n[ \t]*', '', unicodedata.normalize('NFC', text))
    if hyphens == 'join':
        text = re.sub(LINE_BREAK_HYPHEN, r'\1\3', text)
    elif hyphens == 'keep':
        text = re.sub(LINE_BREAK_HYPHEN, r'\1\2\3', text)
    return re.sub(r'\s+', ' ', text.translate(FOLD)).strip()


def text_variants(text):
    return list(dict.fromkeys([normalize(text), normalize(text, 'join'), normalize(text, 'keep')]))


def locate(quote_text, variants):
    """Return (before, after) context around the quote, or None when it is absent."""
    needle = normalize(quote_text)
    if not needle:
        return None
    for haystack in variants:
        index = haystack.find(needle)
        if index >= 0:
            return haystack[max(0, index - CONTEXT_CHARS):index], haystack[index + len(needle):index + len(needle) + CONTEXT_CHARS]
    return None


def is_short(quote_text):
    needle = normalize(quote_text)
    return len(needle) < (MIN_QUOTE_CHARS_CJK if CJK.search(needle) else MIN_QUOTE_CHARS)


def store(root, relative, raw):
    target = inside(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise ValueError('Existing content-addressed snapshot is damaged; refusing overwrite')
    else:
        with target.open('xb') as handle:
            handle.write(raw)


# ---------------------------------------------------------------- scope and init

def select_routes(mode=None, tech=False, all_sources=False, *, community=False, tech_only=False, community_only=False):
    if mode is not None:
        if mode not in MODES or any((tech, all_sources, community, tech_only, community_only)):
            raise ValueError('Choose an explicit --mode OR scope flags')
        return mode, [mode]
    if tech_only or community_only:
        if (tech_only and community_only) or any((tech, community, all_sources)):
            raise ValueError('An -only option cannot be combined with another scope flag')
        only = 'technical' if tech_only else 'community'
        return only, [only]
    if all_sources:
        return 'literature', list(MODES)
    routes = ['literature'] + (['technical'] if tech else []) + (['community'] if community else [])
    return 'literature', routes


def initialize(root, mode=None, tech=False, all_sources=False, question='', *,
               community=False, tech_only=False, community_only=False):
    mode, routes = select_routes(mode, tech, all_sources, community=community,
                                 tech_only=tech_only, community_only=community_only)
    root = Path(root).resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Study must be new or empty; existing records are never overwritten')
    root.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        (root / f'{table}.jsonl').write_text('', encoding='utf-8', newline='\n')
    (root / 'study.json').write_text(json.dumps({'schema_version': SCHEMA_VERSION, 'mode': mode, 'routes': routes,
        'question': question, 'origins': []}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (root / 'brief.md').write_text(
        '# Research brief\n\nDecision/question:\n\nScope, date, versions:\n\n'
        'Subquestions and search routes:\n\nExclusions and access limits:\n\n'
        'Stopping conditions and unresolved gaps:\n', encoding='utf-8', newline='\n')
    return {'root': str(root), 'mode': mode, 'routes': routes,
            'created': [f'{t}.jsonl' for t in TABLES] + ['brief.md', 'study.json']}


# ---------------------------------------------------------------- capture

class _TextExtractor(HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'template', 'svg'}
    BLOCK = {'p', 'div', 'br', 'li', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article',
             'header', 'footer', 'blockquote', 'pre', 'table', 'ul', 'ol', 'dd', 'dt', 'figcaption', 'caption',
             'main', 'nav', 'aside', 'hr', 'title'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skipping = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in self.BLOCK:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skipping = max(0, self.skipping - 1)
        elif tag in self.BLOCK:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def html_to_text(markup):
    parser = _TextExtractor()
    parser.feed(markup)
    parser.close()
    lines = (re.sub(r'[ \t\f\v]+', ' ', line).strip() for line in ''.join(parser.parts).splitlines())
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n'


BOMS = ((b'\xef\xbb\xbf', 'utf-8-sig'), (b'\xff\xfe\x00\x00', 'utf-32'), (b'\x00\x00\xfe\xff', 'utf-32'),
        (b'\xff\xfe', 'utf-16'), (b'\xfe\xff', 'utf-16'))


def bom_encoding(raw):
    return next((name for mark, name in BOMS if raw.startswith(mark)), None)


def decode(raw, content_type=''):
    candidates = [bom_encoding(raw)] if bom_encoding(raw) else []
    header = re.search(r'charset=["\']?([\w.-]+)', content_type or '', re.I)
    if header:
        candidates.append(header.group(1))
    meta = re.search(rb'<meta[^>]+charset=["\']?([\w.-]+)', raw[:4096], re.I)
    if meta:
        candidates.append(meta.group(1).decode('ascii', 'ignore'))
    for encoding in candidates + ['utf-8-sig']:
        try:
            return raw.decode('utf-8-sig' if encoding.lower() in ('utf-8', 'utf8') else encoding), encoding
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode('utf-8', errors='replace'), 'utf-8-with-replacement'


def sniff(raw, content_type='', name=''):
    kind = (content_type or '').split(';')[0].strip().lower()
    head = raw[:1024].lstrip().lower()
    name = name.lower()
    if raw.startswith(b'%PDF-'):
        return 'pdf'
    if kind in ('text/html', 'application/xhtml+xml') or head.startswith((b'<!doctype html', b'<html')):
        return 'html'  # a login or error page served for a .pdf URL is still HTML
    if kind == 'application/pdf' or name.endswith('.pdf'):
        return 'pdf'
    if name.endswith(('.html', '.htm')):
        return 'html'
    if bom_encoding(raw) or kind.startswith('text/') or kind in ('application/json', 'application/xml') \
            or name.endswith(('.txt', '.md', '.json', '.xml', '.csv')):
        return 'text'
    if not kind:
        try:
            raw.decode('utf-8')
            return 'text'
        except UnicodeDecodeError:
            pass
    return 'binary'


def pdf_text(raw):
    executable = shutil.which('pdftotext')
    if not executable:
        return None, 'pdftotext not found; original PDF preserved without extracted text'
    with tempfile.TemporaryDirectory() as temp:
        source, target = Path(temp) / 'in.pdf', Path(temp) / 'out.txt'
        source.write_bytes(raw)
        try:
            run = subprocess.run([executable, '-enc', 'UTF-8', str(source), str(target)],
                                 capture_output=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as error:
            return None, f'pdftotext failed: {error}'
        if run.returncode != 0 or not target.exists():
            return None, 'pdftotext failed: ' + run.stderr.decode('utf-8', 'replace')[-300:]
        return target.read_text(encoding='utf-8', errors='replace'), None


def fetch(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('--url must be an http(s) URL')
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(MAX_FETCH_BYTES + 1)
            if len(raw) > MAX_FETCH_BYTES:
                raise ValueError(f'Response exceeds {MAX_FETCH_BYTES} bytes; save it manually and use --input')
            info = {'requested_url': url, 'final_url': response.geturl(), 'status': response.status,
                    'content_type': response.headers.get('Content-Type'), 'fetched_at': now(), 'bytes': len(raw)}
    except HTTPError as error:
        raise ValueError(f'HTTP {error.code} for {url}; record the source as unavailable with access_limit') from None
    except (URLError, TimeoutError, OSError) as error:
        raise ValueError(f'Fetch failed for {url}: {error}; record the access limit') from None
    return raw, info


def capture(root, input_path=None, source_id='', media_format='auto', capture_kind='user_supplied', *, url=None):
    """Preserve original bytes and, for HTML/PDF/non-UTF-8 text, an extracted UTF-8 text copy."""
    root = Path(root).resolve()
    if not SOURCE_ID_RE.fullmatch(source_id or ''):
        raise ValueError('source_id must be 1-80 ASCII letters/digits/underscores/hyphens')
    if media_format not in ('auto', 'text', 'binary'):
        raise ValueError('format must be auto, text or binary')
    if url:
        raw, info = fetch(url)
        capture_kind, content_type, name = 'helper_fetched', info['content_type'] or '', urlsplit(info['final_url']).path
    else:
        if capture_kind not in ('downloaded', 'user_supplied', 'agent_written'):
            raise ValueError('--capture must be downloaded, user_supplied or agent_written')
        raw, info, content_type, name = Path(input_path).read_bytes(), None, '', str(input_path)
    kind = {'text': 'text', 'binary': 'binary'}.get(media_format) or sniff(raw, content_type, name)
    try:
        raw.decode('utf-8-sig')
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    if media_format == 'text' and not utf8:
        raise ValueError('--format text requires UTF-8 input')
    original_format = 'text' if kind in ('text', 'html') and utf8 else 'binary'
    sha = digest(raw)
    relative = f'snapshots/{source_id}/{sha}.' + {'html': 'html', 'pdf': 'pdf', 'text': 'txt'}.get(kind, 'bin')
    store(root, relative, raw)
    result = {'snapshot_path': relative, 'sha256': sha, 'format': original_format, 'bytes': len(raw),
              'capture': capture_kind, 'content_kind': kind}
    if info:
        result['fetch'] = info
    text, extraction, note = None, None, None
    if kind == 'html':
        text, extraction = html_to_text(decode(raw, content_type)[0]), 'html.parser'
    elif kind == 'pdf':
        text, note = pdf_text(raw)
        extraction = 'pdftotext' if text is not None else None
    elif kind == 'text' and not utf8:
        text, encoding = decode(raw, content_type)
        extraction = f'decode:{encoding}'
    if text is not None:
        encoded = text.encode('utf-8')
        text_sha = digest(encoded)
        store(root, f'snapshots/{source_id}/{text_sha}.txt', encoded)
        result.update(text_path=f'snapshots/{source_id}/{text_sha}.txt', text_sha256=text_sha,
                      text_extraction=extraction)
        if not text.strip():
            note = 'Extracted text is empty; the page may need JavaScript or the file may be scanned'
    if note:
        result['text_note'] = note
    return result


# ---------------------------------------------------------------- load and validate

def load(root):
    root = Path(root).resolve()
    errors, data, raw_counts = [], {}, {}
    for table, key in TABLES.items():
        records, nonempty = {}, 0
        try:
            # Split on \n only: U+2028, U+2029 and U+0085 may appear unescaped inside JSON strings.
            lines = (root / f'{table}.jsonl').read_text(encoding='utf-8-sig').split('\n')
        except (OSError, UnicodeError) as error:
            errors.append(f'{table}: cannot read: {error}')
            lines = []
        pattern = SOURCE_ID_RE if table == 'sources' else ID_RE
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            nonempty += 1
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
            if not isinstance(identity, str) or not pattern.fullmatch(identity) or identity in records:
                errors.append(f'{label}: missing/invalid/duplicate {key}')
                continue
            records[identity] = row
        data[table], raw_counts[table] = records, nonempty
    metadata = read_metadata(root, errors)
    return root, data, metadata, errors, raw_counts


def read_metadata(root, errors):
    path = root / 'study.json'
    if not path.exists():
        errors.append('study.json: missing; run init (schema 3)')
        return None
    try:
        metadata = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        errors.append(f'study.json: {error}')
        return None
    if not isinstance(metadata, dict):
        errors.append('study.json: expected an object')
        return None
    if type(metadata.get('schema_version')) is not int or metadata['schema_version'] != SCHEMA_VERSION:
        errors.append(f'study.json: unsupported schema_version; expected {SCHEMA_VERSION} '
                      '(studies made with 0.1.x need the 0.1.x helper)')
    mode, routes = metadata.get('mode'), metadata.get('routes')
    canonical = next((r for r in VALID_ROUTES if isinstance(routes, list) and len(routes) == len(r)
                      and all(isinstance(x, str) for x in routes) and set(routes) == set(r)), None)
    if mode not in MODES or canonical is None or (len(canonical) > 1 and mode != 'literature') \
            or (len(canonical) == 1 and canonical != [mode]):
        errors.append('study.json: invalid mode/routes combination')
        metadata['routes'] = canonical or []
    if not isinstance(metadata.get('question'), str):
        errors.append('study.json: question must be text')
    if not isinstance(metadata.get('origins'), list) or any(not isinstance(o, dict) for o in metadata['origins']):
        errors.append('study.json: origins must be a list of objects')
        metadata['origins'] = []
    return metadata


def validate(root, data, metadata, errors):
    """Return (report, context). `errors` holds load errors and is extended here."""
    pending, texts = [], {}

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

    origins = {}
    if metadata is not None:
        for table in ('queries', 'sources'):
            for identity, record in data[table].items():
                if record.get('route') not in MODES:
                    errors.append(f'{identity}: route must be literature, technical, general or community')
        for origin in metadata.get('origins', []):
            oid = origin.get('origin_id')
            if not isinstance(oid, str) or not ID_RE.fullmatch(oid) or oid == 'unknown' or oid in origins:
                errors.append('study.json: invalid/duplicate/reserved origin_id')
                continue
            origins[oid] = origin
            text_fields(origin, ('kind', 'label', 'rationale', 'reviewer', 'checked_at'), oid)
            sids = origin.get('source_ids')
            if not isinstance(sids, list) or not sids or any(not isinstance(s, str) or s not in data['sources'] for s in sids):
                errors.append(f'{oid}: source_ids must reference existing sources')
            elif len(set(sids)) != len(sids):
                errors.append(f'{oid}: duplicate source_ids')
            deps = origin.get('shared_dependencies', [])
            if not isinstance(deps, list) or any(not isinstance(d, str) or not d.strip() for d in deps):
                errors.append(f'{oid}: shared_dependencies must be a list of text labels')
            for field in ('design', 'population', 'effect', 'ci'):
                if field in origin and not isinstance(origin[field], str):
                    errors.append(f'{oid}: {field} must be text')
            if 'n' in origin and (type(origin['n']) is not int or origin['n'] < 0):
                errors.append(f'{oid}: n must be a non-negative integer')

    def screening_of(source):
        value = source.get('screening')
        return value if isinstance(value, dict) else {}

    # Every check below runs even when other errors exist, so fixing one error never reveals
    # previously hidden ones as "new" and an existing error never switches a check off.
    coverage = {}
    if metadata is not None:
        for route in metadata['routes']:
            queries = [q for q in data['queries'].values() if q.get('route') == route]
            sources = [s for s in data['sources'].values() if s.get('route') == route]
            coverage[route] = {
                'completed_queries': sum(q.get('status') == 'completed' for q in queries),
                'failed_queries': sum(q.get('status') == 'failed' for q in queries),
                'reported_results': sum(q['result_count'] for q in queries if type(q.get('result_count')) is int),
                'sources': len(sources),
                'read_sources': sum(s.get('read_level') in ('relevant_sections', 'full_text') for s in sources),
                'abstract_only_sources': sum(s.get('read_level') == 'abstract' for s in sources),
                'screened_in': sum(screening_of(s).get('decision') == 'included' for s in sources),
                'screened_out': sum(screening_of(s).get('decision') == 'excluded' for s in sources)}
            if not coverage[route]['completed_queries']:
                pending.append(f'{route}: selected route has no completed search; disclose access or scope gap')

    for sid, source in data['sources'].items():
        text_fields(source, ['url', 'title', 'family_id', 'retrieved_at', 'extraction_method'], sid)
        if source.get('read_level') not in READ_LEVELS:
            errors.append(f'{sid}: invalid read_level')
        if source.get('capture') not in CAPTURES:
            errors.append(f'{sid}: capture must be one of {", ".join(CAPTURES)}')
        elif source['capture'] == 'helper_fetched':
            fetched = source.get('fetch')
            if not isinstance(fetched, dict) or not all(isinstance(fetched.get(k), str) and fetched[k]
                                                         for k in ('final_url', 'fetched_at')):
                errors.append(f'{sid}: helper_fetched source needs fetch.final_url and fetch.fetched_at')
        screening = source.get('screening')
        if screening is not None and (not isinstance(screening, dict) or screening.get('decision') not in SCREENING
                                      or (screening.get('decision') == 'excluded'
                                          and not str(screening.get('reason') or '').strip())):
            errors.append(f'{sid}: screening needs decision included|excluded and a reason for exclusion')
        if not source.get('snapshot_path'):
            if source.get('read_level') not in ('discovered', 'snippet', 'unavailable'):
                pending.append(f'{sid}: read source has no preserved snapshot')
            continue
        if source.get('format') not in ('text', 'binary'):
            errors.append(f'{sid}: snapshot format must be text or binary')
        variants = []
        # With an extracted text copy (HTML, PDF, non-UTF-8 text), quotes are checked against that
        # readable text only, never against markup, comments or scripts in the original bytes.
        raw_is_text = source.get('format') == 'text' and 'text_path' not in source
        for path_key, hash_key, is_text in [('snapshot_path', 'sha256', raw_is_text),
                                           ('text_path', 'text_sha256', True)]:
            if path_key not in source:
                continue
            try:
                raw = inside(root, source[path_key]).read_bytes()
                if digest(raw) != source.get(hash_key):
                    errors.append(f'{sid}: {path_key} hash mismatch')
                if is_text:
                    variants += text_variants(raw.decode('utf-8-sig'))
            except (OSError, ValueError) as error:
                errors.append(f'{sid}: {path_key}: {error}')
        if variants:
            texts[sid] = variants

    for qid, query in data['queries'].items():
        text_fields(query, ['question_id', 'query', 'provider', 'searched_at'], qid)
        if query.get('purpose') not in ('discovery', 'counterevidence'):
            errors.append(f'{qid}: invalid purpose')
        if query.get('status') not in ('completed', 'failed'):
            errors.append(f'{qid}: invalid status')
        if 'result_count' in query and (type(query['result_count']) is not int or query['result_count'] < 0):
            errors.append(f'{qid}: result_count must be a non-negative integer')
        for sid in id_list(query.get('result_source_ids'), qid):
            if sid not in data['sources']:
                errors.append(f'{qid}: unknown source {sid}')

    checked_quotes, contexts = 0, {}
    for eid, evidence in data['evidence'].items():
        text_fields(evidence, ['source_id', 'locator'], eid)
        sid = evidence.get('source_id')
        if not isinstance(sid, str) or sid not in data['sources']:
            errors.append(f'{eid}: unknown source')
            continue
        source = data['sources'][sid]
        oid = evidence.get('origin_id')
        if metadata is not None and oid != 'unknown':
            if not isinstance(oid, str) or oid not in origins:
                errors.append(f'{eid}: missing/unknown origin_id (use "unknown" if unclassified)')
            elif isinstance(origins[oid].get('source_ids'), list) and sid not in origins[oid]['source_ids']:
                errors.append(f'{eid}: origin does not include this source')
        if evidence.get('kind') == 'text':
            text_fields(evidence, ['quote'], eid)
            passage = evidence.get('quote')
            if isinstance(passage, str) and passage.strip() and not normalize(passage):
                errors.append(f'{eid}: quote has no visible characters')
            elif sid not in texts:
                pending.append(f'{eid}: no preserved UTF-8 text for exact quote check')
            elif isinstance(passage, str) and passage.strip():
                found = locate(passage, texts[sid])
                if found is None:
                    errors.append(f'{eid}: quote absent from snapshot text (only whitespace, line-break '
                                  'hyphens, curly quotes and ligatures are normalized)')
                else:
                    checked_quotes += 1
                    contexts[eid] = found
                    if is_short(passage) and not str(evidence.get('short_quote_reason') or '').strip():
                        pending.append(f'{eid}: quote is shorter than {MIN_QUOTE_CHARS} characters '
                                       f'({MIN_QUOTE_CHARS_CJK} for CJK); extend it or give short_quote_reason')
                    if source.get('capture') == 'agent_written':
                        pending.append(f'{eid}: quote checked against agent-written text, not original source bytes')
        elif evidence.get('kind') == 'visual':
            observation = evidence.get('visual_review')
            if not isinstance(observation, dict) or not all(isinstance(observation.get(k), str)
                    and observation[k].strip() for k in ['reviewer', 'checked_at', 'observation']):
                pending.append(f'{eid}: visual evidence has no explicit inspection record')
        else:
            errors.append(f'{eid}: kind must be text or visual')

    reviewed_pairs = supported_pairs = total_pairs = 0
    methods = {}
    for cid, claim in data['claims'].items():
        text_fields(claim, ['text'], cid)
        if claim.get('kind') not in ('fact', 'inference', 'proposal'):
            errors.append(f'{cid}: invalid kind')
        if claim.get('importance') not in ('key', 'context'):
            errors.append(f'{cid}: invalid importance')
        if claim.get('status') not in CLAIM_STATUSES:
            errors.append(f'{cid}: invalid status')
        if (claim.get('kind') == 'proposal') != (claim.get('status') == 'proposed'):
            errors.append(f'{cid}: only proposals use proposed status')
        key_claim = claim.get('importance') == 'key' and claim.get('kind') != 'proposal'
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
            method = review.get('method', 'self')
            if method not in REVIEW_METHODS:
                errors.append(f'{cid}/{rid}: method must be self, fresh_agent or human')
            else:
                methods[method] = methods.get(method, 0) + 1
        for eid in ids:
            evidence = data['evidence'].get(eid)
            if evidence is None:
                errors.append(f'{cid}: unknown evidence {eid}')
                continue
            sid = evidence.get('source_id')
            source = data['sources'].get(sid, {}) if isinstance(sid, str) else {}
            if evidence.get('origin_id') == 'unknown':
                pending.append(f'{cid}/{eid}: evidence origin is unreviewed')
            if metadata is not None and source.get('route') not in metadata['routes']:
                pending.append(f'{cid}/{eid}: evidence route is outside selected scope')
            if source.get('read_level') in ('snippet', 'discovered', 'unavailable'):
                pending.append(f'{cid}/{eid}: underlying source not read')
            judgment = mapped.get(eid, {}).get('judgment')
            basis = mapped.get(eid, {}).get('evidence_sha256')
            if basis is not None and basis != evidence_digest(evidence):
                pending.append(f'{cid}/{eid}: evidence changed after review; review it again')
                judgment = None
            elif judgment in ('supports', 'partial', 'contradicts', 'irrelevant'):
                reviewed_pairs += 1
                supported_pairs += judgment == 'supports'
            else:
                pending.append(f'{cid}/{eid}: semantic review missing or unresolved')
            if key_claim and judgment == 'supports' and source.get('read_level') == 'abstract':
                pending.append(f'{cid}/{eid}: key support relies on an abstract only')
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
        if key_claim:
            counter = claim.get('counter_search')
            if not isinstance(counter, dict):
                pending.append(f'{cid}: counterevidence search missing')
                continue
            qids = id_list(counter.get('query_ids', []), f'{cid}:counter_search')
            outcome = counter.get('outcome')
            if outcome not in COUNTER_OUTCOMES:
                errors.append(f'{cid}: counter_search.outcome must be one of {", ".join(COUNTER_OUTCOMES)}')
            elif outcome == 'not_applicable':
                if not str(counter.get('rationale') or '').strip():
                    pending.append(f'{cid}: counter search exemption needs a specific reason')
            elif outcome in ('found', 'not_found'):
                done = [data['queries'].get(q, {}) for q in qids]
                distinct = {normalize(str(q.get('query', ''))).lower() for q in done
                            if q.get('status') == 'completed' and q.get('purpose') == 'counterevidence'}
                if not str(counter.get('rationale') or '').strip() or any(
                        q.get('status') != 'completed' or q.get('purpose') != 'counterevidence' for q in done):
                    pending.append(f'{cid}: counter search needs completed counterevidence query records and scope')
                elif len(distinct) < MIN_COUNTER_QUERIES:
                    pending.append(f'{cid}: counter search needs at least {MIN_COUNTER_QUERIES} distinct '
                                   'completed counterevidence queries')
                if outcome == 'found':
                    counter_ids = id_list(counter.get('evidence_ids', []), f'{cid}:counter_evidence')
                    if not counter_ids or any(e not in ids for e in counter_ids) or not claim.get('resolution'):
                        pending.append(f'{cid}: found counterevidence needs linked reviews and resolution')
            else:
                pending.append(f'{cid}: counterevidence search not completed')

    if not data['claims']:
        pending.append('No claims recorded; an empty study is not ready')
    if metadata is not None:
        for claim in data['claims'].values():
            if claim.get('importance') == 'key' and claim.get('kind') != 'proposal':
                try:
                    analysis = analyze_claim(data, metadata, claim)
                except (KeyError, TypeError, AttributeError):
                    continue  # malformed links are already reported above; the analysis needs them fixed
                validate_stress_review(claim, analysis, errors, pending)
    families = {s.get('family_id') for s in data['sources'].values()
                if isinstance(s.get('family_id'), str) and s['family_id'] != 'unknown'}
    captures = {}
    for source in data['sources'].values():
        label = source.get('capture') if isinstance(source.get('capture'), str) else 'invalid'
        captures[label] = captures.get(label, 0) + 1
    pending = list(dict.fromkeys(pending))
    report = {'integrity': 'fail' if errors else 'pass',
              'review_readiness': 'needs_review' if errors or pending else 'ready',
              'truth_certified': False,
              'semantic_validation': 'reviewer-recorded judgments only; not independently verified by this script',
              'errors': errors, 'pending': pending, 'route_coverage': coverage,
              'metrics': {'sources': len(data['sources']), 'source_families': len(families),
                          'unclassified_sources': sum(s.get('family_id') == 'unknown' for s in data['sources'].values()),
                          'source_capture': captures, 'claims': len(data['claims']),
                          'exact_quotes_found': checked_quotes, 'claim_evidence_pairs': total_pairs,
                          'reviewed_pairs': reviewed_pairs, 'recorded_supporting_pairs': supported_pairs,
                          'recorded_support_fraction': supported_pairs / reviewed_pairs if reviewed_pairs else None,
                          'review_methods': methods}}
    return report, {'texts': texts, 'contexts': contexts}


def inspect_study(root):
    root, data, metadata, errors, _ = load(root)
    report, context = validate(root, data, metadata, errors)
    return report, data, metadata, context


def check(root):
    return inspect_study(root)[0]


# ---------------------------------------------------------------- origin removal

def analyze_claim(data, metadata, claim):
    """Compute only recorded relations; never infer independence or support."""
    ids = claim['evidence_ids']
    judgments = {r['evidence_id']: r['judgment'] for r in claim.get('reviews', [])}
    origins = {o['origin_id']: o for o in metadata['origins']}
    groups, unknown = {}, []
    for eid in ids:
        oid = data['evidence'][eid].get('origin_id')
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
             'origins': [origins[o] for o in sorted(groups)],
             'scope': {k: metadata[k] for k in ('mode', 'routes', 'question')}}
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
    if not isinstance(recorded.get('selection_rationale'), str) or not recorded['selection_rationale'].strip():
        pending.append(f'{cid}: stress selection rationale missing')
    scenario_ids = {s['excluded_origin_id'] for s in analysis['scenarios']}
    reviewed, exemption = set(), False
    for review in reviews:
        oid, judgment = review.get('excluded_origin_id'), review.get('judgment')
        if judgment not in STRESS_JUDGMENTS:
            errors.append(f'{cid}: invalid stress judgment')
        if review.get('method', 'self') not in REVIEW_METHODS:
            errors.append(f'{cid}: stress review method must be self, fresh_agent or human')
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
    validation, data, metadata, _ = inspect_study(root)
    analyses = []
    if validation['integrity'] == 'pass':
        for claim in data['claims'].values():
            if claim['importance'] == 'key' and claim['kind'] != 'proposal':
                analyses.append(analyze_claim(data, metadata, claim))
    return dict(validation, scope={k: metadata.get(k) for k in ('mode', 'routes', 'question')} if metadata else None,
                analysis_limits='Recorded relations only. Origin labels do not prove independence. '
                                'Shared dependencies are not transitively removed.',
                claims=analyses)


# ---------------------------------------------------------------- record commands

def _rewrite(root, table, rows, raw_count, loaded_count):
    if raw_count != loaded_count:
        raise ValueError(f'{table}.jsonl has unreadable rows; fix them before modifying records')
    path = root / f'{table}.jsonl'
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8', newline='\n')
    temporary.replace(path)


def _append(path, text):
    """Append JSON Lines, first ending an unterminated last line so two rows never merge."""
    prefix = ''
    if path.exists() and path.stat().st_size:
        with path.open('rb') as handle:
            handle.seek(-1, 2)
            prefix = '' if handle.read(1) == b'\n' else '\n'
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(prefix + text)


def _history(root, operation, table, identity, reason, previous):
    _append(root / 'history.jsonl', json.dumps({'at': now(), 'op': operation, 'table': table, 'id': identity,
                                                'reason': reason, 'previous': previous}, ensure_ascii=False) + '\n')


def _commit(root, table, row, *, operation, reason=None, require_existing=False, metadata=None, history=None):
    """Validate the whole ledger with the change applied; write only if no new errors appear.

    `row` may be a list of new rows for one table: they are validated together and written all or none.
    `history` (default: whenever a row is replaced) controls whether the previous version goes to history.jsonl.
    """
    root, data, current_metadata, load_errors, raw_counts = load(root)
    if current_metadata is None:
        raise ValueError('Run init first: study.json is missing or unreadable')
    broken = [e for e in load_errors if e.startswith('study.json')]
    if broken:  # never write back a study.json that was only partly understood
        raise ValueError('Fix study.json by hand before recording: ' + '; '.join(broken))
    before, _ = validate(root, data, current_metadata, list(load_errors))
    candidate = copy.deepcopy(data)
    candidate_metadata = metadata if metadata is not None else current_metadata
    key = TABLES.get(table)
    rows = row if isinstance(row, list) else [row]
    previous = None
    if table == 'study':
        previous = current_metadata
    else:
        pattern = SOURCE_ID_RE if table == 'sources' else ID_RE
        for item in rows:
            identity = item.get(key)
            if not isinstance(identity, str) or not pattern.fullmatch(identity):
                raise ValueError(f'{key} must match {pattern.pattern}')
            previous = data[table].get(identity)
            if require_existing and previous is None:
                raise ValueError(f'{identity} does not exist in {table}')
            if previous is not None and not reason:
                raise ValueError(f'{identity} already exists; pass --replace with --reason to change it')
            if identity in candidate[table] and previous is None:
                raise ValueError(f'{identity} appears twice in this batch')
            candidate[table][identity] = item
        if len(rows) > 1 and previous is not None:
            raise ValueError('Batches only add new rows; replace rows one at a time')
    after, context = validate(root, candidate, candidate_metadata, list(load_errors))
    new_errors = [e for e in after['errors'] if e not in before['errors']]
    if new_errors:
        raise ValueError('Change rejected: ' + '; '.join(new_errors))
    if table == 'study':
        (root / 'study.json').write_text(json.dumps(candidate_metadata, ensure_ascii=False, indent=2) + '\n',
                                         encoding='utf-8', newline='\n')
    elif previous is None:
        _append(root / f'{table}.jsonl', ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in rows))
    else:
        _rewrite(root, table, list(candidate[table].values()), raw_counts[table], len(data[table]))
    if previous is not None and (history if history is not None else True):
        _history(root, operation, table, None if table == 'study' else rows[0].get(key), reason, previous)
    new_pending = [p for p in after['pending'] if p not in before['pending']]
    return {'ok': operation, 'new_pending': new_pending, 'review_readiness': after['review_readiness'],
            'truth_certified': False}, candidate, context


def _with_defaults(table, row):
    row = dict(row)
    if table == 'queries':
        row.setdefault('searched_at', now())
    if table == 'sources':
        row.setdefault('retrieved_at', now())
    if table == 'claims':
        row.setdefault('reviews', [])
    return row


def add_row(root, table, row, reason=None):
    if table not in TABLES:
        raise ValueError(f'table must be one of {", ".join(TABLES)}')
    row = _with_defaults(table, row)
    result, candidate, context = _commit(root, table, row, operation='replace' if reason else 'add', reason=reason)
    identity = row[TABLES[table]]
    if table == 'evidence' and identity in context['contexts']:
        before, after = context['contexts'][identity]
        result['quote_context'] = {'before': before, 'after': after}
    result['id'] = identity
    return result


def add_rows(root, table, rows):
    """Add several new rows to one table at once; nothing is written unless all of them pass."""
    if table not in TABLES:
        raise ValueError(f'table must be one of {", ".join(TABLES)}')
    if not rows:
        raise ValueError('No rows given')
    rows = [_with_defaults(table, row) for row in rows]
    result, candidate, context = _commit(root, table, rows, operation='add')
    key = TABLES[table]
    result['ids'] = [row[key] for row in rows]
    if table == 'evidence':
        result['quote_context'] = {row[key]: dict(zip(('before', 'after'), context['contexts'][row[key]]))
                                   for row in rows if row[key] in context['contexts']}
    return result


def register_source(root, snapshot, *, source_id, title, route, read_level, url, family_id='unknown', extra=None):
    method = snapshot['capture'] + (('+' + snapshot['text_extraction']) if snapshot.get('text_extraction') else '')
    row = {'source_id': source_id, 'url': url, 'title': title, 'route': route, 'family_id': family_id,
           'retrieved_at': (snapshot.get('fetch') or {}).get('fetched_at') or now(), 'read_level': read_level,
           'extraction_method': method}
    row.update({k: v for k, v in snapshot.items() if k not in ('bytes', 'content_kind', 'text_note')})
    row.update({k: v for k, v in (extra or {}).items() if v is not None})
    return add_row(root, 'sources', row)


def _claim(data, claim_id):
    claim = data['claims'].get(claim_id)
    if claim is None:
        raise ValueError(f'Unknown claim {claim_id}')
    return copy.deepcopy(claim)


def set_claim(root, claim_id, fields, reason):
    if not reason:
        raise ValueError('--reason is required when changing a claim')
    _, data, _, _, _ = load(root)
    claim = _claim(data, claim_id)
    claim.update({k: v for k, v in fields.items() if v is not None})
    return _commit(root, 'claims', claim, operation='set-claim', reason=reason, require_existing=True)[0]


def review(root, claim_id, evidence_id, judgment, rationale, reviewer='agent', method='self'):
    root, data, _, _, _ = load(root)
    claim = _claim(data, claim_id)
    if evidence_id not in (claim.get('evidence_ids') or []):
        raise ValueError(f'{evidence_id} is not linked to {claim_id}; add it to evidence_ids with set-claim first')
    reviews = [r for r in claim.get('reviews', []) if r.get('evidence_id') != evidence_id]
    replaced = len(reviews) != len(claim.get('reviews', []))
    entry = {'evidence_id': evidence_id, 'judgment': judgment, 'reviewer': reviewer, 'method': method,
             'checked_at': now(), 'rationale': rationale}
    if evidence_id in data['evidence']:
        entry['evidence_sha256'] = evidence_digest(data['evidence'][evidence_id])
    reviews.append(entry)
    claim['reviews'] = reviews
    result, candidate, context = _commit(root, 'claims', claim, operation='review',
                                         reason='review replaced' if replaced else 'review added',
                                         require_existing=True, history=replaced)
    evidence = candidate['evidence'].get(evidence_id, {})
    result['passage'] = evidence.get('quote') or (evidence.get('visual_review') or {}).get('observation')
    if evidence_id in context['contexts']:
        result['quote_context'] = dict(zip(('before', 'after'), context['contexts'][evidence_id]))
    return result


def counter(root, claim_id, outcome, rationale, query_ids=(), evidence_ids=()):
    root, data, _, _, _ = load(root)
    claim = _claim(data, claim_id)
    record = {'query_ids': list(query_ids), 'outcome': outcome, 'rationale': rationale}
    if evidence_ids:
        record['evidence_ids'] = list(evidence_ids)
    replaced = bool(claim.get('counter_search'))
    claim['counter_search'] = record
    return _commit(root, 'claims', claim, operation='counter', reason='counter search recorded',
                   require_existing=True, history=replaced)[0]


def add_origin(root, origin, reason=None):
    _, data, metadata, _, _ = load(root)
    if metadata is None:
        raise ValueError('Run init first')
    origin = dict(origin)
    origin.setdefault('checked_at', now())
    existing = [o for o in metadata['origins'] if o.get('origin_id') == origin.get('origin_id')]
    if existing and not reason:
        raise ValueError(f'{origin.get("origin_id")} exists; pass --replace with --reason to change it')
    updated = copy.deepcopy(metadata)
    updated['origins'] = [o for o in updated['origins'] if o.get('origin_id') != origin.get('origin_id')] + [origin]
    return _commit(root, 'study', None, operation='origin', reason=reason if existing else None,
                   metadata=updated, history=bool(existing))[0]


def stress_review(root, claim_id, origin_id, judgment, rationale, selection_rationale=None,
                  reviewer='agent', method='self'):
    report, data, metadata, context = inspect_study(root)
    if report['integrity'] != 'pass':
        raise ValueError('Fix record errors before stress review: ' + '; '.join(report['errors']))
    claim = _claim(data, claim_id)
    if claim.get('importance') != 'key' or claim.get('kind') == 'proposal':
        raise ValueError('Stress reviews apply to key fact/inference claims')
    analysis = analyze_claim(data, metadata, claim)
    scenario = next((s for s in analysis['scenarios'] if s['excluded_origin_id'] == origin_id), None)
    if judgment == 'not_applicable':
        if origin_id is not None:
            raise ValueError('not_applicable uses --not-applicable instead of --origin')
    elif scenario is None:
        raise ValueError(f'No removal scenario for origin {origin_id}; scenarios: '
                         + ', '.join(s['excluded_origin_id'] for s in analysis['scenarios']))
    recorded = claim.get('stress_test') or {}
    if selection_rationale:
        recorded['selection_rationale'] = selection_rationale
    if not str(recorded.get('selection_rationale') or '').strip():
        raise ValueError('Give --selection-rationale on the first stress review of a claim')
    entry = {'excluded_origin_id': origin_id, 'judgment': judgment, 'reviewer': reviewer, 'method': method,
             'checked_at': now(), 'rationale': rationale, 'basis_sha256': analysis['basis_sha256']}
    earlier = recorded.get('reviews', [])
    reviews = [] if judgment == 'not_applicable' else [
        r for r in earlier if r.get('excluded_origin_id') not in (origin_id, None)]
    replaced = len(reviews) != len(earlier)
    recorded['reviews'] = reviews + [entry]
    claim['stress_test'] = recorded
    result = _commit(root, 'claims', claim, operation='stress-review', reason='stress review recorded',
                     require_existing=True, history=replaced)[0]
    if scenario:
        def passages(ids):
            return [{'evidence_id': e, 'passage': data['evidence'][e].get('quote')
                     or (data['evidence'][e].get('visual_review') or {}).get('observation')} for e in ids]
        result['scenario'] = {'excluded_origin_id': origin_id, 'removed_evidence_ids': scenario['removed_evidence_ids'],
                              'remaining_support': passages(scenario['remaining_support_ids']),
                              'remaining_counter': passages(scenario['remaining_counter_ids'])}
    return result


# ---------------------------------------------------------------- render

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


def origin_note(origin):
    parts = [origin.get('kind')] + [f'{k}: {origin[k]}' for k in ('design', 'population', 'effect', 'ci') if origin.get(k)]
    if 'n' in origin:
        parts.append(f'n={origin["n"]}')
    return '; '.join(str(p) for p in parts if p)


def render(root):
    validation, data, metadata, context = inspect_study(root)
    if validation['integrity'] != 'pass':
        raise ValueError('Cannot render invalid records: ' + '; '.join(validation['errors']))
    origins = {o['origin_id']: o for o in metadata['origins']}
    lines = ['# Research evidence cards', '',
             'truth_certified: false. Recorded evidence and reviewer judgments; no automatic truth or independence certification.', '',
             '- Review state: ' + validation['review_readiness'],
             '- Routes: ' + ', '.join(metadata['routes']),
             '- Question: ' + safe_text(metadata.get('question', '')), '', '## Search and screening', '']
    for route, counts in validation['route_coverage'].items():
        line = (f'- {route}: {counts["completed_queries"]} completed and {counts["failed_queries"]} failed searches; '
                f'{counts["sources"]} sources, {counts["read_sources"]} read in full or relevant sections, '
                f'{counts["abstract_only_sources"]} abstract only')
        if counts['reported_results']:
            line += f'; {counts["reported_results"]} results reported by searches'
        if counts['screened_in'] or counts['screened_out']:
            line += f'; screening {counts["screened_in"]} included, {counts["screened_out"]} excluded'
        lines.append(line)
    methods = validation['metrics']['review_methods']
    if methods:
        lines.append('- Evidence reviews by method: ' + ', '.join(f'{k} {v}' for k, v in sorted(methods.items())))
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
            item = reviews.get(eid, {})
            observation = evidence.get('quote', '') if evidence['kind'] == 'text' else (
                evidence['visual_review'].get('observation', 'not reviewed') if isinstance(evidence.get('visual_review'), dict) else 'not reviewed')
            tag = item.get('judgment', 'unreviewed') + (', ' + item.get('method', 'self') if item else '')
            lines.extend(['- ' + safe_text(eid) + ' [' + safe_text(tag) + ']: ' + source_link(source),
                          '  - Location: ' + safe_text(evidence['locator']) + '; version: ' + safe_text(source.get('version', 'unknown'))
                          + '; read: ' + safe_text(source['read_level']) + '; capture: ' + safe_text(source.get('capture')),
                          '  - Passage/observation: ' + safe_text(observation)])
            if eid in context['contexts']:
                before, after = context['contexts'][eid]
                lines.append('  - Context: …' + safe_text(before) + ' **[passage]** ' + safe_text(after) + '…')
            lines.append('  - Review: ' + safe_text(item.get('rationale', 'not recorded')))
            if source.get('snapshot_path'):
                lines.append('  - Preserved: [' + safe_text(evidence['source_id']) + ' snapshot](' + quote(source['snapshot_path'], safe='/.-_') + ')')
        if claim['importance'] == 'key' and claim['kind'] != 'proposal':
            analysis = analyze_claim(data, metadata, claim)
            lines.extend(['', '### Origin removal (recorded relations)', '', '- Structure: ' + analysis['structure'],
                          '- Unknown origins: ' + safe_text(', '.join(analysis['unknown_origin_evidence_ids']) or 'none'),
                          '- Shared dependencies: ' + safe_text('; '.join(f'{d} ({", ".join(o)})' for d, o in analysis['shared_dependencies'].items()) or 'none'),
                          '- Basis SHA-256: ' + analysis['basis_sha256']])
            recorded = claim.get('stress_test') or {}
            lines.append('- Review selection: ' + safe_text(recorded.get('selection_rationale', 'not recorded')))
            for scenario in analysis['scenarios']:
                oid = scenario['excluded_origin_id']
                note = origin_note(origins.get(oid, {}))
                lines.append('- Exclude ' + safe_text(oid) + (' (' + safe_text(note) + ')' if note else '')
                             + '; remaining supports: ' + safe_text(', '.join(scenario['remaining_support_ids']) or 'none')
                             + '; remaining counterevidence: ' + safe_text(', '.join(scenario['remaining_counter_ids']) or 'none'))
                found = [r for r in recorded.get('reviews', []) if r['excluded_origin_id'] == oid]
                if not found:
                    lines.append('  - Review: not reviewed (automatic scenario only)')
                else:
                    r = found[0]
                    freshness = 'current' if r['basis_sha256'] == analysis['basis_sha256'] else 'STALE'
                    lines.append('  - Recorded judgment: ' + safe_text(r['judgment']) + ' (' + freshness + ', '
                                 + safe_text(r.get('method', 'self')) + '); ' + safe_text(r['rationale']))
            for item in recorded.get('reviews', []):
                if item['judgment'] == 'not_applicable':
                    lines.append('- Exemption: ' + safe_text(item['rationale']))
        lines.append('')
    lines.extend(['## Pending review and access limits', ''])
    lines.extend('- ' + safe_text(item) for item in validation['pending'])
    if not validation['pending']:
        lines.append('- None recorded in the checked scope; this is not a truth certificate.')
    for sid, source in data['sources'].items():
        if source['read_level'] in ('snippet', 'abstract', 'discovered', 'unavailable') or source.get('access_limit'):
            lines.append('- ' + safe_text(sid) + ': ' + safe_text(source['read_level']) + '; ' + safe_text(source.get('access_limit', 'limited source access')))
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- CLI

def _json_rows(args):
    """One object, a JSON array of objects, or JSON Lines (one object per line)."""
    if (args.json is None) == (args.json_file is None):
        raise ValueError('Give exactly one of --json or --json-file')
    text = (Path(args.json_file).read_text(encoding='utf-8-sig') if args.json_file else args.json).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            value = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as error:
            raise ValueError(f'Not JSON, a JSON array or JSON Lines: {error}') from None
    rows = value if isinstance(value, list) else [value]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError('Each JSON row must be an object')
    return rows


def _ids(value):
    return [item.strip() for item in (value or '').split(',') if item.strip()]


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)

    init = commands.add_parser('init', help='Create an empty study folder.')
    init.add_argument('--root', type=Path, required=True)
    init.add_argument('--mode', choices=MODES)
    for flag in ('-tech', '-tech-only', '-community', '-community-only'):
        init.add_argument(flag, action='store_true')
    init.add_argument('-all', dest='all_sources', action='store_true')
    init.add_argument('--question', default='')

    snap = commands.add_parser('snapshot', help='Preserve a source (download with --url or copy --input) and optionally register it.')
    snap.add_argument('--root', type=Path, required=True)
    snap.add_argument('--source-id', required=True)
    where = snap.add_mutually_exclusive_group(required=True)
    where.add_argument('--url', help='Download this http(s) URL with the helper (capture: helper_fetched).')
    where.add_argument('--input', type=Path, help='Preserve a local file.')
    snap.add_argument('--capture', default='user_supplied', choices=('downloaded', 'user_supplied', 'agent_written'),
                      help='For --input: how the file was obtained.')
    snap.add_argument('--format', default='auto', choices=('auto', 'text', 'binary'))
    snap.add_argument('--title', help='Register the source row too (requires --route and --read-level).')
    snap.add_argument('--route', choices=MODES)
    snap.add_argument('--read-level', choices=READ_LEVELS)
    snap.add_argument('--family-id', default='unknown')
    snap.add_argument('--source-url', help='Original URL of an --input file (default: its local path).')
    for field in ('publication-date', 'version', 'access-limit', 'notes'):
        snap.add_argument('--' + field)

    add = commands.add_parser('add', help='Validate and append rows to queries, sources, evidence or claims '
                                          '(--json-file may hold a JSON array or JSON Lines; all rows or none are written).')
    add.add_argument('--root', type=Path, required=True)
    add.add_argument('--table', required=True, choices=list(TABLES))
    add.add_argument('--json')
    add.add_argument('--json-file', type=Path)
    add.add_argument('--replace', action='store_true', help='Replace an existing row (old row kept in history.jsonl).')
    add.add_argument('--reason')

    setc = commands.add_parser('set-claim', help='Change claim fields; earlier versions go to history.jsonl.')
    setc.add_argument('--root', type=Path, required=True)
    setc.add_argument('--claim', required=True)
    setc.add_argument('--reason', required=True)
    for field in ('text', 'status', 'scope', 'next-action', 'resolution', 'evidence-ids'):
        setc.add_argument('--' + field)

    rev = commands.add_parser('review', help='Record a semantic judgment for one claim-evidence pair.')
    rev.add_argument('--root', type=Path, required=True)
    rev.add_argument('--claim', required=True)
    rev.add_argument('--evidence', required=True)
    rev.add_argument('--judgment', required=True, choices=JUDGMENTS)
    rev.add_argument('--rationale', required=True)
    rev.add_argument('--reviewer', default='agent')
    rev.add_argument('--method', default='self', choices=REVIEW_METHODS)

    cnt = commands.add_parser('counter', help='Record the counterevidence search for a claim.')
    cnt.add_argument('--root', type=Path, required=True)
    cnt.add_argument('--claim', required=True)
    cnt.add_argument('--outcome', required=True, choices=COUNTER_OUTCOMES)
    cnt.add_argument('--rationale', required=True)
    cnt.add_argument('--query-ids', default='')
    cnt.add_argument('--evidence-ids', default='')

    org = commands.add_parser('origin', help='Record one evidence origin (study, disclosure, implementation...).')
    org.add_argument('--root', type=Path, required=True)
    org.add_argument('--origin-id', required=True)
    org.add_argument('--kind', required=True)
    org.add_argument('--label', required=True)
    org.add_argument('--source-ids', required=True)
    org.add_argument('--rationale', required=True)
    org.add_argument('--reviewer', default='agent')
    org.add_argument('--shared-dependencies', nargs='*', default=[])
    for field in ('design', 'population', 'effect', 'ci'):
        org.add_argument('--' + field)
    org.add_argument('--n', type=int)
    org.add_argument('--replace', action='store_true')
    org.add_argument('--reason')

    srv = commands.add_parser('stress-review', help='Record a judgment for one origin-removal scenario.')
    srv.add_argument('--root', type=Path, required=True)
    srv.add_argument('--claim', required=True)
    which = srv.add_mutually_exclusive_group(required=True)
    which.add_argument('--origin')
    which.add_argument('--not-applicable', action='store_true')
    srv.add_argument('--judgment', required=True, choices=STRESS_JUDGMENTS)
    srv.add_argument('--rationale', required=True)
    srv.add_argument('--selection-rationale')
    srv.add_argument('--reviewer', default='agent')
    srv.add_argument('--method', default='self', choices=REVIEW_METHODS)

    for name, text in (('check', 'Check records (JSON).'), ('stress', 'List origin-removal scenarios (JSON).'),
                       ('render', 'Print evidence cards (Markdown).')):
        command = commands.add_parser(name, help=text)
        command.add_argument('--root', type=Path, required=True)
    return parser


def run(args):
    if args.command == 'init':
        return initialize(args.root, args.mode, args.tech, args.all_sources, args.question, community=args.community,
                          tech_only=args.tech_only, community_only=args.community_only), 0
    if args.command == 'snapshot':
        snapshot = capture(args.root, args.input, args.source_id, args.format, args.capture, url=args.url)
        if not args.title:
            return snapshot, 0
        if not args.route or not args.read_level:
            raise ValueError('--title registration also needs --route and --read-level')
        extra = {'publication_date': args.publication_date, 'version': args.version,
                 'access_limit': args.access_limit, 'notes': args.notes}
        url = args.url or args.source_url or str(Path(args.input).resolve())
        result = register_source(args.root, snapshot, source_id=args.source_id, title=args.title, route=args.route,
                                 read_level=args.read_level, url=url, family_id=args.family_id, extra=extra)
        result['snapshot'] = {k: snapshot[k] for k in snapshot if k in ('snapshot_path', 'text_path', 'text_note', 'content_kind')}
        return result, 0
    if args.command == 'add':
        if args.replace and not args.reason:
            raise ValueError('--replace needs --reason')
        rows = _json_rows(args)
        if len(rows) == 1:
            return add_row(args.root, args.table, rows[0], reason=args.reason if args.replace else None), 0
        if args.replace:
            raise ValueError('--replace takes one row')
        return add_rows(args.root, args.table, rows), 0
    if args.command == 'set-claim':
        fields = {'text': args.text, 'status': args.status, 'scope': args.scope, 'next_action': args.next_action,
                  'resolution': args.resolution,
                  'evidence_ids': _ids(args.evidence_ids) if args.evidence_ids is not None else None}
        return set_claim(args.root, args.claim, fields, args.reason), 0
    if args.command == 'review':
        return review(args.root, args.claim, args.evidence, args.judgment, args.rationale, args.reviewer, args.method), 0
    if args.command == 'counter':
        return counter(args.root, args.claim, args.outcome, args.rationale, _ids(args.query_ids), _ids(args.evidence_ids)), 0
    if args.command == 'origin':
        if args.replace and not args.reason:
            raise ValueError('--replace needs --reason')
        origin = {'origin_id': args.origin_id, 'kind': args.kind, 'label': args.label, 'source_ids': _ids(args.source_ids),
                  'rationale': args.rationale, 'reviewer': args.reviewer}
        if args.shared_dependencies:
            origin['shared_dependencies'] = args.shared_dependencies
        origin.update({k: getattr(args, k) for k in ('design', 'population', 'effect', 'ci', 'n') if getattr(args, k) is not None})
        return add_origin(args.root, origin, reason=args.reason if args.replace else None), 0
    if args.command == 'stress-review':
        return stress_review(args.root, args.claim, None if args.not_applicable else args.origin, args.judgment,
                             args.rationale, args.selection_rationale, args.reviewer, args.method), 0
    result = stress(args.root) if args.command == 'stress' else check(args.root)
    code = 1 if result['integrity'] == 'fail' else 2 if result['review_readiness'] != 'ready' else 0
    if args.command == 'render' and code != 1:
        return render(args.root), code
    return result, code


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    args = build_parser().parse_args(argv)
    try:
        result, code = run(args)
    except (OSError, ValueError) as error:
        result, code = {'error': str(error), 'truth_certified': False}, 1
    if isinstance(result, str):
        print(result, end='')
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
