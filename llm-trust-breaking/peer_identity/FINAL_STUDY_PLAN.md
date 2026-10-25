# Active final design: 200 trials; full-output budget proposal pending

**Budget update:** [STRESS_BUDGET_PROPOSAL.md](STRESS_BUDGET_PROPOSAL.md) is the active
budget-planning document. The PRIMARY assumption is now full-output stress ($65.89
at verified rates), with $80 recommended including a $10 reserve. The increase is
not approved/applied: the $60 cumulative policy and $8 pilot guard remain intact.
Middle/higher-input estimates below are references, not the execution planning basis.

This supersedes the earlier 30-checkpoint × 3-repetition planning target and standalone
pilot command. No paid pilot or full experiment has been run. The user wants roughly
$60 as a planning frame, not a precisely consumed amount. We retain a conservative
$60 local cumulative policy with a $10 reserve, subject to review after actual pilot
costs. A different spending frame requires explicit authorization before execution.

## Fixed scientific design

**25 independent checkpoints × 4 swap conditions × 2 behavior settings × 1
continuation = 200 trials.** Each C0/C1/C2/C3 has 25 natural and 25 controlled trials.
Each checkpoint establishes A/original B for rounds 1–5 once, then clones into all
eight continuations for rounds 6–10. No additional cross-provider condition is enabled.

Public Goods rules, private planning/public announcement/final decision/trust
reflection stages, end-of-game SAME/CHANGED question, trust scales, controlled-B
contribution 3, model assignments, inference settings and high-trust subgroup rule
are unchanged. A's checkpoint state is identical across its branches. Negative
controls remain C0 no swap and C1 sham with restored information. C2 resets B's
private context; C3 uses the same handoff/reset with a different model.

Models: A/original B/C0/C1/C2 use gpt-4o-mini; C3 B uses gpt-4.1-mini; external judge
uses gpt-5-mini; each reflection uses the reflecting agent's model. Direct OpenAI only.
No model/prompt/history compression or output-token limit has been changed to save money.

## Cost optimization already safe to use

1. Establish each relationship only once and reuse its exact checkpoint for all eight
   branches: 25 establishment histories, not 200 regenerated histories.
2. The two-checkpoint pilot IS checkpoints 0–1 of the same canonical 25-checkpoint
   study, with the same prompts/settings and global seed schedule. Do not pay for it
   again or add it as checkpoints 26–27.
3. Resume saved stage responses and finished branches without repeated paid calls.
   Errors/pending ambiguous calls require review rather than automatic retry/repair.
4. Keep the existing compact serialized memory and structured outputs. Standard
   provider prompt-cache savings may reduce actual cost, but are not assumed in forecasts.
5. Use independent checkpoint windows in the SAME raw study directory and ledger;
   each window produces a new immutable export. No global budget resets between windows.

Same payloads are produced in split and unsplit execution (tested). This is execution
batching only, not OpenAI's asynchronous Batch API: no Batch API discount is assumed.
Actual model outputs can still vary across time/provider snapshots despite seed reuse.

## Calls and cost estimates

Full study: 25 × (50 establishment + 8 × 51 continuation/detection) = **11,450
maximum generation requests** without retries. Total game rounds: 125 establishment
+ 1,000 continuation = 1,125. Exactly 200 final detection judgments.

Disjoint accounting (judge calls are separated to avoid double counting):

| Component | Requests/models | Middle scenario | Higher-input scenario | Full-output stress |
|---|---|---:|---:|---:|
| Checkpoint establishment, excluding judging | 1,000 gpt-4o-mini | $1.68 | $3.30 | $4.20 |
| Continuations, reflections and final detections, excluding judging | 7,200 gpt-4o-mini + 1,000 gpt-4.1-mini | $16.58 | $32.56 | $41.44 |
| Judging across establishment and continuations | 2,250 gpt-5-mini | $6.98 | $13.50 | $20.25 |
| **Total** | **11,450** | **$25.23** | **$49.36** | **$65.89** |

Middle = mean 10k input/300 output per request; higher-input = 20k/500; stress =
20k/full 2,000 output allowance. Low 2k/150 scenario is $6.04, not a reliable forecast.
Input history can exceed these means. These are scenarios, NOT confidence bounds.
The middle model totals are $13.78 (gpt-4o-mini), $4.48 (gpt-4.1-mini), $6.98 (judge).

Official model-page rates were verified during the latest preparation; see
`PRICING_VERIFICATION.json` for retrieval time, source hashes and excerpts. Rates in
USD/million input/cached/output: .15/.075/.60 for gpt-4o-mini,
.40/.10/1.60 for gpt-4.1-mini, .25/.025/2 for gpt-5-mini. The main pricing landing page returned 403, but all three official model-specific
pages were retrieved successfully. Recheck if significant time elapses before execution. Cache discounts are not assumed.

The pilot is 916 generation calls: estimated $2.02 middle, $3.95 higher-input,
$5.27 full-output stress. Its expenditure is part of these full-study totals, not
added afterward. The earlier successful 8-call diners smoke is not a scientifically
eligible checkpoint. Its estimated $0.00124215 is covered by a conservative **$0.01
prior-spend allowance**. Check for any other study-related charges before initialization;
if prior costs exceed that allowance, configure the actual higher allowance up front.

### What fits, and what does not

The PRIMARY full-output scenario exceeds the unamended $60 policy before reserve.
Recommend $80 total including $10 reserve, but do not apply it without explicit
approval. Do not substitute a middle-case forecast to claim the study fits. We will not silently reduce N or stop at fewer
trials and call the study complete. If observed costs predict a budget overrun,
pause and present the funding or methodological tradeoff for approval.

Potential changes NOT applied:

- Remove external LLM judging and retain action-based promise-breaking measures:
  saves 2,250 calls ($6.98 middle / $20.25 stress) while retaining behavioral outcomes,
  trust reflections, detections and controls, BUT loses the starter's semantic judge
  labels. Requires approval and an explicit equivalence decision for pilot inclusion.
- Use a cheaper judge after checking classification quality: changes the measurement
  instrument and requires approval. Changing A/B/replacement models changes the
  scientific contrast; it is not a silent cost optimization.
- Summarize/truncate/deduplicate displayed memory or reduce output allowances: can
  alter memory salience, private-state discontinuity or truncation rates; requires
  approval and a frozen revised protocol. No such change is currently implemented.

## One cumulative ledger, reserve and safe stopping

All study requests—including the pilot, resumed windows and any failed attempts—use
`outputs/peer-identity/study-200-v1/requests`. The persistent `budget-policy.json`
records $60 total, $10 reserve and $0.01 prior-spend allowance: **$49.99 is available
to that request ledger**. The normal CLI request budget is $50, further bounded by
this policy. Paid mode never resets spending on the next batch. Persisted global
limits remain enforced even if total-budget flags are omitted on a later resume.
The saved policy rejects silently changing totals/reserve/prior allowance.

The pilot also has its own **916-request / $8 window guard**. Scope limits count
all previous requests for its checkpoint window, even after process restart. The
full-study cap is 11,450 requests. The policy is local, not an account-wide meter:
all study commands MUST use this canonical directory. Unrelated manual API requests
or different directories are not automatically counted; include external prior
charges explicitly. Never make a fresh study directory to evade a guard.

Reservations use conservative input-byte/overhead estimates plus full output allowance;
unknown costs retain their reservation. A guard can stop a batch before it finishes.
The $10 reserve is not automatically released. If pilot evidence suggests releasing
part of the reserve is reasonable within the approximate $60 frame, present that
change for approval rather than silently editing the stored policy.

Local guards cannot guarantee an absolute provider billing ceiling. Versioned prices,
token accounting and actual provider billing can differ; provider project budgets
must not be assumed hard caps. Do not spend more just because the account has credits.

## Resumable batch schedule

| Window | Global checkpoint indexes (zero-based) | New checkpoints | Continuation trials | Request cap for window |
|---|---|---:|---:|---:|
| Pilot | 0–1 | 2 | 16 | 916 |
| B2 | 2–6 | 5 | 40 | 2,290 |
| B3 | 7–11 | 5 | 40 | 2,290 |
| B4 | 12–16 | 5 | 40 | 2,290 |
| B5 | 17–21 | 5 | 40 | 2,290 |
| B6 | 22–24 | 3 | 24 | 1,374 |
| **Total** | **0–24** | **25** | **200** | **11,450** |

Each execution attempt has its own UUID/time record and immutable export directory.
The canonical raw directory and checkpoint IDs persist. Intermediate exports include
planned/unstarted trials explicitly; choose ONE export snapshot per study for pooled
analysis, rather than concatenating snapshots and double-counting the same run IDs.
Exports, dictionary, run_metrics.csv, charts and teammate GitHub workflow remain intact.
No push/PR is automatic.

## Exact pilot command — NOT EXECUTED; requires explicit approval

From `/workspace/collusion_hackathon/llm-trust-breaking`:

```bash
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

`--checkpoints 25` declares the final study, not pilot execution size: only the first
TWO checkpoints execute because `--checkpoint-count 2` limits this window. The pilot
has at most 916 calls. Initial export will contain 16 completed and 184 unstarted
planned continuations, assuming no errors. Nothing auto-advances to B2.

For an interrupted pilot, repeat the exact command with `--resume`; complete responses
are reused. A pending/blocked inference remains a manual-review stop.

After review/approval of a later window, use the SAME command/root plus `--resume`,
change the start/count to its row above, set its batch request cap, and set an approved
window dollar limit (e.g. $12 for a five-checkpoint window). The cumulative global cap
still dominates; per-window allowances are not extra money. Never execute all windows
as an unattended loop before pilot review.

## Pilot inclusion and actual-cost refinement

Pilot checkpoints count toward 25 ONLY while the scientific configuration remains
equivalent: Public Goods parameters, displayed identities, stage prompts/full memory,
private-state reset/handoff, models/settings, rounds, controlled policy, qualification
and outcome definitions all match. The proposed pilot uses the exact final config
and global indexes. Export-only changes do not change what agents saw. A substantive
post-pilot revision needs an explicit decision; do not automatically pool incompatible
pilot data or incur replacement checkpoints without revisiting the $60 plan.

Free pre-run scenario calculation:

```bash
.venv/bin/python experiments/estimate_peer_study.py
```

AFTER the real pilot is authorized and completes, refine using actual per-model,
per-phase token usage/costs (without another model call):

```bash
.venv/bin/python experiments/estimate_peer_study.py \
  --pilot outputs/peer-identity/study-200-v1
```

This reports observed spending, remaining-request estimates without assuming cache
savings, and an explicitly labelled token-growth stress scenario. It rejects treating
mock tokens as actual cost evidence and requires two complete independent checkpoints.
The next window should be authorized only after reviewing projection, reserve, failed
requests and comparability. Two checkpoints cannot guarantee a reliable upper tail.
