"""Shared schema-3 fixture for helper tests. Self-authored text only."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/evidrill/scripts/research_ledger.py'
spec = importlib.util.spec_from_file_location('research_ledger', SCRIPT)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

SOURCE_TEXT = ('Release 2.0 supports Linux as the tested platform.\n'
               'Windows support is experimental in this version.\n'
               'Study A reports 90% on the small benchmark.\n'
               'Study B reports 80% on the small benchmark.\n')


def cli(*args, cwd=None, env=None):
    run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), *map(str, args)],
                         capture_output=True, text=True, encoding='utf-8', cwd=cwd, env=env)
    try:
        payload = json.loads(run.stdout)
    except ValueError:
        payload = run.stdout
    return run.returncode, payload, run.stderr


class StudyFixture:
    """A ready study: one source, one origin, one key claim with counter search and stress review."""

    def __init__(self, test):
        temp = tempfile.TemporaryDirectory()
        test.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.root = self.temp / 'study'
        ledger.initialize(self.root, question='What does the release say about Windows?')
        source = self.temp / 'release.txt'
        source.write_text(SOURCE_TEXT, encoding='utf-8')
        snap = ledger.capture(self.root, source, 's1', 'text')
        self.sources = [dict(snap, source_id='s1', url='fixture:release', title='Release notes', family_id='vendor',
                             route='literature', read_level='relevant_sections', retrieved_at='2026-11-06T00:00:00Z',
                             version='2.0', extraction_method='plain_text')]
        self.queries = [dict(query_id=f'q{i}', question_id='platform', query=text, provider='fixture-local-search',
                             searched_at='2026-11-06T00:00:00Z', purpose='counterevidence', status='completed',
                             result_source_ids=['s1'], route='literature')
                        for i, text in ((1, 'Windows stable support'), (2, 'Windows supported platform 2.0'))]
        self.evidence = [dict(evidence_id='e1', source_id='s1', origin_id='a', kind='text', locator='line 2',
                              quote='Windows support is experimental in this version.')]
        self.claims = [dict(claim_id='c1', text='Release 2.0 describes Windows support as experimental.',
                            kind='fact', importance='key', status='supported', evidence_ids=['e1'],
                            reviews=[dict(evidence_id='e1', judgment='supports', reviewer='fixture', method='self',
                                          checked_at='2026-11-06T00:00:00Z', rationale='Same release and platform.')],
                            counter_search=dict(query_ids=['q1', 'q2'], outcome='not_found',
                                                rationale='No stable-support statement in the supplied notes.'),
                            scope='Release 2.0 notes only.', next_action='Run the installer on Windows.')]
        self.meta = dict(schema_version=3, mode='literature', routes=['literature'],
                         question='What does the release say about Windows?', origins=[self.origin('a')])
        self.save()
        self.stress_review('a', 'narrowed')

    @staticmethod
    def origin(oid, sources=('s1',)):
        return dict(origin_id=oid, kind='disclosure', label='Origin ' + oid, source_ids=list(sources),
                    rationale='Vendor statement.', reviewer='fixture', checked_at='2026-11-06T00:00:00Z')

    def save(self):
        for name in ('sources', 'queries', 'evidence', 'claims'):
            rows = getattr(self, name)
            (self.root / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows),
                                                     encoding='utf-8')
        (self.root / 'study.json').write_text(json.dumps(self.meta), encoding='utf-8')

    def stress_review(self, oid, judgment, claim=0):
        self.claims[claim].pop('stress_test', None)
        self.save()
        analysis = {c['claim_id']: c for c in ledger.stress(self.root)['claims']}[self.claims[claim]['claim_id']]
        self.claims[claim]['stress_test'] = dict(selection_rationale='Only recorded origin.', reviews=[
            dict(excluded_origin_id=oid, judgment=judgment, rationale='No support remains without this origin.',
                 reviewer='fixture', method='self', checked_at='2026-11-06T00:00:00Z',
                 basis_sha256=analysis['basis_sha256'])])
        self.save()

    def check(self):
        self.save()
        return ledger.check(self.root)
