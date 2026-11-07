"""Record integrity and review rules. The helper never classifies truth."""
import copy
import hashlib
import json
import os
import unittest

from support import StudyFixture, cli, ledger


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.s = StudyFixture(self)

    def test_complete_records_are_ready_without_truth_certification(self):
        report = self.s.check()
        self.assertEqual((report['integrity'], report['review_readiness']), ('pass', 'ready'), report)
        self.assertIs(report['truth_certified'], False)

    def test_empty_study_is_not_ready(self):
        self.s.sources = self.s.queries = self.s.evidence = self.s.claims = []
        self.s.meta['origins'] = []
        self.assertEqual(self.s.check()['review_readiness'], 'needs_review')

    def test_initialization_never_overwrites(self):
        before = (self.s.root / 'claims.jsonl').read_bytes()
        with self.assertRaises(ValueError):
            ledger.initialize(self.s.root)
        self.assertEqual(before, (self.s.root / 'claims.jsonl').read_bytes())

    def test_missing_study_json_is_an_error_not_legacy(self):
        (self.s.root / 'study.json').unlink()
        report = ledger.check(self.s.root)
        self.assertEqual(report['integrity'], 'fail')
        self.assertTrue(any('study.json' in e for e in report['errors']))

    def test_old_or_malformed_metadata_fails(self):
        good = copy.deepcopy(self.s.meta)
        for meta in ([], {}, dict(good, schema_version=2), dict(good, schema_version=True), dict(good, mode=[]),
                     dict(good, routes=['general']), dict(good, routes=['literature', 'technical', 'general']),
                     dict(good, origins=[[]])):
            with self.subTest(meta=meta):
                self.s.meta = meta
                self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_snapshot_tampering_and_escape_fail(self):
        (self.s.root / self.s.sources[0]['snapshot_path']).write_text('Altered', encoding='utf-8')
        self.assertEqual(ledger.check(self.s.root)['integrity'], 'fail')
        self.s.sources[0]['snapshot_path'] = '../release.txt'
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_fabricated_quote_and_dropped_negation_fail(self):
        for quote in ('Windows support is stable in this version.', 'Windows support is not experimental.'):
            with self.subTest(quote=quote):
                self.s.evidence[0]['quote'] = quote
                self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_capture_field_is_required(self):
        del self.s.sources[0]['capture']
        self.assertEqual(self.s.check()['integrity'], 'fail')
        self.s.sources[0]['capture'] = 'helper_fetched'
        self.assertEqual(self.s.check()['integrity'], 'fail', 'helper_fetched needs fetch metadata')

    def test_duplicate_and_invalid_ids_fail(self):
        self.s.sources.append(copy.deepcopy(self.s.sources[0]))
        self.assertEqual(self.s.check()['integrity'], 'fail')
        self.s.sources.pop()
        self.s.queries[0]['query_id'] = 'has space'
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_dangling_references_fail(self):
        self.s.claims[0]['evidence_ids'].append('missing')
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_missing_or_malformed_files_fail(self):
        (self.s.root / 'claims.jsonl').write_text('{bad', encoding='utf-8')
        self.assertEqual(ledger.check(self.s.root)['integrity'], 'fail')
        (self.s.root / 'claims.jsonl').write_text('[]\n', encoding='utf-8')
        self.assertEqual(ledger.check(self.s.root)['integrity'], 'fail')
        (self.s.root / 'evidence.jsonl').unlink()
        self.assertEqual(ledger.check(self.s.root)['integrity'], 'fail')

    def test_wrong_field_types_are_errors_not_crashes(self):
        for table, key in [('sources', 'read_level'), ('queries', 'purpose'), ('claims', 'kind'),
                           ('claims', 'status'), ('claims', 'importance'), ('evidence', 'source_id')]:
            with self.subTest(table=table, key=key):
                row = getattr(self.s, table)[0]
                old, row[key] = row[key], []
                try:
                    self.assertEqual(self.s.check()['integrity'], 'fail')
                finally:
                    row[key] = old

    def test_optional_extraction_and_screening_fields_are_type_checked(self):
        self.s.meta['origins'][0].update(design='vendor note', n=-1)
        self.assertEqual(self.s.check()['integrity'], 'fail')
        self.s.meta['origins'][0]['n'] = 3
        self.s.sources[0]['screening'] = {'decision': 'excluded'}
        self.assertEqual(self.s.check()['integrity'], 'fail', 'exclusion needs a reason')
        self.s.sources[0]['screening'] = {'decision': 'included'}
        self.s.queries[0]['result_count'] = 'many'
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_cli_exit_codes_distinguish_review_from_integrity(self):
        self.s.save()
        self.assertEqual(cli('check', '--root', self.s.root)[0], 0)
        self.s.claims[0]['reviews'] = []
        self.s.save()
        code, payload, _ = cli('check', '--root', self.s.root)
        self.assertEqual(code, 2)
        self.assertIs(payload['truth_certified'], False)
        self.s.evidence[0]['quote'] = 'Fabricated quotation that is long enough'
        self.s.save()
        self.assertEqual(cli('check', '--root', self.s.root)[0], 1)


class ReviewRuleTests(unittest.TestCase):
    def setUp(self):
        self.s = StudyFixture(self)

    def pending(self):
        report = self.s.check()
        self.assertEqual(report['integrity'], 'pass', report['errors'])
        return report['pending']

    def test_semantic_review_missing_unresolved_or_partial_is_pending(self):
        for reviews in ([], [dict(self.s.claims[0]['reviews'][0], judgment='unresolved')],
                        [dict(self.s.claims[0]['reviews'][0], judgment='partial')]):
            with self.subTest(reviews=reviews):
                self.s.claims[0]['reviews'] = reviews
                self.assertTrue(self.pending())

    def test_supported_label_with_contradiction_needs_resolution(self):
        self.s.claims[0]['reviews'][0]['judgment'] = 'contradicts'
        self.assertTrue(any('supported label' in p for p in self.pending()))

    def test_counter_search_needs_two_distinct_completed_queries(self):
        self.s.claims[0]['counter_search']['query_ids'] = ['q1']
        self.assertTrue(any('at least 2' in p for p in self.pending()))
        self.s.queries[1]['query'] = '  windows STABLE support '
        self.s.claims[0]['counter_search']['query_ids'] = ['q1', 'q2']
        self.assertTrue(any('at least 2' in p for p in self.pending()), 'same query text is not two searches')

    def test_failed_or_missing_counter_search_is_pending(self):
        self.s.queries[0]['status'] = 'failed'
        self.assertTrue(any('counter search' in p for p in self.pending()))
        self.s.queries[0]['status'] = 'completed'
        del self.s.claims[0]['counter_search']
        self.assertTrue(any('counterevidence search missing' in p for p in self.pending()))

    def test_found_counterevidence_needs_link_and_resolution(self):
        self.s.claims[0]['counter_search']['outcome'] = 'found'
        self.assertTrue(any('found counterevidence' in p for p in self.pending()))

    def test_unknown_counter_outcome_is_error(self):
        self.s.claims[0]['counter_search']['outcome'] = 'maybe'
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_snippet_and_abstract_cannot_quietly_support_key_claims(self):
        self.s.sources[0]['read_level'] = 'abstract'
        self.assertTrue(any('abstract only' in p for p in self.pending()))
        self.s.sources[0]['read_level'] = 'snippet'
        self.assertTrue(any('not read' in p for p in self.pending()))

    def test_short_quote_needs_reason(self):
        self.s.evidence[0]['quote'] = 'experimental'
        self.s.stress_review('a', 'narrowed')
        self.assertTrue(any('shorter than' in p for p in self.pending()))
        self.s.evidence[0]['short_quote_reason'] = 'Single defining word in a status table.'
        self.s.stress_review('a', 'narrowed')
        self.assertFalse(any('shorter than' in p for p in self.pending()))

    def test_agent_written_snapshot_is_flagged(self):
        self.s.sources[0]['capture'] = 'agent_written'
        self.s.stress_review('a', 'narrowed')
        self.assertTrue(any('agent-written' in p for p in self.pending()))

    def test_review_method_is_validated_and_counted(self):
        self.s.claims[0]['reviews'][0]['method'] = 'fresh_agent'
        self.s.stress_review('a', 'narrowed')
        self.assertEqual(self.s.check()['metrics']['review_methods'], {'fresh_agent': 1})
        self.s.claims[0]['reviews'][0]['method'] = 'oracle'
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_out_of_scope_route_and_unsearched_route_are_pending(self):
        self.s.sources[0]['route'] = 'general'
        self.assertTrue(any('outside selected scope' in p for p in self.pending()))
        self.s.sources[0]['route'] = 'literature'
        self.s.meta.update(routes=list(ledger.MODES))
        report = self.s.check()
        for route in ('technical', 'general', 'community'):
            self.assertTrue(any(p.startswith(route) for p in report['pending']), route)

    def test_unused_unavailable_candidate_does_not_block(self):
        self.s.sources.append(dict(source_id='cand', url='fixture:none', title='Candidate', family_id='unknown',
                                   route='literature', read_level='unavailable', retrieved_at='2026-11-06T00:00:00Z',
                                   extraction_method='search_snippet', capture='agent_written'))
        self.assertEqual(self.s.check()['review_readiness'], 'ready')

    def test_pending_items_are_deduplicated(self):
        self.s.claims[0]['stress_test']['reviews'][0]['judgment'] = 'unresolved'
        self.s.save()
        pending = ledger.check(self.s.root)['pending']
        self.assertEqual(len(pending), len(set(pending)))


class StressTests(unittest.TestCase):
    def setUp(self):
        self.s = StudyFixture(self)

    def add_second(self, origin='b', judgment='supports', source='s1', quote='Study B reports 80% on the small benchmark.'):
        self.s.evidence.append(dict(evidence_id='e2', source_id=source, origin_id=origin, kind='text',
                                    locator='line 4', quote=quote))
        self.s.claims[0]['evidence_ids'].append('e2')
        self.s.claims[0]['reviews'].append(dict(self.s.claims[0]['reviews'][0], evidence_id='e2', judgment=judgment))
        if origin not in [o['origin_id'] for o in self.s.meta['origins']]:
            self.s.meta['origins'].append(self.s.origin(origin))

    def analysis(self):
        self.s.save()
        return ledger.stress(self.s.root)['claims'][0]

    def test_single_origin_removal_loses_all_recorded_support(self):
        claim = self.analysis()
        self.assertEqual(claim['structure'], 'single_origin')
        self.assertEqual(claim['scenarios'][0]['remaining_support_ids'], [])

    def test_two_origins_in_one_source_are_not_collapsed(self):
        self.add_second()
        scenarios = {x['excluded_origin_id']: x for x in self.analysis()['scenarios']}
        self.assertEqual((scenarios['a']['remaining_support_ids'], scenarios['b']['remaining_support_ids']), (['e2'], ['e1']))

    def test_multiple_reports_of_one_origin_are_removed_together(self):
        self.s.sources.append(dict(self.s.sources[0], source_id='s2', url='fixture:reprint'))
        self.s.meta['origins'][0]['source_ids'].append('s2')
        snap = ledger.capture(self.s.root, self.s.temp / 'release.txt', 's2', 'text')
        self.s.sources[1].update(snap)
        self.add_second(origin='a', source='s2')
        claim = self.analysis()
        self.assertEqual([s['removed_evidence_ids'] for s in claim['scenarios']], [['e1', 'e2']])

    def test_partial_opposing_and_unknown_are_not_support(self):
        for judgment in ('partial', 'contradicts', 'irrelevant', 'unresolved'):
            with self.subTest(judgment=judgment):
                self.s.claims[0]['reviews'][0]['judgment'] = judgment
                self.assertEqual(self.analysis()['structure'], 'no_recorded_support')
        self.s.claims[0]['reviews'][0]['judgment'] = 'supports'
        self.s.evidence[0]['origin_id'] = 'unknown'
        del self.s.claims[0]['stress_test']
        claim = self.analysis()
        self.assertEqual((claim['structure'], claim['scenarios']), ('independence_unknown', []))

    def test_shared_dependency_is_visible(self):
        self.add_second()
        for origin in self.s.meta['origins']:
            origin['shared_dependencies'] = ['dataset W']
        self.assertEqual(self.analysis()['shared_dependencies'], {'dataset W': ['a', 'b']})

    def test_stress_review_states(self):
        self.assertEqual(self.s.check()['review_readiness'], 'ready')
        self.s.stress_review('a', 'unresolved')
        self.assertTrue(any('unresolved' in p for p in self.s.check()['pending']))
        del self.s.claims[0]['stress_test']
        self.assertTrue(any('stress review missing' in p for p in self.s.check()['pending']))

    def test_changed_claim_or_source_makes_review_stale(self):
        self.s.sources[0]['version'] = '2.1'
        self.assertTrue(any('stale' in p for p in self.s.check()['pending']))

    def test_origin_reference_rules(self):
        self.s.evidence[0]['origin_id'] = 'missing'
        self.assertEqual(self.s.check()['integrity'], 'fail')
        self.s.evidence[0]['origin_id'] = 'a'
        self.s.meta['origins'][0]['source_ids'] = []
        self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_wrong_stress_shapes_fail_without_crashing(self):
        for value in ([], {'reviews': [None]}, {'reviews': [{'excluded_origin_id': []}]}):
            self.s.claims[0]['stress_test'] = value
            self.assertEqual(self.s.check()['integrity'], 'fail')

    def test_exemption_requires_single_null_origin(self):
        self.s.claims[0]['stress_test']['reviews'][0].update(excluded_origin_id=None, judgment='not_applicable')
        self.assertEqual(self.s.check()['review_readiness'], 'ready')
        del self.s.claims[0]['stress_test']['reviews'][0]['excluded_origin_id']
        self.assertEqual(self.s.check()['integrity'], 'fail')


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.s = StudyFixture(self)

    def test_render_shows_trace_context_scope_and_methods(self):
        self.s.meta['origins'][0].update(design='vendor release note', n=1)
        self.s.stress_review('a', 'narrowed')
        output = ledger.render(self.s.root)
        for token in ('c1', 'e1', 'line 2', 'Release 2.0 notes only', 'Run the installer', 'supports, self',
                      'Context:', 'Linux as the tested platform', 'vendor release note', 'n=1', 'capture: user\\_supplied'):
            self.assertIn(token, output)
        self.assertIn('truth_certified: false', output)
        self.assertNotIn('\\{', output, 'coverage is plain text, not escaped JSON')

    def test_render_escapes_untrusted_html_and_dangerous_links(self):
        self.s.claims[0]['text'] = '<script>alert(1)</script>'
        self.s.sources[0]['url'] = 'javascript:alert(1)'
        self.s.stress_review('a', 'narrowed')
        output = ledger.render(self.s.root)
        self.assertNotIn('<script>', output)
        self.assertNotIn('](javascript:', output)

    def test_analysis_and_render_do_not_change_research(self):
        files = lambda: {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.s.root.rglob('*') if p.is_file()}
        before = files()
        ledger.stress(self.s.root)
        ledger.render(self.s.root)
        self.assertEqual(before, files())

    def test_cli_render_exit_codes_and_utf8(self):
        self.s.claims[0]['text'] = '문헌 검토 결과'
        self.s.stress_review('a', 'unresolved')
        code, output, stderr = cli('render', '--root', self.s.root, env=dict(os.environ, PYTHONIOENCODING='ascii'))
        self.assertEqual(code, 2, stderr)
        self.assertIn('문헌 검토 결과', output)
        self.s.evidence[0]['quote'] = 'Invented passage that never appears'
        self.s.save()
        code, output, _ = cli('render', '--root', self.s.root)
        self.assertEqual(code, 1)
        self.assertNotIn('# Research', json.dumps(output))


if __name__ == '__main__':
    unittest.main()
