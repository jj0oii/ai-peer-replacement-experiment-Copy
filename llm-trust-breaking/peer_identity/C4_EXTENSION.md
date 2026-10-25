# C4: isolated cross-provider extension — offline implementation

Status: offline only. No live compatibility probe or C4 trial has been authorized.
The original 12 checkpoints, 96 C0–C3 results and 5,496 API records are read-only.
This extension is separate from the planned 200-trial main factorial study.

## Implementation and scope

`python -m peer_identity.c4_extension` imports the existing Version 2 game functions;
it does not change models, prompts, measurements, simultaneous information sets,
rounds or mechanics in the original experiment. It verifies checkpoint state hashes,
clones Agent A exactly, and gives fresh B the exact existing C3 public-history handoff.
All twelve source checkpoints have been checked offline. For the staged rollout,
the paid trial CLI currently enables checkpoint 000 only. Enabling checkpoints
001–011 requires a separate reviewed rollout; they are never started automatically.

A stays `gpt-4o-mini` and judges stay `gpt-5-mini`, both direct OpenAI. Only B uses
`google/gemini-2.5-flash-lite` through OpenRouter. The provider request contains
`only: [google-ai-studio]`, `allow_fallbacks: false`, `require_parameters: true`.
Each B response must report provider `Google AI Studio`, the exact requested model,
valid usage, a normal stop, and locally valid structured JSON. Missing/different
provider reporting stops the run; no substitute provider or JSON-only fallback.
The response ID, actual reported provider, endpoint, payload and usage are retained.
Provider verification relies on OpenRouter's response metadata; no live evidence yet.

The runner keeps temperature, supported seed parameter and 2,000 output-token cap.
Seed support is not a guarantee of identical random-number behavior across models.
It uses `max_tokens` on OpenRouter and the existing `max_completion_tokens` on OpenAI.
No global endpoint/model overrides or modifications to main-study allowlists occur.

## Offline validation

```bash
cd /workspace/ai-peer-replacement-experiment-Copy/llm-trust-breaking
.venv/bin/python -m unittest discover -s tests
```

Tests cover five exact schemas, round-10's absent forecast, state cloning and handoff,
provider/role routing (including judges about B), caps, invalid types/bounds/missing
fields, wrong providers, immutable response recovery, pending calls, source changes,
exports and replay without a second dispatch. A complete synthetic probe + trial
has also run against the original checkpoints, with 56 synthetic requests and zero
network calls. Its CSVs are under:
`/workspace/peer-identity-exports/c4-offline-validation-release/exports/`.
Mock results are synthetic, not scientific findings or evidence of live compatibility.

## Live compatibility probe — separate approval required

Five independent paid B-only requests test planning, announcement, decision,
round-6 reflection, and round-10 reflection. Their schemas and prompt templates are
unchanged. Intermediate interactions are constructed with mock responses, not paid
A calls. These are engineering probes, not continuation data or research outcomes.
They do not test A/judge integration; the subsequent complete smoke trial does.

Current standard Google AI Studio catalog prices: $0.10/M input and $0.40/M output.
Five probes allow 10,000 output tokens total; the offline byte-based input allowance
is approximately 54,600 tokens. Conservative token-price estimate: below $0.01;
local guard $0.10 and maximum five requests. No retries, repairs by generation,
or unapproved additional probes. Catalog support does not prove schema acceptance.

Only after explicit approval:

```bash
cd /workspace/ai-peer-replacement-experiment-Copy/llm-trust-breaking
.venv/bin/python -m peer_identity.c4_extension \
  --source outputs/peer-identity/study-200-v2 \
  --output /workspace/peer-identity-exports/c4-gemini-extension \
  --stage probe --approve-paid-probe --max-requests 5 --budget-usd 0.10
```

The configured OpenRouter key's last authenticated balance was $0. No balance or
funding operation is part of this runner. For the probe alone, at least $0.10 usable
OpenRouter balance comfortably covers its guard. For probe + smoke, $0.60 usable
balance covers both local guards combined (conservatively including OpenAI costs,
although those are billed separately). Funding checkout minimums, taxes and fees
must be checked separately; no purchase is authorized or performed. Existing OpenAI
credits must also remain usable. Do not place credentials in command arguments.

## One full smoke continuation — another separate approval required

Requires a successful **live**, not mock, probe in the same extension directory.
51 requests: 20 Gemini B, 21 OpenAI A including recognition, 10 OpenAI judges.
Observed C3 token proxy: roughly $0.03 total; 24k-input/2k-output stress planning
scenario: approximately $0.27. Guard $0.50, maximum 51 trial requests, plus the
five already-recorded probe requests. The guard may safely stop a run early.

```bash
cd /workspace/ai-peer-replacement-experiment-Copy/llm-trust-breaking
.venv/bin/python -m peer_identity.c4_extension \
  --source outputs/peer-identity/study-200-v2 \
  --output /workspace/peer-identity-exports/c4-gemini-extension \
  --stage trial --checkpoint 0 --approve-paid-trial \
  --max-requests 51 --budget-usd 0.50
```

The same command resumes by reusing matching recorded responses. There is no retry
of missing, ambiguous, or invalid responses. A fully received valid response locally
rejected/interrupted before completion may be recovered via a hash-linked sidecar;
the original journal record is never edited during recovery. Do not increase caps
or alter prompts to resolve a live failure. Pending/unknown responses retain their
reservation and block that request. Any failure exits nonzero and saves partial
progress plus a new export snapshot.

## Separate exports and data dictionary

Every export is a new `exports/snapshot-<UTC timestamp>/` directory.
- `rounds.csv`: ten rows per completed trial (two agents × rounds 6–10).
  `checkpoint_id` links to the original source checkpoint; `run_id` identifies the
  extension continuation; `condition=C4`, `behavior_setting=natural`; `round=6..10`;
  `agent=A/B`, `model` is the requested model; `contribution` is actual 0–5 tokens;
  `payoff` is the game payoff; `promise` is the announced 0–5 contribution;
  `message` is the actual public statement; `trust_1_10` and
  `promise_reliability_1_10` are the agent's ratings; `forecast` predicts the partner's
  next contribution (blank at round 10); `factual_correct` checks reported engine facts.
- `detections.csv`: `judgment` is SAME/CHANGED; `confidence` is 0–100; `correct` means
  CHANGED for C4; `evidence_json` preserves every original recognition field.
- `trials.csv`: one row per completed continuation, checkpoint/state hashes, models,
  request count, input/output token totals and accounted USD. Completed trials must
  have exactly 51 validated journal records. Incomplete trials are represented by
  durable progress/raw records and `requests.csv`, not fabricated completed rows.
- `requests.csv`: every attempted probe/trial request, including pending/blocked ones;
  request ID, stage, status, model, endpoint, reported provider, tokens, accounted USD,
  and cost basis. Reservations are not actual bills. Mock costs are zero.
- `metadata.json`: source inventory, initial configuration, prices/code identity,
  commit SHA, mock marker, creation time and exploratory status.
- `raw.jsonl.gz`: original request payloads/responses, result/progress states and
  hash-linked recovery records, sufficient to audit measurements, factual errors,
  forecasts, announcements and recognition. No credentials are intentionally saved.
  Automated credential-pattern checks block exports containing likely key strings.

Original checkpoint IDs and the absolute source study in metadata jointly identify
the relationship; do not treat these as new independent checkpoints. Use a distinct
extension/study label when joining main and C4 data. Do not concatenate overlapping
snapshots. Publish nothing without separate approval.

## Budget and remaining limitations

The runner enforces the unchanged $60 study limit minus $10 reserve. It includes
$0.4954921 Version 1/prior allowance, the current source-study ledger, and **all**
requests in this extension directory (probes and trial). Blocked unknown-cost calls
retain reservations. OpenRouter reported usage cost is preferred when available;
otherwise token prices estimate cost. OpenAI costs remain token-price estimates.
These are local guards, not provider billing ceilings.

Do not run the main study or another extension concurrently. Source mutations stop
dispatch; final source hashes are rechecked. Before any future main-study batch,
its budget preflight must also include this extension's spending: the unchanged
main runner does not automatically read this new ledger. Never create another paid
extension directory to bypass accounting. Account dashboard costs remain authoritative.

C4 changes both model family and serving provider: GPT versus Gemini via OpenRouter.
It does not isolate provider as a causal factor. Natural-only, 12 matched source
checkpoints, and selected earlier checkpoints limit inference; results remain
exploratory. C3 is different OpenAI models/series, not unambiguously one model family.

Realistic risks: provider metadata may be absent, strict schemas may be rejected,
credit/rate limits, latency or incomplete output may stop safely. A live probe is
necessary before claiming compatibility. No live deadline guarantee is possible.
