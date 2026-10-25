"""Isolated exploratory C4. Importing this module never accesses the network."""
from __future__ import annotations
import argparse
import copy
import csv
import fcntl
import gzip
import json
import math
import os
import re
from pathlib import Path
import subprocess
from datetime import datetime, timezone

from .inference import (DirectOpenAI, MockTransport, StopRun, atomic_json, canonical,
                        digest, validate, usage_cost, ENDPOINT)
from .protocol import Config, clone_branch, run_round, recognize, HANDOFF, prompts
from . import measurements_v2 as v2

MODEL = 'google/gemini-2.5-flash-lite'
ROUTER = 'https://openrouter.ai/api/v1/chat/completions'
PROVIDER = 'Google AI Studio'
PIN = {'only': ['google-ai-studio'], 'allow_fallbacks': False, 'require_parameters': True}
PRICES = {'input_per_million': .10, 'output_per_million': .40}

def read(path):
    return json.loads(Path(path).read_text())

def source_inventory(source):
    files = sorted(source.glob('checkpoint-*/checkpoint.json')) + sorted(source.glob('checkpoint-*/*/result.json'))
    return {str(p.relative_to(source)): digest(read(p)) for p in files}

def source_cost(source):
    total = 0.0
    for p in (source / 'requests').glob('*.json'):
        r = read(p)
        total += r.get('cost_usd', r.get('reserved_usd', 0))
    return total

def load_checkpoint(source, index):
    if not 0 <= index <= 11:
        raise StopRun('Only original checkpoints 000-011 enabled')
    cp = read(source / f'checkpoint-{index:03d}' / 'checkpoint.json')
    if digest(cp['state']) != cp['state_hash'] or [r['round'] for r in cp['state']['rounds']] != list(range(1, 6)):
        raise StopRun('Source checkpoint integrity failure')
    config = Config(**cp['settings'])
    config.validate()
    if config.protocol_version != v2.VERSION:
        raise StopRun('Source must be Version 2')
    state, meta = clone_branch(cp, 'C3', 'natural', config)
    assert state['agents']['A'] == cp['state']['agents']['A']
    assert state['public'] == cp['state']['public']
    assert state['agents']['B'] == {'private': [], 'takeaways': {}, 'handoff': HANDOFF}
    meta.update(condition='C4', category='different_model_and_provider', truth_changed=True)
    meta['models']['B'] = MODEL
    return cp, config, state, meta

class RouterTransport:
    def __init__(self, env_path):
        from dotenv import dotenv_values
        import requests
        self.key = os.environ.get('OPENROUTER_API_KEY') or dotenv_values(env_path).get('OPENROUTER_API_KEY')
        if not self.key:
            raise StopRun('OPENROUTER_API_KEY unavailable')
        self.session = requests.Session()

    def __call__(self, payload):
        import requests
        from .c4_http_diagnostics import http_failure, network_failure
        try:
            response = self.session.post(ROUTER, json=payload,
                headers={'Authorization': 'Bearer ' + self.key}, timeout=(15, 300), allow_redirects=False)
        except requests.RequestException:
            raise network_failure(payload) from None
        if response.status_code != 200:
            raise http_failure(response, payload, (self.key,)) from None
        try:
            body = response.json()
        except ValueError:
            raise http_failure(response, payload, (self.key,)) from None
        if not isinstance(body, dict) or not body.get('choices'):
            raise http_failure(response, payload, (self.key,)) from None
        return {'endpoint': ROUTER, 'response_id': body.get('id'),
            'provider': body.get('provider'), 'model_returned': body.get('model'),
            'usage': body.get('usage'), 'content': body['choices'][0]['message'].get('content'),
            'finish_reason': body['choices'][0].get('finish_reason'),
            'http_diagnostic': {'http_status': response.status_code, 'response_disposition': 'http_accepted',
                'provider_acceptance': 'reported_generation', 'could_have_incurred_charge': True,
                'model': payload.get('model'), 'requested_provider_route': payload.get('provider'),
                'request_identifiers': http_failure(response, payload, (self.key,)).diagnostic['request_identifiers']}}

class RoutedMock:
    def __init__(self):
        self.backend = MockTransport()
    def __call__(self, payload):
        response = self.backend(payload)
        if payload['model'] == MODEL:
            response.update(endpoint=ROUTER, provider=PROVIDER)
        return response

class ExtensionJournal:
    """At-most-once dispatch. Saved valid responses can recover without resending."""
    def __init__(self, root, source, inventory, stage, max_requests, budget, mock=False,
                 openai=None, router=None):
        if type(max_requests) is not int or max_requests < 1 or not math.isfinite(budget) or budget <= 0:
            raise StopRun('Invalid caps')
        self.root, self.source, self.inventory = Path(root), Path(source), inventory
        self.stage, self.max_requests, self.budget, self.mock = stage, max_requests, budget, mock
        self.path = self.root / 'requests'
        self.path.mkdir(parents=True, exist_ok=True)
        self.openai, self.router = openai, router
        self.source_spend = source_cost(self.source)
        self.source_stats = self.stat_source()

    def stat_source(self):
        files = list((self.source / 'requests').glob('*.json')) + [self.source / name for name in self.inventory]
        return {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}

    def records(self):
        records = []
        for p in sorted(self.path.glob('*.json')):
            record = read(p)
            sidecar = self.root / 'recoveries' / p.name
            if sidecar.exists():
                recovered = read(sidecar)
                if recovered['original_record_hash'] != digest(record):
                    raise StopRun('Recovery hash mismatch')
                record = recovered['validated_record']
            records.append(record)
        return records

    def totals(self):
        records = self.records()
        return {'requests': len(records), 'accounted_usd': sum(r.get('cost_usd', r['reserved_usd']) for r in records),
                'complete': sum(r['status'] == 'complete' for r in records), 'mock': self.mock}

    def payload(self, model, prompt, seed, temperature):
        system, user, schema = prompt
        p = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
             'response_format': {'type': 'json_schema', 'json_schema': schema}}
        if model == MODEL:
            p.update(provider=copy.deepcopy(PIN), max_tokens=2000, temperature=temperature, seed=seed)
        elif model in ('gpt-4o-mini', 'gpt-5-mini'):
            p['max_completion_tokens'] = 2000
            if model == 'gpt-5-mini': p['reasoning_effort'] = 'low'
            else: p.update(temperature=temperature, seed=seed)
        else:
            raise StopRun('Unexpected model')
        return p

    def check_response(self, record):
        response, payload = record['response'], record['payload']
        model = payload['model']
        expected_endpoint = ROUTER if model == MODEL else ENDPOINT
        if response.get('endpoint') != expected_endpoint:
            raise StopRun('Unexpected billing route')
        returned = response.get('model_returned', '')
        if not (returned == model or (model != MODEL and returned.startswith(model + '-'))):
            raise StopRun('Unexpected returned model')
        if model == MODEL and response.get('provider') != PROVIDER:
            raise StopRun('Google AI Studio provider could not be verified')
        if response.get('finish_reason') != 'stop':
            raise StopRun('Incomplete response')
        usage = response.get('usage') or {}
        for field in ('prompt_tokens', 'completion_tokens'):
            if type(usage.get(field)) is not int or usage[field] < 0:
                raise StopRun('Missing or invalid usage')
        if model == MODEL:
            estimated = (usage['prompt_tokens'] * .1 + usage['completion_tokens'] * .4) / 1e6
            reported = usage.get('cost')
            if reported is not None and (type(reported) not in (int, float) or not math.isfinite(reported) or reported < 0):
                raise StopRun('Invalid provider cost')
            cost = reported if reported is not None else estimated
        else:
            cost = usage_cost(model, usage)
        record['cost_usd'] = 0.0 if self.mock else cost
        record['cost_basis'] = 'synthetic' if self.mock else ('provider_reported' if model == MODEL and usage.get('cost') is not None else 'token_price_estimate')
        parsed = json.loads(response['content'])
        validate(parsed, payload['response_format']['json_schema']['schema'])
        for name in ('intended_action', 'stated_action', 'choice'):
            if name in parsed and (type(parsed[name]) is not int or not 0 <= parsed[name] <= 5):
                raise StopRun('Contribution outside 0-5')
        if cost > record['reserved_usd']:
            raise StopRun('Reservation exceeded')
        return parsed

    def ask(self, request_id, model, prompt, seed, temperature=1):
        # No treatment label may be used to infer routing: judges about B remain OpenAI.
        if self.stage == 'probe' and model != MODEL:
            raise StopRun('Probes may only use replacement B')
        if self.stage == 'trial':
            is_b = request_id.endswith('/B') and '/judge/' not in request_id
            if (model == MODEL) != is_b:
                raise StopRun('Role routing mismatch')
        payload = self.payload(model, prompt, seed, temperature)
        p = self.path / (digest(request_id) + '.json')
        if p.exists():
            record = read(p)
            if record['payload_hash'] != digest(payload) or record['stage'] != self.stage:
                raise StopRun('Resume payload mismatch')
            if record['status'] == 'complete': return copy.deepcopy(record['parsed'])
            if record.get('response'):
                # Original raw response remains immutable; recovery is an audited sidecar.
                recovered = copy.deepcopy(record)
                parsed = self.check_response(recovered)
                atomic_json(self.root / 'recoveries' / p.name, {'original_record_hash': digest(record), 'validated_record': dict(recovered, status='complete', parsed=parsed)})
                return parsed
            raise StopRun('Unresolved request: no automatic resend')
        if self.stat_source() != self.source_stats:
            raise StopRun('Source study changed; stop before dispatch')
        records = self.records()
        stage_records = [r for r in records if r['stage'] == self.stage]
        tokens = len(canonical(payload).encode()) + 1024
        prices = (.1, .4) if model == MODEL else ((.15, .6) if model == 'gpt-4o-mini' else (.25, 2))
        reserve = (tokens * prices[0] + 2000 * prices[1]) / 1e6
        used = sum(r.get('cost_usd', r['reserved_usd']) for r in stage_records)
        all_used = sum(r.get('cost_usd', r['reserved_usd']) for r in records)
        if len(stage_records) >= self.max_requests or used + reserve > self.budget:
            raise StopRun('Stage request/spending cap reached')
        if .4954921 + self.source_spend + all_used + reserve > 50:
            raise StopRun('Study $60 ceiling with $10 reserve reached')
        record = {'request_id': request_id, 'stage': self.stage, 'payload': payload, 'payload_hash': digest(payload),
            'status': 'pending', 'reserved_usd': reserve, 'mock': self.mock,
            'created_at': datetime.now(timezone.utc).isoformat()}
        atomic_json(p, record)
        try:
            response = (self.router if model == MODEL else self.openai)(payload)
            record['response'] = response
            # Preserve received response before any local validation.
            atomic_json(p, record)
            parsed = self.check_response(record)
            record.update(status='complete', parsed=parsed)
            atomic_json(p, record)
            return copy.deepcopy(parsed)
        except Exception as error:
            record.update(status='blocked', error_type=type(error).__name__)
            from .c4_http_diagnostics import RouterDiagnosticFailure
            if isinstance(error, RouterDiagnosticFailure):
                record['http_diagnostic'] = error.diagnostic
            elif record.get('response'):
                record['http_diagnostic'] = {
                    'response_disposition': 'http_accepted_locally_rejected',
                    'provider_acceptance': 'reported_generation',
                    'could_have_incurred_charge': True,
                    'billing_status': 'recorded_cost' if 'cost_usd' in record else 'unknown_keep_reservation',
                    'model': payload.get('model'), 'requested_provider_route': payload.get('provider')}
            atomic_json(p, record)
            raise StopRun('Stopped; inspect durable record; no automatic paid retry') from None

class Capture:
    def __init__(self): self.mock, self.b = RoutedMock(), []
    def ask(self, request_id, model, prompt, seed, temperature=1):
        if model == MODEL: self.b.append((request_id, model, copy.deepcopy(prompt), seed, temperature))
        payload = ExtensionJournal.payload(self, model, prompt, seed, temperature)
        return json.loads(self.mock(payload)['content'])

def probe_prompts(source):
    cp, config, state, meta = load_checkpoint(source, 0)
    capture = Capture()
    for rnd in range(6, 11):
        run_round(state, meta['models'], capture, 'fixture', rnd, config.seed, config)
    wanted = ('/r6/planning/B', '/r6/announcement/B', '/r6/decision/B', '/r6/reflection/B', '/r10/reflection/B')
    return [item for item in capture.b if any(item[0].endswith(suffix) for suffix in wanted)]

def export(root):
    root = Path(root)
    results = [read(p) for p in sorted((root / 'trials').glob('*/result.json'))]
    records = []
    for path in sorted((root / 'requests').glob('*.json')):
        record = read(path)
        sidecar = root / 'recoveries' / path.name
        if sidecar.exists():
            recovery = read(sidecar)
            if recovery['original_record_hash'] != digest(record): raise StopRun('Invalid recovery hash')
            record = recovery['validated_record']
        records.append(record)
    rounds, detections, trials = [], [], []
    for result in results:
        cp, run = result['checkpoint_id'], result['run_id']
        if result['condition'] != 'C4' or result['setting'] != 'natural': raise StopRun('Invalid export condition')
        for rnd in result['state']['rounds'][5:]:
            for agent in ('A', 'B'):
                a = rnd['agents'][agent]; reflection = a['reflection']
                rounds.append({'checkpoint_id': cp, 'run_id': run, 'condition': 'C4', 'behavior_setting': 'natural',
                    'round': rnd['round'], 'agent': agent, 'model': rnd['models'][agent],
                    'contribution': a['actual_contribution'], 'payoff': rnd['outcomes']['payoffs'][agent],
                    'promise': a['stage2']['stated_action'], 'message': a['stage2']['message'],
                    'trust_1_10': reflection['score'], 'promise_reliability_1_10': reflection['promise_reliability_1_10'],
                    'forecast': reflection.get('predicted_next_partner_contribution'),
                    'factual_correct': a['factual_validation']['factual_assessment_correct']})
        d = result['recognition']
        detections.append({'checkpoint_id': cp, 'run_id': run, 'condition': 'C4', 'judgment': d['judgment'],
            'confidence': d['confidence'], 'correct': d['judgment'] == 'CHANGED', 'evidence_json': canonical(d)})
        trials.append({'checkpoint_id': cp, 'run_id': run, 'condition': 'C4', 'behavior_setting': 'natural',
            'status': 'complete', 'source_checkpoint_hash': result['source_checkpoint_hash'],
            'a_initial_state_hash': result['metadata']['a_initial_state_hash'], 'model_a': 'gpt-4o-mini', 'model_b': MODEL})
    for trial in trials:
        matching = [r for r in records if r['request_id'].startswith(trial['run_id'] + '/')]
        if len(matching) != 51 or any(r['status'] != 'complete' for r in matching):
            raise StopRun('Completed trial lacks 51 validated requests')
        trial.update(requests=len(matching), input_tokens=sum(r.get('response', {}).get('usage', {}).get('prompt_tokens', 0) for r in matching),
            output_tokens=sum(r.get('response', {}).get('usage', {}).get('completion_tokens', 0) for r in matching),
            accounted_usd=sum(r.get('cost_usd', r['reserved_usd']) for r in matching))
    if len({r['run_id'] for r in trials}) != len(trials) or len(rounds) != len(trials) * 10:
        raise StopRun('Export completeness failure')
    for p in list((root / 'requests').glob('*.json')) + list((root / 'trials').rglob('*.json')):
        if re.search(r'(?:sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9_-]{20,})', p.read_text()):
            raise StopRun('Potential credential detected; export blocked')
    target = root / 'exports' / ('snapshot-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    target.mkdir(parents=True, exist_ok=False)
    request_rows = [{'request_id': r['request_id'], 'stage': r['stage'], 'status': r['status'],
        'model': r['payload']['model'], 'endpoint': r.get('response', {}).get('endpoint'),
        'provider': r.get('response', {}).get('provider', 'OpenAI' if r['payload']['model'] != MODEL else ''),
        'input_tokens': r.get('response', {}).get('usage', {}).get('prompt_tokens'),
        'output_tokens': r.get('response', {}).get('usage', {}).get('completion_tokens'),
        'accounted_usd': r.get('cost_usd', r['reserved_usd']), 'cost_basis': r.get('cost_basis', 'reservation')} for r in records]
    for name, rows in [('rounds', rounds), ('detections', detections), ('trials', trials), ('requests', request_rows)]:
        with (target / (name + '.csv')).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['run_id'])
            writer.writeheader(); writer.writerows(rows)
    with gzip.open(target / 'raw.jsonl.gz', 'wt') as f:
        for folder in ('requests', 'recoveries', 'trials'):
            for p in sorted((root / folder).rglob('*.json')):
                f.write(canonical({'path': str(p.relative_to(root)), 'data': read(p)}) + '\n')
    atomic_json(target / 'metadata.json', {'manifest': read(root / 'manifest.json'), 'trials': len(trials),
        'synthetic': read(root / 'manifest.json')['mock'], 'original_main_study_unchanged': True,
        'note': 'Exploratory natural-only add-on. Not the original factorial study. Raw records include usage, costs, provider and all outputs.'})
    return target

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=['probe', 'trial'], required=True)
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--approve-paid-probe', action='store_true')
    parser.add_argument('--approve-paid-trial', action='store_true')
    parser.add_argument('--checkpoint', type=int, default=0)
    parser.add_argument('--max-requests', type=int, required=True)
    parser.add_argument('--budget-usd', type=float, required=True)
    parser.add_argument('--env-file', type=Path, default=Path('../compute.env'))
    args = parser.parse_args(argv)
    if not args.mock and not (args.approve_paid_probe if args.stage == 'probe' else args.approve_paid_trial):
        parser.error('Separate explicit approval required for this paid stage')
    if args.stage == 'probe' and args.max_requests > 5: parser.error('Probe maximum is five requests')
    if args.stage == 'trial' and (args.checkpoint != 0 or args.max_requests > 51): parser.error('Only one checkpoint-000 smoke trial enabled')
    source, root = args.source.resolve(), args.output.resolve()
    if root == source or source in root.parents or root in source.parents:
        parser.error('Extension output must be isolated from source')
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        inventory = source_inventory(source)
        if len(list(source.glob('checkpoint-*/checkpoint.json'))) < 12 or len(list(source.glob('checkpoint-*/*/result.json'))) != 96:
            raise StopRun('Expected preserved 12-checkpoint, 96-trial source')
        cp, config, state, meta = load_checkpoint(source, args.checkpoint)
        identity = {'source': str(source), 'source_inventory': inventory, 'mock': args.mock,
                    'model': MODEL, 'provider_pin': PIN, 'gemini_prices_usd_per_million': PRICES,
                    'source_configuration': cp['settings'], 'output_token_limit': 2000,
                    'prompt_code_hash': digest(Path(prompts.__file__).read_text()), 'code_hash': digest(Path(__file__).read_text()),
                    'core_code_hashes': {name: digest((Path(__file__).parent / name).read_text()) for name in ('protocol.py', 'inference.py', 'measurements_v2.py')},
                    'protocol': v2.VERSION, 'prior_spend_usd': .4954921, 'study_limit_usd': 60, 'reserve_usd': 10}
        manifest = root / 'manifest.json'
        if manifest.exists():
            saved = read(manifest)
            if saved['identity'] != identity: raise StopRun('Extension identity mismatch')
        else:
            try: commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
            except Exception: commit = 'unknown'
            atomic_json(manifest, {'identity': identity, 'mock': args.mock, 'created_at': datetime.now(timezone.utc).isoformat(), 'code_commit': commit})
        mock = RoutedMock() if args.mock else None
        journal = ExtensionJournal(root, source, inventory, args.stage, args.max_requests, args.budget_usd, args.mock,
            mock or DirectOpenAI(args.env_file), mock or RouterTransport(args.env_file))
        try:
            if args.stage == 'probe':
                for i, (_, model, prompt, seed, temperature) in enumerate(probe_prompts(source)):
                    journal.ask(f'probe/schema-{i}', model, prompt, seed, temperature)
                atomic_json(root / 'probe-passed.json', {'model': MODEL, 'provider': PROVIDER, 'mock': args.mock, 'requests': 5})
            else:
                probe = root / 'probe-passed.json'
                if not probe.exists() or read(probe)['mock'] != args.mock: raise StopRun('Matching successful compatibility probe required')
                run_id = 'checkpoint-000/natural-C4-rep000'
                result_path = root / 'trials' / 'checkpoint-000' / 'result.json'
                if not result_path.exists():
                    for rnd in range(6, 11):
                        run_round(state, meta['models'], journal, run_id, rnd, config.seed, config)
                        atomic_json(result_path.with_name('progress.json'), {'metadata': meta, 'state': state})
                    recognition = recognize(state, journal, run_id, config.model_a, config.seed, config)
                    atomic_json(result_path, {'checkpoint_id': cp['checkpoint_id'], 'source_checkpoint_hash': cp['state_hash'],
                        'run_id': run_id, 'condition': 'C4', 'setting': 'natural', 'metadata': meta,
                        'recognition': recognition, 'state': state})
        finally:
            atomic_json(root / 'usage-summary.json', journal.totals())
            snapshot = export(root)
            if source_inventory(source) != inventory: raise StopRun('Source changed during execution')
        print('Local export:', snapshot)
        print(canonical(journal.totals()))

if __name__ == '__main__': main()
