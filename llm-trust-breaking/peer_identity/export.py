"""Validated, immutable sharing bundles. Local only: no Git/network mutations."""
from __future__ import annotations
import csv
from datetime import datetime
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from src.games.publicgoods import PublicGoodsGame
from .inference import PRICES, atomic_json, canonical, digest, validate, usage_cost
from .protocol import Config, CATEGORIES, PARAMS
from .provenance import ensure_batch, utc_now
from . import measurements_v2 as v2
from .analyze_shared import compute_run_metrics, RUN_METRIC_FIELDS

class ExportError(ValueError):
    pass

LEGACY_FILES={'rounds.csv','detections.csv','trials.csv','checkpoints.csv','metadata.json',
               'raw.jsonl.gz','DATA_DICTIONARY.md','analyze.py','validation.json','checksums.json'}
ALLOWED_FILES=LEGACY_FILES|{'run_metrics.csv','charts.py','REVIEW_README.md'}
PATTERNS=[('provider_key',re.compile(r'\bsk-(?:proj-|or-v1-|ant-)?[A-Za-z0-9_-]{16,}')),
          ('github_token',re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')),
          ('aws_access_key',re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
          ('private_key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
          ('bearer_token',re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{20,}'))]
SENSITIVE_NAME=re.compile(r'(?i)(?:api[_-]?key|authorization|password|credential|client[_-]?secret|access[_-]?token|refresh[_-]?token)')


def known_secrets(env_file=None):
    """Inspect credential values only in memory to detect accidental exact inclusion. Never emit them."""
    values=dict(os.environ)
    if env_file is not None and Path(env_file).is_file():
        from dotenv import dotenv_values
        values.update(dotenv_values(env_file))
    return [v for k,v in values.items() if SENSITIVE_NAME.search(k) and isinstance(v,str) and len(v)>=8]


def scan(value, secrets=(), location='data'):
    def walk(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if SENSITIVE_NAME.search(k):
                    raise ExportError('Sensitive field name detected in '+location)
                walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
        elif isinstance(v,str):
            for name,pattern in PATTERNS:
                if pattern.search(v):raise ExportError('Possible '+name+' detected in '+location)
            if any(secret in v for secret in secrets):
                raise ExportError('Known credential detected in '+location)
    walk(value)


def load_json(path):
    if path.is_symlink():raise ExportError('Symlink source rejected')
    try:
        return json.loads(path.read_text(),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite')))
    except (ValueError,OSError) as e:
        raise ExportError('Unreadable or invalid JSON: '+path.name) from None


def required(record, names, location):
    if not isinstance(record,dict) or set(names)-record.keys():raise ExportError('Missing fields in '+location)


def sources(directory, include_requests=True):
    paths=[]
    for name in ['batch.json','manifest.json','source-snapshot.json','cost-plan.json','run-status.json','usage-summary.json','budget-policy.json']:
        if (directory/name).is_file():paths.append(directory/name)
    for pattern in ['budget-history/*.json','windows/*-policy.json','attempts/*.json','requests/*.json','checkpoint-*/checkpoint.json',
                    'checkpoint-*/establishment-progress.json','checkpoint-*/branch-order.json',
                    'checkpoint-*/*/result.json','checkpoint-*/*/progress.json']:
        paths.extend(directory.glob(pattern))
    for p in sorted(set(paths)):
        if not include_requests and p.parent.name=='requests':continue
        if p.is_symlink() or not p.resolve().is_relative_to(directory.resolve()):raise ExportError('Escaping source path')
        yield p.relative_to(directory).as_posix(),load_json(p)


def numeric(value, low, high, location, integer=True):
    if type(value) not in ((int,) if integer else (int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ExportError('Invalid numeric value in '+location)


def request_totals(records):
    result={'api_requests':len(records),'requests_with_usage':0,'input_tokens':0,'output_tokens':0,
            'cached_input_tokens':0,'reasoning_tokens':0,'known_cost_usd':0.,'reserved_unknown_cost_usd':0.,
            'error_requests':sum(r['status']=='blocked' for r in records),
            'pending_requests':sum(r['status']=='pending' for r in records)}
    for r in records:
        usage=r.get('response',{}).get('usage')
        if usage:
            result['requests_with_usage']+=1
            result['input_tokens']+=usage['prompt_tokens'];result['output_tokens']+=usage['completion_tokens']
            result['cached_input_tokens']+=(usage.get('prompt_tokens_details') or {}).get('cached_tokens',0)
            result['reasoning_tokens']+=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
        result['known_cost_usd']+=r.get('cost_usd',0.)
        if 'cost_usd' not in r:result['reserved_unknown_cost_usd']+=r['reserved_usd']
    result['usage_complete']=result['requests_with_usage']==len(records)
    return result


ROUND_FIELDS=['batch_id','checkpoint_id','run_id','condition_id','condition','setting','repetition','phase',
 'round','agent','model','round_status','planned_contribution','promised_contribution','proposed_contribution',
 'contribution','contribution_imposed','payoff','promise_broken','proposed_promise_broken','trust_target','trust_score',
 'started_at','last_response_at']
TRIAL_FIELDS=['batch_id','checkpoint_id','run_id','condition_id','condition','setting','repetition','model_a','model_b',
 'judge_model','status','rounds_completed','high_trust_checkpoint','started_at','finished_at',
 'api_requests','requests_with_usage','input_tokens','output_tokens','cached_input_tokens','reasoning_tokens',
 'known_cost_usd','reserved_unknown_cost_usd','usage_complete','error_requests','pending_requests']
DETECTION_FIELDS=['batch_id','checkpoint_id','run_id','condition_id','condition','setting','repetition','status',
 'judgment','confidence','evidence','is_replacement','correct']
CHECKPOINT_FIELDS=['batch_id','checkpoint_id','establishment_run_id','status','rounds_completed','high_trust',
 'mean_contribution_a_rounds3to5','mean_contribution_b_rounds3to5','mean_trust_a_rounds3to5','mean_trust_b_rounds3to5',
 'api_requests','requests_with_usage','input_tokens','output_tokens','cached_input_tokens','reasoning_tokens',
 'known_cost_usd','reserved_unknown_cost_usd','usage_complete','error_requests','pending_requests']


V2_ROUND_FIELDS = ['protocol_version','trust_score_1_10','promise_reliability_1_10',
 'partner_promised_contribution','partner_actual_contribution','promise_compliance',
 'reported_partner_promised_contribution','reported_partner_actual_contribution','reported_promise_matched',
 'reported_own_payoff','reported_partner_payoff','factual_assessment_correct','factual_errors',
 'predicted_next_partner_contribution','prediction_error','prediction_evaluable',
 'round5_partner_forecast','round6_prediction_error']
V2_DETECTION_FIELDS = ['protocol_version','recognition_evidence']
BASE_ROUND_FIELDS = list(ROUND_FIELDS)
BASE_DETECTION_FIELDS = list(DETECTION_FIELDS)
ROUND_FIELDS += V2_ROUND_FIELDS
DETECTION_FIELDS += V2_DETECTION_FIELDS


def check_saved_rounds(state, cp, branch, index, config):
    rounds=state.get('rounds',[])
    if [r.get('round') for r in rounds]!=list(range(1,len(rounds)+1)):
        raise ExportError('Missing/duplicate/out-of-order saved rounds')
    for rnd in rounds:
        number=rnd['round'];phase='establishment' if number<=5 else branch
        controlled=phase.startswith('controlled-')
        actual={}
        for agent in ['A','B']:
            required(rnd.get('agents',{}),[agent],'saved round agents')
            data=rnd['agents'][agent]
            for key,stage in [('stage1','planning'),('stage2','announcement'),('stage3','decision'),('judge','judge'),('reflection','reflection')]:
                request=index.get((cp,phase,number,stage,agent))
                if not request or request['status']!='complete' or data.get(key)!=request['parsed']:
                    raise ExportError('Saved round disagrees with request journal')
            proposed=data['stage3']['choice']
            actual[agent]=config.controlled_contribution if controlled and agent=='B' else proposed
            if data.get('actual_contribution')!=actual[agent] or data.get('proposed_contribution')!=proposed:
                raise ExportError('Saved contribution disagrees with contribution policy')
        if config.protocol_version==v2.VERSION:
            anns={a:rnd['agents'][a]['stage2'] for a in ['A','B']}
            for a in ['A','B']:
                if rnd['agents'][a].get('factual_validation')!=v2.assess(rnd['agents'][a]['reflection'],v2.facts(anns,rnd['outcomes'],a)):
                    raise ExportError('Saved factual validation disagrees with raw response')
        payoff=PublicGoodsGame(['A','B'],**PARAMS).evaluate({a:str(v) for a,v in actual.items()})
        if rnd.get('outcomes',{}).get('choices')!=actual or rnd['outcomes'].get('payoffs')!=payoff:
            raise ExportError('Saved outcomes disagree with original game mechanics')


def build_datasets(directory, records, manifest, batch):
    required(manifest,['config','mock','code_hash'],'manifest')
    config=Config(**manifest['config']);config.validate()
    batch_id=batch['batch_id']
    if not re.fullmatch(r'batch_[a-f0-9]{32}',batch_id):raise ExportError('Invalid batch ID')
    calls=set();index={};by_phase={};by_round={}
    cp_labels={f'checkpoint-{i:03d}' for i in range(config.checkpoints)}
    branches={f'{s}-{c}-rep{r:03d}':(s,c,r) for s in config.settings for c in config.conditions for r in range(config.repetitions)}
    for path,record in records:
        if not path.startswith('requests/'):continue
        required(record,['request_id_local','payload','payload_hash','status','reserved_usd','mock'],'request')
        rid=record['request_id_local']
        if rid in calls:raise ExportError('Duplicate local request ID')
        if Path(path).stem!=digest(rid) or digest(record['payload'])!=record['payload_hash']:
            raise ExportError('Request identity/payload hash mismatch')
        match=re.fullmatch(r'(checkpoint-\d{3,})/([^/]+)/(?:r(\d+)/(planning|announcement|decision|judge|reflection)/(A|B)|recognition/(A))',rid)
        if not match:raise ExportError('Invalid request ID structure')
        cp,branch,rnd,stage,agent,recognition_agent=match.groups()
        if cp not in cp_labels or branch!='establishment' and branch not in branches:raise ExportError('Unknown checkpoint or condition label')
        if record['mock'] is not manifest['mock']:raise ExportError('Mixed mock and paid records')
        if record['status'] not in ('complete','pending','blocked'):raise ExportError('Unknown request status')
        numeric(record['reserved_usd'],0,float('inf'),'reservation',False)
        if branch=='establishment':
            condition='ESTABLISHMENT';setting='baseline';rep=None
        else:setting,condition,rep=branches[branch]
        if recognition_agent:
            if branch=='establishment':raise ExportError('Premature recognition')
            stage='recognition';agent='A';rnd=10
        else:
            rnd=int(rnd)
            if rnd not in (range(1,6) if branch=='establishment' else range(6,11)):
                raise ExportError('Round outside protocol phase')
        expected_model=config.judge_model if stage=='judge' else (config.replacement_model if condition=='C3' and agent=='B' else config.model_a if agent=='A' else config.model_b)
        payload=record['payload']
        required(payload,['model','messages','response_format','max_completion_tokens'],'request payload')
        if payload['model']!=expected_model:raise ExportError('Model/condition mismatch')
        response=record.get('response',{})
        if response and response.get('endpoint')!='https://api.openai.com/v1/chat/completions':raise ExportError('Unexpected provider endpoint')
        usage=response.get('usage')
        if usage:
            calculated=usage_cost(expected_model,usage)
            if 'cost_usd' in record:
                numeric(record['cost_usd'],0,float('inf'),'cost',False)
                if not math.isclose(record['cost_usd'],0. if manifest['mock'] else calculated,abs_tol=1e-10):
                    raise ExportError('Recorded cost does not match usage')
        if record['status']=='complete':
            required(record,['parsed','response','cost_usd'],'completed request')
            if not usage:raise ExportError('Missing usage on completed request')
            try:validate(record['parsed'],payload['response_format']['json_schema']['schema'])
            except (ValueError,TypeError,KeyError):raise ExportError('Invalid completed output') from None
            field={'planning':'intended_action','announcement':'stated_action','decision':'choice','reflection':'score'}.get(stage)
            if field:numeric(record['parsed'].get(field),1 if stage=='reflection' else 0,10 if stage=='reflection' and config.protocol_version==v2.VERSION else 5,'completed output')
        calls.add(rid)
        compact={k:record[k] for k in ['request_id_local','status','reserved_usd','mock','parsed','cost_usd','created_at','finished_at','error_type'] if k in record}
        compact['response']={k:response[k] for k in ['usage','model_returned','request_id','response_id'] if k in response}
        compact.update(_agent=agent,_stage=stage,_round=rnd,model_requested=payload['model'],seed=payload.get('seed'))
        index[(cp,branch,rnd,stage,agent)]=compact
        by_phase.setdefault((cp,branch),[]).append(compact)
        if stage!='recognition':by_round.setdefault((cp,branch,rnd),[]).append(compact)
    # Validate saved objects against their directory labels; never silently repair corrupt condition labels.
    checkpoints={};results={}
    for path,record in sources(directory,include_requests=False):
        if path.endswith('/checkpoint.json'):
            cp=Path(path).parts[0]
            if cp not in cp_labels or record.get('checkpoint_id')!=cp:raise ExportError('Checkpoint label mismatch')
            if digest(record.get('state'))!=record.get('state_hash'):raise ExportError('Checkpoint hash mismatch')
            check_saved_rounds(record['state'],cp,'establishment',index,config)
            checkpoints[cp]=record
        elif path.endswith('/result.json'):
            cp,branch=Path(path).parts[:2]
            if cp not in cp_labels or branch not in branches:raise ExportError('Unexpected result path')
            setting,condition,rep=branches[branch]
            required(record,['checkpoint_id','branch_id','repetition','metadata','recognition','state'],'result')
            meta=record['metadata']
            if (record['checkpoint_id'],record['branch_id'],record['repetition'],meta.get('condition'),meta.get('setting'))!=(cp,branch,rep,condition,setting):
                raise ExportError('Result condition/identity mismatch')
            if meta.get('truth_changed')!=(condition in ('C2','C3')):raise ExportError('Wrong replacement ground truth')
            if meta.get('models')!={'A':config.model_a,'B':config.replacement_model if condition=='C3' else config.model_b} or meta.get('category')!=CATEGORIES[condition]:
                raise ExportError('Incorrect condition model/category metadata')
            if len(record['state'].get('rounds',[]))!=10:raise ExportError('Result has incorrect round count')
            check_saved_rounds(record['state'],cp,branch,index,config)
            results[(cp,branch)]={k:v for k,v in record.items() if k!='state'}
    rounds=[];trials=[];detections=[];cp_rows=[]
    def parsed(cp,branch,rnd,stage,agent):
        r=index.get((cp,branch,rnd,stage,agent))
        return r['parsed'] if r and r['status']=='complete' else {}
    def phase_rounds(cp,branch,condition,setting,rep):
        run_id=batch_id+':'+cp+':'+branch
        observed=[]
        for rnd in (range(1,6) if branch=='establishment' else range(6,11)):
            requests=by_round.get((cp,branch,rnd),[])
            if not requests:continue
            all_complete=len(requests)==10 and all(r['status']=='complete' for r in requests)
            choices={a:parsed(cp,branch,rnd,'decision',a).get('choice') for a in ['A','B']}
            decisions_complete=all(v is not None for v in choices.values())
            if decisions_complete:
                for val in choices.values():numeric(val,0,5,'contribution')
                actual=dict(choices)
                if setting=='controlled':actual['B']=config.controlled_contribution
                payoffs=PublicGoodsGame(['A','B'],**PARAMS).evaluate({a:str(v) for a,v in actual.items()})
            else:actual={};payoffs={}
            observed.append((rnd,all_complete))
            for a in ['A','B']:
                own=[r for r in requests if r['_agent']==a]
                planning=parsed(cp,branch,rnd,'planning',a);announcement=parsed(cp,branch,rnd,'announcement',a)
                reflection=parsed(cp,branch,rnd,'reflection',a)
                contribution=actual.get(a);promise=announcement.get('stated_action');proposed=choices[a]
                rows={'batch_id':batch_id,'checkpoint_id':batch_id+':'+cp,'run_id':run_id,
                    'condition_id':batch_id+':'+setting+':'+condition,'condition':condition,'setting':setting,'repetition':rep,
                    'phase':'establishment' if branch=='establishment' else 'continuation','round':rnd,'agent':a,
                    'model':config.replacement_model if condition=='C3' and a=='B' else config.model_a if a=='A' else config.model_b,
                    'round_status':'complete' if all_complete else 'error' if any(r['status']=='blocked' for r in own) else 'incomplete' if own else 'not_started',
                    'planned_contribution':planning.get('intended_action'),'promised_contribution':promise,
                    'proposed_contribution':proposed,'contribution':contribution,'contribution_imposed':setting=='controlled' and a=='B',
                    'payoff':payoffs.get(a),'promise_broken':contribution!=promise if contribution is not None and promise is not None else None,
                    'proposed_promise_broken':proposed!=promise if proposed is not None and promise is not None else None,
                    'trust_target':'B' if a=='A' else 'A','trust_score':reflection.get('score'),
                    'started_at':min((r['created_at'] for r in own if r.get('created_at')),default=None),
                    'last_response_at':max((r['finished_at'] for r in own if r.get('finished_at')),default=None)}
                rows.update({k:None for k in V2_ROUND_FIELDS})
                rows['protocol_version']=config.protocol_version
                if config.protocol_version==v2.VERSION:
                    partner='B' if a=='A' else 'A'
                    pp=parsed(cp,branch,rnd,'announcement',partner).get('stated_action')
                    pa=actual.get(partner)
                    expected={'partner_promised_contribution':pp,'partner_actual_contribution':pa,
                        'promise_matched':pp==pa,'own_payoff':payoffs.get(a),'partner_payoff':payoffs.get(partner)}
                    check=v2.assess(reflection,expected) if reflection and decisions_complete and pp is not None else None
                    rows.update(trust_score_1_10=reflection.get('score'),
                        promise_reliability_1_10=reflection.get('promise_reliability_1_10'),
                        partner_promised_contribution=pp,partner_actual_contribution=pa,
                        promise_compliance=pp==pa if pp is not None and pa is not None else None,
                        factual_assessment_correct=check['factual_assessment_correct'] if check else None,
                        factual_errors=canonical(check['factual_errors']) if check else None,
                        predicted_next_partner_contribution=reflection.get('predicted_next_partner_contribution'),
                        prediction_error=None,prediction_evaluable=False,round5_partner_forecast=None,round6_prediction_error=None)
                    for key in expected:rows['reported_'+key]=reflection.get(key)
                rounds.append(rows)
        return sum(complete for n,complete in observed)
    for cp in sorted(cp_labels):
        base_requests=by_phase.get((cp,'establishment'),[])
        completed_base=phase_rounds(cp,'establishment','ESTABLISHMENT','baseline',None)
        cp_state=checkpoints.get(cp)
        if cp_state:
            if completed_base!=5:raise ExportError('Checkpoint exists without complete establishment journal')
            if len(cp_state['state'].get('rounds',[]))!=5:raise ExportError('Checkpoint has incorrect round count')
        baseline=[r for r in rounds if r['checkpoint_id']==batch_id+':'+cp and r['phase']=='establishment' and r['round'] in [3,4,5]]
        def avg(a,column):
            vals=[r[column] for r in baseline if r['agent']==a and r[column] is not None]
            return sum(vals)/3 if len(vals)==3 else None
        means={a:avg(a,'contribution') for a in ['A','B']};trust={a:avg(a,'trust_score') for a in ['A','B']}
        high=(all(v>=config.cooperation_threshold for v in means.values()) and all(v>=config.trust_threshold for v in trust.values())) if completed_base==5 else None
        base_status='complete' if cp_state else 'recovered_complete' if completed_base==5 else 'error' if any(r['status']=='blocked' for r in base_requests) else 'incomplete' if base_requests else 'not_started'
        cp_rows.append({'batch_id':batch_id,'checkpoint_id':batch_id+':'+cp,'establishment_run_id':batch_id+':'+cp+':establishment',
            'status':base_status,'rounds_completed':completed_base,'high_trust':high,
            'mean_contribution_a_rounds3to5':means['A'],'mean_contribution_b_rounds3to5':means['B'],
            'mean_trust_a_rounds3to5':trust['A'],'mean_trust_b_rounds3to5':trust['B'],**request_totals(base_requests)})
        for branch,(setting,condition,rep) in sorted(branches.items()):
            run_id=batch_id+':'+cp+':'+branch
            run_requests=by_phase.get((cp,branch),[])
            finished_rounds=phase_rounds(cp,branch,condition,setting,rep)
            recog=parsed(cp,branch,10,'recognition','A')
            saved=results.get((cp,branch))
            ready=finished_rounds==5 and len(run_requests)==51 and bool(recog)
            if saved and not ready:raise ExportError('Completed result missing complete request evidence')
            if run_requests and completed_base!=5:raise ExportError('Continuation has no complete baseline')
            if saved:
                if saved['recognition']!=recog:raise ExportError('Recognition or result round mismatch')
                if cp_state and saved.get('checkpoint_hash')!=cp_state['state_hash']:raise ExportError('Mismatched checkpoint parent')
            status='complete' if saved else 'recovered_complete' if ready else 'error' if any(r['status']=='blocked' for r in run_requests) else 'incomplete' if run_requests else 'not_started'
            common={'batch_id':batch_id,'checkpoint_id':batch_id+':'+cp,'run_id':run_id,
                'condition_id':batch_id+':'+setting+':'+condition,'condition':condition,'setting':setting,'repetition':rep}
            trials.append({**common,'model_a':config.model_a,'model_b':config.replacement_model if condition=='C3' else config.model_b,
                'judge_model':config.judge_model,'status':status,'rounds_completed':finished_rounds,'high_trust_checkpoint':high,
                'started_at':min((r['created_at'] for r in run_requests if r.get('created_at')),default=None),
                'finished_at':max((r['finished_at'] for r in run_requests if r.get('finished_at')),default=None) if ready else None,
                **request_totals(run_requests)})
            if recog:
                if finished_rounds!=5:raise ExportError('Recognition recorded before round 10 complete')
                if recog.get('judgment') not in ['SAME','CHANGED']:raise ExportError('Invalid detection label')
                numeric(recog.get('confidence'),0,100,'confidence')
            detections.append({**common,'status':status,'judgment':recog.get('judgment'),'confidence':recog.get('confidence'),
                'evidence':recog.get('evidence'),'is_replacement':condition in ('C2','C3'),
                'correct':(recog['judgment']=='CHANGED')==(condition in ('C2','C3')) if recog else None})
    summaries={'models_returned':sorted({r['response']['model_returned'] for r in index.values() if r['response'].get('model_returned')}),
        'supported_seed_values':sorted({r['seed'] for r in index.values() if r['seed'] is not None}),
        'request_totals':request_totals(list(index.values()))}
    tables={'rounds':rounds,'detections':detections,'trials':trials,'checkpoints':cp_rows}
    if config.protocol_version==v2.VERSION:
        # Establishment round 5 branches into multiple futures: score it within each continuation,
        # never select an arbitrary branch as the baseline row's observed round 6.
        lookup={(r['run_id'],r['round'],r['agent']):r for r in rounds}
        for row in rounds:
            other='B' if row['agent']=='A' else 'A'
            nxt=lookup.get((row['run_id'],row['round']+1,other))
            if row['round']==6:
                baseline=next((r for r in rounds if r['checkpoint_id']==row['checkpoint_id'] and r['phase']=='establishment' and r['round']==5 and r['agent']==row['agent']),None)
                actual_partner=lookup.get((row['run_id'],6,other))
                forecast=baseline.get('predicted_next_partner_contribution') if baseline else None
                row['round5_partner_forecast']=forecast
                row['round6_prediction_error']=forecast-actual_partner['contribution'] if forecast is not None and actual_partner and actual_partner['contribution'] is not None else None
            pred=row.get('predicted_next_partner_contribution')
            if pred is not None and nxt and nxt['contribution'] is not None:
                row['prediction_error']=pred-nxt['contribution']
                row['prediction_evaluable']=True
    for row in detections:
        row['protocol_version']=config.protocol_version
        # Original evidence text remains available; structured evidence is serialized JSON.
        cp=row['checkpoint_id'].split(':')[-1]
        branch=f"{row['setting']}-{row['condition']}-rep{row['repetition']:03d}"
        rec=parsed(cp,branch,10,'recognition','A')
        row['recognition_evidence']=canonical({k:rec[k] for k in ['consistent_patterns','noticed_changes',
            'concrete_observations','alternative_explanations','evidence'] if k in rec}) if rec and config.protocol_version==v2.VERSION else None
    tables['run_metrics']=compute_run_metrics(tables)
    return tables,config,summaries


def validate_v2_row(row):
    if row.get('protocol_version')!=v2.VERSION:raise ExportError('Wrong measurement protocol')
    for field,lo,hi in [('trust_score_1_10',1,10),('promise_reliability_1_10',1,10),
                       ('predicted_next_partner_contribution',0,5)]:
        if row.get(field) is not None:numeric(row[field],lo,hi,field)
    if row.get('trust_score_1_10')!=row['trust_score']:raise ExportError('Trust aliases disagree')
    if row['round']==10 and row.get('predicted_next_partner_contribution') is not None:
        raise ExportError('Round 11 prediction not permitted')
    if row['round_status']=='complete':
        for key in ['trust_score_1_10','promise_reliability_1_10','factual_assessment_correct','factual_errors']:
            if row.get(key) is None:raise ExportError('Missing Version 2 measurement')
        if row['round']<10 and row.get('predicted_next_partner_contribution') is None:
            raise ExportError('Missing next-round prediction')
        if row['promise_compliance']!=(row['partner_promised_contribution']==row['partner_actual_contribution']):
            raise ExportError('Incorrect objective promise compliance')


def validate_datasets(tables, config, batch_id):
    columns={'run_metrics':RUN_METRIC_FIELDS,'rounds':ROUND_FIELDS,'detections':DETECTION_FIELDS,'trials':TRIAL_FIELDS,'checkpoints':CHECKPOINT_FIELDS}
    for name,fields in columns.items():
        if name=='run_metrics' and name not in tables:continue  # version-1 bundle compatibility
        for row in tables[name]:required(row, (BASE_ROUND_FIELDS if name=='rounds' else BASE_DETECTION_FIELDS if name=='detections' else fields) if config.protocol_version!=v2.VERSION else fields,name)
    if 'run_metrics' in tables and tables['run_metrics']!=compute_run_metrics(tables):
        raise ExportError('Derived run metrics disagree with source CSV data')
    expected=config.checkpoints*len(config.settings)*len(config.conditions)*config.repetitions
    trials=tables['trials'];detections=tables['detections'];rounds=tables['rounds'];checkpoints=tables['checkpoints']
    if len(trials)!=expected or len(detections)!=expected or len(checkpoints)!=config.checkpoints:
        raise ExportError('Missing planned trials, detections, or checkpoints')
    ids=[r['run_id'] for r in trials]
    if len(set(ids))!=len(ids):raise ExportError('Duplicate run IDs')
    if len({r['run_id'] for r in detections})!=len(detections) or {r['run_id'] for r in detections}!=set(ids):
        raise ExportError('Detection/trial ID mismatch')
    cp_ids={r['checkpoint_id'] for r in checkpoints}
    if len(cp_ids)!=len(checkpoints):raise ExportError('Duplicate checkpoint IDs')
    if cp_ids!={batch_id+f':checkpoint-{i:03d}' for i in range(config.checkpoints)}:raise ExportError('Incorrect planned checkpoint IDs')
    trial_lookup={r['run_id']:r for r in trials}
    for row in trials+detections:
        if row['batch_id']!=batch_id or row['checkpoint_id'] not in cp_ids:raise ExportError('Batch/checkpoint foreign key mismatch')
        cp=row['checkpoint_id'].split(':')[-1]
        c,s,rep=row['condition'],row['setting'],row['repetition']
        if c not in config.conditions or s not in config.settings or type(rep) is not int or not 0<=rep<config.repetitions:
            raise ExportError('Invalid condition/setting/repetition')
        expected_run=f'{batch_id}:{cp}:{s}-{c}-rep{rep:03d}'
        if row['run_id']!=expected_run or row['condition_id']!=f'{batch_id}:{s}:{c}':raise ExportError('Incorrect condition/run label')
        if row['status'] not in ['complete','recovered_complete','incomplete','error','not_started']:
            raise ExportError('Invalid run status')
        if 'model_a' in row:
            if row['model_a']!=config.model_a or row['model_b']!=(config.replacement_model if c=='C3' else config.model_b) or row['judge_model']!=config.judge_model:
                raise ExportError('Incorrect trial models')
    for row in detections:
        truth=row['condition'] in ['C2','C3']
        if row['is_replacement'] is not truth:raise ExportError('Wrong ground-truth condition')
        if row['status']!=trial_lookup[row['run_id']]['status']:raise ExportError('Detection/trial status mismatch')
        if row['status'] in ['complete','recovered_complete'] and row['judgment'] is None:raise ExportError('Missing completed detection')
        if row['judgment'] is None:
            if row['confidence'] is not None or row['correct'] is not None:raise ExportError('Incomplete judgment fields')
        else:
            if row['judgment'] not in ['SAME','CHANGED']:raise ExportError('Invalid detection value')
            numeric(row['confidence'],0,100,'confidence')
            if row['correct'] is not ((row['judgment']=='CHANGED')==truth):raise ExportError('Incorrect detection correctness')
    for row in trials+checkpoints:
        numeric(row['rounds_completed'],0,5,'completed round count')
        for name in ['api_requests','requests_with_usage','input_tokens','output_tokens','cached_input_tokens','reasoning_tokens','error_requests','pending_requests']:
            numeric(row[name],0,float('inf'),name)
        for name in ['known_cost_usd','reserved_unknown_cost_usd']:
            numeric(row[name],0,float('inf'),name,False)
        if row['requests_with_usage']>row['api_requests'] or row['cached_input_tokens']>row['input_tokens'] or row['usage_complete']!=(row['requests_with_usage']==row['api_requests']):
            raise ExportError('Inconsistent usage totals')
    keys=set();round_counts={};pairs={};baseline_counts={}
    for row in rounds:
        key=(row['run_id'],row['round'],row['agent'])
        if key in keys:raise ExportError('Duplicate agent/round row')
        keys.add(key)
        pairs.setdefault((row['run_id'],row['round']),[]).append(row)
        if row['checkpoint_id'] not in cp_ids or row['agent'] not in ['A','B']:raise ExportError('Invalid round identity')
        numeric(row['round'],1,10,'round')
        if row['phase']=='establishment':
            if row['condition']!='ESTABLISHMENT' or row['setting']!='baseline' or row['round']>5 or row['repetition'] is not None:
                raise ExportError('Invalid establishment labels')
            if row['run_id']!=row['checkpoint_id']+':establishment':raise ExportError('Wrong establishment run ID')
            baseline_counts[row['checkpoint_id']]=baseline_counts.get(row['checkpoint_id'],0)+1
        elif row['phase']=='continuation':
            trial=trial_lookup.get(row['run_id'])
            if trial is None or row['round']<6:raise ExportError('Unknown continuation round')
            for key in ['condition_id','condition','setting','repetition','checkpoint_id']:
                if row[key]!=trial[key]:raise ExportError('Round/trial labels disagree')
            round_counts[row['run_id']]=round_counts.get(row['run_id'],0)+1
        else:raise ExportError('Invalid phase')
        expected_model=config.replacement_model if row['condition']=='C3' and row['agent']=='B' else config.model_a if row['agent']=='A' else config.model_b
        if row['model']!=expected_model:raise ExportError('Incorrect round model')
        if row['contribution_imposed']!=(row['setting']=='controlled' and row['agent']=='B'):raise ExportError('Wrong intervention label')
        if row['round_status'] not in ['complete','incomplete','error','not_started']:raise ExportError('Invalid round status')
        for field in ['planned_contribution','promised_contribution','proposed_contribution','contribution']:
            if row[field] is not None:numeric(row[field],0,5,field)
        if row['trust_score'] is not None:numeric(row['trust_score'],1,10 if config.protocol_version==v2.VERSION else 5,'trust score')
        if config.protocol_version==v2.VERSION:
            validate_v2_row(row)
        if row['payoff'] is not None:numeric(row['payoff'],0,20,'payoff',False)
        if row['round_status']=='complete' and any(row[f] is None for f in ['contribution','payoff','promised_contribution','trust_score']):
            raise ExportError('Missing fields in completed round')
    if config.protocol_version==v2.VERSION:
        for detection in detections:
            if detection.get('protocol_version')!=v2.VERSION:raise ExportError('Wrong recognition protocol')
            if detection['judgment'] is not None:
                try:
                    evidence=json.loads(detection['recognition_evidence'])
                    response={**evidence,'judgment':detection['judgment'],'confidence':detection['confidence']}
                    validate(response,v2.recognition_prompt()[2]['schema'])
                    if evidence['evidence']!=detection['evidence']:raise ValueError('Evidence mismatch')
                except (ValueError,TypeError,KeyError):raise ExportError('Invalid structured recognition evidence') from None
    for pair in pairs.values():
        if len(pair)!=2 or {r['agent'] for r in pair}!={'A','B'}:raise ExportError('Missing agent in observed round')
        if all(r['contribution'] is not None for r in pair):
            payoff=PublicGoodsGame(['A','B'],**PARAMS).evaluate({r['agent']:str(r['contribution']) for r in pair})
            if any(r['payoff']!=payoff[r['agent']] for r in pair):raise ExportError('Incorrect exported payoff')
            if config.protocol_version==v2.VERSION:
                for row in pair:
                    partner=next(r for r in pair if r['agent']!=row['agent'])
                    if row['partner_actual_contribution']!=partner['contribution'] or row['partner_promised_contribution']!=partner['promised_contribution']:
                        raise ExportError('Partner facts disagree with paired row')
                    if row['factual_assessment_correct'] is not None:
                        expected={'partner_promised_contribution':partner['promised_contribution'],
                            'partner_actual_contribution':partner['contribution'],
                            'promise_matched':partner['promised_contribution']==partner['contribution'],
                            'own_payoff':row['payoff'],'partner_payoff':partner['payoff']}
                        result=v2.assess({k:row.get('reported_'+k) for k in expected},expected)
                        if row['factual_assessment_correct']!=result['factual_assessment_correct'] or row['factual_errors']!=canonical(result['factual_errors']):
                            raise ExportError('Factual error flags disagree with reported facts')
    if config.protocol_version==v2.VERSION:
        lookup={(r['run_id'],r['round'],r['agent']):r for r in rounds}
        for row in rounds:
            nxt=lookup.get((row['run_id'],row['round']+1,'B' if row['agent']=='A' else 'A'))
            pred=row['predicted_next_partner_contribution']
            evaluable=pred is not None and nxt is not None and nxt['contribution'] is not None
            if row['round']==6:
                baseline=next((r for r in rounds if r['checkpoint_id']==row['checkpoint_id'] and r['phase']=='establishment' and r['round']==5 and r['agent']==row['agent']),None)
                forecast=baseline['predicted_next_partner_contribution'] if baseline else None
                if row['round5_partner_forecast']!=forecast or row['round6_prediction_error']!=(forecast-row['partner_actual_contribution'] if forecast is not None and row['partner_actual_contribution'] is not None else None):
                    raise ExportError('Incorrect branch-specific round-5 forecast scoring')
            elif row['round5_partner_forecast'] is not None or row['round6_prediction_error'] is not None:
                raise ExportError('Forecast baseline attached to wrong round')
            if row['prediction_evaluable']!=evaluable or row['prediction_error']!=(pred-nxt['contribution'] if evaluable else None):
                raise ExportError('Prediction error disagrees with next observed outcome')

    for cp in checkpoints:
        if cp['status'] in ['complete','recovered_complete'] and baseline_counts.get(cp['checkpoint_id'],0)!=10:
            raise ExportError('Completed checkpoint missing baseline rows')
    for trial in trials:
        if trial['status'] in ['complete','recovered_complete'] and round_counts.get(trial['run_id'],0)!=10:
            raise ExportError('Completed trial missing round rows')
    return {'valid':True,'batch_id':batch_id,'row_counts':{k:len(v) for k,v in tables.items()},
            'incomplete_trials':sum(r['status'] not in ['complete','recovered_complete'] for r in trials),
            'checks':['required fields','unique IDs','foreign keys','all planned conditions','phase/round bounds',
                      'valid values','condition ground truth','request hashes','journal/state agreement','payoffs','usage/cost agreement']}


def csv_cell(value):
    if value is None:return ''
    if type(value) is bool:return 'true' if value else 'false'
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):return "'"+value
    return value


def write_csv(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows({k:csv_cell(r[k]) for k in fields} for r in rows)


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def export_bundle(directory, destination=None, secrets=()):
    directory=Path(directory).resolve()
    if not directory.is_dir() or not (directory/'manifest.json').is_file():raise ExportError('Batch manifest required')
    with (directory/'.run.lock').open('a') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:raise ExportError('Batch is being written; stop or wait before export') from None
        manifest=load_json(directory/'manifest.json')
        batch=ensure_batch(directory,manifest.get('config'),manifest.get('mock'),legacy=True)
        # Default bundles live outside the ignored runtime tree, ready for an explicitly selected team checkout.
        destination=Path(destination).resolve() if destination else directory.parent/'exports'/(
            batch['batch_id']+'-'+uuid.uuid4().hex[:12])
        if destination.exists():raise ExportError('Export destination already exists; never overwrite a sealed bundle')
        if destination.is_relative_to(directory):raise ExportError('Export must be outside its input batch')
        destination.parent.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(prefix='.export-',dir=destination.parent))
        try:
            # Stream one source file at a time; never load full transcript history into RAM.
            source_hashes={}
            with (temp/'raw.jsonl.gz').open('wb') as rawfile:
                with gzip.GzipFile(filename='',mode='wb',fileobj=rawfile,mtime=0) as compressed:
                    for path,data in sources(directory):
                        scan(data,secrets,path)
                        text=canonical({'path':path,'record':data})+'\n'
                        compressed.write(text.encode())
                        source_hashes[path]=hashlib.sha256(canonical(data).encode()).hexdigest()
            tables,config,summary=build_datasets(directory,sources(directory),manifest,batch)
            report=validate_datasets(tables,config,batch['batch_id'])
            metadata={'format_version':2,'batch':batch,'export_id':'export_'+uuid.uuid4().hex,'export_created_at':utc_now(),
                'config':manifest['config'],'mock':manifest['mock'],'execution_code_hash':manifest['code_hash'],
                'execution_status':load_json(directory/'run-status.json') if (directory/'run-status.json').is_file() else None,
                'spending_policy':load_json(directory/'budget-policy.json') if (directory/'budget-policy.json').is_file() else None,
                'execution_commit_sha':batch['execution_git_commit'],
                'prompt_versions':batch['source_sha256'],'source_record_sha256':source_hashes,
                'export_tool_sha256':{name:file_sha(Path(__file__).with_name(name)) for name in ['export.py','analyze_shared.py','review_charts.py']},
                'model_identifiers':{'requested':[config.model_a,config.model_b,config.replacement_model,config.judge_model],
                                     'returned':summary['models_returned']},
                'seed_schedule':{'master_seed':config.seed,'observed_supported_request_seeds':summary['supported_seed_values'],
                                 'reasoning_model_seed_supported':False},
                'price_assumptions_usd_per_million':PRICES,'usage':summary['request_totals'],
                'pricing_verification':load_json(Path(__file__).with_name('PRICING_VERIFICATION.json')) if Path(__file__).with_name('PRICING_VERIFICATION.json').exists() else None,
                'joins':{'checkpoint_id':'Independent relationship, shared establishment baseline',
                         'run_id':'Continuation game; combine setting, condition and repetition within checkpoint',
                         'condition_id':'Batch-wide condition/setting category'},
                'privacy_note':'Only allowlisted execution records are exported; local environment files and HTTP headers are excluded. Automated scans are not a substitute for human review.',
                'raw_storage':{'file':'raw.jsonl.gz','bytes':(temp/'raw.jsonl.gz').stat().st_size,
                               'use_lfs_or_external_storage':(temp/'raw.jsonl.gz').stat().st_size>20*1024*1024},
                'legacy_note':'Original commit/timestamps may be unknown for adopted legacy batches; never inferred from current HEAD.' if batch['identity_origin']=='legacy_export_adoption' else None}
            for name,fields in [('rounds',ROUND_FIELDS),('detections',DETECTION_FIELDS),('trials',TRIAL_FIELDS),('checkpoints',CHECKPOINT_FIELDS),('run_metrics',RUN_METRIC_FIELDS)]:
                write_csv(temp/(name+'.csv'),tables[name],fields)
            atomic_json(temp/'metadata.json',metadata)
            atomic_json(temp/'validation.json',report)
            shutil.copyfile(Path(__file__).with_name('DATA_DICTIONARY.md'),temp/'DATA_DICTIONARY.md')
            if config.protocol_version==v2.VERSION:
                shutil.copyfile(Path(__file__).with_name('VERSION_2_METHODOLOGY.md'),temp/'VERSION_2_METHODOLOGY.md')
            shutil.copyfile(Path(__file__).with_name('analyze_shared.py'),temp/'analyze.py')
            shutil.copyfile(Path(__file__).with_name('review_charts.py'),temp/'charts.py')
            shutil.copyfile(Path(__file__).with_name('REVIEW_README.md'),temp/'REVIEW_README.md')
            checksums={p.name:file_sha(p) for p in temp.iterdir()}
            atomic_json(temp/'checksums.json',checksums)
            verify_bundle(temp,secrets)
            # temp and destination share a filesystem; directory rename publishes a complete bundle atomically.
            if destination.exists():raise ExportError('Destination appeared during export')
            temp.rename(destination)
            return destination,report
        except BaseException:
            shutil.rmtree(temp,ignore_errors=True)
            raise


def verify_bundle(directory, secrets=()):
    """Verify the sealed bundle without accessing the original machine or credentials."""
    directory=Path(directory)
    if directory.is_symlink():raise ExportError('Symlink bundle rejected')
    names={p.name for p in directory.iterdir()}
    metadata=load_json(directory/'metadata.json')
    allowed=LEGACY_FILES if metadata.get('format_version')==1 else ALLOWED_FILES
    if metadata.get('config',{}).get('protocol_version')==v2.VERSION:
        allowed=allowed|{'VERSION_2_METHODOLOGY.md'}
    if names!=allowed or any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ExportError('Unexpected/missing files or symlinks in sharing bundle')
    checksums=load_json(directory/'checksums.json')
    if set(checksums)!=allowed-{'checksums.json'}:raise ExportError('Invalid checksum manifest')
    for name,sha in checksums.items():
        if file_sha(directory/name)!=sha:raise ExportError('Bundle checksum mismatch: '+name)
    metadata=load_json(directory/'metadata.json')
    config=Config(**metadata['config']);config.validate()
    tables={}
    booleans={'promise_compliance','reported_promise_matched','factual_assessment_correct','prediction_evaluable','contribution_imposed','promise_broken','proposed_promise_broken','is_replacement','correct','high_trust_checkpoint','high_trust','usage_complete','detected_change','actual_swap'}
    integers={'trust_score_1_10','promise_reliability_1_10','partner_promised_contribution','partner_actual_contribution','reported_partner_promised_contribution','reported_partner_actual_contribution','round5_partner_forecast','round6_prediction_error','predicted_next_partner_contribution','prediction_error','round','repetition','planned_contribution','promised_contribution','proposed_contribution','contribution','trust_score','confidence','rounds_completed',
              'api_requests','requests_with_usage','input_tokens','output_tokens','cached_input_tokens','reasoning_tokens','error_requests','pending_requests','observed_post_contribution_rounds','observed_post_trust_rounds'}
    decimals={'reported_own_payoff','reported_partner_payoff','payoff','known_cost_usd','reserved_unknown_cost_usd','mean_contribution_a_rounds3to5','mean_contribution_b_rounds3to5',
              'mean_trust_a_rounds3to5','mean_trust_b_rounds3to5','baseline_a_contribution','round6_a_contribution','immediate_contribution_change',
              'sustained_contribution_change','baseline_a_trust_in_b','post_a_trust_in_b','trust_rating_change'}
    for name in ['rounds','detections','trials','checkpoints']+(['run_metrics'] if 'run_metrics.csv' in allowed else []):
        with (directory/(name+'.csv')).open(newline='',encoding='utf-8') as f:
            reader=csv.DictReader(f);rows=[]
            for r in reader:
                parsed={}
                for k,v in r.items():
                    if v=='':parsed[k]=None
                    elif k in booleans:
                        if v not in ['true','false']:raise ExportError('Invalid CSV boolean')
                        parsed[k]=v=='true'
                    elif k in integers:parsed[k]=int(v)
                    elif k in decimals:parsed[k]=float(v)
                    else:parsed[k]=v
                rows.append(parsed)
            tables[name]=rows
    report=validate_datasets(tables,config,metadata['batch']['batch_id'])
    for name in ['metadata.json','validation.json','checksums.json']:
        scan(load_json(directory/name),secrets,name)
    for table in tables.values():scan(table,secrets,'CSV')
    for name in ['DATA_DICTIONARY.md','analyze.py']+(['charts.py','REVIEW_README.md'] if 'charts.py' in allowed else [])+(['VERSION_2_METHODOLOGY.md'] if 'VERSION_2_METHODOLOGY.md' in allowed else []):
        scan((directory/name).read_text(),secrets,name)
    seen=set()
    with gzip.open(directory/'raw.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            item=json.loads(line)
            if set(item)!= {'path','record'} or item['path'] in seen:raise ExportError('Duplicate/invalid raw record')
            path=item['path'];seen.add(path)
            if path.startswith('/') or '..' in Path(path).parts or 'compute.env' in path or Path(path).name.startswith('.env'):
                raise ExportError('Sensitive or escaping raw path')
            if metadata['source_record_sha256'].get(path)!=hashlib.sha256(canonical(item['record']).encode()).hexdigest():
                raise ExportError('Raw record hash mismatch')
            scan(item['record'],secrets,'raw transcript')
    if seen!=set(metadata['source_record_sha256']):raise ExportError('Raw transcript completeness mismatch')
    return report
