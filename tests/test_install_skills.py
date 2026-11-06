"""Install both host layouts without losing existing work; run the installed helpers."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/install_skills.py'
spec = importlib.util.spec_from_file_location('install_skills', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / '호환성 공간'
        self.targets = installer.destinations('both', self.home)

    def test_host_locations_and_custom_single_host(self):
        self.assertEqual(self.targets, {'codex': self.home / '.agents/skills',
                                       'claude': self.home / '.claude/skills'})
        legacy = self.home / '.codex/skills'
        self.assertEqual(installer.destinations('codex', self.home, legacy), {'codex': legacy})
        with self.assertRaises(ValueError):
            installer.destinations('both', self.home, legacy)

    def test_both_hosts_are_complete_idempotent_and_preserve_unrelated_files(self):
        result = installer.install(self.targets)
        self.assertEqual(result['files_copied'], 40)
        for root in self.targets.values():
            # Each alias must resolve its shared skill and helper after installation.
            for package in installer.PACKAGES:
                skill = root / package / 'SKILL.md'
                content = skill.read_text(encoding='utf-8-sig')
                self.assertIn(f'name: {package}\n', content)
                for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                    self.assertTrue((skill.parent / link).is_file(), link)
            extra = root / 'deep-research' / 'personal-notes.txt'
            extra.write_text('keep', encoding='utf-8')
            other = root / 'other-skill/SKILL.md'
            other.parent.mkdir()
            other.write_text('unrelated', encoding='utf-8')
        self.assertEqual(installer.install(self.targets)['files_copied'], 0)
        for root in self.targets.values():
            self.assertEqual((root / 'deep-research/personal-notes.txt').read_text(), 'keep')
            self.assertEqual((root / 'other-skill/SKILL.md').read_text(), 'unrelated')

    def test_dry_run_makes_no_directories(self):
        result = installer.install(self.targets, dry_run=True)
        self.assertEqual(result['files_to_copy'], 40)
        self.assertEqual(result['files_copied'], 0)
        self.assertFalse(self.home.exists())

    def test_conflict_in_second_host_prevents_writes_to_first(self):
        changed = self.targets['claude'] / 'deep-research-comu-only/SKILL.md'
        changed.parent.mkdir(parents=True)
        changed.write_text('my customization', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Existing file differs'):
            installer.install(self.targets)
        self.assertFalse(self.targets['codex'].exists())
        self.assertFalse((self.targets['claude'] / 'deep-research').exists())
        self.assertEqual(changed.read_text(), 'my customization')

    def test_missing_source_prevents_partial_bundle(self):
        source = Path(self.temp.name) / 'incomplete-source'
        shutil.copytree(installer.SOURCE, source)
        (source / 'deep-research-comu-only/SKILL.md').unlink()
        with self.assertRaises(FileNotFoundError):
            installer.install(self.targets, source=source)
        self.assertFalse(self.home.exists())

    def test_directory_collision_is_detected_before_any_copy(self):
        blocking_file = self.targets['claude'] / 'deep-research/agents'
        blocking_file.parent.mkdir(parents=True)
        blocking_file.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Expected a directory'):
            installer.install(self.targets)
        self.assertFalse(self.targets['codex'].exists())
        self.assertEqual(blocking_file.read_text(), 'keep')

    def test_linked_package_does_not_write_outside_target(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        root = self.targets['claude']
        root.mkdir(parents=True)
        try:
            (root / 'deep-research').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Symlinks unavailable: {error}')
        with self.assertRaisesRegex(ValueError, 'Linked skill path'):
            installer.install(self.targets)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.targets['codex'].exists())

    def test_blocked_host_parent_prevents_writes_to_other_host(self):
        self.home.mkdir(parents=True)
        blocking_file = self.home / '.claude'
        blocking_file.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Expected a directory'):
            installer.install(self.targets)
        self.assertFalse(self.targets['codex'].exists())
        self.assertEqual(blocking_file.read_text(), 'keep')

    def test_cli_works_from_other_working_directory(self):
        root = self.targets['claude']
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--target', 'claude',
                              '--skills-dir', str(root)], cwd=self.temp.name,
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['files_copied'], 20)
        self.assertFalse(self.targets['codex'].exists())

    def test_cli_conflict_exits_cleanly(self):
        root = self.targets['claude']
        root.mkdir(parents=True)
        (root / 'deep-research').write_text('keep', encoding='utf-8')
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--target', 'claude',
                              '--skills-dir', str(root)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 1)
        self.assertIn('Installation stopped', run.stderr)
        self.assertNotIn('Traceback', run.stderr)

    def test_all_scopes_run_from_both_installed_helpers(self):
        installer.install(self.targets)
        cases = [((), ['literature']), (('-tech',), ['literature', 'technical']),
                 (('-tech-only',), ['technical']), (('-comu',), ['literature', 'community']),
                 (('-comu-only',), ['community']),
                 (('-tech', '-comu'), ['literature', 'technical', 'community']),
                 (('-all',), ['literature', 'technical', 'general', 'community'])]
        for host, root in self.targets.items():
            helper = root / 'deep-research/scripts/research_ledger.py'
            for index, (flags, expected) in enumerate(cases):
                with self.subTest(host=host, flags=flags):
                    study = self.home / f'{host}-study-{index}'
                    run = subprocess.run([sys.executable, '-X', 'utf8', str(helper), 'init',
                                          '--root', str(study), '--question', '검증 질문', *flags],
                                         cwd=self.temp.name, capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(json.loads((study / 'study.json').read_text(encoding='utf-8'))['routes'],
                                     expected)


if __name__ == '__main__':
    unittest.main()
