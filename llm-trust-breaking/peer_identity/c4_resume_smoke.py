"""Prepared checkpoint-000 completion only. Separate paid approval is mandatory."""
from __future__ import annotations
import argparse
import copy
import csv
import fcntl
import gzip
import json
from pathlib import Path
import shutil
import tempfile
from . import c4_extension as c, c4_recovery as recovery
from .inference import StopRun, atomic_json, canonical, digest


def verified_recovery(root):
    root = Path(root)
    receipt = c.read(root / 'explicit-recovery/software-correction.json')
    manifest = c.read(root / 'manifest.json')
    if digest(manifest) != receipt['original_manifest_hash']:
        raise StopRun('Original manifest changed')
    modules = [(Path(c.__file__), 'reviewed_diagnostic_extension_code_hash'),
               (Path(recovery.__file__), 'recovery_module_hash'),
               (Path(recovery.diagnostics.__file__), 'diagnostic_module_hash')]
    for path, field in modules:
        if digest(path.read_text()) != receipt[field]: raise StopRun('Reviewed code changed')
    identity = manifest['identity']; source = Path(identity['source'])
    if c.source_inventory(source) != identity['source_inventory']:
        raise StopRun('Original source changed')
    for name, expected in identity['core_code_hashes'].items():
        if digest((Path(c.__file__).parent / name).read_text()) != expected: raise StopRun('Protocol changed')
    if digest(Path(c.prompts.__file__).read_text()) != identity['prompt_code_hash']:
        raise StopRun('Prompts changed')
    for name, expected in receipt['original_request_inventory'].items():
        if digest(c.read(root / name)) != expected: raise StopRun('Original journal changed')
    attempt = c.read(root / 'explicit-recovery/attempt-1.json')
    old = c.read(root / 'requests' / (digest(recovery.TARGET) + '.json'))
    if attempt['status'] != 'complete' or attempt['original_record_hash'] != digest(old):
        raise StopRun('Validated successful explicit recovery required')
    if attempt['payload'] != old['payload'] or attempt['payload_hash'] != recovery.EXPECTED_PAYLOAD:
        raise StopRun('Recovery payload mismatch')
    if recovery.validator().check_response(copy.deepcopy(attempt)) != attempt['parsed']:
        raise StopRun('Recovery response validation mismatch')
    return source, receipt, attempt


class CompletionJournal(c.ExtensionJournal):
    def __init__(self, root, source, inventory, attempt, openai, router):
        self.recovered_attempt = copy.deepcopy(attempt)
        self.new_calls = 0
        super().__init__(root, source, inventory, 'trial', 52, .50, False, openai, router)
    def records(self):
        attempt = copy.deepcopy(self.recovered_attempt)
        attempt['stage'] = 'trial'
        return super().records() + [attempt]
    def ask(self, request_id, model, prompt, seed, temperature=1):
        if not request_id.startswith('checkpoint-000/natural-C4-rep000/'):
            raise StopRun('Only checkpoint-000 smoke completion permitted')
        if request_id == recovery.TARGET:
            payload = self.payload(model, prompt, seed, temperature)
            if payload != self.recovered_attempt['payload']: raise StopRun('Recovery replay mismatch')
            return copy.deepcopy(self.recovered_attempt['parsed'])
        existing = (self.path / (digest(request_id) + '.json')).exists()
        if not existing and self.new_calls >= 49: raise StopRun('49-new-request completion guard reached')
        before = len(self.records())
        try: return super().ask(request_id, model, prompt, seed, temperature)
        finally:
            self.new_calls += len(self.records()) - before


def export_completion(root, journal):
    """Logical scientific calls plus a separate, complete physical-attempt audit."""
    root = Path(root)
    actual = journal.records()
    with tempfile.TemporaryDirectory() as temp:
        view = Path(temp)
        atomic_json(view / 'manifest.json', c.read(root / 'manifest.json'))
        for record in actual:
            if record['request_id'] == recovery.TARGET: continue  # kept in attempts and raw audit
            logical = copy.deepcopy(record)
            if logical['request_id'] == recovery.TARGET + '/explicit-recovery-1':
                logical['physical_attempt_id'] = logical['request_id']
                logical['request_id'] = recovery.TARGET
                logical['stage'] = 'trial'
            atomic_json(view / 'requests' / (digest(logical['request_id']) + '.json'), logical)
        if (root / 'trials').exists(): shutil.copytree(root / 'trials', view / 'trials')
        snapshot = c.export(view)
        attempt_rows = []
        for record in actual:
            usage = record.get('response', {}).get('usage', {})
            attempt_rows.append({'request_id': record['request_id'], 'stage': record['stage'],
                'status': record['status'], 'model': record['payload']['model'],
                'provider': record.get('response', {}).get('provider'),
                'input_tokens': usage.get('prompt_tokens'), 'output_tokens': usage.get('completion_tokens'),
                'known_cost_usd': record.get('cost_usd'), 'accounted_usd': record.get('cost_usd', record['reserved_usd'])})
        with (snapshot / 'attempts.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(attempt_rows[0]))
            writer.writeheader(); writer.writerows(attempt_rows)
        with gzip.open(snapshot / 'raw.jsonl.gz', 'at') as handle:
            for record in actual:
                handle.write(canonical({'path': 'physical-attempts/' + record['request_id'], 'data': record}) + '\n')
            handle.write(canonical({'path': 'explicit-recovery/software-correction.json',
                                    'data': c.read(root / 'explicit-recovery/software-correction.json')}) + '\n')
        metadata = c.read(snapshot / 'metadata.json')
        metadata.update(physical_attempts=len(actual), accounting=journal.totals(),
            recovery_note='requests.csv represents logical calls. attempts.csv and raw audit preserve failed original and separate replacement charge. Unknown original reservation remains counted.')
        atomic_json(snapshot / 'metadata.json', metadata)
        destination = root / 'exports' / ('recovered-' + snapshot.name)
        destination.parent.mkdir(exist_ok=True)
        if destination.exists(): raise StopRun('Never overwrite export')
        shutil.copytree(snapshot, destination)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--approve-paid-completion', action='store_true')
    parser.add_argument('--max-new-requests', type=int, required=True)
    parser.add_argument('--max-total-trial-attempts', type=int, required=True)
    parser.add_argument('--trial-budget-usd', type=float, required=True)
    parser.add_argument('--env-file', default='../compute.env')
    args = parser.parse_args(argv)
    if not args.approve_paid_completion or (args.max_new_requests, args.max_total_trial_attempts, args.trial_budget_usd) != (49, 52, .50):
        parser.error('Require separate completion approval, 49 new / 52 lifetime trial attempts, unchanged $0.50 trial guard')
    root = args.output.resolve()
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source, receipt, attempt = verified_recovery(root)
        cp, config, state, meta = c.load_checkpoint(source, 0)
        journal = CompletionJournal(root, source, receipt['source_inventory'], attempt,
            c.DirectOpenAI(args.env_file), c.RouterTransport(args.env_file))
        result_path = root / 'trials/checkpoint-000/result.json'
        try:
            if not result_path.exists():
                prefix = 'checkpoint-000/natural-C4-rep000'
                for rnd in range(6, 11):
                    c.run_round(state, meta['models'], journal, prefix, rnd, config.seed, config)
                    atomic_json(result_path.with_name('progress.json'), {'metadata': meta, 'state': state})
                recognition = c.recognize(state, journal, prefix, config.model_a, config.seed, config)
                atomic_json(result_path, {'checkpoint_id': cp['checkpoint_id'], 'source_checkpoint_hash': cp['state_hash'],
                    'run_id': prefix, 'condition': 'C4', 'setting': 'natural', 'metadata': meta,
                    'recognition': recognition, 'state': state})
        finally:
            atomic_json(root / 'explicit-recovery/completion-accounting.json', journal.totals())
            snapshot = export_completion(root, journal)
            if c.source_inventory(source) != receipt['source_inventory']: raise StopRun('Source changed')
        print('Local export:', snapshot)
        print(json.dumps(journal.totals()))

if __name__ == '__main__': main()
