"""Run one behavioral trial of a skill variant with Claude Code and record cost/behavior metrics.

Each trial runs `claude -p` in a fresh temporary workspace. The skill variant is copied into
that workspace's `.claude/skills/`, so nothing is installed into the user's own skill folders.
Raw transcripts and workspaces go under `evals/runs/` (ignored by git) because real-topic runs
contain third-party page snapshots. Only summaries are committed.

This measures behavior, not truth. Quality is graded separately by a person against
`evals/tasks/<task>.rubric.md` (fixture) or by spot-checking cited sources (real topics).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'evals/tasks'
RUNS = ROOT / 'evals/runs'
HELPER_NAMES = ('research_ledger.py', 'evidrill.py')
LEDGER_FILES = ('queries.jsonl', 'sources.jsonl', 'evidence.jsonl', 'claims.jsonl', 'study.json')


def copy_skills(variant: str, workspace: Path) -> list[str]:
    """`none`, `worktree` (current files) or a git ref such as `d1a97d4`."""
    if variant == 'none':
        return []
    target = workspace / '.claude/skills'
    target.mkdir(parents=True)
    if variant == 'worktree':
        source = ROOT / 'skills'
        for package in sorted(p for p in source.iterdir() if p.is_dir()):
            shutil.copytree(package, target / package.name, ignore=shutil.ignore_patterns('__pycache__'))
    else:
        archive = subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', variant, 'skills'],
                                 capture_output=True, check=True).stdout
        with tarfile.open(fileobj=BytesIO(archive)) as tar:
            for member in tar.getmembers():
                if not member.name.startswith('skills/') or '..' in Path(member.name).parts:
                    continue
                relative = Path(member.name).relative_to('skills')
                if member.isdir() or not relative.parts:
                    continue
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(tar.extractfile(member).read())
    return sorted(p.name for p in target.iterdir() if p.is_dir())


def summarize(transcript: Path) -> dict:
    tools, ledger_calls, ledger_exits, ledger_writes = {}, {}, [], {'calls': 0, 'chars': 0}
    pending_commands, result, init = {}, {}, {}
    written, denials, web = {'calls': 0, 'chars': 0}, 0, {'searches': 0, 'fetches': 0, 'curl': 0, 'helper_url': 0}
    for line in transcript.read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get('type')
        if kind == 'system' and event.get('subtype') == 'init':
            init = event
        elif kind == 'result':
            result = event
        message = event.get('message') if isinstance(event.get('message'), dict) else {}
        for block in message.get('content') or []:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use':
                name = block.get('name', '?')
                tools[name] = tools.get(name, 0) + 1
                data = block.get('input') or {}
                command = data.get('command', '') if isinstance(data, dict) else ''
                if any(helper in command for helper in HELPER_NAMES):
                    subs = re.findall(r'(?:research_ledger|evidrill)\.py["\']?\s+([a-z-]+)', command) or ['other']
                    for sub in subs:  # chained commands (&&) count individually
                        ledger_calls[sub] = ledger_calls.get(sub, 0) + 1
                    pending_commands[block.get('id')] = subs[-1]
                path = str(data.get('file_path', '')) if isinstance(data, dict) else ''
                if name in ('Write', 'Edit') and isinstance(data, dict):
                    written['calls'] += 1
                    written['chars'] += len(str(data.get('content') or data.get('new_string') or ''))
                web['searches'] += name == 'WebSearch'
                web['fetches'] += name == 'WebFetch'
                web['curl'] += bool(re.search(r'(^|[;&|\s])curl\s', command))
                web['helper_url'] += bool(re.search(r'snapshot\b.*--url', command))
                if name in ('Write', 'Edit') and path.endswith(LEDGER_FILES):
                    ledger_writes['calls'] += 1
                    ledger_writes['chars'] += len(json.dumps(data, ensure_ascii=False))
            elif block.get('type') == 'tool_result':
                content = block.get('content')
                text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                denied = block.get('is_error') and re.search(r'requires approval|can.t be checked|permission', text, re.I)
                denials += bool(denied)
                if block.get('tool_use_id') not in pending_commands:
                    continue
                if denied:
                    ledger_exits.append({'command': pending_commands.pop(block['tool_use_id']), 'exit': 'denied'})
                    continue
                match = re.search(r'[Ee]xit code[: ]+(\d+)', text)
                code = int(match.group(1)) if match else (1 if block.get('is_error') else 0)
                ledger_exits.append({'command': pending_commands.pop(block['tool_use_id']), 'exit': code})
    usage = result.get('usage') or {}
    return {'cost_usd': result.get('total_cost_usd'), 'duration_s': round((result.get('duration_ms') or 0) / 1000),
            'turns': result.get('num_turns'), 'stop': result.get('subtype'),
            'tokens': {k: usage.get(k) for k in ('input_tokens', 'output_tokens',
                                                  'cache_read_input_tokens', 'cache_creation_input_tokens')},
            'tool_calls': dict(sorted(tools.items())), 'tool_calls_total': sum(tools.values()),
            'ledger_commands': ledger_calls, 'ledger_exit_codes': ledger_exits,
            'ledger_hand_writes': ledger_writes, 'written_by_agent': written, 'permission_denials': denials,
            'web': web,
            'skills_listed': [s for s in (init.get('skills') or init.get('slash_commands') or [])
                              if 'research' in str(s) or 'evidrill' in str(s)],
            'answer_chars': len(result.get('result') or ''), 'answer': result.get('result') or ''}


def final_checks(workspace: Path) -> list[dict]:
    """Run the trial's own helper on each study folder it produced."""
    helpers = [p for name in HELPER_NAMES for p in (workspace / '.claude/skills').rglob(name)]
    studies = sorted({p.parent for p in workspace.rglob('claims.jsonl') if '.claude' not in p.parts})
    results = []
    for study in studies:
        if not helpers:
            results.append({'study': str(study.relative_to(workspace)), 'helper': None})
            continue
        run = subprocess.run([sys.executable, '-X', 'utf8', str(helpers[0]), 'check', '--root', str(study)],
                             capture_output=True, text=True, encoding='utf-8')
        try:
            report = json.loads(run.stdout)
        except ValueError:
            report = {}
        results.append({'study': str(study.relative_to(workspace)), 'exit': run.returncode,
                        'integrity': report.get('integrity'), 'readiness': report.get('review_readiness'),
                        'errors': len(report.get('errors') or []), 'pending': len(report.get('pending') or []),
                        'metrics': report.get('metrics')})
    return results


def resummarize(label: str) -> int:
    """Recompute transcript metrics for an existing run (keeps final checks and run settings)."""
    out = RUNS / label
    metrics = json.loads((out / 'metrics.json').read_text(encoding='utf-8'))
    fresh = summarize(out / 'transcript.jsonl')
    fresh.pop('answer')
    metrics.update(fresh)
    (out / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == '--resummarize':
        return resummarize(sys.argv[2])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, help='Task name in evals/tasks (without .json).')
    parser.add_argument('--variant', required=True, help='none, worktree, or a git ref.')
    parser.add_argument('--invoke', default='',
                        help='Skill and options without the slash, e.g. "evidrill -all" (Git Bash rewrites a leading /).')
    parser.add_argument('--label', required=True, help='Run folder name under evals/runs.')
    parser.add_argument('--model', default='sonnet')
    parser.add_argument('--max-budget-usd', type=float, default=10.0)
    args = parser.parse_args()

    task = json.loads((TASKS / f'{args.task}.json').read_text(encoding='utf-8'))
    out = RUNS / args.label
    if out.exists():
        raise SystemExit(f'Run folder exists; choose a new label: {out}')
    out.mkdir(parents=True)
    workspace = Path(tempfile.mkdtemp(prefix='evidrill-trial-'))
    skills = copy_skills(args.variant, workspace)
    for relative in task.get('materials', []):
        source = ROOT / relative
        destination = workspace / 'materials' / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    invoke = re.sub(r'^[A-Za-z]:/.*?/Git/', '', args.invoke.strip()).lstrip('/')  # undo MSYS path conversion
    args.invoke = '/' + invoke if invoke else ''
    prompt = (args.invoke + ' ' + task['prompt']).strip() if args.invoke else task['prompt']
    command = [shutil.which('claude') or 'claude', '-p', '--output-format', 'stream-json', '--verbose',
               '--model', args.model, '--max-budget-usd', str(args.max_budget_usd),
               '--permission-mode', 'acceptEdits', '--strict-mcp-config', '--setting-sources', 'project',
               '--no-session-persistence', '--allowedTools', *task['allowed_tools'],
               '--disallowedTools', *task.get('disallowed_tools', ['PowerShell'])]
    started = time.time()
    with (out / 'transcript.jsonl').open('w', encoding='utf-8') as transcript:
        run = subprocess.run(command, input=prompt, cwd=workspace, stdout=transcript,
                             stderr=subprocess.PIPE, text=True, encoding='utf-8')
    summary = summarize(out / 'transcript.jsonl')
    (out / 'answer.md').write_text(summary.pop('answer'), encoding='utf-8')
    summary.update({'task': args.task, 'variant': args.variant, 'invoke': args.invoke, 'model': args.model,
                    'skills_installed': skills, 'claude_exit': run.returncode, 'stderr_tail': run.stderr[-2000:],
                    'wall_s': round(time.time() - started), 'final_checks': final_checks(workspace),
                    'workspace': str(workspace)})
    (out / 'metrics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copytree(workspace, out / 'workspace', ignore=shutil.ignore_patterns('.claude'))
    print(json.dumps({k: summary[k] for k in ('cost_usd', 'duration_s', 'turns', 'tool_calls_total',
                                               'ledger_commands', 'final_checks')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
