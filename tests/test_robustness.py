"""Regressions from the 0.2.0 review: records survive odd input and hand edits, checks stay on."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from support import ROOT, StudyFixture, cli, ledger
from test_install_skills import installer, legacy_bundle


class RecordFileTests(unittest.TestCase):
    def setUp(self):
        self.study = StudyFixture(self)
        self.root = self.study.root

    def test_line_separator_characters_inside_strings_round_trip(self):
        source = dict(self.study.sources[0], source_id='s2', title='Line Separator and\x85next')
        ledger.add_row(self.root, 'sources', source)
        report = ledger.check(self.root)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['metrics']['sources'], 2)
        ledger.add_row(self.root, 'sources', dict(source, title='Plain'), reason='retitle')
        self.assertEqual(ledger.load(self.root)[1]['sources']['s2']['title'], 'Plain')

    def test_append_after_unterminated_last_line_keeps_both_rows(self):
        path = self.root / 'sources.jsonl'
        path.write_text(path.read_text(encoding='utf-8').rstrip('\n'), encoding='utf-8')
        ledger.add_row(self.root, 'sources', dict(self.study.sources[0], source_id='s2'))
        self.assertEqual(sorted(ledger.load(self.root)[1]['sources']), ['s1', 's2'])
        self.assertEqual(ledger.check(self.root)['errors'], [])

    def test_broken_study_json_is_never_rewritten(self):
        meta = json.loads((self.root / 'study.json').read_text(encoding='utf-8'))
        meta['origins'].append('TODO: classify the second source')
        (self.root / 'study.json').write_text(json.dumps(meta), encoding='utf-8')
        before = (self.root / 'study.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Fix study.json'):
            ledger.add_origin(self.root, StudyFixture.origin('b'))
        with self.assertRaisesRegex(ValueError, 'Fix study.json'):
            ledger.add_row(self.root, 'queries', dict(self.study.queries[0], query_id='q9'))
        self.assertEqual((self.root / 'study.json').read_bytes(), before)

    def test_old_schema_studies_are_refused(self):
        meta = json.loads((self.root / 'study.json').read_text(encoding='utf-8'))
        (self.root / 'study.json').write_text(json.dumps(dict(meta, schema_version=2)), encoding='utf-8')
        code, payload, _ = cli('add', '--root', self.root, '--table', 'queries',
                               '--json', json.dumps(dict(self.study.queries[0], query_id='q9')))
        self.assertEqual(code, 1)
        self.assertIn('schema_version', payload['error'])

    def test_route_order_does_not_matter(self):
        self.study.meta.update(mode='literature', routes=['technical', 'literature'])
        self.study.save()
        self.assertEqual(ledger.check(self.root)['errors'], [])
        ledger.add_origin(self.root, StudyFixture.origin('b'))
        meta = json.loads((self.root / 'study.json').read_text(encoding='utf-8'))
        self.assertEqual((meta['routes'], [o['origin_id'] for o in meta['origins']]),
                         (['technical', 'literature'], ['a', 'b']))

    def test_existing_errors_do_not_switch_checks_off_or_block_fixes(self):
        self.study.claims[0]['stress_test'] = 'garbage'
        self.study.sources[0]['sha256'] = '0' * 64
        report = self.study.check()
        self.assertIn('c1: stress_test must be an object', report['errors'])
        fixed = dict(self.study.sources[0], sha256=ledger.digest(
            (self.root / self.study.sources[0]['snapshot_path']).read_bytes()))
        ledger.add_row(self.root, 'sources', fixed, reason='correct the hash')
        self.assertEqual(ledger.check(self.root)['errors'], ['c1: stress_test must be an object'])

    def test_malformed_screening_is_an_error_not_a_crash(self):
        self.study.sources[0]['screening'] = 'included'
        self.study.save()
        code, report, stderr = cli('check', '--root', self.root)
        self.assertEqual(code, 1)
        self.assertNotIn('Traceback', stderr)
        self.assertTrue(any('screening' in e for e in report['errors']))

    def test_wrong_field_types_never_crash_the_check(self):
        samples = {'sources': self.study.sources[0], 'queries': self.study.queries[0],
                   'evidence': self.study.evidence[0], 'claims': self.study.claims[0]}
        for table, row in samples.items():
            for field in row:
                for value in ([1], {'x': 1}, 7, None):
                    with self.subTest(table=table, field=field, value=value):
                        broken = dict(row, **{field: value})
                        (self.root / f'{table}.jsonl').write_text(json.dumps(broken) + '\n', encoding='utf-8')
                        ledger.check(self.root)
                        ledger.stress(self.root)
                        try:
                            ledger.render(self.root)
                        except ValueError:  # refusing to render invalid records is the CLI's exit 1
                            pass
            self.study.save()


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.study = StudyFixture(self)
        self.root = self.study.root

    def source_with(self, sid, name, content):
        path = self.study.temp / name
        path.write_bytes(content)
        snap = ledger.capture(self.root, path, sid)
        ledger.register_source(self.root, snap, source_id=sid, title=name, route='literature',
                               read_level='full_text', url='fixture:' + name)

    def quote(self, sid, text, **extra):
        return ledger.add_row(self.root, 'evidence', dict(evidence_id='e9', source_id=sid, origin_id='unknown',
                                                          kind='text', locator='test', quote=text, **extra))

    def test_html_markup_comments_and_scripts_are_not_quotable(self):
        self.source_with('h1', 'page.html', b'<html><body><!-- retracted draft: The drug reduced mortality by half. -->'
                         b'<script>var claim = "The drug reduced mortality by half.";</script>'
                         b'<p>The drug did not reduce mortality in the final analysis.</p></body></html>')
        with self.assertRaisesRegex(ValueError, 'quote absent'):
            self.quote('h1', 'The drug reduced mortality by half.')
        self.assertIn('before', self.quote('h1', 'The drug did not reduce mortality in the final analysis.')['quote_context'])

    def test_invisible_quotes_are_rejected(self):
        for text in ('­', '​', '﻿'):
            with self.subTest(text=repr(text)), self.assertRaisesRegex(ValueError, 'no visible characters'):
                self.quote('s1', text, short_quote_reason='test')

    def test_line_break_hyphens_in_compounds_and_soft_hyphens(self):
        self.source_with('t1', 'hyphens.txt', 'A state-of-the-\nart method beat the hyphen-\nation baseline and the '
                         'nonde­\nscript one.\n'.encode('utf-8'))
        for text in ('A state-of-the-art method', 'beat the hyphenation baseline', 'and the nondescript one'):
            with self.subTest(text=text):
                ledger.add_row(self.root, 'evidence', dict(evidence_id='e-' + text[:5].replace(' ', ''), source_id='t1',
                                                           origin_id='unknown', kind='text', locator='line 1', quote=text))
        with self.assertRaisesRegex(ValueError, 'quote absent'):
            self.quote('t1', 'A state-of-the-arts method')

    def test_replacing_evidence_makes_its_review_stale(self):
        ledger.review(self.root, 'c1', 'e1', 'supports', 'Same release.')
        self.assertFalse(any('evidence changed' in p for p in ledger.check(self.root)['pending']))
        replaced = dict(self.study.evidence[0], quote='Release 2.0 supports Linux as the tested platform.')
        ledger.add_row(self.root, 'evidence', replaced, reason='different sentence')
        pending = ledger.check(self.root)['pending']
        self.assertIn('c1/e1: evidence changed after review; review it again', pending)

    def test_inline_reviews_get_a_fingerprint_and_origin_changes_do_not_stale_them(self):
        claim = dict(self.study.claims[0], claim_id='c2', importance='context')
        claim.pop('stress_test', None)
        ledger.add_row(self.root, 'claims', claim)
        self.assertIn('evidence_sha256', ledger.load(self.root)[1]['claims']['c2']['reviews'][0])
        ledger.add_origin(self.root, StudyFixture.origin('b'))
        ledger.add_row(self.root, 'evidence', dict(self.study.evidence[0], origin_id='b'), reason='reclassify')
        self.assertFalse(any('c2/e1: evidence changed' in p for p in ledger.check(self.root)['pending']))
        ledger.add_row(self.root, 'evidence', dict(self.study.evidence[0], origin_id='b', locator='line 2, end'),
                       reason='more precise location')
        self.assertIn('c2/e1: evidence changed after review; review it again', ledger.check(self.root)['pending'])
        self.assertIn('c1: stale stress review; current claim/evidence/scope differs', ledger.check(self.root)['pending'])
        ledger.stress_review(self.root, 'c1', 'b', 'narrowed', 'Only origin b remains.')
        stress = ledger.load(self.root)[1]['claims']['c1']['stress_test']['reviews']
        self.assertEqual([r['excluded_origin_id'] for r in stress], ['b'])
        self.assertFalse(any(p.startswith('c1: stale') for p in ledger.check(self.root)['pending']))

    def test_json_lines_input_keeps_line_separators_inside_strings(self):
        rows = self.study.temp / 'rows.jsonl'
        rows.write_text('\n'.join(json.dumps(dict(self.study.queries[0], query_id=q, query=q + ' text'),
                                             ensure_ascii=False) for q in ('q7', 'q8')), encoding='utf-8')
        code, payload, _ = cli('add', '--root', self.root, '--table', 'queries', '--json-file', rows)
        self.assertEqual((code, payload.get('ids')), (0, ['q7', 'q8']))

    def test_sniffing_and_byte_order_marks(self):
        self.assertEqual(ledger.sniff(b'<!DOCTYPE html><html>login</html>', 'text/html', '/paper.pdf'), 'html')
        self.assertEqual(ledger.sniff(b'%PDF-1.4 ...', '', '/download'), 'pdf')
        text = 'Windows support is experimental in this version.\n'
        self.source_with('u1', 'utf16.txt', '﻿'.encode('utf-16-le') + text.encode('utf-16-le'))
        self.assertIn('before', self.quote('u1', 'Windows support is experimental in this version.')['quote_context'])


def make_link(target, link):
    if sys.platform == 'win32':
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


class LegacyLinkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.skills = self.temp / 'skills'
        self.outside = self.temp / 'outside'
        (self.outside / 'cache/empty').mkdir(parents=True)
        (self.outside / 'notes.txt').write_text('keep', encoding='utf-8')
        self.skills.mkdir()

    def link_or_skip(self, link):
        try:
            make_link(self.outside, link)
        except OSError as error:
            self.skipTest(f'Links unavailable: {error}')

    def test_linked_legacy_folder_is_not_entered(self):
        self.link_or_skip(self.skills / 'deep-research')
        result = installer.remove_legacy(self.skills)
        self.assertEqual(result['legacy_removed'], [])
        self.assertTrue((self.outside / 'cache/empty').is_dir())
        self.assertTrue((self.skills / 'deep-research').exists())

    def test_undeletable_files_and_plain_file_packages_are_reported(self):
        legacy_bundle(self, self.skills)
        (self.skills / 'deep-research-all').rename(self.temp / 'moved')
        (self.skills / 'deep-research-all').write_text('not a folder', encoding='utf-8')
        target = self.skills / 'deep-research/SKILL.md'
        original = Path.unlink

        def unlink(path, *args, **kwargs):
            if path == target:
                raise PermissionError(13, 'Permission denied')
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, 'unlink', unlink):
            result = installer.remove_legacy(self.skills)
        kept = result['legacy_kept_modified_or_unknown']
        self.assertIn('deep-research-all (not a folder)', kept)
        self.assertIn('deep-research/SKILL.md (could not remove: Permission denied)', kept)
        self.assertTrue(target.exists())
        self.assertFalse((self.skills / 'deep-research-tech').exists())

    def test_link_inside_a_legacy_folder_is_not_entered(self):
        legacy_bundle(self, self.skills)
        self.link_or_skip(self.skills / 'deep-research/references/linked')
        result = installer.remove_legacy(self.skills)
        self.assertTrue(result['legacy_removed'])
        self.assertIn('deep-research/references/linked (link, not entered)', result['legacy_kept_modified_or_unknown'])
        self.assertTrue((self.outside / 'cache/empty').is_dir())
        self.assertEqual((self.outside / 'notes.txt').read_text(encoding='utf-8'), 'keep')


if __name__ == '__main__':
    unittest.main()
