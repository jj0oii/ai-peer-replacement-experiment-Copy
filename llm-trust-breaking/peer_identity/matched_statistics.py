"""Standalone Version 2 checkpoint-level analysis. Standard library; no model calls.

Run this file directly with a sealed export directory and --output NEW_DIRECTORY.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

VERSION='publicgoods-peer-identity-v2'
CONTRASTS=[('C3','C2'),('C2','C1'),('C1','C0')]
BOUNDS={'mean_contribution':(0,5),'immediate_contribution_change':(-5,5),'sustained_contribution_change':(-5,5),
 'mean_trust':(1,10),'trust_change':(-9,9),'mean_reliability':(1,10),'reliability_change':(-9,9),
 'objective_partner_compliance':(0,1),'partner_above_promise_rate':(0,1),'partner_below_promise_rate':(0,1),
 'forecast_mae':(0,5),'forecast_exact_rate':(0,1),'forecast_signed_error':(-5,5),
 'factual_accuracy':(0,1),'recognition_changed':(0,1),'recognition_correct':(0,1),'confidence':(0,100)}
# Common baselines cancel within a matched checkpoint/repetition.
DIFF_BOUNDS={k:(-(hi-lo),hi-lo) for k,(lo,hi) in BOUNDS.items()}
for k in ['immediate_contribution_change','sustained_contribution_change']:DIFF_BOUNDS[k]=(-5,5)
for k in ['trust_change','reliability_change']:DIFF_BOUNDS[k]=(-9,9)

def average(xs):
 xs=list(xs);return statistics.mean(xs) if xs else None

def interval(values,bounds,alpha=.05):
 """Finite-sample bounded-mean Hoeffding interval over independent checkpoints."""
 values=list(values);lo,hi=bounds
 if not 0<alpha<1 or not lo<hi:raise ValueError('Invalid interval parameters')
 if any(not math.isfinite(v) or not lo<=v<=hi for v in values):raise ValueError('Value outside prespecified bounds')
 if len(values)<2:return {'estimate':average(values),'ci_low':None,'ci_high':None,'n_checkpoints':len(values),'interval_status':'withheld: fewer than two checkpoints'}
 center=average(values);radius=(hi-lo)*math.sqrt(math.log(2/alpha)/(2*len(values)))
 return {'estimate':center,'ci_low':max(lo,center-radius),'ci_high':min(hi,center+radius),
  'n_checkpoints':len(values),'interval_status':'95% pointwise Hoeffding; assumes independent checkpoint draws; conservative'}

def exact_binomial(k,n,alpha=.05):
 """Clopper–Pearson interval, used only for one Bernoulli observation per checkpoint."""
 if type(k)is not int or type(n)is not int or not 0<=k<=n or n<1:raise ValueError('Invalid counts')
 def tail(p):return sum(math.comb(n,j)*p**j*(1-p)**(n-j) for j in range(k,n+1))
 def cdf(p):return sum(math.comb(n,j)*p**j*(1-p)**(n-j) for j in range(k+1))
 low=0.;high=1.
 if k:
  a,b=0.,1.
  for _ in range(80):
   m=(a+b)/2
   if tail(m)<alpha/2:a=m
   else:b=m
  low=(a+b)/2
 if k<n:
  a,b=0.,1.
  for _ in range(80):
   m=(a+b)/2
   if cdf(m)>alpha/2:a=m
   else:b=m
  high=(a+b)/2
 return low,high

def load_bundle(bundle):
 bundle=Path(bundle);checks=json.loads((bundle/'checksums.json').read_text())
 names=['metadata.json','rounds.csv','trials.csv','detections.csv','checkpoints.csv']
 for name in names:
  if hashlib.sha256((bundle/name).read_bytes()).hexdigest()!=checks.get(name):raise ValueError('Compact bundle checksum mismatch')
 metadata=json.loads((bundle/'metadata.json').read_text())
 if metadata['config'].get('protocol_version')!=VERSION:raise ValueError('Analyze Version 2 separately; Version 1 is not pooled or rescaled')
 tables={}
 for name in names[1:]:
  with (bundle/name).open(newline='') as f:tables[name[:-4]]=list(csv.DictReader(f))
 trials=tables['trials'];ids=[r['run_id'] for r in trials]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate trial IDs')
 roundkeys=[(r['run_id'],r['agent'],r['round']) for r in tables['rounds']]
 if len(roundkeys)!=len(set(roundkeys)):raise ValueError('Duplicate agent round')
 dkeys=[r['run_id'] for r in tables['detections']]
 if len(dkeys)!=len(set(dkeys)) or set(dkeys)!=set(ids):raise ValueError('Recognition/trial joins differ')
 return metadata,tables

def per_run(tables):
 baseline={};by_run={};detection={r['run_id']:r for r in tables['detections']}
 for r in tables['rounds']:
  key=(r['checkpoint_id'],r['agent']) if r['phase']=='establishment' else (r['run_id'],r['agent'])
  (baseline if r['phase']=='establishment' else by_run).setdefault(key,[]).append(r)
 results=[];omitted=[]
 def avg(rs,k):return average(float(r[k]) for r in rs if r.get(k) not in ('',None))
 for trial in tables['trials']:
  if trial['status'] not in ['complete','recovered_complete']:
   omitted.append({'run_id':trial['run_id'],'checkpoint_id':trial['checkpoint_id'],'status':trial['status']});continue
  for agent in ['A','B']:
   post=sorted(by_run.get((trial['run_id'],agent),[]),key=lambda r:int(r['round']))
   base=[r for r in baseline.get((trial['checkpoint_id'],agent),[]) if int(r['round']) in [3,4,5]]
   if [int(r['round']) for r in post]!=list(range(6,11)) or len(base)!=3:raise ValueError('Complete trial has missing baseline/post rounds')
   if any(r['protocol_version']!=VERSION for r in post+base):raise ValueError('Mixed row protocols')
   bs=avg(base,'contribution');bt=avg(base,'trust_score_1_10');br=avg(base,'promise_reliability_1_10')
   es=[float(r['prediction_error']) for r in post if r['prediction_evaluable']=='true']
   rec=detection[trial['run_id']]
   row={k:trial[k] for k in ['checkpoint_id','run_id','setting','condition','repetition']};row['repetition']=int(row['repetition']);row['agent']=agent
   row.update(mean_contribution=avg(post,'contribution'),immediate_contribution_change=float(post[0]['contribution'])-bs,
    sustained_contribution_change=avg(post,'contribution')-bs,mean_trust=avg(post,'trust_score_1_10'),trust_change=avg(post,'trust_score_1_10')-bt,
    mean_reliability=avg(post,'promise_reliability_1_10'),reliability_change=avg(post,'promise_reliability_1_10')-br,
    objective_partner_compliance=average(r['promise_compliance']=='true' for r in post),
    partner_above_promise_rate=average(int(r['partner_actual_contribution'])>int(r['partner_promised_contribution']) for r in post),
    partner_below_promise_rate=average(int(r['partner_actual_contribution'])<int(r['partner_promised_contribution']) for r in post),
    forecast_mae=average(abs(e) for e in es),forecast_exact_rate=average(e==0 for e in es),forecast_signed_error=average(es),
    factual_accuracy=average(r['factual_assessment_correct']=='true' for r in post),
    recognition_changed=float(rec['judgment']=='CHANGED') if agent=='A' else None,
    recognition_correct=float(rec['correct']=='true') if agent=='A' else None,confidence=float(rec['confidence']) if agent=='A' else None)
   results.append(row)
 return results,omitted

def analyze_rows(rows):
 """Match the SAME repetitions first; collapse to one difference per checkpoint."""
 identities=[(r['checkpoint_id'],r['setting'],r['condition'],r['agent'],r['repetition']) for r in rows]
 if len(identities)!=len(set(identities)):raise ValueError('Duplicate checkpoint/condition/repetition')
 matched=[];missing=[];summaries=[];conditions=[]
 cps=sorted({r['checkpoint_id'] for r in rows});settings=sorted({r['setting'] for r in rows});agents=sorted({r['agent'] for r in rows})
 for setting in settings:
  for agent in agents:
   for treatment,reference in CONTRASTS:
    for cp in cps:
     left={r['repetition']:r for r in rows if (r['checkpoint_id'],r['setting'],r['agent'],r['condition'])==(cp,setting,agent,treatment)}
     right={r['repetition']:r for r in rows if (r['checkpoint_id'],r['setting'],r['agent'],r['condition'])==(cp,setting,agent,reference)}
     shared=sorted(left.keys()&right.keys())
     if not shared:
      missing.append(dict(checkpoint_id=cp,setting=setting,agent=agent,treatment=treatment,reference=reference,reason='No completed matched repetitions'));continue
     for metric in BOUNDS:
      values=[left[rep][metric]-right[rep][metric] for rep in shared if left[rep].get(metric) is not None and right[rep].get(metric) is not None]
      if values:matched.append(dict(checkpoint_id=cp,setting=setting,agent=agent,treatment=treatment,reference=reference,
       metric=metric,matched_repetitions=len(values),difference=average(values)))
    for metric,bounds in DIFF_BOUNDS.items():
     values=[r['difference'] for r in matched if (r['setting'],r['agent'],r['treatment'],r['reference'],r['metric'])==(setting,agent,treatment,reference,metric)]
     if not values:continue
     summaries.append(dict(setting=setting,agent=agent,treatment=treatment,reference=reference,metric=metric,
      **interval(values,bounds),bounded_difference_min=bounds[0],bounded_difference_max=bounds[1]))
   for condition in ['C0','C1','C2','C3']:
    group=[r for r in rows if (r['setting'],r['agent'],r['condition'])==(setting,agent,condition)]
    for metric,bounds in BOUNDS.items():
     cp_values=[average(r[metric] for r in group if r['checkpoint_id']==cp and r.get(metric) is not None) for cp in cps]
     cp_values=[v for v in cp_values if v is not None]
     if not cp_values:continue
     record=dict(setting=setting,agent=agent,condition=condition,metric=metric,**interval(cp_values,bounds),
      exact_binomial_low=None,exact_binomial_high=None,exact_binomial_n=None)
     # This exact interval is not applied to pooled correlated trials or round counts.
     if metric in ['recognition_changed','recognition_correct'] and all(sum(r['checkpoint_id']==cp for r in group)==1 for cp in cps if any(r['checkpoint_id']==cp for r in group)):
      low,high=exact_binomial(int(sum(cp_values)),len(cp_values));record.update(exact_binomial_low=low,exact_binomial_high=high,exact_binomial_n=len(cp_values))
     conditions.append(record)
 return matched,summaries,conditions,missing

def recognition_tables(tables):
 review=[];cluster=[]
 for r in tables['detections']:
  if not r['judgment']:continue
  evidence=json.loads(r['recognition_evidence'])
  # Narrow reproducible lexical screen; flags are evidence annotations, never changed judgments.
  text=' '.join(evidence.get(k,'') for k in ['evidence','alternative_explanations'])
  flag=r['judgment']=='CHANGED' and bool(re.search(r'rather than (?:an? (?:actual )?|a full )?partner (?:change|replacement)|still the same partner|partner remained the same|rather than a full replacement',text,re.I))
  review.append({**r,'potential_contradiction_review_flag':flag,'empty_text_fields':json.dumps([k for k,v in evidence.items() if v=='']),
   'review_note':'Lexical screen only; requires human interpretation and is not exhaustive.'})
 for setting in sorted({r['setting'] for r in review}):
  group=[r for r in review if r['setting']==setting]
  for kind,selected in [('accuracy',group),('detection_rate',[r for r in group if r['condition'] in ['C2','C3']]),('false_positive_rate',[r for r in group if r['condition'] in ['C0','C1']])]:
   cp_values=[average((r['correct']=='true') if kind=='accuracy' else (r['judgment']=='CHANGED') for r in selected if r['checkpoint_id']==cp) for cp in sorted({r['checkpoint_id'] for r in selected})]
   cluster.append(dict(setting=setting,statistic=kind,trial_count=len(selected),**interval(cp_values,(0,1))))
 return review,cluster

def write_csv(path,rows):
 if not rows:return
 with Path(path).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:'' if v is None else str(v).lower() if type(v)is bool else v for k,v in r.items()} for r in rows)

def run(bundle,output):
 bundle=Path(bundle).resolve();output=Path(output).resolve()
 if output.is_relative_to(bundle):raise ValueError('Keep analysis outside immutable source export')
 meta,tables=load_bundle(bundle);rows,omitted=per_run(tables);matched,comparisons,conditions,missing=analyze_rows(rows);review,recognition=recognition_tables(tables)
 distributions=[]
 for field in ['trust_score_1_10','promise_reliability_1_10']:
  counts={};denominators={}
  for r in tables['rounds']:
   if r['phase']!='continuation' or r['run_id'] not in {x['run_id'] for x in rows}:continue
   key=(r['checkpoint_id'],r['setting'],r['condition'],r['agent'])
   denominators[key]=denominators.get(key,0)+1
   score=int(r[field]);counts[(key,score)]=counts.get((key,score),0)+1
  for key,total in sorted(denominators.items()):
   for score in range(1,11):
    count=counts.get((key,score),0)
    distributions.append(dict(checkpoint_id=key[0],setting=key[1],condition=key[2],agent=key[3],rating=field,
     score=score,round_count=count,observed_rounds=total,within_checkpoint_fraction=count/total))
 output.mkdir(parents=True,exist_ok=False)
 for name,data in [('score_distributions_by_checkpoint',distributions),('run_measurements',rows),('matched_checkpoint_differences',matched),('matched_contrasts',comparisons),('condition_measurements',conditions),('recognition_review',review),('recognition_cluster_intervals',recognition),('unmatched_checkpoints',missing),('unstarted_or_incomplete_trials',omitted)]:write_csv(output/(name+'.csv'),data)
 summary={'protocol_version':VERSION,'mock':meta['mock'],'batch_id':meta['batch']['batch_id'],'source_export':str(bundle),
  'independent_completed_checkpoints':len({r['checkpoint_id'] for r in rows}),'completed_continuations':len(rows)//2,
  'unstarted_or_incomplete_planned_trials':len(omitted),'contrasts':[f'{a}-{b}' for a,b in CONTRASTS],
  'uncertainty_method':'95% pointwise bounded-mean Hoeffding intervals over checkpoint means; exact Clopper–Pearson additionally for one binary recognition outcome per checkpoint within a condition/setting.',
  'warning':f"{len({r['checkpoint_id'] for r in rows})} independent completed checkpoints. With small samples distribution-free intervals are broad, often the full feasible range. Equal/zero observed differences do not establish a null effect. No bootstrap round/trial pseudoreplication. No multiplicity-adjusted simultaneous claims. Mean ordinal ratings are descriptive, not equal-interval psychological measurements.",
  'matching_rule':'Match repetitions within checkpoint/setting, then average differences within checkpoint. Incomplete pairs are not imputed.',
  'forecast_rule':'Within-run next observed contribution; round-5 branch forecast scoring remains separately in source rounds.csv; no round-11 prediction.',
  'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'input_sha256':{name:hashlib.sha256((bundle/name).read_bytes()).hexdigest() for name in ['metadata.json','rounds.csv','trials.csv','detections.csv','checkpoints.csv']}}
 (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');write_csv(output/'data_dictionary',[{'file':'matched_contrasts.csv','meaning':'Treatment minus reference, checkpoint-weighted; ci bounds are conservative pointwise population-mean intervals.'},
  {'file':'run_measurements.csv','meaning':'One row per agent per completed continuation. Partner metrics refer to the other agent; A recognition fields are missing for B.'},
  {'file':'condition_measurements.csv','meaning':'Condition means over checkpoints, with one average per checkpoint. Exact binomial intervals only where one Bernoulli per checkpoint.'},
  {'file':'recognition_review.csv','meaning':'Unmodified judgments/evidence plus lexical review flags, not an automated semantic correction.'}])
 return summary

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();print(json.dumps(run(a.bundle,a.output),indent=2))
