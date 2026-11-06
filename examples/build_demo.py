"""Build self-authored synthetic demo records; never a real research result."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ledger', ROOT / 'skills/deep-research/scripts/research_ledger.py')
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


def build(root):
    ledger.initialize(root, question='Does fictional Lumen outperform Baseline?')
    root = Path(root)
    fixture = ROOT / 'examples/fixtures/research-corpus'
    sources = []
    for sid, filename, origin in [('s1', 'paper-a-journal.txt', 'lx01'), ('s2', 'paper-b-conference.txt', 'ly02')]:
        snap = ledger.capture(root, fixture / filename, sid, 'text')
        sources.append(dict(snap, source_id=sid, url='fixture:'+filename, title=filename,
                            family_id=origin, route='literature', retrieved_at='2026-11-06T00:00:00Z',
                            read_level='full_text', extraction_method='synthetic_fixture', version='fixture-v1'))
    query = dict(query_id='q1', question_id='superiority', query='fixture comparison: Lumen Baseline results',
                 provider='authored demo fixture selection (not a live search)', searched_at='2026-11-06T00:00:00Z',
                 purpose='counterevidence', status='completed', result_source_ids=['s1','s2'], route='literature')
    evidence = [dict(evidence_id='e1', source_id='s1', origin_id='lx01', kind='text', locator='line 4',
                     quote='Correction: Lumen succeeded on 18/20 items, which is 90%, not 95%. Baseline succeeded on 16/20 items (80%).'),
                dict(evidence_id='e2', source_id='s2', origin_id='ly02', kind='text', locator='line 4',
                     quote='Lumen succeeded on 70/100 items; Baseline succeeded on 75/100 items.')]
    def review(eid, judgment, reason):
        return dict(evidence_id=eid, judgment=judgment, reviewer='authored fixture (not independent reviewer)',
                    checked_at='2026-11-06T00:00:00Z', rationale=reason)
    claims = [dict(claim_id='c1', text='On Small-X, the journal fixture reports Lumen at 90% and Baseline at 80%.',
                   kind='fact', importance='key', status='supported', evidence_ids=['e1'],
                   reviews=[review('e1','supports','Same experiment and corrected denominator.')],
                   counter_search=dict(query_ids=['q1'], outcome='not_found', rationale='Different Large-Y results do not contradict the scoped Small-X observation.'),
                   scope='Fictional LX-01 Small-X experiment only.', next_action='Review independent same-condition replications.'),
              dict(claim_id='c2', text='Lumen generally outperforms Baseline.', kind='inference', importance='key',
                   status='unresolved', evidence_ids=['e1','e2'],
                   reviews=[review('e1','partial','One small dataset cannot establish generality.'),
                            review('e2','contradicts','The other dataset favors Baseline; conditions differ.')],
                   counter_search=dict(query_ids=['q1'], outcome='found', evidence_ids=['e2'], rationale='Counterexample in the supplied fictional materials.'),
                   resolution='General superiority remains unresolved; compare populations and methods.',
                   scope='Fictional cross-dataset generalization.', next_action='Seek comparable independent studies.')]
    metadata = json.loads((root/'study.json').read_text())
    metadata['origins'] = [dict(origin_id=oid, kind='study', label=oid, source_ids=[sid],
                               rationale='Explicit study ID in fictional input.', reviewer='authored fixture',
                               checked_at='2026-11-06T00:00:00Z') for oid,sid in [('lx01','s1'),('ly02','s2')]]
    (root/'study.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    def write(name, rows):
        (root/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    for name,rows in [('sources',sources),('queries',[query]),('evidence',evidence),('claims',claims)]:
        write(name,rows)
    analysis = ledger.stress(root)
    for claim, result in zip(claims, analysis['claims']):
        claim['stress_test'] = dict(selection_rationale='Demonstrate all recorded origin-removal scenarios.', reviews=[
            dict(excluded_origin_id=s['excluded_origin_id'], judgment='narrowed' if claim['claim_id']=='c1' else 'unresolved',
                 rationale='Source-specific observation only.' if claim['claim_id']=='c1' else 'No general conclusion from the remaining conditions.',
                 reviewer='authored fixture (not independent reviewer)', checked_at='2026-11-06T00:00:00Z',
                 basis_sha256=result['basis_sha256']) for s in result['scenarios']])
    write('claims',claims)
    (root/'report.md').write_text(ledger.render(root),encoding='utf-8')
    (root/'validation.json').write_text(json.dumps(ledger.check(root),indent=2)+'\n',encoding='utf-8')
    print('Created synthetic demo. Expected check/stress/render exit: 2; truth_certified:false.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    build(parser.parse_args().root)
