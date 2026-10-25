"""Sanitized HTTP diagnostics only: no dispatch or retries on import."""
from __future__ import annotations
import json
import re
from .inference import StopRun

SAFE_HEADER_IDS = ('x-request-id', 'x-openrouter-request-id', 'request-id', 'cf-ray')


def sanitized_text(value, secrets=(), limit=1500):
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?i)Bearer\s+[^\s\"\'<>;,]+', 'Bearer [REDACTED]', text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]+', '[REDACTED]', text)
    text = re.sub(r'(?i)(api[_ -]?key|authorization|token[_ -]?secret|password)([\"\'\s:=]+)([^\s,;}]+)', r'\1=[REDACTED]', text)
    return text[:limit]


def safe_error_body(response, payload, secrets=()):
    """Keep only diagnostic fields, not arbitrary metadata, headers or prompt echoes."""
    # Also redact exact sent messages if a provider echoes them in an error.
    secrets = tuple(secrets) + tuple(m.get('content', '') for m in payload.get('messages', []))
    try:
        body = response.json()
    except (ValueError, TypeError):
        return {'format': 'non-json', 'message': 'Non-JSON error body omitted',
                'body_characters': len(getattr(response, 'text', ''))}
    if not isinstance(body, dict):
        return {'format': 'unexpected-json', 'message': 'Non-object body omitted'}
    error = body.get('error', body)
    if not isinstance(error, dict):
        return {'message': sanitized_text(error, secrets)}
    result = {}
    for name in ('code', 'message', 'type', 'status'):
        if name in error and isinstance(error[name], (str, int, float, bool)):
            result[name] = sanitized_text(error[name], secrets)
    metadata = error.get('metadata')
    if isinstance(metadata, dict):
        if isinstance(metadata.get('provider_name'), str):
            result['provider_name'] = sanitized_text(metadata['provider_name'], secrets, 120)
        raw = metadata.get('raw')
        # Nested provider JSON often contains the useful Google error message.
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except (ValueError, TypeError): raw = None
        if isinstance(raw, dict):
            nested = raw.get('error', raw)
            if isinstance(nested, dict):
                result['upstream_error'] = {k: sanitized_text(nested[k], secrets)
                    for k in ('code', 'message', 'status', 'type')
                    if k in nested and isinstance(nested[k], (str, int, float, bool))}
    return result


class RouterDiagnosticFailure(StopRun):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        # Exception text never contains provider error text, URLs with keys, or headers.
        super().__init__('OpenRouter request stopped; sanitized diagnostics available')


def context(payload):
    return {'model': payload.get('model'), 'requested_provider_route': payload.get('provider'),
            'automatic_retry': False}


def http_failure(response, payload, secrets=()):
    identifiers = {name: sanitized_text(response.headers[name], secrets, 160)
                   for name in SAFE_HEADER_IDS if response.headers.get(name)}
    try:
        body = response.json()
        if isinstance(body, dict):
            for name in ('request_id', 'id'):
                value = body.get(name)
                if isinstance(value, str):
                    identifiers['body_' + name] = sanitized_text(value, secrets, 160)
    except (ValueError, TypeError):
        pass
    # Never infer non-billing from HTTP status. A provider may generate before a
    # gateway error. Keep the original reservation until billing is reconciled.
    return RouterDiagnosticFailure({**context(payload), 'http_status': response.status_code,
        'response_disposition': 'http_rejected' if response.status_code != 200 else 'http_accepted_unusable_body', 'provider_acceptance': 'unknown',
        'could_have_incurred_charge': True, 'billing_status': 'unknown_keep_reservation',
        'request_identifiers': identifiers, 'provider_error': safe_error_body(response, payload, secrets)})


def network_failure(payload):
    return RouterDiagnosticFailure({**context(payload), 'http_status': None,
        'response_disposition': 'uncertain', 'provider_acceptance': 'unknown',
        'could_have_incurred_charge': True, 'billing_status': 'unknown_keep_reservation',
        'request_identifiers': {}, 'provider_error': {'message': 'Transport failed without an HTTP response'}})
