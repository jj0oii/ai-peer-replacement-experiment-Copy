"""Standalone offline pilot-based budgets from a validated Version 2 export; no API client."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from collections import Counter,defaultdict
from statistics import mean

def groups(n):
 return {('checkpoint_establishment','gpt-4o-mini'):40*n,('continuations','gpt-4o-mini'):288*n,
         ('continuations','gpt-4.1-mini'):40*n,('judging','gpt-5-mini'):90*n}

def load(bundle):
 bundle=Path(bundle);checks=json.loads((bundle/'checksums.json').read_text())
 for name in ['metadata.json','trials.csv','raw.jsonl.gz']:
  h=hashlib.sha256()
  with (bundle/name).open('rb') as f:
   for block in iter(lambda:f.read(1<<20),b''):h.update(block)
  if h.hexdigest()!=checks.get(name):raise ValueError('Budget source checksum mismatch')
 meta=json.loads((bundle/'metadata.json').read_text());cfg=meta['config']
 if meta['mock']:raise ValueError('Synthetic usage must not be presented as real costs')
 expected={'protocol_version':'publicgoods-peer-identity-v2','checkpoints':25,'repetitions':1,
  'conditions':['C0','C1','C2','C3'],'settings':['natural','controlled'],'model_a':'gpt-4o-mini','model_b':'gpt-4o-mini',
  'replacement_model':'gpt-4.1-mini','judge_model':'gpt-5-mini'}
 if any(cfg.get(k)!=v for k,v in expected.items()):raise ValueError('Budget assumes unchanged documented 200-trial V2 configuration')
 with (bundle/'trials.csv').open(newline='') as f:trials=list(csv.DictReader(f))
 complete=[r for r in trials if r['status'] in ['complete','recovered_complete']];counts=Counter(r['checkpoint_id'] for r in complete)
 if len(counts)<2 or any(v!=8 for v in counts.values()):raise ValueError('Require at least two fully completed checkpoints and no partial checkpoint for this estimate')
 records=[];recovered=set();ids=set()
 with gzip.open(bundle/'raw.jsonl.gz','rt') as f:
  for line in f:
   item=json.loads(line);path=item['path'];r=item['record']
   if path.startswith('recoveries/'):recovered.add(r['request_id_local'])
   if not path.startswith('requests/'):continue
   rid=r['request_id_local']
   if rid in ids:raise ValueError('Duplicate billed request');
   ids.add(rid)
   phase='judging' if '/judge/' in rid else 'checkpoint_establishment' if '/establishment/' in rid else 'continuations'
   response=r.get('response',{})
   if response.get('endpoint')!='https://api.openai.com/v1/chat/completions' or response.get('finish_reason')!='stop' or not response.get('usage') or 'cost_usd' not in r:
    raise ValueError('Resolve missing usage, incomplete generation or provider issue first')
   records.append({'phase':phase,'model':r['payload']['model'],'usage':response['usage'],'cost_usd':r['cost_usd'],'status':r['status'],'id':rid})
 if any(r['status']!='complete' and r['id'] not in recovered for r in records):raise ValueError('Unresolved recorded request')
 observed=Counter((r['phase'],r['model']) for r in records)
 if observed!=Counter(groups(len(counts))):raise ValueError('Request ledger does not match completed-checkpoint scope; do not ignore failed or extra costs')
 return meta,records,len(counts)

def scenarios(records,ncp,prices,target=25,next_count=5):
 data=defaultdict(list)
 for r in records:data[(r['phase'],r['model'])].append(r)
 results=[]
 for name in ['observed_usage','higher_usage','full_output_stress']:
  rows=[]
  for key,total in groups(target).items():
   samples=data[key];input_mean=mean(r['usage']['prompt_tokens'] for r in samples);output_mean=mean(r['usage']['completion_tokens'] for r in samples)
   input_max=max(r['usage']['prompt_tokens'] for r in samples);output_max=max(r['usage']['completion_tokens'] for r in samples)
   rate_in,_,rate_out=prices[key[1]]
   if name=='observed_usage':
    unit=mean(r['cost_usd'] for r in samples);inp=input_mean;out=output_mean;cache='Observed phase/model cache discounts retained; uncertain future cache behavior'
   elif name=='higher_usage':
    inp=max(2*input_mean,input_max);out=min(2000,max(2*output_mean,output_max));unit=(inp*rate_in+out*rate_out)/1e6;cache='No cache discount'
   else:
    inp=max(24000,input_max,1.5*input_mean);out=2000;unit=(inp*rate_in+out*rate_out)/1e6;cache='No cache discount; full existing output allowance'
   remaining=total-len(samples)
   if remaining<0:raise ValueError('Observed data exceed planned sample')
   next_calls=groups(next_count)[key]
   rows.append(dict(scenario=name,phase=key[0],model=key[1],observed_requests=len(samples),
    input_tokens_per_call=inp,output_tokens_per_call=out,cache_assumption=cache,unit_cost_usd=unit,
    remaining_requests=remaining,remaining_checkpoint_cost_usd=remaining*unit,
    next_batch_requests=next_calls,next_five_checkpoint_cost_usd=next_calls*unit))
  results.extend(rows)
 return results

def run(bundle,output):
 bundle=Path(bundle).resolve();output=Path(output).resolve()
 if output.is_relative_to(bundle):raise ValueError('Do not modify sealed source bundle')
 meta,records,ncp=load(bundle)
 if not 2<=ncp<=25:raise ValueError('Completed-checkpoint count outside the planned study')
 remaining_count=25-ncp;next_count=min(5,remaining_count)
 prices=meta['price_assumptions_usd_per_million'];rows=scenarios(records,ncp,prices,next_count=next_count)
 policy=meta.get('spending_policy') or {};prior=policy.get('prior_spend_allowance_usd')
 if policy.get('total_budget_usd')!=60 or policy.get('safety_reserve_usd')!=10 or prior is None:raise ValueError('Unexpected approved cumulative policy')
 known=sum(r['cost_usd'] for r in records);totals=[]
 for scenario in ['observed_usage','higher_usage','full_output_stress']:
  group=[r for r in rows if r['scenario']==scenario];remaining=sum(r['remaining_checkpoint_cost_usd'] for r in group);nxt=sum(r['next_five_checkpoint_cost_usd'] for r in group)
  totals.append(dict(scenario=scenario,current_v2_paid_usd=known,prior_v1_and_allowance_usd=prior,remaining_checkpoints_cost_usd=remaining,
   cumulative_200_trial_forecast_usd=known+prior+remaining,total_with_reserve_usd=known+prior+remaining+10,
   next_five_checkpoint_cost_usd=nxt,cumulative_after_next_batch_usd=known+prior+nxt))
 output.mkdir(parents=True,exist_ok=False)
 for name,rs in [('scenario_phase_model_costs',rows),('scenario_totals',totals)]:
  with (output/(name+'.csv')).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 summary={'paid_calls_during_review':0,'protocol_version':meta['config']['protocol_version'],'completed_checkpoints':ncp,
  'pilot_inclusion':'All completed Version 2 checkpoints count toward the unchanged 25 if protocol remains identical; original V1 does not count.',
  'observed_v2_paid_usd':known,'prior_v1_paid_usd':.4854921,'prior_other_spending_allowance_usd':prior-.4854921,
  'cumulative_current_usd':known+prior,'cumulative_limit_usd':60,'reserve_usd':10,
  'remaining_spendable_after_reserve_usd':60-10-prior-known,'remaining_checkpoints':remaining_count,'remaining_continuations':8*remaining_count,
  'remaining_planned_requests':sum(groups(remaining_count).values()),'scenario_totals':totals,
  'next_batch':{'checkpoint_start':ncp,'checkpoint_count':next_count,'checkpoint_indices':list(range(ncp,ncp+next_count)),'continuations':8*next_count,
   'batch_request_cap':458*next_count,'proposed_batch_guard_usd':16 if next_count==5 else None,'cumulative_request_cap':11450,
   'new_cumulative_request_total_after_batch':458*(ncp+next_count),'post_batch_checkpoint_total':ncp+next_count,'post_batch_trial_total':8*(ncp+next_count),
   'pilot_window_000_001_guards_unchanged':'916 requests / $8; proposed new window does not reset pilot guard',
   'proposed_only':True,'scope':'Only the new five-checkpoint window. No policy file created and no execution authorized.'},
  'pricing_verification':meta.get('pricing_verification'),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'limitations':'Scenarios, not confidence bounds. Limited completed-checkpoint sample; cache hit rates, language length, reasoning usage and errors can vary. Higher-usage scenario doubles observed means and floors at observed maxima, uncached, without changing actual 2000-token limits. Stress retains at least 24000 input/2000 output per future call. No reserve consumption, sample reduction or $60 limit increase is approved; local guards are not provider billing ceilings.'}
 (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();print(json.dumps(run(a.bundle,a.output),indent=2))
