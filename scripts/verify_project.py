"""Verify the standalone project without depending on the old workspace."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/deep-research'
EVIDENCE = ROOT / 'research/deep-research-skill-2026-11-06'
FILES = ['SKILL.md', 'agents/openai.yaml', 'references/records.md',
         'references/verification.md', 'references/provenance.md', 'scripts/research_ledger.py',
         'references/literature.md', 'references/technical.md', 'references/general.md', 'references/community.md']
PACKAGES = {'deep-research': FILES,
            'deep-research-tech': ['SKILL.md', 'agents/openai.yaml'],
            'deep-research-all': ['SKILL.md', 'agents/openai.yaml'],
            'deep-research-tech-only': ['SKILL.md', 'agents/openai.yaml'],
            'deep-research-comu': ['SKILL.md', 'agents/openai.yaml'],
            'deep-research-comu-only': ['SKILL.md', 'agents/openai.yaml']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-skill', type=Path)
    parser.add_argument('--include-private-evidence', action='store_true',
                        help='Also check locally preserved historical cases (not included in the public repository).')
    args = parser.parse_args()
    errors = []
    hashes = []
    for package, names in PACKAGES.items():
        for name in names:
            path = ROOT / 'skills' / package / name
            label = f'{package}/{name}'
            if not path.is_file():
                errors.append(f'Missing skill file: {label}')
                continue
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.append({'path': label, 'sha256': sha})
            if args.installed_skill:
                installed = args.installed_skill.parent / package / name
                if not installed.is_file() or hashlib.sha256(installed.read_bytes()).hexdigest() != sha:
                    errors.append(f'Installed skill differs: {label}')

    local_links = 0
    for path in [ROOT / 'README.md', ROOT / 'README.ko.md', ROOT / 'CONTRIBUTING.md',
                 ROOT / 'docs/PUBLICATION.md', ROOT / 'docs/COMMUNITY_MODES.md',
                 *(ROOT / 'skills').rglob('*.md'), *(ROOT / 'examples').rglob('*.md')]:
        if not path.exists():
            errors.append(f'Missing documentation: {path.name}')
            continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            if target.startswith(('http://', 'https://', '#')):
                continue
            local_links += 1
            if not (path.parent / target.split('#')[0]).exists():
                errors.append(f'Broken link: {path.relative_to(ROOT)} -> {target}')

    cases = []
    for name in ('abcde' if args.include_private_evidence else ''):
        study = EVIDENCE / 'guided' / name
        run = subprocess.run([sys.executable, '-X', 'utf8', str(SKILL / 'scripts/research_ledger.py'),
                              'check', '--root', str(study)], capture_output=True, text=True, encoding='utf-8')
        try:
            report = json.loads(run.stdout)
        except ValueError:
            errors.append(f'Case {name} did not produce JSON: {run.stderr}')
            continue
        cases.append({'case': name, 'exit_code': run.returncode, 'integrity': report.get('integrity'),
                      'truth_certified': report.get('truth_certified'), 'pending': report.get('pending')})
        if run.returncode != 2 or report.get('integrity') != 'pass' or report.get('truth_certified') is not False:
            errors.append(f'Case {name} changed integrity or unresolved-evidence behavior')

    demo_run = subprocess.run([sys.executable, '-X', 'utf8', str(SKILL / 'scripts/research_ledger.py'),
                               'stress', '--root', str(ROOT / 'examples/demo')],
                              capture_output=True, text=True, encoding='utf-8')
    try:
        demo_report = json.loads(demo_run.stdout)
        if demo_run.returncode != 2 or demo_report.get('integrity') != 'pass' or demo_report.get('truth_certified') is not False:
            errors.append('Synthetic demo lost its valid unresolved state')
        demo_result = {'exit_code': demo_run.returncode, 'integrity': demo_report.get('integrity'),
                       'truth_certified': demo_report.get('truth_certified'), 'claims': len(demo_report.get('claims', []))}
    except ValueError:
        demo_result = {'exit_code': demo_run.returncode}
        errors.append('Synthetic demo did not produce JSON')

    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'project_root': str(ROOT),
              'installed_skill_checked': str(args.installed_skill) if args.installed_skill else None,
              'skill_files': hashes, 'local_links_checked': local_links,
              'private_evidence_requested': args.include_private_evidence,
              'cases': cases, 'synthetic_demo': demo_result, 'errors': errors,
              'limits': 'File integrity and recorded review state only; not an independent semantic truth evaluation.'}
    output = ROOT / 'verification/project-verification.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'skill_files': len(hashes), 'cases': len(cases), 'errors': errors}))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
