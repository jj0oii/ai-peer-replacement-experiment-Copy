# C4 HTTP diagnostic repair — offline only

No paid request, metadata request, retry, or publication was performed during this
repair. All 5,775 existing protected files (canonical V2 study and C4 extension)
were verified byte-for-byte unchanged. Original core protocol, inference and
measurement modules are unchanged. Agent A's paid planning response is preserved.

## Confirmed findings

The successful live planning probe and failed checkpoint-000 B planning attempt
have exactly the same payload, including the full prompt:

- Payload SHA-256: `74a950fa21f6e59d8e2a3b1cfdbd68874f60d73cffc44a8c6da0c8cd237e685c`.
- Canonical payload: 7,744 bytes; system message 6,399 bytes, user message 477 bytes.
- Identical JSON schema, model, Google AI Studio pin, disabled fallbacks, strict
  parameter requirement, 2,000 output cap, temperature 1.0 and seed 3915.
- Successful probe used 1,541 input and 84 output tokens, cost $0.0001877.

Thus the probe already tested the *full-length* real B planning prompt. The failure
was not caused by increasing its length or changing any listed request parameter.
Routing/schema/settings were supported by an actual successful identical request.
This is evidence of compatibility, not a guarantee of permanent route availability.

The runner uses `requests.Session.post`, not an OpenRouter SDK. In its previous
version the only RouterTransport branch raising StopRun before returning a response
was HTTP status != 200. The journal saved only the exception class and suppressed
exception chaining. It saved no HTTP status, body, response ID or headers for that
failed attempt. The subprocess exited. The original exact HTTP details cannot be
recovered from the preserved journal, diagnostic report, or captured traceback.

A transient gateway/provider availability error is plausible; rate limiting,
authentication or other HTTP rejection cannot be excluded without its status/body.
The post-failure account metadata previously saved in smoke-diagnostic.json showed
$4.998886 usable balance and only the $0.001114 probe spending. That supports but
does not prove an uncharged failure. No new account check was made during this repair.
A new attempt cannot retrospectively establish the original HTTP error code.

## Minimal software correction

`c4_http_diagnostics.py` introduces a diagnostic exception with allowlisted fields:
HTTP status; bounded/redacted error code/message and nested upstream error;
allowlisted request identifiers; requested model/provider routing; accepted,
rejected or uncertain disposition; and conservative billing uncertainty.

`c4_extension.py` now attaches that diagnostic to *new* journal failures. It also
records successful-response HTTP metadata. Transport failures retain no raw
exception text. Only allowlisted header identifiers are copied; Authorization,
cookies, arbitrary metadata and non-JSON bodies are omitted. Known keys, key-like
strings, bearer credentials and complete sent-message echoes are redacted.
HTTP errors never imply zero cost. Unknown billing retains the reservation.

The request payload constructor, schemas, prompts, model choices, token caps,
provider routing, retry behavior and game protocol are unchanged. No probe result
was relabeled as research data. The software correction affects diagnostics only.

Regression tests cover status/body/request IDs, upstream errors, redaction,
non-JSON bodies, timeouts, accepted versus locally rejected responses, bounded
messages, persistent reservations, no retries and reuse of successful A output.
The complete offline suite passed: 155 tests. Python syntax checks passed.

## Recovery recommendation and limits

No offline response recovery is possible: the failed B attempt has no saved model
response. It is **not** safe to silently mark it complete or delete its reservation.
A new identical B request requires separate explicit paid authorization, with at
most **1 new request**, a **$0.01 new spending guard**, and no automatic retry.
The successful A request must be reused, never resent. Keep the original failed
attempt and $0.0016768 reservation, and attach any new result as an explicit,
hash-linked replacement attempt rather than overwriting the old record.

This is a conditional GO for one controlled recovery attempt after approval,
not a GO for unattended smoke completion or the remaining 11 continuations.
Duplicate upstream billing cannot be excluded because acceptance is unknown and
this API has no verified idempotency guarantee. Future request IDs do not guarantee
deduplication of the original attempt.

Existing CLI resume deliberately remains blocked: the unresolved request is still
blocked, and the logging correction changes the extension code identity. The
original manifest is unchanged. Before executing recovery, prepare an explicitly
reviewed code-identity correction and single-attempt recovery path; do not bypass
either guard by editing the original manifest or journal. No retry bypass was added
in this repair. A separate machine-readable old/new code hash record is saved at
`/workspace/peer-identity-exports/c4-diagnostic-review/offline-review.json`.

If all 51 scientific requests ultimately succeed after this one failure, the smoke
will have used **52 attempted trial requests**, not the originally approved 51.
Completing it would therefore require explicit later approval of that request-cap
adjustment. No request cap, $0.50 smoke guard, $60 cumulative limit or $10 reserve
was changed here. Exactly 12 C4 trials remain the intended extension; none complete.
