"""Verify the repository: skill files, plugin manifests, documentation links and the synthetic demo."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from install_skills import PACKAGES

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/evidrill'
HELPER = SKILL / 'scripts/research_ledger.py'
EVIDENCE = ROOT / 'research/deep-research-skill-2026-11-06/guided'
LEGACY_REF = 'd1a97d4'  # 0.1.1, whose schema-2 helper checks the preserved historical cases
DOCS = ['README.md', 'README.ko.md', 'CONTRIBUTING.md', 'CHANGELOG.md', 'docs/PUBLICATION.md',
        'docs/COMPATIBILITY.md', 'docs/PROVENANCE.md', 'evals/README.md', 'evals/results.md']


def run_helper(helper, *args):
    run = subprocess.run([sys.executable, '-X', 'utf8', str(helper), *map(str, args)],
                         capture_output=True, text=True, encoding='utf-8')
    try:
        return run.returncode, json.loads(run.stdout)
    except ValueError:
        return run.returncode, {'stderr': run.stderr.strip()[-400:]}


def private_cases(errors):
    if not EVIDENCE.is_dir():
        errors.append(f'Private evidence requested but missing: {EVIDENCE.relative_to(ROOT)}')
        return []
    old = subprocess.run(['git', '-C', str(ROOT), 'show', f'{LEGACY_REF}:skills/deep-research/scripts/research_ledger.py'],
                         capture_output=True)
    if old.returncode:
        errors.append(f'Cannot read the 0.1.1 helper from git ({LEGACY_REF})')
        return []
    cases = []
    with tempfile.TemporaryDirectory() as temp:
        helper = Path(temp) / 'research_ledger_0_1_1.py'
        helper.write_bytes(old.stdout)
        for study in sorted(p for p in EVIDENCE.iterdir() if (p / 'study.json').is_file()):
            code, report = run_helper(helper, 'check', '--root', study)
            cases.append({'case': study.name, 'exit_code': code, 'integrity': report.get('integrity'),
                          'truth_certified': report.get('truth_certified'), 'pending': report.get('pending')})
            if code != 2 or report.get('integrity') != 'pass' or report.get('truth_certified') is not False:
                errors.append(f'Case {study.name} changed integrity or unresolved-evidence behavior')
    if not cases:
        errors.append('No historical cases found')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-skill', type=Path, help='An installed evidrill folder to compare by SHA-256.')
    parser.add_argument('--include-private-evidence', action='store_true',
                        help='Also check locally preserved historical cases (not in the public repository).')
    args = parser.parse_args()
    installed = args.installed_skill.expanduser().resolve() if args.installed_skill else None
    errors, hashes = [], []
    for package, names in PACKAGES.items():
        for name in names:
            path = ROOT / 'skills' / package / name
            if not path.is_file():
                errors.append(f'Missing skill file: {package}/{name}')
                continue
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.append({'path': f'{package}/{name}', 'sha256': sha})
            if installed:
                copy = installed / name
                if not copy.is_file() or hashlib.sha256(copy.read_bytes()).hexdigest() != sha:
                    errors.append(f'Installed skill differs: {name}')

    version = re.search(r"^VERSION = '([^']+)'", HELPER.read_text(encoding='utf-8'), re.M).group(1)
    plugin = json.loads((ROOT / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
    market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
    if {plugin.get('version'), *(p.get('version') for p in market.get('plugins', []))} != {version}:
        errors.append(f'Version mismatch between helper ({version}) and plugin manifests')
    if f'## {version}' not in (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'):
        errors.append(f'CHANGELOG has no {version} section')

    local_links = 0
    for path in [*(ROOT / doc for doc in DOCS), *SKILL.rglob('*.md'), *(ROOT / 'examples').rglob('*.md')]:
        if not path.exists():
            errors.append(f'Missing documentation: {path.relative_to(ROOT)}')
            continue
        for target in re.findall(r'\[[^\]]*\]\(([^)\s]+)\)', path.read_text(encoding='utf-8-sig')):
            if target.startswith(('http://', 'https://', '#', 'mailto:')):
                continue
            local_links += 1
            if not (path.parent / target.split('#')[0]).exists():
                errors.append(f'Broken link: {path.relative_to(ROOT)} -> {target}')

    cases = private_cases(errors) if args.include_private_evidence else []

    code, report = run_helper(HELPER, 'check', '--root', ROOT / 'examples/demo')
    demo = {'exit_code': code, 'integrity': report.get('integrity'), 'pending': report.get('pending'),
            'truth_certified': report.get('truth_certified')}
    if code != 2 or report.get('integrity') != 'pass' or report.get('truth_certified') is not False:
        errors.append('Synthetic demo lost its valid unresolved state')
    with tempfile.TemporaryDirectory() as temp:
        rebuilt = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'examples/build_demo.py'), '--root',
                                  str(Path(temp) / 'demo')], capture_output=True, text=True, encoding='utf-8')
        same = rebuilt.returncode == 0 and all(
            (Path(temp) / 'demo' / p.relative_to(ROOT / 'examples/demo')).read_bytes() == p.read_bytes()
            for p in (ROOT / 'examples/demo').rglob('*') if p.is_file())
        if not same:
            errors.append('examples/demo differs from a fresh build_demo.py run; rebuild it')

    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'version': version,
              'installed_skill_checked': str(installed) if installed else None, 'skill_files': hashes,
              'local_links_checked': local_links, 'private_evidence_requested': args.include_private_evidence,
              'cases': cases, 'synthetic_demo': demo, 'errors': errors,
              'limits': 'File integrity and recorded review state only; not an independent semantic truth evaluation.'}
    output = ROOT / 'verification/project-verification.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'version': version, 'skill_files': len(hashes), 'links': local_links, 'cases': len(cases),
                      'errors': errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
