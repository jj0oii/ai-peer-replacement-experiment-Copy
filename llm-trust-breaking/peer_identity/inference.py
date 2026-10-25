"""Direct OpenAI transport, strict validation, and an at-most-once request journal.

No dependency on the legacy config module; importing this file makes no requests.
"""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path

ENDPOINT = 'https://api.openai.com/v1/chat/completions'
# USD / million tokens: input, cached input, output. Versioned assumptions, not live quotes.
PRICES = {'gpt-4o-mini': (.15, .075, .60), 'gpt-4.1-mini': (.40, .10, 1.60),
          'gpt-5-mini': (.25, .025, 2.00)}

class StopRun(RuntimeError):
    """Safe stop; completed responses stay reusable, ambiguous calls are never resent."""


class HTTPFailure(StopRun):
    """Only allowlisted, non-secret error diagnostics are retained."""
    def __init__(self, status, code):
        self.status = status
        allowed = {'insufficient_quota','rate_limit_exceeded','invalid_api_key','model_not_found',
                   'billing_hard_limit_reached','permission_denied','context_length_exceeded'}
        self.code = code if code in allowed else 'unknown'
        super().__init__('OpenAI HTTP failure')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=True) + '\n')
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate(value, schema):
    """Validate the object/array/scalar JSON subset used by starter schemas, without coercion."""
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError('Output outside permitted enum')
    kind = schema.get('type')
    if kind == 'object':
        if not isinstance(value, dict):
            raise ValueError('Expected JSON object')
        props = schema.get('properties', {})
        if set(schema.get('required', [])) - value.keys():
            raise ValueError('Missing required output field')
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError('Unexpected output field')
        for key, val in value.items():
            if key in props:
                validate(val, props[key])
    elif kind == 'boolean':
        if type(value) is not bool:
            raise ValueError('Expected boolean')
    elif kind == 'array':
        if not isinstance(value, list):
            raise ValueError('Expected array')
        for val in value:
            validate(val, schema['items'])
    elif kind in ('integer', 'number'):
        if type(value) not in ((int,) if kind == 'integer' else (int, float)):
            raise ValueError('Expected numeric output')
        if not math.isfinite(value):
            raise ValueError('Nonfinite numeric output')
        if value < schema.get('minimum', float('-inf')) or value > schema.get('maximum', float('inf')):
            raise ValueError('Numeric output outside permitted bounds')
    elif kind == 'string':
        if not isinstance(value, str):
            raise ValueError('Expected text')
        if len(value) < schema.get('minLength', 0):
            raise ValueError('Text shorter than schema minimum')
        if len(value) > schema.get('maxLength', 100_000):
            raise ValueError('Text exceeds limit')


def usage_cost(model, usage):
    i, c, o = PRICES[model]
    for name in ('prompt_tokens', 'completion_tokens'):
        if type(usage.get(name)) is not int or usage[name] < 0:
            raise ValueError('Invalid usage accounting')
    cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
    if type(cached) is not int or not 0 <= cached <= usage['prompt_tokens']:
        raise ValueError('Invalid cached token usage')
    return ((usage['prompt_tokens'] - cached) * i + cached * c + usage['completion_tokens'] * o) / 1e6


def reservation(payload):
    # UTF-8 bytes upper-bound byte-BPE text tokens; JSON syntax and 1024 extra tokens
    # cover message framing/schema overhead. This is deliberately loose, not a billing guarantee.
    tokens = len(canonical(payload).encode()) + 1024
    inp, _, out = PRICES[payload['model']]
    return tokens, (tokens * inp + payload['max_completion_tokens'] * out) / 1e6


class DirectOpenAI:
    """One network attempt; redirects and SDK retries are deliberately disabled."""
    def __init__(self, env_path):
        from dotenv import dotenv_values
        v = dotenv_values(env_path)
        base = os.environ.get('LLM_BASE_URL', v.get('LLM_BASE_URL', ''))
        key = os.environ.get('LLM_API_KEY', v.get('LLM_API_KEY', ''))
        forced = os.environ.get('LLM_MODEL', v.get('LLM_MODEL', ''))
        if base != 'https://api.openai.com/v1' or not key or forced:
            raise StopRun('Require direct OpenAI base URL, nonempty LLM_API_KEY, disabled LLM_MODEL')
        self._key = key
        import requests
        self._session = requests.Session()  # trust_env=True: existing verified proxy route

    def fresh(self):
        import requests
        other = object.__new__(type(self))
        other._key = self._key
        other._session = requests.Session()
        return other

    def close(self):
        self._session.close()

    def __call__(self, payload):
        response = self._session.post(ENDPOINT, json=payload,
            headers={'Authorization': 'Bearer ' + self._key}, timeout=(15, 300), allow_redirects=False)
        if response.status_code != 200:
            code = 'unknown'
            try:
                code = str(response.json().get('error', {}).get('code', 'unknown'))
            except (ValueError, AttributeError):
                pass
            # Never save raw headers, authorization, or error bodies.
            raise HTTPFailure(response.status_code, code)
        body = response.json()
        return {'endpoint': ENDPOINT, 'request_id': response.headers.get('x-request-id'),
                'response_id': body.get('id'), 'model_returned': body.get('model'),
                'usage': body.get('usage'), 'content': body['choices'][0]['message'].get('content'),
                'finish_reason': body['choices'][0].get('finish_reason')}


class MockTransport:
    """Deterministic, no sockets or credentials; researcher labels never reach the model payload."""
    def __init__(self):
        self.calls = 0
        self.payloads = []
        self.fresh_count = 0

    def fresh(self):
        self.fresh_count += 1
        # New mock runtime facade, shared audit counter for exact call accounting.
        return lambda payload: self(payload)

    def __call__(self, payload):
        self.calls += 1
        self.payloads.append(copy.deepcopy(payload))
        props = payload['response_format']['json_schema']['schema']['properties']
        value = {}
        for key, schema in props.items():
            if key in ('intended_action', 'stated_action', 'choice'):
                value[key] = 4
            elif key == 'score':
                value[key] = 8 if 'promise_reliability_1_10' in props else 4
            elif key == 'promise_reliability_1_10':
                value[key] = 8
            elif key == 'predicted_next_partner_contribution':
                value[key] = 4
            elif key in ('partner_promised_contribution','partner_actual_contribution','promise_matched','own_payoff','partner_payoff'):
                marker = payload['messages'][1]['content'].split('ENGINE_FACTS=',1)[1].split('\n',1)[0]
                value[key] = json.loads(marker)[key]
            elif key == 'confidence':
                value[key] = 80 if 'judgment' in props else 4
            elif key == 'primary_label':
                value[key] = 'Honest Consistency'
            elif key == 'judgment':
                value[key] = 'SAME'
            elif 'enum' in schema:
                value[key] = schema['enum'][0]
            else:
                value[key] = 'A consistent contribution supports cooperation.'
        return {'endpoint': ENDPOINT, 'request_id': f'mock-{self.calls}',
                'response_id': f'mock-{self.calls}', 'model_returned': payload['model'],
                'usage': {'prompt_tokens': 100, 'completion_tokens': 30},
                'content': json.dumps(value), 'finish_reason': 'stop'}


class Journal:
    """Durably reserve BEFORE sending. Reuse completed outputs on identical request IDs.

    A pending, errored or invalid response blocks that request on resume. Resolving an
    ambiguous network failure requires manual review, never silent duplicate billing.
    """
    def __init__(self, directory, transport, max_requests, budget, mock=False, scope_prefixes=None, scope_max_requests=None, scope_budget=None):
        if type(max_requests) is not int or max_requests < 1 or not math.isfinite(budget) or budget <= 0:
            raise ValueError('Finite positive budget and positive integer request limit required')
        self.path = Path(directory) / 'requests'
        self.path.mkdir(parents=True, exist_ok=True)
        self.transport, self.max_requests, self.budget, self.mock = transport, max_requests, budget, mock
        self.scope_prefixes=set(scope_prefixes) if scope_prefixes is not None else None
        self.scope_max_requests=scope_max_requests
        self.scope_budget=scope_budget
        self._scope_count=0
        self._scope_accounted=0.0
        self._agent_transports = {}
        self._accounting = {}
        self._accounted = 0.0
        self._completed = 0
        for p in self.path.glob('*.json'):
            from .repair import effective_request
            r = effective_request(Path(directory), json.loads(p.read_text()))
            self._accounting[p.name] = (r.get('cost_usd', r['reserved_usd']), r['status'])
            self._accounted += self._accounting[p.name][0]
            self._completed += r['status'] == 'complete'
            if self._in_scope(r['request_id_local']):
                self._scope_count+=1
                self._scope_accounted+=self._accounting[p.name][0]

    def _in_scope(self, request_id):
        return self.scope_prefixes is not None and request_id.split('/')[0] in self.scope_prefixes

    def start_branch(self, condition):
        for backend in self._agent_transports.values():
            if hasattr(backend, 'close'):
                backend.close()
        self._agent_transports = {}
        if condition in ('C1', 'C2', 'C3') and hasattr(self.transport, 'fresh'):
            self._agent_transports['B'] = self.transport.fresh()

    def _save(self, path, record):
        atomic_json(path, record)
        existed=path.name in self._accounting
        previous, status = self._accounting.get(path.name, (0.0, ''))
        if self._in_scope(record['request_id_local']):
            self._scope_count+=int(not existed)
            self._scope_accounted+=record.get('cost_usd',record['reserved_usd'])-previous
        accounted = record.get('cost_usd', record['reserved_usd'])
        self._accounted += accounted - previous
        self._completed += int(record['status'] == 'complete') - int(status == 'complete')
        self._accounting[path.name] = (accounted, record['status'])

    def records(self):
        from .repair import effective_request
        return [effective_request(self.path.parent, json.loads(p.read_text())) for p in sorted(self.path.glob('*.json'))]

    def totals(self):
        return {'requests': len(self._accounting), 'accounted_usd': max(0.0, self._accounted),
                'completed': self._completed, 'mock': self.mock}

    def report(self):
        by_model = {}
        for r in self.records():
            model = r['payload']['model']
            group = by_model.setdefault(model, {'requests': 0, 'input_tokens': 0, 'output_tokens': 0,
                'cached_input_tokens': 0, 'reasoning_tokens': 0, 'requests_with_usage': 0})
            group['requests'] += 1
            usage = r.get('response', {}).get('usage')
            if usage:
                group['requests_with_usage'] += 1
                group['input_tokens'] += usage['prompt_tokens']
                group['output_tokens'] += usage['completion_tokens']
                group['cached_input_tokens'] += (usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
                group['reasoning_tokens'] += (usage.get('completion_tokens_details') or {}).get('reasoning_tokens', 0)
        records = self.records()
        return {**self.totals(), 'by_model': by_model,
                'known_cost_usd': sum(r.get('cost_usd', 0.0) for r in records),
                'unknown_usage_requests': sum(not bool(r.get('response', {}).get('usage')) for r in records),
                'usage_note': 'Mock usage is fabricated; pending/blocked requests without usage retain their conservative reservation. Reasoning tokens are included in output tokens. Prices are estimates; billing dashboard is authoritative.'}

    def ask(self, request_id, model, prompt, seed, temperature=1.0):
        if model not in PRICES:
            raise StopRun('Unsupported/unpriced OpenAI model')
        system, user, schema = prompt
        payload = {'model': model, 'messages': [{'role': 'system', 'content': system},
                   {'role': 'user', 'content': user}], 'response_format': {'type': 'json_schema', 'json_schema': schema},
                   'max_completion_tokens': 2000}
        if model.startswith('gpt-5'):
            payload['reasoning_effort'] = 'low'
        else:
            payload.update(temperature=temperature, seed=seed)
        path = self.path / (digest(request_id) + '.json')
        fingerprint = digest(payload)
        if path.exists():
            from .repair import effective_request
            previous = effective_request(self.path.parent, json.loads(path.read_text()))
            if previous['payload_hash'] != fingerprint:
                raise StopRun('Resume payload mismatch: refusing changed or duplicate inference')
            if previous['status'] != 'complete':
                raise StopRun('Unresolved prior request; inspect journal before any further inference')
            return copy.deepcopy(previous['parsed'])
        tokens, reserve = reservation(payload)
        totals = self.totals()
        if totals['requests'] >= self.max_requests or totals['accounted_usd'] + reserve > self.budget:
            raise StopRun('Request count or conservative dollar budget limit reached before dispatch')
        if self.scope_prefixes is not None:
            if not self._in_scope(request_id):raise StopRun('Request outside approved checkpoint window')
            if self.scope_max_requests is not None and self._scope_count>=self.scope_max_requests:
                raise StopRun('Checkpoint-window request limit reached')
            if self.scope_budget is not None and self._scope_accounted+reserve>self.scope_budget:
                raise StopRun('Checkpoint-window dollar guard reached')
        record = {'request_id_local': request_id, 'payload_hash': fingerprint, 'payload': payload,
                  'reserved_input_tokens': tokens, 'reserved_usd': reserve, 'status': 'pending',
                  'created_at': datetime.now(timezone.utc).isoformat(),
                  'mock': self.mock, 'billing_route': 'mock' if self.mock else 'direct OpenAI'}
        self._save(path, record)
        try:
            backend = self._agent_transports.get(request_id.rsplit('/', 1)[-1], self.transport)
            response = backend(payload)
            record['response'] = response
            if response.get('endpoint') != ENDPOINT:
                raise StopRun('Unexpected billing endpoint')
            usage = response.get('usage')
            if usage is None:
                raise StopRun('Missing usage; retain reservation and stop')
            returned = response.get('model_returned') or ''
            if returned != model and not returned.startswith(model + '-'):
                raise StopRun('Unexpected returned model')
            record['cost_usd'] = 0.0 if self.mock else usage_cost(model, usage)
            if self.mock:
                record['hypothetical_cost_usd'] = usage_cost(model, usage)
            if record['cost_usd'] > reserve:
                record['reservation_exceeded'] = True
                raise StopRun('Actual usage exceeded conservative reservation; inspect before continuing')
            if response.get('finish_reason') != 'stop':
                raise ValueError('Incomplete generation or refusal')
            parsed = json.loads(response['content'])
            validate(parsed, schema['schema'])
            for name in ('intended_action', 'stated_action', 'choice'):
                if name in parsed and (type(parsed[name]) is not int or not 0 <= parsed[name] <= 5):
                    raise ValueError('Invalid contribution: do not clamp or fabricate actions')
            record.update(status='complete', parsed=parsed, finished_at=datetime.now(timezone.utc).isoformat())
            self._save(path, record)
            return copy.deepcopy(parsed)
        except Exception as error:
            record['finished_at'] = datetime.now(timezone.utc).isoformat()
            record['status'] = 'blocked'
            # Do not copy exception strings: third-party exceptions can contain secrets.
            record['error_type'] = type(error).__name__
            if isinstance(error, HTTPFailure):
                record.update(http_status=error.status, error_code=error.code)
            self._save(path, record)
            raise StopRun(f'Request stopped ({type(error).__name__}); inspect sanitized journal') from None
