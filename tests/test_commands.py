"""Record commands: validated appends, reviews, origins and stress reviews without hand-written files."""
import json
import tempfile
import unittest
from pathlib import Path

from support import SOURCE_TEXT, cli, ledger


class CommandFlowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.root = self.temp / 'study'
        self.ok('init', '--root', self.root, '--question', 'Windows status?')
        source = self.temp / 'release.txt'
        source.write_text(SOURCE_TEXT, encoding='utf-8')
        self.ok('snapshot', '--root', self.root, '--source-id', 's1', '--input', source, '--capture', 'user_supplied',
                '--title', 'Release notes', '--route', 'literature', '--read-level', 'full_text',
                '--family-id', 'vendor', '--version', '2.0')

    def ok(self, *args, expect=0):
        code, payload, stderr = cli(*args)
        self.assertEqual(code, expect, (payload, stderr))
        return payload

    def add(self, table, row, expect=0, *extra):
        return self.ok('add', '--root', self.root, '--table', table, '--json', json.dumps(row), *extra, expect=expect)

    def build_ready_study(self):
        for qid, text in (('q1', 'Windows stable support'), ('q2', 'Windows supported platform 2.0')):
            self.add('queries', dict(query_id=qid, question_id='platform', query=text, provider='local search',
                                     purpose='counterevidence', status='completed', result_source_ids=['s1'],
                                     route='literature', result_count=1))
        self.ok('origin', '--root', self.root, '--origin-id', 'rel2', '--kind', 'disclosure', '--label', 'Release 2.0',
                '--source-ids', 's1', '--rationale', 'Vendor release note.', '--design', 'vendor note')
        added = self.add('evidence', dict(evidence_id='e1', source_id='s1', origin_id='rel2', kind='text',
                                          locator='line 2', quote='Windows support is experimental in this version.'))
        self.assertIn('Linux as the tested platform', added['quote_context']['before'])
        self.add('claims', dict(claim_id='c1', text='Release 2.0 describes Windows support as experimental.',
                                kind='fact', importance='key', status='supported', evidence_ids=['e1'],
                                scope='Release 2.0 notes.', next_action='Run the installer on Windows.'))
        reviewed = self.ok('review', '--root', self.root, '--claim', 'c1', '--evidence', 'e1', '--judgment', 'supports',
                           '--rationale', 'Direct statement about the same release.')
        self.assertEqual(reviewed['passage'], 'Windows support is experimental in this version.')
        self.ok('counter', '--root', self.root, '--claim', 'c1', '--outcome', 'not_found', '--query-ids', 'q1,q2',
                '--rationale', 'Two local searches found no stable-support statement.')
        stressed = self.ok('stress-review', '--root', self.root, '--claim', 'c1', '--origin', 'rel2',
                           '--judgment', 'narrowed', '--rationale', 'Only the vendor note supports this.',
                           '--selection-rationale', 'Single recorded origin.')
        self.assertEqual(stressed['scenario']['remaining_support'], [])

    def test_ready_study_from_commands_only(self):
        self.build_ready_study()
        code, report, _ = cli('check', '--root', self.root)
        self.assertEqual((code, report['review_readiness']), (0, 'ready'), report)
        self.assertEqual(report['metrics']['source_capture'], {'user_supplied': 1})
        code, output, _ = cli('render', '--root', self.root)
        self.assertEqual(code, 0)
        self.assertIn('narrowed (current, self)', output)
        self.assertIn('design: vendor note', output)

    def test_history_keeps_only_replaced_versions(self):
        self.build_ready_study()
        history = self.root / 'history.jsonl'
        self.assertFalse(history.exists() and history.read_text(encoding='utf-8').strip())
        self.ok('review', '--root', self.root, '--claim', 'c1', '--evidence', 'e1', '--judgment', 'partial',
                '--rationale', 'Second look.')
        entries = [json.loads(line) for line in history.read_text(encoding='utf-8').splitlines()]
        self.assertEqual([(e['op'], e['previous']['reviews'][0]['judgment']) for e in entries], [('review', 'supports')])

    def test_batch_file_adds_all_rows_or_none(self):
        query = dict(question_id='platform', provider='local search', purpose='discovery', status='completed',
                     result_source_ids=['s1'], route='literature')
        lines = self.temp / 'queries.jsonl'
        lines.write_text('\n'.join(json.dumps(dict(query, query_id=q, query=q + ' text')) for q in ('q1', 'q2')),
                         encoding='utf-8')
        added = self.ok('add', '--root', self.root, '--table', 'queries', '--json-file', lines)
        self.assertEqual(added['ids'], ['q1', 'q2'])
        self.ok('origin', '--root', self.root, '--origin-id', 'rel2', '--kind', 'disclosure', '--label', 'Release 2.0',
                '--source-ids', 's1', '--rationale', 'Vendor release note.')
        evidence = [dict(evidence_id='e1', source_id='s1', origin_id='rel2', kind='text', locator='line 2',
                         quote='Windows support is experimental in this version.'),
                    dict(evidence_id='e2', source_id='s1', origin_id='rel2', kind='text', locator='line 3',
                         quote='Windows support is stable in this version.')]
        array = self.temp / 'evidence.json'
        array.write_text(json.dumps(evidence), encoding='utf-8')
        self.ok('add', '--root', self.root, '--table', 'evidence', '--json-file', array, expect=1)
        self.assertFalse((self.root / 'evidence.jsonl').read_text(encoding='utf-8').strip())
        array.write_text(json.dumps(evidence[:1] * 2), encoding='utf-8')
        self.ok('add', '--root', self.root, '--table', 'evidence', '--json-file', array, expect=1)
        array.write_text(json.dumps(evidence[:1] + [dict(evidence[0], evidence_id='e2', locator='line 2 again')]),
                         encoding='utf-8')
        added = self.ok('add', '--root', self.root, '--table', 'evidence', '--json-file', array)
        self.assertIn('Linux as the tested platform', added['quote_context']['e1']['before'])
        self.ok('add', '--root', self.root, '--table', 'queries', '--json-file', lines, '--replace', '--reason', 'x',
                expect=1)

    def test_invalid_rows_are_rejected_before_writing(self):
        before = (self.root / 'evidence.jsonl').read_text(encoding='utf-8')
        payload = self.add('evidence', dict(evidence_id='e1', source_id='s1', origin_id='unknown', kind='text',
                                            locator='line 2', quote='Windows support is stable.'), 1)
        self.assertIn('quote absent', payload['error'])
        self.assertEqual(before, (self.root / 'evidence.jsonl').read_text(encoding='utf-8'))
        payload = self.add('claims', dict(claim_id='c1', text='x', kind='fact', importance='key', status='supported',
                                          evidence_ids=['missing']), 1)
        self.assertIn('unknown evidence', payload['error'])

    def test_existing_rows_need_replace_with_reason_and_keep_history(self):
        row = dict(query_id='q1', question_id='p', query='a', provider='local', purpose='discovery',
                   status='completed', result_source_ids=[], route='literature')
        self.add('queries', row)
        self.assertIn('already exists', self.add('queries', row, 1)['error'])
        self.ok('add', '--root', self.root, '--table', 'queries', '--json', json.dumps(dict(row, query='b')),
                '--replace', '--reason', 'typo in query text')
        history = [json.loads(line) for line in (self.root / 'history.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual((history[-1]['reason'], history[-1]['previous']['query']), ('typo in query text', 'a'))
        rows = (self.root / 'queries.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual([json.loads(r)['query'] for r in rows], ['b'])

    def test_set_claim_makes_stress_review_stale(self):
        self.build_ready_study()
        self.ok('set-claim', '--root', self.root, '--claim', 'c1', '--text',
                'Release 2.0 calls Windows support experimental.', '--reason', 'clearer wording')
        code, report, _ = cli('check', '--root', self.root)
        self.assertEqual(code, 2)
        self.assertTrue(any('stale' in p for p in report['pending']))
        self.ok('stress-review', '--root', self.root, '--claim', 'c1', '--origin', 'rel2', '--judgment', 'narrowed',
                '--rationale', 'Rechecked after rewording.')
        self.assertEqual(cli('check', '--root', self.root)[0], 0)

    def test_review_replaces_previous_judgment(self):
        self.build_ready_study()
        self.ok('review', '--root', self.root, '--claim', 'c1', '--evidence', 'e1', '--judgment', 'partial',
                '--rationale', 'Only part of the claim.', '--method', 'fresh_agent', '--reviewer', 'second agent')
        claim = ledger.load(self.root)[1]['claims']['c1']
        self.assertEqual([(r['judgment'], r['method']) for r in claim['reviews']], [('partial', 'fresh_agent')])

    def test_stress_review_rejects_unknown_origin_and_needs_selection_reason(self):
        self.build_ready_study()
        payload = self.ok('stress-review', '--root', self.root, '--claim', 'c1', '--origin', 'nope',
                          '--judgment', 'retained', '--rationale', 'x', expect=1)
        self.assertIn('No removal scenario', payload['error'])

    def test_origin_replacement_needs_reason(self):
        self.build_ready_study()
        payload = self.ok('origin', '--root', self.root, '--origin-id', 'rel2', '--kind', 'study', '--label', 'x',
                          '--source-ids', 's1', '--rationale', 'y', expect=1)
        self.assertIn('exists', payload['error'])
        self.ok('origin', '--root', self.root, '--origin-id', 'rel2', '--kind', 'disclosure', '--label', 'Release 2.0',
                '--source-ids', 's1', '--rationale', 'Vendor release note.', '--n', '1', '--replace', '--reason', 'add n')

    def test_snapshot_registration_refuses_duplicate_source(self):
        payload = self.ok('snapshot', '--root', self.root, '--source-id', 's1', '--input', self.temp / 'release.txt',
                          '--title', 'Again', '--route', 'literature', '--read-level', 'full_text', expect=1)
        self.assertIn('already exists', payload['error'])

    def test_commands_refuse_to_rewrite_unreadable_tables(self):
        self.build_ready_study()
        with (self.root / 'claims.jsonl').open('a', encoding='utf-8') as handle:
            handle.write('{broken\n')
        payload = self.ok('review', '--root', self.root, '--claim', 'c1', '--evidence', 'e1', '--judgment', 'supports',
                          '--rationale', 'again', expect=1)
        self.assertIn('unreadable rows', payload['error'])
        self.assertIn('{broken', (self.root / 'claims.jsonl').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
