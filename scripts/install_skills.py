"""Install the Evidrill skill for Codex, Claude Code, or both (Python 3.10+).

Claude Code users can instead install the plugin:
    /plugin install evidrill --marketplace darve1/evidrill-research
"""
import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills'
PACKAGES = {'evidrill': ['SKILL.md', 'agents/openai.yaml', 'references/records.md', 'references/routes.md',
                         'references/verification.md', 'scripts/research_ledger.py']}
LEGACY_MANIFEST = Path(__file__).resolve().parent / 'legacy_manifest.json'
LEGACY_PACKAGES = ('deep-research', 'deep-research-all', 'deep-research-comu', 'deep-research-comu-only',
                   'deep-research-tech', 'deep-research-tech-only')


def destinations(target: str, home: Path, skills_dir: Path | None = None) -> dict[str, Path]:
    if skills_dir is not None:
        if target == 'both':
            raise ValueError('--skills-dir requires --target codex or --target claude')
        return {target: skills_dir.expanduser().resolve()}
    defaults = {'codex': home / '.agents/skills', 'claude': home / '.claude/skills'}
    return {name: path.resolve() for name, path in defaults.items() if target == 'both' or target == name}


def _linked(path: Path) -> bool:
    return path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0)
                                 & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))


def legacy_files(root: Path) -> list[Path]:
    return sorted(p for package in LEGACY_PACKAGES if (root / package).is_dir()
                  for p in (root / package).rglob('*') if p.is_file())


def remove_legacy(root: Path, *, dry_run: bool = False) -> dict:
    """Remove only 0.1.x files whose SHA-256 matches a released version; keep everything else."""
    known = json.loads(LEGACY_MANIFEST.read_text(encoding='utf-8'))['files']
    removed, kept = [], []
    for path in legacy_files(root):
        if any(_linked(parent) for parent in (path, *path.parents) if parent.is_relative_to(root)):
            kept.append(str(path))
            continue
        relative = path.relative_to(root).as_posix()
        if hashlib.sha256(path.read_bytes()).hexdigest() in known.get(relative, []):
            removed.append(relative)
            if not dry_run:
                path.unlink()
        else:
            kept.append(relative)
    if not dry_run:
        for package in LEGACY_PACKAGES:
            directory = root / package
            for folder in sorted((d for d in directory.rglob('*') if d.is_dir()), reverse=True) if directory.is_dir() else []:
                if not any(folder.iterdir()):
                    folder.rmdir()
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
    return {'legacy_removed': removed, 'legacy_kept_modified_or_unknown': kept}


def install(targets: dict[str, Path], *, source: Path = SOURCE, dry_run: bool = False,
            remove_old: bool = False) -> dict:
    # Read the complete allowlisted bundle before writing any destination.
    payloads = {Path(package) / name: (source / package / name).read_bytes()
                for package, names in PACKAGES.items() for name in names}
    pending, checked = {}, {}
    for root in targets.values():
        root = root.expanduser().resolve()
        for directory in (root, *root.parents):
            if directory.exists() and not directory.is_dir():
                raise ValueError(f'Expected a directory: {directory}')
        for relative, data in payloads.items():
            path = root / relative
            current = root
            for part in relative.parts:
                current = current / part
                if _linked(current):
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
            with path.open('xb') as output:  # exclusive creation never overwrites a concurrent writer
                output.write(data)
        for path, data in checked.items():
            if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(data).digest():
                raise ValueError(f'Installed hash differs: {path}')
    result = {'targets': {name: str(path.expanduser().resolve()) for name, path in targets.items()},
              'packages_per_target': len(PACKAGES), 'files_checked': len(checked),
              'files_to_copy': len(pending), 'files_copied': 0 if dry_run else len(pending), 'dry_run': dry_run}
    legacy = {}
    for name, root in targets.items():
        if remove_old:
            legacy[name] = remove_legacy(root.expanduser().resolve(), dry_run=dry_run)
        elif legacy_files(root.expanduser().resolve()):
            legacy[name] = {'warning': 'Evidrill 0.1.x deep-research folders found; they shadow Claude Code\'s '
                                       'built-in deep-research skill. Rerun with --remove-legacy.'}
    if legacy:
        result['legacy'] = legacy
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--target', required=True, choices=('codex', 'claude', 'both'))
    parser.add_argument('--skills-dir', type=Path,
                        help='Override one host directory (e.g. an existing ~/.codex/skills install).')
    parser.add_argument('--dry-run', action='store_true', help='Check the full plan without writing files.')
    parser.add_argument('--remove-legacy', action='store_true',
                        help='Also remove unmodified 0.1.x deep-research* files (hash-matched only).')
    args = parser.parse_args()
    try:
        result = install(destinations(args.target, Path.home(), args.skills_dir), dry_run=args.dry_run,
                         remove_old=args.remove_legacy)
    except (OSError, ValueError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
