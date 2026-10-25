> **Superseded execution command:** the active plan is now [FINAL_STUDY_PLAN.md](FINAL_STUDY_PLAN.md),
> with 25 checkpoints/200 trials and the two-checkpoint pilot as its first budgeted window.
> This earlier standalone pilot document is retained as preparation history; do not execute its old command.

# Experiment 3.3 — small real-pilot proposal (NOT RUN)

Purpose: validate live branching, structured responses, output completeness and real
costs before any larger study. Exactly two independent five-round establishment
checkpoints. Each checkpoint gets C0, C1, C2, C3 in natural AND controlled settings,
one five-round continuation per condition/setting: **16 continuation games total**.
Every valid checkpoint is retained, including low-cooperation histories.

## Models and access

Direct endpoint: `https://api.openai.com/v1/chat/completions` only.

| Role | Exact requested ID |
|---|---|
| Agent A in every round/branch | `gpt-4o-mini` |
| Original B, C0, C1, C2 | `gpt-4o-mini` |
| Different-model B in C3 | `gpt-4.1-mini` |
| External classification judge | `gpt-5-mini` |
| Trust reflection | The reflecting agent's assigned model |

Read-only GET `/v1/models/<id>` checks returned the matching ID for all three models
during preparation. These were not generation calls. Live structured-output behavior
for the replacement model still needs the approved pilot to validate. No OpenRouter,
Claude, other provider, credit purchase or full experiment is included.

## Request count and limits

- Ten generation requests per two-agent round: six play, two judge, two reflection.
- Establishment: 2 checkpoints × 5 rounds × 10 = 100 requests.
- Continuations: 16 × (5 × 10 + one final detection judgment) = 816 requests.
- **Expected generation calls if completed: 916. Hard generation-request limit: 916.**
- Per model: 656 gpt-4o-mini, 80 gpt-4.1-mini, 180 gpt-5-mini.
- No automatic retries, repair calls, model fallback, or extra checkpoints.
- Requests have a maximum of 2,000 generated tokens including reasoning where used.
- Seeds, temperature 1, reasoning effort low, returned snapshots and usage are logged.

## Pricing status — current quote is NOT verified

The official pricing/model documentation pages at `openai.com` and
`developers.openai.com` returned proxy 403 during preparation. Model access is
confirmed, but model metadata does not contain prices. The following are explicitly
**last-known assumptions**, not a claim of verified current pricing:

| Model | Input / million | Cached input / million | Output / million |
|---|---:|---:|---:|
| gpt-4o-mini | $0.15 | $0.075 | $0.60 |
| gpt-4.1-mini | $0.40 | $0.10 | $1.60 |
| gpt-5-mini | $0.25 | $0.025 | $2.00 |

Verify https://openai.com/api/pricing/ and the respective official model pages before
approving paid execution. Update the versioned price table if necessary; do not treat
an old estimate or OpenRouter prices as a current direct OpenAI quote.

Ignoring cache discounts:

| Planning scenario: mean input / output per call | Total estimate |
|---|---:|
| 2,000 / 150 | $0.48 |
| 10,000 / 300 | $2.02 |
| 20,000 / 500 | $3.95 |
| Conservative 20,000 input / full 2,000 output allowance | **$5.27** |

The conservative scenario is not a maximum possible context size: retained history
can grow beyond that mean. The local dollar guard is **$8**. Before every dispatch,
serialized input bytes plus overhead and the full output allowance are reserved at
the versioned model rates. Calls are refused when that reservation would cross $8;
unknown-response costs retain their reservations. The pilot can stop incomplete.

**Important distinction:** the request count is a hard cap. The $8 local admission
limit is enforced by code against its conservative token/price accounting, but it is
not a provider-enforced guarantee of an $8 final bill. Price changes, token-accounting
overhead and delayed billing can differ. No provider billing settings were changed.
OpenAI project monthly budgets should not be assumed to be hard spending caps. If an
absolute provider-enforced $8 bill ceiling is mandatory, this remains an unresolved
prerequisite; do not approve execution on the assumption that the runner guarantees it.

## Exact command — only after separate explicit approval

From `/workspace/collusion_hackathon/llm-trust-breaking`:

```bash
PILOT_DIR="outputs/peer-identity/real-pilot-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid \
  --checkpoints 2 --repetitions 1 \
  --conditions C0 C1 C2 C3 --settings natural controlled \
  --seed 3303 --temperature 1 --controlled-contribution 3 \
  --max-requests 916 --budget-usd 8 --output "$PILOT_DIR"
```

No part of this command has been executed in paid mode. After completion or a safe
stop, export/validate its preserved directory with `export_peer_identity.py`.

## Methodological review

- A's private state and public history are cloned exactly. The first A request at
  round 6 is identical across branches within checkpoint/repetition. Later histories
  naturally diverge. Treatment/model metadata never enter the supplied A prompt.
- C0 retains original B state/client; C1 creates a new B client but restores all its
  information. APIs are stateless, so this is a weak runtime placebo, not proof of a
  persistent server-side agent identity.
- C2/C3 share the same public handoff and lose prior private notes. C3-versus-C2 is
  the cleaner model comparison; C3-versus-C0 also changes available private context.
- Controlled B proposes an action, but its actual contribution is imposed at 3 tokens
  after both decisions and before payoffs. Proposal and intervention are logged
  separately. Communication remains uncontrolled, and B may react to the intervention.
- A's round-6 decision follows announcements but precedes new observed outcomes.
- Explicit recognition is asked only after round 10. SAME/CHANGED can be biased or
  wrong. A lower contribution alone does not establish recognition.
- Natural/controlled analyses stay separate. Two independent relationships are too
  few for reliable power/variance conclusions. The 16 continuations are not 16
  independent established relationships.
- Shared seed schedules reduce matched noise but do not guarantee API determinism.
  Record returned model snapshots and any failures/attrition.
- Cooperation is not evidence of harmful collusion. Provider categories are not a
  numerical behavioral-distance metric. C4 remains disabled.

## Approval gates

1. Teammate review of the synthetic example, protocol and source changes.
2. Confirm current official direct OpenAI prices (currently blocked here).
3. Accept the local guard's limitation, or establish the required true billing cap.
4. Explicit approval for this 916-request pilot and its budget, then execute once.
5. Separate approval and target team repository for any GitHub push or PR publication.
