"""Behavioral tests for preservation and integrity, never a truth classifier."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/deep-research/scripts/research_ledger.py'
spec = importlib.util.spec_from_file_location('research_ledger', SCRIPT)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'study'
        ledger.initialize(self.root)
        # These fixtures exercise the original metadata-free contract.
        (self.root / 'study.json').unlink(missing_ok=True)
        source = Path(self.temp.name) / 'input.txt'
        source.write_text('The release supports Linux.\nWindows is experimental.\n', encoding='utf-8')
        record = ledger.capture(self.root, source, 's1', 'text')
        self.sources = [dict(record, source_id='s1', url='fixture:s1', title='Release',
                             family_id='vendor', read_level='relevant_sections',
                             retrieved_at='2026-11-06T00:00:00Z', version='v2',
                             extraction_method='plain_text')]
        self.queries = [dict(query_id='q1', question_id='platform', query='Windows unsupported',
                             provider='fixture-local-search', searched_at='2026-11-06T00:00:00Z',
                             purpose='counterevidence', status='completed', result_source_ids=['s1'])]
        self.evidence = [dict(evidence_id='e1', source_id='s1', kind='text',
                              locator='line 2', quote='Windows is experimental.')]
        self.claims = [dict(claim_id='c1', text='The release describes Windows as experimental.',
                           kind='fact', importance='key', status='supported', evidence_ids=['e1'],
                           reviews=[dict(evidence_id='e1', judgment='supports', reviewer='fixture-reviewer',
                                         checked_at='2026-11-06T00:00:00Z', rationale='Same platform and release scope.')],
                           counter_search=dict(query_ids=['q1'], outcome='not_found',
                                               rationale='No contrary evidence in the supplied fixture.'))]
        self.save()

    def save(self):
        for name in ('sources', 'queries', 'evidence', 'claims'):
            rows = getattr(self, name)
            (self.root / f'{name}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

    def result(self):
        self.save()
        return ledger.check(self.root)

    def test_complete_records_are_ready_without_truth_certification(self):
        result = self.result()
        self.assertEqual(result['integrity'], 'pass')
        self.assertEqual(result['review_readiness'], 'ready')
        self.assertIs(result['truth_certified'], False)

    def test_empty_study_is_not_ready(self):
        self.sources = self.queries = self.evidence = self.claims = []
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_initialization_never_overwrites(self):
        before = (self.root / 'claims.jsonl').read_bytes()
        with self.assertRaises(ValueError):
            ledger.initialize(self.root)
        self.assertEqual(before, (self.root / 'claims.jsonl').read_bytes())

    def test_capture_is_content_addressed_and_preserves_old_versions(self):
        source = Path(self.temp.name) / 'new.txt'
        source.write_text('Old', encoding='utf-8')
        a = ledger.capture(self.root, source, 's2', 'text')
        source.write_text('New', encoding='utf-8')
        b = ledger.capture(self.root, source, 's2', 'text')
        self.assertNotEqual(a['snapshot_path'], b['snapshot_path'])
        self.assertEqual((self.root / a['snapshot_path']).read_text(), 'Old')

    def test_path_traversal_source_id_rejected(self):
        with self.assertRaises(ValueError):
            ledger.capture(self.root, Path(self.temp.name) / 'input.txt', '../escape', 'text')

    def test_snapshot_tampering_fails(self):
        (self.root / self.sources[0]['snapshot_path']).write_text('Altered', encoding='utf-8')
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_external_snapshot_path_fails(self):
        self.sources[0]['snapshot_path'] = '../input.txt'
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_fabricated_quote_fails(self):
        self.evidence[0]['quote'] = 'Windows is stable.'
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_exact_quotes_keep_negation(self):
        self.evidence[0]['quote'] = 'Windows is not experimental.'
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_real_quote_without_semantic_review_is_not_ready(self):
        self.claims[0]['text'] = 'Volcanoes emit lava.'
        self.claims[0]['reviews'] = []
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_unresolved_review_is_not_ready(self):
        self.claims[0]['reviews'][0]['judgment'] = 'unresolved'
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_partial_review_is_not_promoted(self):
        self.claims[0]['reviews'][0]['judgment'] = 'partial'
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_missing_counter_search_is_not_ready(self):
        del self.claims[0]['counter_search']
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_counter_query_must_have_really_completed(self):
        self.queries[0]['status'] = 'failed'
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_found_counterevidence_needs_link_and_resolution(self):
        self.claims[0]['counter_search'] = dict(query_ids=['q1'], outcome='found', rationale='Contradiction found')
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_false_supported_with_contradiction_is_not_ready(self):
        self.claims[0]['reviews'][0]['judgment'] = 'contradicts'
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_duplicate_source_ids_fail(self):
        self.sources.append(copy.deepcopy(self.sources[0]))
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_dangling_evidence_reference_fails(self):
        self.claims[0]['evidence_ids'].append('missing')
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_snippet_cannot_support_a_reviewed_claim(self):
        self.sources[0]['read_level'] = 'snippet'
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_copied_reports_remain_one_family(self):
        self.sources.append(dict(self.sources[0], source_id='s2', url='fixture:copy'))
        self.assertEqual(self.result()['metrics']['source_families'], 1)

    def test_missing_file_fails_instead_of_becoming_empty(self):
        (self.root / 'evidence.jsonl').unlink()
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_malformed_json_is_an_actionable_error(self):
        (self.root / 'claims.jsonl').write_text('{bad', encoding='utf-8')
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_non_object_row_is_an_actionable_error(self):
        (self.root / 'claims.jsonl').write_text('[]\n', encoding='utf-8')
        self.assertEqual(ledger.check(self.root)['integrity'], 'fail')

    def test_visual_evidence_needs_an_explicit_observation(self):
        self.evidence[0] = dict(evidence_id='e1', source_id='s1', kind='visual', locator='figure 1')
        self.assertEqual(self.result()['review_readiness'], 'needs_review')

    def test_wrong_field_types_are_errors_not_crashes(self):
        for table, key in [('sources', 'read_level'), ('queries', 'purpose'),
                           ('claims', 'kind'), ('claims', 'status'), ('claims', 'importance'),
                           ('evidence', 'source_id')]:
            with self.subTest(table=table, key=key):
                row = getattr(self, table)[0]
                old = row[key]
                row[key] = []
                try:
                    self.assertEqual(self.result()['integrity'], 'fail')
                finally:
                    row[key] = old

    def test_wrong_review_judgment_type_is_error(self):
        self.claims[0]['reviews'][0]['judgment'] = []
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_factual_claim_cannot_be_labeled_as_proposal(self):
        self.claims[0]['status'] = 'proposed'
        self.assertEqual(self.result()['integrity'], 'fail')

    def test_unused_unavailable_candidate_does_not_block_reviewed_claims(self):
        self.sources.append(dict(source_id='candidate', url='fixture:unavailable', title='Candidate',
                                 family_id='unknown', read_level='unavailable',
                                 retrieved_at='2026-11-06T00:00:00Z', extraction_method='search_snippet'))
        self.assertEqual(self.result()['review_readiness'], 'ready')

    def test_cli_exit_codes_distinguish_review_from_integrity(self):
        def run():
            return subprocess.run([sys.executable, str(SCRIPT), 'check', '--root', str(self.root)],
                                  capture_output=True, text=True)
        self.assertEqual(run().returncode, 0)
        self.claims[0]['reviews'] = []
        self.save()
        pending = run()
        self.assertEqual(pending.returncode, 2)
        self.assertIs(json.loads(pending.stdout)['truth_certified'], False)
        self.evidence[0]['quote'] = 'Fabricated quotation'
        self.save()
        self.assertEqual(run().returncode, 1)


if __name__ == '__main__':
    unittest.main()
