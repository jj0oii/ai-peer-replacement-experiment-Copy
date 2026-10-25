# Version 2 pilot — prepared, NOT authorized for paid execution

The original Version 1 paid data remain at `outputs/peer-identity/study-200-v1`.
The new canonical PAID Version 2 root is `outputs/peer-identity/study-200-v2`.
Do not use a mock root for paid data. The full plan is 25 NEW checkpoints, four
conditions × two behavior settings × one continuation = 200 trials. This command
executes ONLY checkpoint indexes 0–1: exactly two checkpoints and 16 continuations.
There is no automatic subsequent batch. Resume only this same canonical root with
`--resume` after reviewing a stopped run; uncertain requests are not resent.

## Budget and cost estimate

No budget increase is approved. Total stays $60; reserve $10. Prior allowance is
$0.4954921 = Version 1 recorded $0.4854921 plus the existing $0.01 allowance for
other prior smoke usage. V2 request ledger ceiling is $49.5045079. All future V2
windows must share this root/policy; the old V1 study is frozen. This is cumulative
local accounting, not an OpenAI account-wide/provider billing ceiling. Other API
work and incorrect rate/token estimates can escape local accounting. No concurrent
or alternative study roots are authorized. The CLI rejects paid V2 attempts omitting
the $60 cumulative policy or reducing the historical allowance below $0.4954921.

Prices use the official-model-page receipt verified 2026-10-24 in
PRICING_VERIFICATION.json, not mock token usage: per million uncached input/output,
gpt-4o-mini $0.15/$0.60; gpt-4.1-mini $0.40/$1.60; gpt-5-mini $0.25/$2.00.
No cache discount is assumed in forecasts. Future approval should recheck prices
if execution is delayed or models/prices change. No new pricing or inference API
request was needed for this offline implementation.

Keep the conservative FULL-OUTPUT assumption: 2000 output tokens on EVERY call,
including reasoning output. No response limits or strategies are shortened. Add a
provisional 20% input allowance, 24,000 rather than 20,000 tokens/call, for longer
measurements and accumulated private memory. This is a planning assumption, not a
measured upper bound. Actual prompt growth can exceed it; pre-dispatch reservations
and local guards stop safely. The new measurements use existing requests, so call
counts are unchanged. Expanded outputs consume the existing 2000-token allowance.
The old $0.485 pilot is not an estimate of the new pilot's actual cost.

| Disjoint phase | Model | Pilot requests | Pilot stress dollars |
|---|---|---:|---:|
| Establishment, excluding judges | gpt-4o-mini |80|0.3840|
| Continuations, including recognition, excluding judges | gpt-4o-mini |576|2.7648|
| Continuations, excluding judges | gpt-4.1-mini |80|1.0240|
| Judging, establishment and continuations | gpt-5-mini |180|1.8000|
| Total | |916|5.9728|

By model: gpt-4o-mini $3.1488 (656 requests), gpt-4.1-mini $1.024 (80),
gpt-5-mini $1.80 (180). Inclusive of its judges, establishment is $0.584 and
continuations $5.3888. Pilot hard local guards remain $8 and 916 requests, with no
repair retries. Guards include conservative reservations and may stop before all
trials finish. An incomplete run and partial export are retained, never fabricated.

At unchanged 20k/2k assumptions the stress estimate is still $5.2712 for this pilot
and $65.89 for V2's 200 trials; the additional provisional input allowance adds
$0.7016 to the pilot and $8.77 to the study. At 24k/2k the full V2 forecast is:
establishment excluding judges $4.80; continuations excluding judges $47.36;
judging $22.50; total $74.66. With prior allowance and $10 reserve, planning total
is **$85.1554921**. This does NOT fit the currently approved $60 conservative
plan. No higher spending limit has been applied or requested by a tool.

GO for a separately approved small pilot, subject to measurement review and guards;
NO-GO for automatic 200-trial rollout under the present stress forecast. After the
pilot, use actual per-model input/output/cache/reasoning usage and costs to refine
remaining full-output estimates (retain 2000 outputs; at least 24000 inputs, raised
if observed maxima/1.5×means require it). Do not silently reduce 200 trials.

## Exact proposed paid-pilot command — DO NOT RUN without explicit authorization

Run from `llm-trust-breaking`:

```bash
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid --protocol-version v2 \
  --checkpoints 25 --repetitions 1 \
  --checkpoint-start 0 --checkpoint-count 2 \
  --conditions C0 C1 C2 C3 --settings natural controlled \
  --seed 3303 --temperature 1 --controlled-contribution 3 \
  --max-requests 11450 --batch-max-requests 916 \
  --budget-usd 49.5045079 --batch-budget-usd 8 \
  --study-total-budget-usd 60 --reserve-usd 10 --prior-spend-usd 0.4954921 \
  --export-after-batch --export-root /workspace/peer-identity-exports/study-200-v2 \
  --output outputs/peer-identity/study-200-v2
```

`--max-requests` is the cumulative 25-checkpoint cap. The active two-checkpoint
window has the stricter 916 cap; this command does not execute other windows.
Direct OpenAI transport remains unchanged. Do not run `poseidon-run`.

## Offline reproduction and export

Choose new, unused output and export directories (never overwrite sealed results).
For a complete two-checkpoint synthetic pilot:

```bash
.venv/bin/python experiments/run_peer_identity.py \
  --mode mock --protocol-version v2 --checkpoints 2 \
  --checkpoint-count 2 --max-requests 916 --batch-max-requests 916 \
  --budget-usd 49.5045079 --batch-budget-usd 8 \
  --study-total-budget-usd 60 --reserve-usd 10 --prior-spend-usd 0.4954921 \
  --export-after-batch --export-root /workspace/peer-identity-exports/v2-mock-new \
  --output outputs/peer-identity/v2-mock-new
.venv/bin/python -m unittest discover -s tests
.venv/bin/python experiments/export_peer_identity.py outputs/peer-identity/v2-mock-new \
  --output /workspace/peer-identity-exports/v2-manual-new
.venv/bin/python experiments/export_peer_identity.py \
  /workspace/peer-identity-exports/v2-manual-new --verify-export
```

From a downloaded bundle: `python analyze.py --output ../analysis-new` and
`python charts.py --output ../charts-new`. CSV analysis needs Python's standard
library; charts require matplotlib. All mock data are synthetic, not findings.
Follow SHARING.md to prepare a dedicated branch/PR when authorized; no remote
settings, pushes or paid runs are part of these instructions' implementation.
