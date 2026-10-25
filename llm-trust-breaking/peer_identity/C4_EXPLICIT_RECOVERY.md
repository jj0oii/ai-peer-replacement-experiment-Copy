# Checkpoint-000 C4: one explicitly authorized replacement attempt

The single-request CLI is `python -m peer_identity.c4_recovery`. It never runs a
round or constructs an OpenAI transport. It reads the original blocked request,
checks its fixed payload hash, compares it with the successful exact live probe,
and reconstructs the prompt offline to verify equality. It also checks original
source, scientific code and prompt hashes and the reviewed diagnostic correction.

It writes new files only in the extension's `explicit-recovery/` directory:
- `software-correction.json`: old/new extension identity, diagnostic/recovery module
  hashes, original manifest and request hashes, preserved successful A hash,
  authorization scope, budgets and original journal inventory.
- `attempt-1.json`: one new payload and response, linked to the immutable failed
  original by ID and hash. Durable pending intent is saved BEFORE dispatch.
- `accounting.json`: separate new charge/reservation and retained original unknown
  reservation. The $60 study limit, $10 reserve and $0.50 trial guard also apply.

An existing `attempt-1.json` of **any** status prevents dispatch. No automatic retry,
no alternate provider, no second model and no conversion of the earlier probe to
research data. A failure records sanitized HTTP diagnostics and stops. The original
journal, manifest and prior exports are not rewritten. A remains a saved response.

The approved single-request command is:

```bash
.venv/bin/python -m peer_identity.c4_recovery \
  --output /workspace/peer-identity-exports/c4-gemini-extension \
  --approve-one-paid-recovery --max-new-requests 1 --budget-usd 0.01
```

## Future smoke completion: NOT authorized by the recovery approval

`c4_resume_smoke.py` is a separately gated, checkpoint-000-only completion runner.
It requires a fully validated successful recovery and verifies the correction
receipt, original journal, payload, scientific code and source checkpoint hashes.
It replays A's original planning response and B's new recovery response without
sending either request. It permits at most 49 further generation attempts, 52
lifetime trial attempts including the original failed attempt, and the unchanged
$0.50 trial spending guard. The original unknown-cost reservation remains counted.
It cannot start checkpoint 001 or generate establishment rounds.

Only if recovery succeeds and the user separately approves completion:

```bash
cd /workspace/ai-peer-replacement-experiment-Copy/llm-trust-breaking
.venv/bin/python -m peer_identity.c4_resume_smoke \
  --output /workspace/peer-identity-exports/c4-gemini-extension \
  --approve-paid-completion --max-new-requests 49 \
  --max-total-trial-attempts 52 --trial-budget-usd 0.50
```

The original `c4_extension --stage trial` command intentionally remains blocked by
its original software identity and failed record. Do not edit those records or
raise its original limit. Use only the explicit correction-aware completion path
after approval. A new failed completion request also blocks normal replay; there
is no general-purpose paid retry mechanism.

## Completion export semantics

New `exports/recovered-snapshot-...` directories contain the existing analysis
CSVs for logical game requests plus `attempts.csv` for **all** physical attempts,
including the original failed request and its separate paid replacement.
`requests.csv` is the validated logical-response view; its one replacement response
is labeled with its physical recovery ID. The original failed record, new physical
attempt, software correction and all actual request records are retained in raw
JSONL audit data. Metadata and accounting retain unknown-cost reservations and
physical counts. Never interpret an accounted reservation as a confirmed charge.
The original canonical 96-trial dataset remains a separate unchanged study.
