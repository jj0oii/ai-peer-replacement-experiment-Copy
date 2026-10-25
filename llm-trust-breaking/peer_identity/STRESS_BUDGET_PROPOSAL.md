# Primary budget: full-output stress scenario — approval pending

The scientific design is fixed: **25 independent checkpoints × C0/C1/C2/C3 × natural/
controlled × one continuation = 200 trials**. Models, prompts, memory, five establishment
and five continuation rounds, trust reflections, detection judgments and negative
controls are unchanged. C4 remains disabled. No paid pilot has been launched.

## Verified prices and existing output limit

During this preparation all three official OpenAI model pages were retrieved and
confirmed these standard direct-API USD/million token rates:

| Exact model ID | Input | Cached input | Output | Official source |
|---|---:|---:|---:|---|
| gpt-4o-mini | $0.15 | $0.075 | $0.60 | https://developers.openai.com/api/docs/models/gpt-4o-mini |
| gpt-4.1-mini | $0.40 | $0.10 | $1.60 | https://developers.openai.com/api/docs/models/gpt-4.1-mini |
| gpt-5-mini | $0.25 | $0.025 | $2.00 | https://developers.openai.com/api/docs/models/gpt-5-mini |

Verification time, source hashes and excerpts are in `PRICING_VERIFICATION.json`.
The main pricing landing page still returned 403, but these official model-specific
pages were accessible. No OpenRouter prices, cache savings or Batch API discount
are assumed. Prices can change; this is a quote checked at the recorded time.

The existing study transport sets **max_completion_tokens=2000 on every request**.
This limit is unchanged, including the judge; reasoning tokens count inside it. It
is the experiment's configured limit, not each model's maximum supported capacity.
No response shortening, prompt compression, model substitution or procedure change
has been introduced to make the cheaper estimate fit.

Primary planning assumption: **20,000 input tokens plus the full 2,000 output-token
allowance per request**. Full output is conservative; 20k input is still a scenario,
not a guaranteed upper bound on growing histories. The local pre-call guard uses
its own input-byte/overhead bound and can stop earlier if necessary.

## Full study cost breakdown (including the pilot)

10 generation calls per two-agent round: 6 play, 2 classification judge, 2 trust
reflections. Each continuation adds one final recognition judgment.

| Disjoint component | Model/calls | Input cost | Full output cost | Total |
|---|---|---:|---:|---:|
| Checkpoint establishment, excluding classification judges | 1,000 gpt-4o-mini | $3.00 | $1.20 | $4.20 |
| Continuations/reflections/detections, excluding classification judges | 7,200 gpt-4o-mini | $21.60 | $8.64 | $30.24 |
| Continuations/reflections with different B | 1,000 gpt-4.1-mini | $8.00 | $3.20 | $11.20 |
| Classification judging across both phases | 2,250 gpt-5-mini | $11.25 | $9.00 | $20.25 |
| **Total** | **11,450 requests** | **$43.85** | **$22.04** | **$65.89** |

Thus checkpoint establishment excluding judges costs $4.20; continuations excluding
judges cost $41.44; classification judging costs $20.25. If judges are instead allocated
to each phase, establishment is $6.45 (1,250 requests) and continuations are $59.44
(10,200 requests). These are alternative presentations of the same $65.89, not additive
extra charges. Per-model totals: $34.44 / $11.20 / $20.25 respectively.

The 2-checkpoint/16-continuation pilot is 8% of the design: **916 requests, $5.2712
under the same scenario**. This pilot is included in the 25 checkpoints and total
cost, not purchased again. Current known earlier smoke-test spending is covered by
the existing $0.01 prior-spend allowance; check for additional external costs before
initializing the real ledger.

## Proposed total versus currently allowed limit

- Full-output primary estimate: **$65.89**.
- Prior-spend allowance: **$0.01**.
- Requested safety reserve: **$10**.
- Nominal minimum with reserve: **$75.90**.
- **Recommended authorization: $80 total**, leaving $70 less prior allowance for the
  request ledger, the $10 reserve, and approximately $4.10 extra working margin over
  the nominal scenario.

**The increase is NOT approved or applied. The cumulative policy remains $60.** Its
current $10 reserve and $0.01 prior allowance leave $49.99 for study requests. That
policy cannot fund the primary full-study scenario. We can separately request the
unchanged pilot under that existing policy, but must not quietly launch the remaining
study on the middle estimate or silently reduce the sample.

$80 is a conservative recommendation for this scenario, not an absolute guarantee.
Actual input histories may exceed 20k; failures consume costs; providers may change
prices. Local guards cannot guarantee the final provider bill. Unknown requests keep
reservations, and there are no automatic retries or paid parse-repair calls.

## Command 1 — proposed pilot only, current $60 cumulative policy

Requires explicit approval before execution. Only checkpoints 0 and 1 run; the
25-checkpoint declaration preserves their identities in the final study ledger.

```bash
cd /workspace/collusion_hackathon/llm-trust-breaking
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid \
  --checkpoints 25 --repetitions 1 \
  --checkpoint-start 0 --checkpoint-count 2 \
  --conditions C0 C1 C2 C3 --settings natural controlled \
  --seed 3303 --temperature 1 --controlled-contribution 3 \
  --max-requests 11450 --batch-max-requests 916 \
  --budget-usd 50 --batch-budget-usd 8 \
  --study-total-budget-usd 60 --reserve-usd 10 --prior-spend-usd 0.01 \
  --export-after-batch --export-root /workspace/peer-identity-exports/study-200 \
  --output outputs/peer-identity/study-200-v1
```

The pilot's **$8 window guard and 916-call limit remain unchanged**. No batch advances
automatically. All eight conditions start A from identical saved state. Completed
pilot data count toward 25 only while the scientific protocol remains equivalent.

## Command 2 — free refinement after the approved pilot completes

```bash
.venv/bin/python experiments/estimate_peer_study.py \
  --pilot outputs/peer-identity/study-200-v1
```

Observed per-model/per-phase costs replace forecasts for completed calls. The PRIMARY
remaining-call forecast still reserves all **2,000 output tokens**, and uses at least
20k input per call, raised when observed maxima or 1.5× observed means are larger.
Short actual pilot responses do not lower the full-output allowance for remaining
calls. Supplemental mean-output scenarios remain labelled reference estimates.
Mock tokens are rejected as actual cost evidence. Two relationships do not establish
a reliable statistical upper tail, so inspect observed length/truncation/failure
rates and retain reserve. Update this plan before authorizing another window.

## Command 3 — proposed budget amendment, only after separate approval

This is a local budget-policy change, not an API call. It preserves all request
records, checkpoint IDs, scientific config, window limits and the 11,450-request
ceiling. It records the old/new policy in exported `budget-history/` audit files.
It has NOT been executed against any real or saved study ledger during preparation.

After the user approves the increase (and preferably after reviewing the pilot):

```bash
.venv/bin/python experiments/amend_peer_budget.py outputs/peer-identity/study-200-v1 \
  --new-total 80 --reserve 10 --expected-current-total 60 --approve-budget-change
```

Omit `--approve-budget-change` for a preview with no policy change. The real canonical
ledger must already exist. The command refuses an unexpected starting policy; do not
manually reset or replace budget files. Offline tests exercised amendments only in
throwaway temporary directories.

## Command 4 — later batch example, only after its approval AND budget amendment

After pilot review, next window is global checkpoints 2–6, 40 continuations, at most
2,290 generation calls. The full-output estimate is $13.178, so a $16 batch guard
allows some input variation while the cumulative policy continues to dominate.

```bash
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid --resume \
  --checkpoints 25 --repetitions 1 --checkpoint-start 2 --checkpoint-count 5 \
  --conditions C0 C1 C2 C3 --settings natural controlled \
  --seed 3303 --temperature 1 --controlled-contribution 3 \
  --max-requests 11450 --batch-max-requests 2290 \
  --budget-usd 70 --batch-budget-usd 16 \
  --study-total-budget-usd 80 --reserve-usd 10 --prior-spend-usd 0.01 \
  --export-after-batch --export-root /workspace/peer-identity-exports/study-200 \
  --output outputs/peer-identity/study-200-v1
```

Subsequent windows remain 7–11, 12–16, 17–21, and 22–24 (the last is 3 checkpoints,
24 continuations, 1,374 calls; propose a $10 window guard for it). Same raw ledger,
unique validated export per attempt/window, no duplicated checkpoints or paid calls.
Cumulative accounting never resets per batch, and window caps are not extra money.
Full study remains exactly 200 trials; a budget stop is incomplete data, not permission
to redefine the target. No GitHub push, cross-provider run or purchase is authorized.
