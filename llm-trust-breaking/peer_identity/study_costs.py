"""Disjoint cost estimates and empirical projection for the fixed 200-trial study."""
from collections import defaultdict
import json
from pathlib import Path
from statistics import mean
from .inference import PRICES


def groups(checkpoints=25):
    return {('checkpoint_establishment','gpt-4o-mini'):40*checkpoints,
            ('continuations','gpt-4o-mini'):288*checkpoints,
            ('continuations','gpt-4.1-mini'):40*checkpoints,
            ('judging','gpt-5-mini'):90*checkpoints}


FULL_OUTPUT_TOKENS=2000
PRIMARY_INPUT_TOKENS=20000


def pricing_status():
    path=Path(__file__).with_name('PRICING_VERIFICATION.json')
    if not path.exists():return {'prices_live_verified':False}
    verified=json.loads(path.read_text())
    rates={r['model']:(r['input_per_million_usd'],r['cached_input_per_million_usd'],r['output_per_million_usd']) for r in verified['models']}
    return {'prices_live_verified':rates==PRICES and verified.get('live_verified') is True,
            'prices_verified_at_utc':verified['checked_at_utc'],
            'price_sources':[r['official_url'] for r in verified['models']]}


def estimate(input_tokens,output_tokens):
    rows=[]
    for (phase,model),count in groups().items():
        rate_in,_,rate_out=PRICES[model]
        rows.append({'phase':phase,'model':model,'requests':count,
                     'estimated_usd':count*(input_tokens*rate_in+output_tokens*rate_out)/1e6})
    return {'input_tokens_per_call':input_tokens,'output_tokens_per_call':output_tokens,
            'rows':rows,'total_usd':sum(r['estimated_usd'] for r in rows),**pricing_status()}


def refine(directory):
    """Real completed pilot only. Mock usage is never presented as actual cost evidence."""
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest['mock']:
        return {'projection_withheld':True,'reason':'Mock token usage is fabricated; no real pilot has been measured.'}
    cfg=manifest['config']
    expected={'model_a':'gpt-4o-mini','model_b':'gpt-4o-mini','replacement_model':'gpt-4.1-mini',
              'judge_model':'gpt-5-mini','repetitions':1,'conditions':['C0','C1','C2','C3'],
              'settings':['natural','controlled']}
    if any(cfg.get(k)!=v for k,v in expected.items()):raise ValueError('Pilot is not scientifically equivalent to the fixed study')
    completed=[]
    for cp in directory.glob('checkpoint-*/checkpoint.json'):
        if len(list(cp.parent.glob('*/result.json')))==8:completed.append(cp.parent.name)
    if len(completed)<2:raise ValueError('At least two complete independent pilot checkpoints required')
    observed=defaultdict(list);known=0.;attempts=0
    for p in (directory/'requests').glob('*.json'):
        r=json.loads(p.read_text());attempts+=1
        if r['status']!='complete' or not r.get('response',{}).get('usage'):
            raise ValueError('Resolve incomplete/error requests before an empirical projection')
        known+=r['cost_usd']
        stage=r['request_id_local'].split('/')[-2]
        phase='judging' if stage=='judge' else 'checkpoint_establishment' if '/establishment/' in r['request_id_local'] else 'continuations'
        usage=r['response']['usage'];model=r['payload']['model']
        observed[(phase,model)].append((usage['prompt_tokens'],usage['completion_tokens']))
    rows=[]
    for key,count in groups().items():
        values=observed[key]
        if not values:raise ValueError('Pilot lacks model/phase usage coverage')
        inp,out=mean(v[0] for v in values),mean(v[1] for v in values)
        rate_in,_,rate_out=PRICES[key[1]]
        remaining=count-len(values)
        if remaining<0:raise ValueError('Observed requests exceed the target design')
        predicted=remaining*(inp*rate_in+out*rate_out)/1e6
        # Explicit stress scenario, not a confidence interval from two relationships.
        stress_input=max(max(v[0] for v in values),inp*1.5)
        stress_output=min(FULL_OUTPUT_TOKENS,max(max(v[1] for v in values),out*1.5))
        full_input=max(24000 if cfg.get('protocol_version')=='publicgoods-peer-identity-v2' else PRIMARY_INPUT_TOKENS,stress_input)
        rows.append({'phase':key[0],'model':key[1],'observed_requests':len(values),'remaining_requests':remaining,
            'mean_input_tokens':inp,'mean_output_tokens':out,'remaining_uncached_estimate_usd':predicted,
            'remaining_stress_scenario_usd':remaining*(stress_input*rate_in+stress_output*rate_out)/1e6,
            'full_output_forecast_input_tokens_per_call':full_input,
            'full_output_forecast_output_tokens_per_call':FULL_OUTPUT_TOKENS,
            'remaining_full_output_forecast_usd':remaining*(full_input*rate_in+FULL_OUTPUT_TOKENS*rate_out)/1e6})
    policy=json.loads((directory/'budget-policy.json').read_text()) if (directory/'budget-policy.json').exists() else {}
    prior=policy.get('prior_spend_allowance_usd',0)
    return {'projection_withheld':False,**pricing_status(),'completed_checkpoints':len(completed),'observed_requests':attempts,
        'observed_cost_usd':known,'prior_spend_allowance_usd':prior,'rows':rows,
        'projected_total_including_prior_usd':prior+known+sum(r['remaining_uncached_estimate_usd'] for r in rows),
        'stress_total_including_prior_usd':prior+known+sum(r['remaining_stress_scenario_usd'] for r in rows),
        'primary_full_output_total_including_prior_usd':prior+known+sum(r['remaining_full_output_forecast_usd'] for r in rows),
        'protocol_version':cfg.get('protocol_version','publicgoods-peer-identity-v1'),
        'primary_note':'Remaining calls keep full 2000 output allowance and at least 20000 input tokens (24000 for V2), raised using observed maxima or 1.5x means. Actual completed-call costs replace their forecasts. No output reduction is inferred from short pilot replies.',
        'limitation':'Token-based projection at the versioned rates, not a billing guarantee or statistical confidence bound. Two relationships may underestimate variability; cache savings are not assumed.'}
