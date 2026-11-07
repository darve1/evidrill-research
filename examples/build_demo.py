"""Build the synthetic demo study with the helper's own commands; never a real research result.

    python -X utf8 examples/build_demo.py --root examples/demo
"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ledger', ROOT / 'skills/evidrill/scripts/research_ledger.py')
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
ledger.now = lambda: '2026-11-07T00:00:00Z'  # fixed timestamps keep the demo reproducible
CORPUS = ROOT / 'examples/fixtures/research-corpus'
REVIEWER = 'authored fixture (not an independent reviewer)'


def build(root):
    root = Path(root)
    ledger.initialize(root, question='Does the fictional Lumen method outperform Baseline?')
    (root / 'brief.md').write_text(
        '# Brief\n\nKey claims: (1) the Small-X result, (2) general superiority.\n'
        'Cut-off: the supplied fictional corpus. Exclusions: anything outside examples/fixtures/research-corpus.\n',
        encoding='utf-8', newline='\n')
    for sid, name, title in (('s1', 'paper-a-journal.txt', 'LX-01 journal article'),
                             ('s2', 'paper-b-conference.txt', 'LY-02 conference paper'),
                             ('s3', 'paper-a-preprint.txt', 'LX-01 preprint')):
        snap = ledger.capture(root, CORPUS / name, sid, 'text', 'user_supplied')
        ledger.register_source(root, snap, source_id=sid, title=title, route='literature', read_level='full_text',
                               url='fixture:' + name, family_id=sid, extra={'version': 'fixture-v1'})
    query = dict(question_id='main', provider='authored fixture selection (not a live search)',
                 status='completed', route='literature')
    ledger.add_rows(root, 'queries', [
        dict(query, query_id='q1', query='Lumen Baseline comparison', purpose='discovery',
             result_source_ids=['s1', 's2', 's3']),
        dict(query, query_id='q2', query='Lumen correction erratum', purpose='counterevidence',
             result_source_ids=['s1']),
        dict(query, query_id='q3', query='Lumen Baseline other benchmark', purpose='counterevidence',
             result_source_ids=['s2'])])
    ledger.add_origin(root, dict(origin_id='lx01', kind='study', label='LX-01 Small-X experiment',
                                 source_ids=['s1', 's3'], rationale='Preprint and journal article share study ID LX-01.',
                                 reviewer=REVIEWER, design='benchmark', n=20))
    ledger.add_origin(root, dict(origin_id='ly02', kind='study', label='LY-02 Large-Y experiment', source_ids=['s2'],
                                 rationale='Separate study ID, team and benchmark.', reviewer=REVIEWER,
                                 design='benchmark', n=100))
    ledger.add_rows(root, 'evidence', [
        dict(evidence_id='e1', source_id='s1', origin_id='lx01', kind='text', locator='line 4',
             quote='Lumen succeeded on 18/20 items, which is 90%, not 95%.'),
        dict(evidence_id='e2', source_id='s1', origin_id='lx01', kind='text', locator='line 4',
             quote='Baseline succeeded on 16/20 items (80%).'),
        dict(evidence_id='e3', source_id='s2', origin_id='ly02', kind='text', locator='line 4',
             quote='Lumen succeeded on 70/100 items; Baseline succeeded on 75/100 items.')])
    ledger.add_rows(root, 'claims', [
        dict(claim_id='c1', text='On Small-X, LX-01 reports Lumen at 90% and Baseline at 80% (18/20 vs 16/20).',
             kind='fact', importance='key', status='supported', evidence_ids=['e1', 'e2'],
             scope='Fictional LX-01 Small-X experiment only.',
             next_action='Look for an independent same-condition replication.'),
        dict(claim_id='c2', text='Lumen generally outperforms Baseline.', kind='inference', importance='key',
             status='unresolved', evidence_ids=['e1', 'e3'],
             resolution='The two benchmarks disagree and differ in size and items; general superiority is not established.',
             scope='Cross-benchmark generalization.', next_action='Seek comparable independent studies.')])
    for claim, eid, judgment, why in (
            ('c1', 'e1', 'supports', 'Corrected figure for the same experiment.'),
            ('c1', 'e2', 'supports', 'Comparator figure in the same sentence group.'),
            ('c2', 'e1', 'partial', 'One 20-item benchmark cannot establish generality.'),
            ('c2', 'e3', 'contradicts', 'The larger benchmark favors Baseline.')):
        ledger.review(root, claim, eid, judgment, why, reviewer=REVIEWER)
    ledger.counter(root, 'c1', 'not_found', 'No correction beyond the visible 95% to 90% fix.', ['q2', 'q3'])
    ledger.counter(root, 'c2', 'found', 'LY-02 reverses the ranking on Large-Y.', ['q2', 'q3'], ['e3'])
    ledger.stress_review(root, 'c1', 'lx01', 'narrowed', 'Only LX-01 supports the Small-X result.',
                         'Removing the only origin leaves no support.', reviewer=REVIEWER)
    ledger.stress_review(root, 'c2', 'lx01', 'unresolved', 'Only the contrary LY-02 result remains.',
                         'Removes the only partial support.', reviewer=REVIEWER)
    ledger.stress_review(root, 'c2', 'ly02', 'unresolved', 'Only the 20-item Small-X result remains; it is partial.',
                         'Removing the contrary origin still leaves no full support.', reviewer=REVIEWER)
    (root / 'report.md').write_text(ledger.render(root), encoding='utf-8', newline='\n')
    report = ledger.check(root)
    (root / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'review_readiness': report['review_readiness'], 'pending': report['pending'],
                      'truth_certified': report['truth_certified']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, required=True)
    build(parser.parse_args().root)
