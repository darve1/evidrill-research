"""Scope flags select routes before any folder is created."""
import json
import tempfile
import unittest
from pathlib import Path

from support import cli


class ScopeTests(unittest.TestCase):
    def init(self, *flags, expect=0):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'study'
            code, payload, stderr = cli('init', '--root', root, *flags)
            self.assertEqual(code, expect, (payload, stderr))
            if expect:
                self.assertFalse(root.exists(), 'rejected scopes must not create a study')
                return None
            return json.loads((root / 'study.json').read_text(encoding='utf-8'))

    def test_scope_combinations(self):
        cases = {(): ['literature'], ('-tech',): ['literature', 'technical'],
                 ('-community',): ['literature', 'community'],
                 ('-tech', '-community'): ['literature', 'technical', 'community'],
                 ('-all',): ['literature', 'technical', 'general', 'community'],
                 ('-tech', '-all'): ['literature', 'technical', 'general', 'community'],
                 ('-tech-only',): ['technical'], ('-community-only',): ['community'],
                 ('--mode', 'general'): ['general'], ('--mode', 'community'): ['community']}
        for flags, routes in cases.items():
            with self.subTest(flags=flags):
                meta = self.init(*flags)
                self.assertEqual((meta['schema_version'], meta['routes']), (3, routes))
                self.assertEqual(meta['mode'], routes[0] if len(routes) == 1 else 'literature')

    def test_conflicts_are_rejected(self):
        for flags in (('-tech-only', '-tech'), ('-community-only', '-all'), ('-tech-only', '-community-only'),
                      ('--mode', 'general', '-tech')):
            with self.subTest(flags=flags):
                self.init(*flags, expect=1)

    def test_old_comu_spelling_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            code, _, stderr = cli('init', '--root', Path(temp) / 'study', '-comu')
            self.assertEqual(code, 2, stderr)
            self.assertFalse((Path(temp) / 'study').exists())


if __name__ == '__main__':
    unittest.main()
