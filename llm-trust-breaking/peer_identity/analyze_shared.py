"""Analyze downloaded compact Experiment 3.3 CSVs; standard library only, no API calls.

Copied into each sharing bundle as analyze.py. Raw transcripts/LFS are not required.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics


def csv_row(row):
    return {key: '' if value is None else str(value).lower() if type(value) is bool else value for key,value in row.items()}


def mean(xs):
    xs=list(xs)
    return statistics.mean(xs) if xs else None


RUN_METRIC_FIELDS=['checkpoint_id','run_id','condition','behavior_setting','baseline_a_contribution',
    'round6_a_contribution','immediate_contribution_change','sustained_contribution_change',
    'baseline_a_trust_in_b','post_a_trust_in_b','trust_rating_change','detected_change','actual_swap',
    'batch_id','condition_id','repetition','run_status','observed_post_contribution_rounds','observed_post_trust_rounds']


def compute_run_metrics(tables):
    """All planned continuations; incomplete measurements remain missing, never zero-filled."""
    baseline={r['checkpoint_id']:r for r in tables['checkpoints']}
    detection={r['run_id']:r for r in tables['detections']}
    by_run={}
    for r in tables['rounds']:
        if r['agent']=='A' and r['phase']=='continuation':by_run.setdefault(r['run_id'],[]).append(r)
    def num(v):return float(v) if v is not None and v!='' else None
    result=[]
    for trial in tables['trials']:
        cp=baseline[trial['checkpoint_id']];d=detection[trial['run_id']]
        rows=by_run.get(trial['run_id'],[])
        base=num(cp['mean_contribution_a_rounds3to5']);trust_base=num(cp['mean_trust_a_rounds3to5'])
        r6=next((num(r['contribution']) for r in rows if int(r['round'])==6),None)
        contributions=[num(r['contribution']) for r in rows if num(r['contribution']) is not None]
        trust=[num(r['trust_score']) for r in rows if num(r['trust_score']) is not None]
        post_contribution=mean(contributions) if len(contributions)==5 else None
        post_trust=mean(trust) if len(trust)==5 else None
        result.append(dict(zip(RUN_METRIC_FIELDS,[trial['checkpoint_id'],trial['run_id'],trial['condition'],trial['setting'],
            base,r6,r6-base if r6 is not None and base is not None else None,
            post_contribution-base if post_contribution is not None and base is not None else None,
            trust_base,post_trust,post_trust-trust_base if post_trust is not None and trust_base is not None else None,
            d['judgment']=='CHANGED' if d['judgment'] else None,trial['condition'] in ['C2','C3'],
            trial['batch_id'],trial['condition_id'],int(trial['repetition']),trial['status'],len(contributions),len(trust)])))
    return result


def analyze(bundle):
    bundle=Path(bundle)
    checksums=json.loads((bundle/'checksums.json').read_text())
    metadata_path=bundle/'metadata.json'
    if hashlib.sha256(metadata_path.read_bytes()).hexdigest()!=checksums['metadata.json']:
        raise ValueError('Metadata checksum mismatch')
    metadata=json.loads(metadata_path.read_text())
    tables={}
    for name in ['rounds','trials','detections','checkpoints']:
        p=bundle/(name+'.csv')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=checksums[p.name]:
            raise ValueError('CSV checksum mismatch')
        with p.open(newline='',encoding='utf-8') as f:tables[name]=list(csv.DictReader(f))
    baseline={r['checkpoint_id']:r for r in tables['checkpoints']}
    detection={r['run_id']:r for r in tables['detections']}
    by_run={}
    for row in tables['rounds']:
        if row['phase']=='continuation' and row['agent']=='A':by_run.setdefault(row['run_id'],[]).append(row)
    metrics=[]
    for trial in tables['trials']:
        if trial['status'] not in ['complete','recovered_complete']:continue
        cp=baseline[trial['checkpoint_id']]
        post=sorted(by_run[trial['run_id']],key=lambda r:int(r['round']))
        if [int(r['round']) for r in post]!=list(range(6,11)):raise ValueError('Missing/duplicate continuation rounds')
        base=float(cp['mean_contribution_a_rounds3to5']);trust=float(cp['mean_trust_a_rounds3to5'])
        d=detection[trial['run_id']]
        metrics.append({'checkpoint_id':trial['checkpoint_id'],'run_id':trial['run_id'],
            'condition':trial['condition'],'setting':trial['setting'],'repetition':int(trial['repetition']),
            'high_trust':cp['high_trust']=='true','immediate_change_a':float(post[0]['contribution'])-base,
            'post_average_change_a':mean(float(r['contribution']) for r in post)-base,
            'trust_change_a':mean(float(r['trust_score']) for r in post)-trust,
            'said_changed':d['judgment']=='CHANGED','correct':d['correct']=='true','confidence':int(d['confidence'])})
    lookup={(r['checkpoint_id'],r['setting'],r['condition'],r['repetition']):r for r in metrics}
    paired=[]
    for row in metrics:
        if row['condition']=='C0':continue
        control=lookup.get((row['checkpoint_id'],row['setting'],'C0',row['repetition']))
        if control:
            paired.append({**{k:row[k] for k in ['checkpoint_id','setting','condition','repetition','high_trust']},
                **{'matched_'+f:row[f]-control[f] for f in ['immediate_change_a','post_average_change_a','trust_change_a']}})
    checkpoint_effects=[]
    for key in sorted({(r['checkpoint_id'],r['setting'],r['condition']) for r in paired}):
        group=[r for r in paired if (r['checkpoint_id'],r['setting'],r['condition'])==key]
        checkpoint_effects.append({'checkpoint_id':key[0],'setting':key[1],'condition':key[2],
            'matched_repetitions':len(group),'high_trust':group[0]['high_trust'],
            **{f:mean(r[f] for r in group) for f in ['matched_immediate_change_a','matched_post_average_change_a','matched_trust_change_a']}})
    recognition=[]
    for setting,condition in sorted({(r['setting'],r['condition']) for r in metrics}):
        group=[r for r in metrics if (r['setting'],r['condition'])==(setting,condition)]
        cps=sorted({r['checkpoint_id'] for r in group})
        recognition.append({'setting':setting,'condition':condition,'independent_checkpoints':len(cps),
            'continuations':len(group),'negative_control':condition in ['C0','C1'],
            'changed_rate_checkpoint_weighted':mean(mean(r['said_changed'] for r in group if r['checkpoint_id']==cp) for cp in cps),
            'accuracy_checkpoint_weighted':mean(mean(r['correct'] for r in group if r['checkpoint_id']==cp) for cp in cps),
            'confidence_checkpoint_weighted':mean(mean(r['confidence'] for r in group if r['checkpoint_id']==cp) for cp in cps)})
    summary={'protocol_version':metadata['config'].get('protocol_version','publicgoods-peer-identity-v1'),'mock':metadata['mock'],'batch_id':metadata['batch']['batch_id'],'planned_continuations':len(tables['trials']),'complete_continuations':len(metrics),
             'incomplete_continuations':len(tables['trials'])-len(metrics),
             'independent_checkpoints_with_results':len({r['checkpoint_id'] for r in metrics}),
             'recognition_by_condition':recognition,
             'interpretation':'Descriptive checkpoint-weighted results. Negative-control changed rates are false positives. Average matched repetitions within checkpoints; natural and controlled remain separate. No behavioral-recognition classifier or power guarantee.'}
    outputs={'run_metrics':compute_run_metrics(tables),'matched_checkpoint_effects':checkpoint_effects,'recognition_by_condition':recognition}
    if summary['protocol_version']=='publicgoods-peer-identity-v2':
        measures=[]
        for setting,condition in sorted({(r['setting'],r['condition']) for r in metrics}):
            group=[r for r in tables['rounds'] if r['agent']=='A' and r['phase']=='continuation' and r['setting']==setting and r['condition']==condition]
            def avg(field):return mean(float(r[field]) for r in group if r.get(field) not in ('',None))
            errors=[float(r['prediction_error']) for r in group if r.get('prediction_error') not in ('',None)]
            measures.append({'protocol_version':summary['protocol_version'],'setting':setting,'condition':condition,
                'independent_checkpoints':len({r['checkpoint_id'] for r in group}),
                'mean_trust_1_10':avg('trust_score_1_10'),'mean_promise_reliability_1_10':avg('promise_reliability_1_10'),
                'factual_accuracy':mean(r['factual_assessment_correct']=='true' for r in group if r.get('factual_assessment_correct') not in ('',None)),
                'objective_promise_compliance':mean(r['promise_compliance']=='true' for r in group if r.get('promise_compliance') not in ('',None)),
                'forecast_mean_absolute_error':mean(abs(e) for e in errors),'forecast_evaluable_rounds':len(errors)})
        outputs['v2_measurement_summary']=measures
    return outputs,summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle',type=Path,nargs='?',default=Path(__file__).resolve().parent)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.output.resolve().is_relative_to(a.bundle.resolve()):p.error('Analysis output must be outside the immutable bundle')
    tables,summary=analyze(a.bundle)
    a.output.mkdir(parents=True,exist_ok=False)
    for name,rows in tables.items():
        if rows:
            with (a.output/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(csv_row(row) for row in rows)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
