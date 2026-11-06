"""Install the shared skill bundle for Codex, Claude Code, or both (Python 3.10+)."""
import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'skills'
PACKAGES = {
    'deep-research': ['SKILL.md', 'agents/openai.yaml', 'references/records.md',
                      'references/verification.md', 'references/provenance.md',
                      'scripts/research_ledger.py', 'references/literature.md',
                      'references/technical.md', 'references/general.md', 'references/community.md'],
    **{f'deep-research-{suffix}': ['SKILL.md', 'agents/openai.yaml']
       for suffix in ('tech', 'all', 'tech-only', 'comu', 'comu-only')},
}


def destinations(target: str, home: Path, skills_dir: Path | None = None) -> dict[str, Path]:
    if skills_dir is not None:
        if target == 'both':
            raise ValueError('--skills-dir requires --target codex or --target claude')
        return {target: skills_dir.expanduser().resolve()}
    defaults = {'codex': home / '.agents/skills', 'claude': home / '.claude/skills'}
    return {name: path.resolve() for name, path in defaults.items()
            if target == 'both' or target == name}


def install(targets: dict[str, Path], *, source: Path = SOURCE, dry_run: bool = False) -> dict:
    # Read the complete allowlisted bundle before writing any destination.
    payloads = {Path(package) / name: (source / package / name).read_bytes()
                for package, names in PACKAGES.items() for name in names}
    pending = {}
    checked = {}
    for root in targets.values():
        root = root.expanduser().resolve()
        for directory in (root, *root.parents):
            if directory.exists() and not directory.is_dir():
                raise ValueError(f'Expected a directory: {directory}')
        for relative, data in payloads.items():
            path = root / relative
            # A linked package or nested directory must not redirect this install.
            current = root
            for part in relative.parts:
                current = current / part
                if current.is_symlink() or (current.exists() and
                        getattr(current.lstat(), 'st_file_attributes', 0)
                        & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)):
                    raise ValueError(f'Linked skill path requires manual installation: {current}')
                if current != path and current.exists() and not current.is_dir():
                    raise ValueError(f'Expected a directory: {current}')
            if path.exists():
                if not path.is_file() or path.read_bytes() != data:
                    raise ValueError(f'Existing file differs; compare and back it up outside the '
                                     f'skills directory before reinstalling: {path}')
            else:
                pending[path] = data
            checked[path] = data
    if not dry_run:
        for path, data in pending.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also prevents a concurrent writer from being overwritten.
            with path.open('xb') as output:
                output.write(data)
        for path, data in checked.items():
            if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(data).digest():
                raise ValueError(f'Installed hash differs: {path}')
    return {'targets': {name: str(path.expanduser().resolve()) for name, path in targets.items()},
            'packages_per_target': len(PACKAGES), 'files_checked': len(checked),
            'files_to_copy': len(pending), 'files_copied': 0 if dry_run else len(pending),
            'dry_run': dry_run}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=('codex', 'claude', 'both'))
    parser.add_argument('--skills-dir', type=Path,
                        help='Override one host directory (e.g. an existing ~/.codex/skills install).')
    parser.add_argument('--dry-run', action='store_true', help='Check the full plan without writing files.')
    args = parser.parse_args()
    try:
        result = install(destinations(args.target, Path.home(), args.skills_dir), dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
