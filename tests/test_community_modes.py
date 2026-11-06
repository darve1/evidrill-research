"""Additive and exclusive routes, plus compatibility with existing study scopes."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_v2 as v2


class CommunityModeTests(unittest.TestCase):
    def init(self, *flags):
        return v2.ScopeTests.run_init(self, *flags)

    def case(self):
        case = v2.StressTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def test_tech_only(self):
        meta = self.init('-tech-only')
        self.assertEqual((meta['mode'], meta['routes']), ('technical', ['technical']))

    def test_community_adds_to_academic_default(self):
        meta = self.init('-comu')
        self.assertEqual((meta['mode'], meta['routes']), ('literature', ['literature', 'community']))

    def test_community_only(self):
        meta = self.init('-comu-only')
        self.assertEqual((meta['mode'], meta['routes']), ('community', ['community']))

    def test_community_explicit_mode(self):
        self.assertEqual(self.init('--mode', 'community')['routes'], ['community'])

    def test_additive_tech_and_community_combine_without_general(self):
        self.assertEqual(self.init('-tech', '-comu')['routes'], ['literature', 'technical', 'community'])

    def test_all_dominates_both_additive_flags(self):
        self.assertEqual(self.init('-tech', '-comu', '-all')['routes'],
                         ['literature', 'technical', 'general', 'community'])

    def test_exclusive_conflicts_fail_before_creating_study(self):
        conflicts = [('-tech-only','-comu-only'), ('-tech-only','-all'), ('-comu-only','-all'),
                     ('-tech-only','-comu'), ('-comu-only','-tech'), ('-tech-only','-tech'),
                     ('-comu-only','-comu'), ('--mode','general','-comu'),
                     ('--mode','technical','-tech-only')]
        with tempfile.TemporaryDirectory() as temp:
            for index, flags in enumerate(conflicts):
                with self.subTest(flags=flags):
                    root = Path(temp) / str(index)
                    run = subprocess.run([sys.executable, '-X', 'utf8', str(v2.SCRIPT), 'init',
                                          '--root', str(root), *flags], capture_output=True, text=True, encoding='utf-8')
                    self.assertNotEqual(run.returncode, 0)
                    self.assertFalse(root.exists())
                    self.assertNotIn('Traceback', run.stderr)

    def test_existing_three_route_study_remains_valid(self):
        case = self.case()
        case.meta['routes'] = ['literature', 'technical', 'general']
        case.save()
        report = v2.ledger.check(case.root)
        self.assertEqual(report['integrity'], 'pass')
        self.assertNotIn('community', report['route_coverage'])

    def test_community_records_work_through_check_stress_render(self):
        case = self.case()
        case.meta.update(mode='community', routes=['community'])
        case.sources[0]['route'] = case.queries[0]['route'] = 'community'
        case.meta['origins'][0]['kind'] = 'community_report'
        case.review(judgment='narrowed')
        report = v2.ledger.check(case.root)
        self.assertEqual(report['integrity'], 'pass', report)
        self.assertEqual(report['review_readiness'], 'ready', report)
        self.assertEqual(report['route_coverage']['community']['completed_queries'], 1)
        self.assertEqual(v2.ledger.stress(case.root)['claims'][0]['structure'], 'single_origin')
        self.assertIn('Routes: community', v2.ledger.render(case.root))
        self.assertFalse(report['truth_certified'])

    def test_new_all_scope_exposes_missing_community_search(self):
        case = self.case()
        case.meta['routes'] = ['literature', 'technical', 'general', 'community']
        case.save()
        report = v2.ledger.check(case.root)
        self.assertEqual(report['integrity'], 'pass', report)
        self.assertEqual(report['route_coverage']['community']['completed_queries'], 0)
        self.assertTrue(any('community' in p for p in report['pending']))

    def test_additive_community_metadata_is_valid(self):
        for routes in (['literature', 'community'], ['literature', 'technical', 'community']):
            with self.subTest(routes=routes):
                case = self.case()
                case.meta['routes'] = routes
                case.save()
                self.assertEqual(v2.ledger.check(case.root)['integrity'], 'pass')

    def test_unknown_duplicate_or_misordered_routes_fail(self):
        for routes in (['literature','comu'], ['community','literature'],
                       ['literature','community','community'], ['literature',[]]):
            with self.subTest(routes=routes):
                case = self.case()
                case.meta['routes'] = routes
                case.save()
                self.assertEqual(v2.ledger.check(case.root)['integrity'], 'fail')


if __name__ == '__main__':
    unittest.main()
