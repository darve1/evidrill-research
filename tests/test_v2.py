"""Observable scope, origin removal, review freshness and delivery contracts."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_ledger import ledger, SCRIPT


class ScopeTests(unittest.TestCase):
    def run_init(self, *flags):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'study'
            run = subprocess.run([sys.executable, str(SCRIPT), 'init', '--root', str(root), *flags],
                                 capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue((root / 'study.json').is_file(), 'new studies need explicit scope metadata')
            return json.loads((root / 'study.json').read_text(encoding='utf-8'))

    def test_default_is_literature(self):
        meta = self.run_init()
        self.assertEqual((meta['schema_version'], meta['mode'], meta['routes']), (2, 'literature', ['literature']))

    def test_tech_adds_to_literature(self):
        self.assertEqual(self.run_init('-tech')['routes'], ['literature', 'technical'])

    def test_all_includes_all_routes(self):
        self.assertEqual(self.run_init('-all')['routes'], ['literature', 'technical', 'general', 'community'])

    def test_all_dominates_tech(self):
        self.assertEqual(self.run_init('-tech', '-all')['routes'], ['literature', 'technical', 'general', 'community'])

    def test_explicit_standalone_modes(self):
        for mode in ('literature', 'technical', 'general'):
            with self.subTest(mode=mode):
                self.assertEqual(self.run_init('--mode', mode)['routes'], [mode])

    def test_conflicting_explicit_mode_and_addition_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'study'
            run = subprocess.run([sys.executable, str(SCRIPT), 'init', '--root', str(root),
                                  '--mode', 'general', '-tech'], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(root.exists())


class StressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'study'
        ledger.initialize(self.root)
        source = Path(self.temp.name) / 'source.txt'
        source.write_text('Study A reports 90%.\nStudy B reports 80%.\n', encoding='utf-8')
        snap = ledger.capture(self.root, source, 's1', 'text')
        self.sources = [dict(snap, source_id='s1', url='fixture:paper', title='Two studies',
                             family_id='publication', read_level='relevant_sections',
                             retrieved_at='2026-11-06T00:00:00Z', extraction_method='plain_text', version='v1', route='literature')]
        self.evidence = [dict(evidence_id='e1', source_id='s1', origin_id='a', kind='text',
                              locator='line 1', quote='Study A reports 90%.')]
        self.queries = [dict(query_id='q1', question_id='result', query='contrary results',
                             provider='fixture-local-search', searched_at='2026-11-06T00:00:00Z',
                             purpose='counterevidence', status='completed', result_source_ids=['s1'], route='literature')]
        self.claims = [dict(claim_id='c1', text='Study A reports 90%.', kind='fact', importance='key',
                            status='supported', evidence_ids=['e1'],
                            reviews=[dict(evidence_id='e1', judgment='supports', reviewer='fixture',
                                          checked_at='2026-11-06T00:00:00Z', rationale='Direct report.')],
                            counter_search=dict(query_ids=['q1'], outcome='not_found', rationale='Fixture only.'),
                            scope='Study A, v1', next_action='Independent replication remains to be checked.')]
        self.meta = dict(schema_version=2, mode='literature', routes=['literature'], question='What was reported?',
                         origins=[self.origin('a')])
        self.save()

    def origin(self, oid):
        return dict(origin_id=oid, kind='study', label='Study '+oid, source_ids=['s1'],
                    rationale='Identified by experiment ID.', reviewer='fixture', checked_at='2026-11-06T00:00:00Z')

    def save(self):
        for name in ('sources', 'evidence', 'queries', 'claims'):
            (self.root / (name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in getattr(self, name)), encoding='utf-8')
        (self.root / 'study.json').write_text(json.dumps(self.meta), encoding='utf-8')

    def analysis(self):
        self.save()
        self.assertTrue(callable(getattr(ledger, 'stress', None)), 'stress analysis is required')
        return ledger.stress(self.root)

    def review(self, oid='a', judgment='unresolved'):
        result = self.analysis()['claims'][0]
        self.claims[0]['stress_test'] = dict(selection_rationale='This origin supplies the decisive observation.', reviews=[
            dict(excluded_origin_id=oid, judgment=judgment, rationale='Removing this origin removes the recorded support.',
                 reviewer='fixture', checked_at='2026-11-06T00:00:00Z', basis_sha256=result['basis_sha256'])])
        self.save()

    def add_second(self, origin='b', judgment='supports'):
        self.evidence.append(dict(evidence_id='e2', source_id='s1', origin_id=origin, kind='text',
                                  locator='line 2', quote='Study B reports 80%.'))
        self.claims[0]['evidence_ids'].append('e2')
        self.claims[0]['reviews'].append(dict(self.claims[0]['reviews'][0], evidence_id='e2', judgment=judgment))
        if origin != 'a':
            self.meta['origins'].append(self.origin(origin))

    def test_single_origin_removal_loses_all_recorded_support(self):
        result = self.analysis()
        self.assertFalse(result['truth_certified'])
        claim = result['claims'][0]
        self.assertEqual(claim['structure'], 'single_origin')
        self.assertEqual(claim['scenarios'][0]['remaining_support_ids'], [])
        self.assertEqual(claim['scenarios'][0]['removed_evidence_ids'], ['e1'])

    def test_two_studies_in_one_paper_are_not_collapsed(self):
        self.add_second()
        claim = self.analysis()['claims'][0]
        self.assertEqual(claim['structure'], 'multiple_origins')
        scenarios = {x['excluded_origin_id']: x for x in claim['scenarios']}
        self.assertEqual(scenarios['a']['remaining_support_ids'], ['e2'])
        self.assertEqual(scenarios['b']['remaining_support_ids'], ['e1'])

    def test_multiple_reports_of_one_study_removed_together(self):
        self.add_second(origin='a')
        self.sources.append(dict(self.sources[0], source_id='s2', url='fixture:reprint'))
        self.evidence[1]['source_id'] = 's2'
        self.meta['origins'][0]['source_ids'].append('s2')
        claim = self.analysis()['claims'][0]
        self.assertEqual(len(claim['scenarios']), 1)
        self.assertEqual(claim['scenarios'][0]['removed_evidence_ids'], ['e1', 'e2'])

    def test_partial_and_opposing_evidence_are_not_support(self):
        for judgment in ('partial', 'contradicts', 'irrelevant', 'unresolved'):
            with self.subTest(judgment=judgment):
                self.claims[0]['reviews'][0]['judgment'] = judgment
                claim = self.analysis()['claims'][0]
                self.assertEqual(claim['support_ids'], [])
                self.assertEqual(claim['structure'], 'no_recorded_support')

    def test_unknown_origin_is_not_independent_support(self):
        self.evidence[0]['origin_id'] = 'unknown'
        claim = self.analysis()['claims'][0]
        self.assertEqual(claim['structure'], 'independence_unknown')
        self.assertEqual(claim['unknown_origin_evidence_ids'], ['e1'])
        self.assertEqual(claim['scenarios'], [])

    def test_shared_dependency_is_visible_without_merging_studies(self):
        self.add_second()
        for origin in self.meta['origins']:
            origin['shared_dependencies'] = ['dataset W']
        claim = self.analysis()['claims'][0]
        self.assertEqual(claim['shared_dependencies'], {'dataset W': ['a', 'b']})
        self.assertEqual(len(claim['scenarios']), 2)

    def test_missing_manual_stress_review_stays_pending(self):
        self.save()
        report = ledger.check(self.root)
        self.assertEqual(report['review_readiness'], 'needs_review')
        self.assertTrue(any('stress' in p for p in report['pending']))

    def test_manual_review_can_complete_records_without_truth_claim(self):
        self.review(judgment='narrowed')
        report = ledger.check(self.root)
        self.assertEqual(report['review_readiness'], 'ready', report)
        self.assertFalse(report['truth_certified'])

    def test_unresolved_stress_review_remains_pending(self):
        self.review()
        self.assertEqual(ledger.check(self.root)['review_readiness'], 'needs_review')

    def test_changed_claim_or_source_invalidates_manual_review(self):
        self.review(judgment='narrowed')
        self.sources[0]['version'] = 'v2'
        self.save()
        report = ledger.check(self.root)
        self.assertTrue(any('stale' in p for p in report['pending']), report)

    def test_invalid_origin_reference_fails(self):
        self.evidence[0]['origin_id'] = 'missing'
        self.save()
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_origin_must_include_the_evidence_source(self):
        self.meta['origins'][0]['source_ids'] = []
        self.save()
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_malformed_or_future_metadata_is_not_legacy(self):
        for meta in ([], {}, dict(self.meta, schema_version=999), dict(self.meta, schema_version=True),
                     dict(self.meta, mode=[]), dict(self.meta, routes=['general']),
                     dict(self.meta, origins=[[]])):
            with self.subTest(meta=meta):
                self.meta = meta
                self.save()
                self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_invalid_json_metadata_fails(self):
        (self.root / 'study.json').write_text('{bad', encoding='utf-8')
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_wrong_manual_review_shapes_fail_without_crashing(self):
        for value in ([], {'reviews': [None]}, {'reviews': [{'excluded_origin_id': []}]}):
            self.claims[0]['stress_test'] = value
            self.save()
            self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_legacy_uses_source_family_with_explicit_limit(self):
        (self.root / 'study.json').unlink()
        self.assertTrue(callable(getattr(ledger, 'stress', None)))
        result = ledger.stress(self.root)
        self.assertEqual(result['origin_basis'], 'legacy_source_family')
        self.assertEqual(result['claims'][0]['scenarios'][0]['excluded_origin_id'], 'publication')

    def test_render_contains_trace_scope_opposition_and_pending(self):
        self.add_second(judgment='contradicts')
        self.save()
        self.assertTrue(callable(getattr(ledger, 'render', None)))
        output = ledger.render(self.root)
        for token in ('c1', 'e1', 'e2', 'line 1', 'line 2', 'Study A, v1', 'Independent replication', 'contradicts'):
            self.assertIn(token, output)
        self.assertIn('truth_certified: false', output)

    def test_render_escapes_untrusted_html_and_dangerous_link(self):
        self.claims[0]['text'] = '<script>alert(1)</script>'
        self.sources[0]['url'] = 'javascript:alert(1)'
        self.save()
        self.assertTrue(callable(getattr(ledger, 'render', None)))
        output = ledger.render(self.root)
        self.assertNotIn('<script>', output)
        self.assertNotIn('](javascript:', output)

    def test_text_evidence_ignores_unused_null_visual_metadata(self):
        self.evidence[0]['visual_review'] = None
        self.save()
        self.assertIn('Study A reports 90%.', ledger.render(self.root))

    def test_unreviewed_visual_can_be_rendered_as_pending(self):
        self.evidence[0].update(kind='visual', visual_review={})
        self.save()
        self.assertIn('not reviewed', ledger.render(self.root))

    def test_analysis_and_render_do_not_change_research(self):
        self.review(judgment='narrowed')
        before = {p.relative_to(self.root): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.root.rglob('*') if p.is_file()}
        ledger.stress(self.root)
        ledger.render(self.root)
        after = {p.relative_to(self.root): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_cli_pending_analysis_and_report_exit_two(self):
        for command in ('stress', 'render'):
            run = subprocess.run([sys.executable, str(SCRIPT), command, '--root', str(self.root)],
                                 capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 2)
            self.assertTrue(run.stdout.strip())
            self.assertNotIn('Traceback', run.stderr)

    def test_cli_refuses_report_for_broken_evidence(self):
        self.evidence[0]['quote'] = 'Invented'
        self.save()
        run = subprocess.run([sys.executable, str(SCRIPT), 'render', '--root', str(self.root)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 1)
        self.assertNotIn('# Research', run.stdout)

    def test_cli_report_is_utf8_even_with_legacy_console_encoding(self):
        self.claims[0]['text'] = '문헌 검토 결과'
        self.save()
        run = subprocess.run([sys.executable, str(SCRIPT), 'render', '--root', str(self.root)],
                             capture_output=True, env=dict(os.environ, PYTHONIOENCODING='ascii'))
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn('문헌 검토 결과', run.stdout.decode('utf-8'))

    def test_all_scope_cannot_hide_unsearched_routes(self):
        self.meta['routes'] = ['literature', 'technical', 'general']
        self.save()
        report = ledger.check(self.root)
        self.assertEqual(report['route_coverage']['literature']['completed_queries'], 1)
        self.assertEqual(report['route_coverage']['general']['completed_queries'], 0)
        self.assertTrue(any('general' in p for p in report['pending']))
        self.assertTrue(any('technical' in p for p in report['pending']))

    def test_empty_completed_search_is_not_fabricated_source_coverage(self):
        self.meta['routes'] = ['literature', 'technical', 'general']
        for route in ('technical', 'general'):
            self.queries.append(dict(self.queries[0], query_id=route, route=route, result_source_ids=[]))
        self.save()
        report = ledger.check(self.root)
        self.assertEqual(report['route_coverage']['general']['completed_queries'], 1)
        self.assertEqual(report['route_coverage']['general']['read_sources'], 0)

    def test_bad_route_and_out_of_scope_evidence_are_detected(self):
        self.sources[0]['route'] = 'general'
        self.save()
        self.assertTrue(any('scope' in p for p in ledger.check(self.root)['pending']))
        self.queries[0]['route'] = []
        self.save()
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_explicit_null_stress_review_renders_pending_without_crash(self):
        self.claims[0]['stress_test'] = None
        self.save()
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), 'render', '--root', str(self.root)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn('stress review missing', run.stdout)
        self.assertEqual(run.stderr, '')

    def test_exemption_requires_explicit_null_origin(self):
        self.review(oid=None, judgment='not_applicable')
        del self.claims[0]['stress_test']['reviews'][0]['excluded_origin_id']
        self.save()
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), 'render', '--root', str(self.root)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 1)
        self.assertNotIn('Traceback', run.stderr)
        self.assertIn('stress exemption', run.stdout)


if __name__ == '__main__':
    unittest.main()
