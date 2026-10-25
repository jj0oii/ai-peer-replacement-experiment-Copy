"""One explicitly authorized C4 request recovery; never continues a game."""
from __future__ import annotations
import argparse
import copy
import fcntl
import json
from pathlib import Path
from datetime import datetime, timezone

from . import c4_extension as c
from . import c4_http_diagnostics as diagnostics
from .inference import StopRun, atomic_json, digest

TARGET = 'checkpoint-000/natural-C4-rep000/r6/planning/B'
A_TARGET = 'checkpoint-000/natural-C4-rep000/r6/planning/A'
EXPECTED_PAYLOAD = '74a950fa21f6e59d8e2a3b1cfdbd68874f60d73cffc44a8c6da0c8cd237e685c'
REVIEW = Path('/workspace/peer-identity-exports/c4-diagnostic-review/offline-review.json')


def files(root):
    return {str(p.relative_to(root)): digest(c.read(p)) for p in sorted((root / 'requests').glob('*.json'))}


def prepare(root, review_path=REVIEW):
    root = Path(root)
    manifest = c.read(root / 'manifest.json')
    identity = manifest['identity']
    review = c.read(review_path)
    source = Path(identity['source'])
    if identity['mock'] or identity['code_hash'] != review['old_extension_code_hash']:
        raise StopRun('Unexpected original software identity')
    if digest(Path(c.__file__).read_text()) != review['new_extension_code_hash']:
        raise StopRun('Diagnostic correction does not match reviewed code')
    if c.source_inventory(source) != identity['source_inventory']:
        raise StopRun('Source checkpoint/result hashes changed')
    for name, expected in identity['core_code_hashes'].items():
        if digest((Path(c.__file__).parent / name).read_text()) != expected:
            raise StopRun('Scientific protocol changed')
    if digest(Path(c.prompts.__file__).read_text()) != identity['prompt_code_hash']:
        raise StopRun('Scientific prompts changed')
    old = c.read(root / 'requests' / (digest(TARGET) + '.json'))
    a = c.read(root / 'requests' / (digest(A_TARGET) + '.json'))
    probe = c.read(root / 'requests' / (digest('probe/schema-0') + '.json'))
    if old['request_id'] != TARGET or old['status'] != 'blocked' or old.get('response'):
        raise StopRun('Only the one unresolved Gemini planning attempt is eligible')
    if a['status'] != 'complete' or a['payload']['model'] != 'gpt-4o-mini':
        raise StopRun('Successful A planning response required')
    payload = old['payload']
    if old['payload_hash'] != EXPECTED_PAYLOAD or digest(payload) != EXPECTED_PAYLOAD:
        raise StopRun('Original target payload mismatch')
    if probe['status'] != 'complete' or probe['payload'] != payload:
        raise StopRun('Successful identical probe not found')
    _, model, prompt, seed, temperature = c.probe_prompts(source)[0]
    rebuilt = c.ExtensionJournal.payload(None, model, prompt, seed, temperature)
    if rebuilt != payload or payload['provider'] != c.PIN or payload['model'] != c.MODEL:
        raise StopRun('Reconstructed request mismatch')
    return source, old, a, {
        'purpose': 'Explicitly authorized single recovery; no continuation execution',
        'original_manifest_hash': digest(manifest), 'original_request_hash': digest(old),
        'original_request_id': TARGET, 'successful_a_record_hash': digest(a),
        'original_request_inventory': files(root), 'source_inventory': identity['source_inventory'],
        'old_extension_code_hash': identity['code_hash'],
        'reviewed_diagnostic_extension_code_hash': review['new_extension_code_hash'],
        'diagnostic_module_hash': digest(Path(diagnostics.__file__).read_text()),
        'recovery_module_hash': digest(Path(__file__).read_text()),
        'original_unknown_cost_reservation_usd': old['reserved_usd'],
        'max_new_requests': 1, 'new_spending_guard_usd': .01,
        'documented_smoke_attempt_limit': 52, 'smoke_spending_limit_usd': .50,
        'study_limit_usd': 60, 'reserve_usd': 10,
    }


def validator():
    journal = object.__new__(c.ExtensionJournal)
    journal.mock = False
    return journal


def recover(root, transport=None, env_file='../compute.env', review_path=REVIEW):
    """Caller must have explicit paid authorization. An existing attempt never resends."""
    root = Path(root)
    source, old, a, receipt = prepare(root, review_path)
    directory = root / 'explicit-recovery'
    directory.mkdir(exist_ok=True)
    attempt_path = directory / 'attempt-1.json'
    receipt_path = directory / 'software-correction.json'
    if receipt_path.exists() and c.read(receipt_path) != receipt:
        raise StopRun('Recovery correction identity mismatch')
    if attempt_path.exists():
        # Do not dispatch, even for a previous failed or ambiguous attempt.
        raise StopRun('Single authorized recovery attempt already exists; no resend')
    atomic_json(receipt_path, receipt)
    payload = copy.deepcopy(old['payload'])
    reserve = old['reserved_usd']
    originals = [c.read(p) for p in (root / 'requests').glob('*.json')]
    trial = [r for r in originals if r['stage'] == 'trial']
    if len(trial) != 2 or sum(r['status'] == 'complete' for r in trial) != 1:
        raise StopRun('Unexpected trial progress')
    accounted = sum(r.get('cost_usd', r['reserved_usd']) for r in originals)
    trial_accounted = sum(r.get('cost_usd', r['reserved_usd']) for r in trial)
    if reserve > .01 or trial_accounted + reserve > .50:
        raise StopRun('Recovery or unchanged smoke spending guard reached')
    if .4954921 + c.source_cost(source) + accounted + reserve > 50:
        raise StopRun('Cumulative study limit including reserve reached')
    transport = transport or c.RouterTransport(env_file)
    attempt = {'request_id': TARGET + '/explicit-recovery-1', 'original_request_id': TARGET,
        'original_record_hash': digest(old), 'payload_hash': old['payload_hash'], 'payload': payload,
        'original_unknown_reservation_usd': reserve, 'reserved_usd': reserve,
        'status': 'pending', 'mock': False, 'stage': 'explicit_recovery',
        'authorization': {'max_new_requests': 1, 'budget_usd': .01, 'automatic_retry': False},
        'created_at': datetime.now(timezone.utc).isoformat()}
    # Durable intent before the one and only dispatch. No completion routine is called.
    atomic_json(attempt_path, attempt)
    try:
        attempt['response'] = transport(payload)
        atomic_json(attempt_path, attempt)
        parsed = validator().check_response(attempt)
        attempt.update(status='complete', parsed=parsed)
        atomic_json(attempt_path, attempt)
    except Exception as error:
        attempt.update(status='blocked', error_type=type(error).__name__)
        if isinstance(error, diagnostics.RouterDiagnosticFailure):
            attempt['http_diagnostic'] = error.diagnostic
        elif attempt.get('response'):
            attempt['http_diagnostic'] = {'response_disposition': 'http_accepted_locally_rejected',
                'could_have_incurred_charge': True, 'billing_status': 'unknown_keep_reservation'}
        atomic_json(attempt_path, attempt)
        raise StopRun('Single recovery attempt stopped; inspect sanitized record; no retry') from None
    finally:
        if files(root) != receipt['original_request_inventory']:
            raise StopRun('Original paid journal changed')
        if c.source_inventory(source) != receipt['source_inventory']:
            raise StopRun('Original study changed')
        atomic_json(directory / 'accounting.json', {
            'new_requests': 1, 'new_record_status': attempt['status'],
            'new_accounted_usd': attempt.get('cost_usd', reserve),
            'original_unknown_reservation_usd': reserve,
            'extension_accounted_usd_including_original_reservation': accounted + attempt.get('cost_usd', reserve),
            'trial_attempts_including_failed_original_and_recovery': 3,
            'no_rounds_continued': True,
        })
    return attempt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--approve-one-paid-recovery', action='store_true')
    parser.add_argument('--max-new-requests', type=int, required=True)
    parser.add_argument('--budget-usd', type=float, required=True)
    parser.add_argument('--env-file', default='../compute.env')
    args = parser.parse_args(argv)
    if not args.approve_one_paid_recovery or args.max_new_requests != 1 or args.budget_usd != .01:
        parser.error('Require explicit one-request approval and exactly the $0.01 guard')
    root = args.output.resolve()
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        attempt = recover(root, env_file=args.env_file)
    print(json.dumps({'status': attempt['status'], 'provider': attempt['response'].get('provider'),
        'cost_usd': attempt['cost_usd'], 'new_requests': 1, 'continued_game': False}))

if __name__ == '__main__': main()
