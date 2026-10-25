# Version 2 local analysis and next-batch budget review

**Recommendation: GO for separately authorizing one five-checkpoint batch. No paid
execution is authorized by this review. NO-GO for committing the entire remaining
study under the full-output stress forecast with the unchanged $60 limit.**

All 131 offline tests pass (114 previous + 17 statistical/budget regressions). No
models, prompts, treatment procedures, seeds, token allowances or measurements changed.
No paid calls, new checkpoints, budget-policy changes or GitHub pushes occurred.

## Pilot inclusion and statistical unit

The completed Version 2 pilot has two checkpoints and 16 continuation trials, all
complete. Both checkpoints count toward the planned **25 × 4 × 2 × 1 = 200 trials**
if the current protocol is preserved. The code-identity receipt still matches. The
empty-string software correction accepted the original recorded response without
changing prompts or making another paid call. V1 checkpoints/results remain separate.

Only **two independently established relationships** are observed. The 16 games are
matched branches, not 16 independent starting histories. Current intervals are broad;
small observed differences or equal actions do not establish equivalence or no effect.

## Implemented matched analyses

The standalone `matched_statistics.py` tool matches repetition IDs within checkpoint
and setting, averages matched repetitions within checkpoint, and then gives checkpoints
equal weight. It computes C3−C2, C2−C1 and C1−C0 separately under natural/controlled
behavior for both agents where applicable. Recognition belongs to Agent A only.

The table shows Agent A checkpoint-weighted differences. Baselines are rounds 3–5;
identical matched baselines cancel. Trust/reliability numeric means are descriptive
summaries of ordinal judgments, not equal psychological distances.

| Setting | Contrast | Sustained contribution change | Trust change | Mean reliability | Partner promise compliance rate | Forecast MAE |
|---|---|---:|---:|---:|---:|---:|
| Natural | C3−C2 |0.0|+0.5|+0.3|+0.1|−0.125|
| Natural | C2−C1 |0.0|−0.4|−0.3|−0.1|+0.125|
| Natural | C1−C0 |0.0|−0.3|0.0|0.0|0.0|
| Controlled | C3−C2 |−0.4|−0.9|−1.8|−0.6|+0.375|
| Controlled | C2−C1 |+0.4|+1.0|+2.4|+0.6|0.0|
| Controlled | C1−C0 |−0.4|−0.3|−1.0|−0.2|+0.375|

Every immediate contribution contrast was zero. For these six sustained contribution
contrasts the conservative 95% intervals are **[−5,5]**; trust/reliability differences
have **[−9,9]** intervals, compliance differences **[−1,1]**, and forecast MAE differences
**[−5,5]**. The data are far too sparse to support confident rankings.

Intervals use bounded-outcome Hoeffding inequalities over independent checkpoint
means. They remain wide even with equal observed values, avoiding misleading
zero-width bootstrap intervals from n=2. Within a single condition/setting, one binary
recognition outcome per checkpoint additionally receives an exact Clopper–Pearson
interval. For 0/2 it is [0,0.8419]; 1/2 [0.0126,0.9874]; 2/2 [0.1581,1]. Pooled
correlated trials never supply a binomial sample size of 8 or 16. These are pointwise,
not simultaneous multiplicity-adjusted claims. See STATISTICAL_ANALYSIS.md.

## Recognition, confidence and contradictions

Overall descriptive counts: **7/16 correct**, **2/8 replacements detected**, **3/8
negative controls falsely labeled CHANGED**. Natural: detection 0/4 and false positives
0/4. Controlled: detection 2/4 and false positives 3/4. Uncertainty calculations use
the two checkpoint averages separately for each setting, not four independent trials.

| Setting | Condition | CHANGED judgments | Mean confidence | Interpretation |
|---|---|---:|---:|---|
| Natural |C0|0/2|95|No false positives|
| Natural |C1|0/2|95|No false positives|
| Natural |C2|0/2|97.5|Two missed replacements|
| Natural |C3|0/2|97.5|Two missed replacements|
| Controlled |C0|1/2|85|One false positive|
| Controlled |C1|2/2|80|Two false positives|
| Controlled |C2|0/2|87.5|Two missed replacements|
| Controlled |C3|2/2|80|Two detections|

The review screen flags P0 controlled C0 and P1 controlled C1: CHANGED judgments
accompany evidence favoring ordinary adjustment or the same partner. The flags are
non-destructive lexical screening, not exhaustive semantic adjudication. Original
judgments, confidence, empty text and evidence are retained. Final narratives also
misremembered some promises despite correct immediate factual fields. Two missed
natural replacements received confidence 100. These confidence values are uncalibrated.

## Cooperation, trust, reliability and expectations

All natural A contributions stayed at 2. A increased to 3 after round 6 in P0 controlled
C2 and P1 controlled C0. Thus behavioral change was not exclusive to replacement.
Across both checkpoints C0/C2 controlled averaged 2.4 versus 2.0 for C1/C3; the C2−C0
matched sustained differences (+0.8 and −0.8) canceled across checkpoints.

A continuation trust ranged 5–10, with 10/80 at the maximum. Promise reliability was
more ceiling-heavy: 46/80 at 10. The new score-distribution CSV preserves each ordinal
rating's count within checkpoint, agent, condition and setting. Trust/reliability were
lower with promise mismatches but must not be conflated with replacement recognition.

B matched its structured promise in **47/80** continuation rounds, exceeded it in
**32/80**, and fell below it in **1/80**. Natural behavior had 39 matches and one
undercontribution; controlled had eight matches and 32 overcontributions. Controlled
B always actually gave 3, but promises varied (not fixed by the protocol). P1 controlled
C2 promised and delivered 3, unlike C1/C3 promising 2 and delivering 3. These are
important differences in available evidence even with equal imposed actual actions.

All **180/180 structured factual assessments** were correct. This checks five reported
engine facts, not all free-form explanations. A continuation forecasts were **47/64
exact (73.4%)**, MAE **0.265625**; B **62/64 (96.9%)**, MAE **0.03125**. Round-5 branch
forecasts are separately available, and no round-11 outcome is invented. The 64 round
forecasts are not 64 independent starting relationships.

Both checkpoints correctly remain in the primary analysis even though neither meets
the secondary combined cooperation/trust subset (baseline contributions 2 < 3).
There is no selection/regeneration to force a convention, trust response or detection.
These exploratory results are not sufficient evidence of replacement effects or harmful
collusion. V1 and V2 differ in measurement and cannot be pooled or rescaled.

## Three cost scenarios: 23 remaining checkpoints, 184 trials

Prior V1 recorded cost $0.4854921 + V2 $0.5753529 + earlier-work allowance $0.01 =
**$1.070845 currently accounted**. The approved limit stays **$60**, with a **$10 reserve**;
spendable remaining after reserve is **$48.929155**. No increase is applied.

| Scenario | Remaining 23 checkpoints | Cumulative through 200 V2 trials, including V1/allowance | Including $10 reserve | Next five checkpoints |
|---|---:|---:|---:|---:|
| Actual observed pilot unit costs/cache pattern |$6.6166|$7.6874|$17.6874|$1.4384|
| Higher usage, no future cache discount |$17.3526|$18.4235|$28.4235|$3.7723|
| Full-output stress |$68.6872|$69.7580|$79.7580|$14.9320|

Observed extrapolates the returned usage-derived cost by phase/model, including
observed cache discounts. Higher usage doubles each phase/model's mean input/output,
floors at its observed maximum, caps the planning output at the unchanged 2000-token
allowance, and assumes no cache discount. Stress uses the full 2000 output tokens and
at least 24000 input tokens for every remaining call, raised for observed maxima or
1.5×mean if needed. No response or protocol limit is shortened. These are scenarios,
not confidence intervals, provider invoices or guarantees. Prices use the versioned
October 24 verification receipt; future prices/cache behavior can change.

Detailed phase/model rows are exported, with classification counted once. The full
remaining schedule is 10,534 requests. The actual and higher-usage scenarios fit the
approved budget; **full-output stress does not**. Retain all 200 planned trials and the
current protocol, but do not promise completion under $60 at stress usage. If usage
rises, pause before consuming the reserve and seek a separate budget decision. Do not
silently reduce the sample, increase the total, trim prompts/history or switch models.

## Proposed next five-checkpoint batch — NOT executed

- New global checkpoint indices **2–6** (IDs checkpoint-002 through checkpoint-006).
- **40 new continuations**; afterward seven checkpoints/56 trials would be complete.
- Exactly **2,290 requests**: 1,640 gpt-4o-mini, 200 gpt-4.1-mini, 450 gpt-5-mini.
- Expected observed-cost reference **$1.4384**; higher usage **$3.7723**; stress **$14.9320**.
- Propose a **$16 guard for this new window only**. This is not a cumulative-budget
  increase and does not change the completed pilot's $8/916 policy.
- The $60 cumulative limit, $10 reserve and 11,450 global request cap remain unchanged.
  Total requests afterward would be 3,206, leaving 8,244 planned requests for later.
- At stress usage, cumulative spending after this batch is approximately **$16.002845**;
  with the reserve, $26.002845 fits $60. Even the $16 batch guard fits current spendable
  funds. Guards reserve before dispatch and stop rather than automatically retry/raise.

The new window policy file has NOT been created. The following command is prepared
for separate authorization only:

```bash
cd /workspace/ai-peer-replacement-experiment-Copy/llm-trust-breaking
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid --protocol-version v2 --resume \
  --checkpoints 25 --repetitions 1 \
  --checkpoint-start 2 --checkpoint-count 5 \
  --conditions C0 C1 C2 C3 --settings natural controlled \
  --seed 3303 --temperature 1 --controlled-contribution 3 \
  --max-requests 11450 --batch-max-requests 2290 \
  --budget-usd 49.5045079 --batch-budget-usd 16 \
  --study-total-budget-usd 60 --reserve-usd 10 --prior-spend-usd 0.4954921 \
  --export-after-batch \
  --export-root /workspace/peer-identity-exports/study-200-v2 \
  --output outputs/peer-identity/study-200-v2
```

These guards are cumulative within their scope, not reset on resume. V2 pilot costs
already live in the canonical ledger; do not add them again to prior spending.
No checkpoint outside 2–6 is executed by this command, and no later window starts
automatically. Any new invalid/ambiguous request stops for review, not a paid repair.
Local guards cannot guarantee an absolute account-wide/provider billing ceiling.

## Validated combination and teammate use

Use the same canonical V2 root for every approved window. Existing results are skipped;
new global IDs, matched state hashes and payload-hashed cache entries prevent duplicate
paid requests. Export validation checks IDs, labels, joins, source agreement, usage and
costs. Existing pilot data plus five checkpoints would appear in one cumulative export
with 56 completed trial rows and 144 unstarted rows. The full plan remains 200 rows.

**Use the newest cumulative export, not concatenated snapshots.** Older snapshots
already contain earlier checkpoints. Once all 25 are complete, validation expects
25 checkpoints, 200 trials/detections/run-metric rows and 2250 agent-round rows.

New reproducible outputs are under:
`/workspace/peer-identity-exports/study-200-v2/checkpoint-statistics-final` and
`/workspace/peer-identity-exports/study-200-v2/budget-review-final`.
STATISTICAL_ANALYSIS.md explains every analysis table and the portable scripts.
Original paid datasets and sealed exports were not edited. No GitHub publication
is authorized by this review. Stop here until explicit approval of the next batch.
