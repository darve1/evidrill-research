"""Install both host layouts without losing existing work; run the installed helper."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/install_skills.py'
spec = importlib.util.spec_from_file_location('install_skills', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
FILES = sum(len(names) for names in installer.PACKAGES.values())


def legacy_bundle(test, root):
    """Write the real 0.1.1 files from git history into a skills folder."""
    listing = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'd1a97d4', 'skills'],
                             capture_output=True, text=True)
    if listing.returncode:
        test.skipTest('0.1.1 history unavailable (shallow clone or archive)')
    names = listing.stdout.split()
    for name in names:
        target = root / name[len('skills/'):]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(['git', '-C', str(ROOT), 'show', f'd1a97d4:{name}'],
                                          capture_output=True, check=True).stdout)
    return len(names)


class InstallSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / '호환성 공간'
        self.targets = installer.destinations('both', self.home)

    def test_host_locations_and_custom_single_host(self):
        self.assertEqual(self.targets, {'codex': self.home / '.agents/skills', 'claude': self.home / '.claude/skills'})
        legacy = self.home / '.codex/skills'
        self.assertEqual(installer.destinations('codex', self.home, legacy), {'codex': legacy})
        with self.assertRaises(ValueError):
            installer.destinations('both', self.home, legacy)

    def test_both_hosts_are_complete_idempotent_and_preserve_unrelated_files(self):
        self.assertEqual(installer.install(self.targets)['files_copied'], 2 * FILES)
        for root in self.targets.values():
            skill = root / 'evidrill/SKILL.md'
            content = skill.read_text(encoding='utf-8')
            self.assertIn('name: evidrill\n', content)
            for link in re.findall(r'\[[^\]]*\]\(([^)#]+)\)', content):
                self.assertTrue((skill.parent / link).is_file(), link)
            (root / 'evidrill/personal-notes.txt').write_text('keep', encoding='utf-8')
            (root / 'other-skill').mkdir()
            (root / 'other-skill/SKILL.md').write_text('unrelated', encoding='utf-8')
        self.assertEqual(installer.install(self.targets)['files_copied'], 0)
        for root in self.targets.values():
            self.assertEqual((root / 'evidrill/personal-notes.txt').read_text(), 'keep')
            self.assertEqual((root / 'other-skill/SKILL.md').read_text(), 'unrelated')

    def test_dry_run_makes_no_directories(self):
        result = installer.install(self.targets, dry_run=True)
        self.assertEqual((result['files_to_copy'], result['files_copied']), (2 * FILES, 0))
        self.assertFalse(self.home.exists())

    def test_conflict_in_second_host_prevents_writes_to_first(self):
        changed = self.targets['claude'] / 'evidrill/references/routes.md'
        changed.parent.mkdir(parents=True)
        changed.write_text('my customization', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Existing file differs'):
            installer.install(self.targets)
        self.assertFalse(self.targets['codex'].exists())
        self.assertEqual(changed.read_text(), 'my customization')

    def test_missing_source_prevents_partial_bundle(self):
        source = Path(self.temp.name) / 'incomplete-source'
        shutil.copytree(installer.SOURCE, source)
        (source / 'evidrill/references/routes.md').unlink()
        with self.assertRaises(FileNotFoundError):
            installer.install(self.targets, source=source)
        self.assertFalse(self.home.exists())

    def test_directory_collisions_are_detected_before_any_copy(self):
        blocking = self.targets['claude'] / 'evidrill/agents'
        blocking.parent.mkdir(parents=True)
        blocking.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Expected a directory'):
            installer.install(self.targets)
        self.assertFalse(self.targets['codex'].exists())
        shutil.rmtree(self.targets['claude'])
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / '.claude').rmdir() if (self.home / '.claude').is_dir() else None
        (self.home / '.claude').write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Expected a directory'):
            installer.install(self.targets)
        self.assertFalse(self.targets['codex'].exists())

    def test_linked_package_does_not_write_outside_target(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        root = self.targets['claude']
        root.mkdir(parents=True)
        try:
            (root / 'evidrill').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Symlinks unavailable: {error}')
        with self.assertRaisesRegex(ValueError, 'Linked skill path'):
            installer.install(self.targets)
        self.assertEqual(list(outside.iterdir()), [])

    def test_legacy_folders_warn_and_only_unmodified_files_are_removed(self):
        root = self.targets['claude']
        count = legacy_bundle(self, root)
        modified = root / 'deep-research/references/records.md'
        modified.write_text('my notes', encoding='utf-8')
        warned = installer.install({'claude': root})
        self.assertIn('warning', warned['legacy']['claude'])
        self.assertTrue((root / 'deep-research-tech/SKILL.md').exists())
        cleaned = installer.install({'claude': root}, remove_old=True)['legacy']['claude']
        self.assertEqual(len(cleaned['legacy_removed']), count - 1)
        self.assertEqual(cleaned['legacy_kept_modified_or_unknown'], ['deep-research/references/records.md'])
        self.assertEqual(modified.read_text(), 'my notes')
        self.assertFalse((root / 'deep-research-tech').exists())
        self.assertTrue((root / 'evidrill/SKILL.md').exists())

    def test_legacy_dry_run_removes_nothing(self):
        root = self.targets['codex']
        legacy_bundle(self, root)
        before = sorted(p for p in root.rglob('*') if p.is_file())
        result = installer.install({'codex': root}, dry_run=True, remove_old=True)
        self.assertTrue(result['legacy']['codex']['legacy_removed'])
        self.assertEqual(before, sorted(p for p in root.rglob('*') if p.is_file()))

    def test_cli_from_other_directory_and_clean_conflict_message(self):
        root = self.targets['claude']
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--target', 'claude', '--skills-dir', str(root)],
                             cwd=self.temp.name, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['files_copied'], FILES)
        (root / 'evidrill/SKILL.md').write_text('changed', encoding='utf-8')
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--target', 'claude', '--skills-dir', str(root)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 1)
        self.assertIn('Installation stopped', run.stderr)
        self.assertNotIn('Traceback', run.stderr)

    def test_installed_helpers_run_every_scope(self):
        installer.install(self.targets)
        cases = [((), ['literature']), (('-tech',), ['literature', 'technical']), (('-tech-only',), ['technical']),
                 (('-community',), ['literature', 'community']), (('-community-only',), ['community']),
                 (('-tech', '-community'), ['literature', 'technical', 'community']),
                 (('-all',), ['literature', 'technical', 'general', 'community'])]
        for host, root in self.targets.items():
            helper = root / 'evidrill/scripts/research_ledger.py'
            for index, (flags, expected) in enumerate(cases):
                with self.subTest(host=host, flags=flags):
                    study = self.home / f'{host} study {index}'
                    run = subprocess.run([sys.executable, '-X', 'utf8', str(helper), 'init', '--root', str(study),
                                          '--question', '검증 질문', *flags], cwd=self.temp.name,
                                         capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(json.loads((study / 'study.json').read_text(encoding='utf-8'))['routes'], expected)


class PluginManifestTests(unittest.TestCase):
    def test_plugin_and_marketplace_agree_with_the_skill(self):
        plugin = json.loads((ROOT / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        entry = market['plugins'][0]
        self.assertEqual((plugin['name'], entry['name'], entry['source']), ('evidrill', 'evidrill', './'))
        self.assertEqual(plugin['version'], entry['version'])
        ledger = (ROOT / 'skills/evidrill/scripts/research_ledger.py').read_text(encoding='utf-8')
        self.assertIn(f"VERSION = '{plugin['version']}'", ledger)
        self.assertEqual(sorted(p.name for p in (ROOT / 'skills').iterdir() if p.is_dir()), ['evidrill'])


if __name__ == '__main__':
    unittest.main()
