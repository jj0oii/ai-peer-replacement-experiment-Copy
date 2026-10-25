"""Offline-first Experiment 3.3 entry point. Default: estimate only, never inference."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import fcntl
import json
import math
import os
from pathlib import Path
import sys
import signal
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peer_identity.inference import DirectOpenAI, Journal, MockTransport, PRICES, StopRun, atomic_json
from peer_identity.protocol import Config, run_study, prepare_study
from peer_identity.analysis import analyze
from peer_identity.provenance import utc_now
from peer_identity.spending import study_budget, window_policy
from peer_identity.study_costs import estimate,pricing_status,FULL_OUTPUT_TOKENS,PRIMARY_INPUT_TOKENS


def cost_plan(config):
    config.validate()
    branches = len(config.settings) * len(config.conditions) * config.repetitions
    different = len(config.settings) * config.repetitions if 'C3' in config.conditions else 0
    # Five rounds: four play/reflection calls per agent and two judge calls per round.
    counts = {config.model_a: config.checkpoints * (40 + branches * 41 - different * 20),
              config.replacement_model: config.checkpoints * different * 20,
              config.judge_model: config.checkpoints * (10 + branches * 10)}
    scenarios = []
    for input_tokens, output_tokens in [(2000,150),(10000,300),(20000,500)]:
        cost = sum(count * (input_tokens * PRICES[m][0] + output_tokens * PRICES[m][2]) / 1e6 for m,count in counts.items())
        scenarios.append({'average_input_tokens_per_call': input_tokens, 'average_output_tokens_per_call': output_tokens,
                          'estimated_usd': round(cost, 4)})
    return {'planned_requests': config.calls(), 'requests_by_model': counts, 'scenarios': scenarios,
            'price_assumptions_usd_per_million': PRICES,
            **pricing_status(), 'retry_limit': 0,
            'primary_full_output_scenario':estimate(24000 if config.protocol_version.endswith('-v2') else PRIMARY_INPUT_TOKENS,FULL_OUTPUT_TOKENS),
            'warning': 'Scenarios, not confidence bounds. Growing memory can exceed these averages; pre-call reservations stop the run safely. Dollar estimate is not an exact provider-enforced cap.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['estimate','mock','paid'], default='estimate')
    p.add_argument('--output', type=Path, help='New empty batch directory; default is a UTC/UUID path')
    p.add_argument('--resume', action='store_true', help='Explicitly resume an incomplete batch without repeating completed requests')
    p.add_argument('--protocol-version', choices=['v1','v2'], default='v1')
    p.add_argument('--checkpoints', type=int, default=2)
    p.add_argument('--repetitions', type=int, default=1)
    p.add_argument('--checkpoint-start',type=int,default=0,help='First global checkpoint index in this batch')
    p.add_argument('--checkpoint-count',type=int,help='Number of checkpoints to execute in this batch, without changing the full study')
    p.add_argument('--batch-max-requests',type=int)
    p.add_argument('--batch-budget-usd',type=float)
    p.add_argument('--study-total-budget-usd',type=float)
    p.add_argument('--reserve-usd',type=float,default=10)
    p.add_argument('--prior-spend-usd',type=float,default=.01)
    p.add_argument('--export-after-batch',action='store_true')
    p.add_argument('--export-root',type=Path)
    p.add_argument('--conditions', nargs='+', default=['C0','C1','C2','C3'])
    p.add_argument('--settings', nargs='+', default=['natural','controlled'])
    p.add_argument('--seed', type=int, default=3303)
    p.add_argument('--temperature', type=float, default=1.0)
    p.add_argument('--controlled-contribution', type=int, default=3)
    p.add_argument('--max-requests', type=int)
    p.add_argument('--budget-usd', type=float)
    p.add_argument('--approve-paid', action='store_true', help='Use only after explicit user approval of this run and budget')
    args = p.parse_args()
    config = Config(protocol_version='publicgoods-peer-identity-'+args.protocol_version, trust_threshold=8.0 if args.protocol_version=='v2' else 4.0, checkpoints=args.checkpoints,repetitions=args.repetitions,conditions=args.conditions,
        settings=args.settings,seed=args.seed,temperature=args.temperature,controlled_contribution=args.controlled_contribution)
    try:
        config.validate()
    except ValueError as e:
        p.error(str(e))
    count=config.checkpoints-args.checkpoint_start if args.checkpoint_count is None else args.checkpoint_count
    if args.checkpoint_start<0 or count<1 or args.checkpoint_start+count>config.checkpoints:
        p.error('Invalid checkpoint execution window')
    scoped=args.checkpoint_count is not None or args.checkpoint_start!=0 or args.study_total_budget_usd is not None
    if args.study_total_budget_usd is not None and (args.budget_usd is None or not math.isfinite(args.study_total_budget_usd)):
        p.error('Study-wide budget requires a finite total and --budget-usd')
    plan=cost_plan(config)
    plan['execution_window']={'checkpoint_start':args.checkpoint_start,'checkpoint_count':count,
        'planned_requests':count*(50+len(config.conditions)*len(config.settings)*config.repetitions*51)}
    print(json.dumps(plan, indent=2))
    if args.mode == 'estimate':
        return
    if args.mode == 'paid' and args.protocol_version=='v2' and (args.study_total_budget_usd!=60 or args.prior_spend_usd < .4954921):
        p.error('Version 2 requires the unchanged $60 cumulative policy and at least $0.4954921 prior spending allowance')
    if args.mode == 'paid' and (not args.approve_paid or args.max_requests is None or args.budget_usd is None):
        p.error('Paid mode requires explicit --approve-paid, --max-requests, --budget-usd')
    if args.max_requests is not None and args.max_requests < 1 or args.budget_usd is not None and (not math.isfinite(args.budget_usd) or args.budget_usd <= 0):
        p.error('Positive request and dollar limits required')
    output = (args.output or Path('outputs/peer-identity') /
              ('batch-' + utc_now().replace(':','').replace('+','_') + '-' + uuid.uuid4().hex[:12])).resolve()
    if output.exists() and any(output.iterdir()) and not args.resume:
        p.error('Output directory already contains data; choose a new directory or explicit --resume')
    if args.resume and not (output/'manifest.json').exists():
        p.error('--resume requires an existing batch manifest')
    output.mkdir(parents=True,exist_ok=True)
    with (output / '.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another process owns this study directory')
        if (output/'run-status.json').exists() and json.loads((output/'run-status.json').read_text()).get('status')=='complete':
            print('Completed batch is immutable; no files or requests changed: ' + str(output))
            return
        attempt_id='attempt_'+uuid.uuid4().hex
        attempt={'attempt_id':attempt_id,'started_at':utc_now(),'status':'running',
                 'max_requests':args.max_requests or config.calls(),
                 'budget_usd':args.budget_usd if args.budget_usd is not None else 1_000_000,
                 'mock':args.mode=='mock','checkpoint_start':args.checkpoint_start,'checkpoint_count':count}
        attempt_file=output/'attempts'/(attempt_id+'.json')
        atomic_json(attempt_file,attempt)
        atomic_json(output/'run-status.json',attempt)
        journal=None
        def terminate(signum,frame):
            raise KeyboardInterrupt()
        prior_handler=signal.signal(signal.SIGTERM,terminate)
        try:
            prepare_study(config,output,args.mode=='mock')
            effective_budget=attempt['budget_usd']
            if args.study_total_budget_usd is not None:
                policy=study_budget(output,args.study_total_budget_usd,args.reserve_usd,args.prior_spend_usd,attempt['max_requests'])
                effective_budget=min(effective_budget,policy['request_ledger_ceiling_usd'])
            elif (output/'budget-policy.json').exists():
                policy=json.loads((output/'budget-policy.json').read_text())
                effective_budget=min(effective_budget,policy['request_ledger_ceiling_usd'])
                if policy.get('max_requests') is not None:
                    attempt['max_requests']=min(attempt['max_requests'],policy['max_requests'])
            scope_limit=args.batch_max_requests or plan['execution_window']['planned_requests']
            scope_budget=args.batch_budget_usd if args.batch_budget_usd is not None else effective_budget
            if scoped:window_policy(output,args.checkpoint_start,count,scope_limit,scope_budget)
            transport = MockTransport() if args.mode == 'mock' else DirectOpenAI(Path(__file__).resolve().parents[2] / 'compute.env')
            journal = Journal(output,transport,attempt['max_requests'],effective_budget,mock=args.mode=='mock',
                scope_prefixes=[f'checkpoint-{i:03d}' for i in range(args.checkpoint_start,args.checkpoint_start+count)] if scoped else None,
                scope_max_requests=scope_limit if scoped else None,scope_budget=scope_budget if scoped else None)
            if not (output/'cost-plan.json').exists():
                atomic_json(output/'cost-plan.json',cost_plan(config))
            results=run_study(config,output,journal,args.checkpoint_start,count)
            analyze(output)
            expected=config.checkpoints*len(config.conditions)*len(config.settings)*config.repetitions
            complete=len(list(output.glob('checkpoint-*/*/result.json')))==expected
            attempt.update(status='complete' if complete else 'window_complete',usage=journal.totals(),effective_request_budget_usd=effective_budget)
            print(json.dumps({'batch_directory':str(output),'completed_continuations':len(results),'usage':journal.totals()},indent=2))
        except BaseException as error:
            attempt.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'error',error_type=type(error).__name__)
            if journal is not None:
                attempt['usage']=journal.totals()
            raise SystemExit('Batch stopped; all saved data retained at ' + str(output)) from None
        finally:
            signal.signal(signal.SIGTERM,prior_handler)
            attempt['finished_at']=utc_now()
            atomic_json(attempt_file,attempt)
            atomic_json(output/'run-status.json',attempt)
            if journal is not None:
                atomic_json(output/'usage-summary.json',journal.report())
            if args.export_after_batch and (output/'manifest.json').exists():
                # Release the writer lock before the exporter obtains its own read lock.
                fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
                try:
                    from peer_identity.export import export_bundle, known_secrets
                    destination=(args.export_root/attempt_id) if args.export_root else None
                    bundle,report=export_bundle(output,destination,known_secrets(Path(__file__).resolve().parents[2]/'compute.env'))
                    print(json.dumps({'export_bundle':str(bundle),'validation':report},indent=2))
                except Exception as export_error:
                    atomic_json(output/'export-errors'/(attempt_id+'.json'),{'error_type':type(export_error).__name__})
                    print('Local export failed; raw study data retained. Inspect export-errors.')

if __name__ == '__main__':
    main()
