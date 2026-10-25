# Version 2 validator correction and offline recovery

Software correction: `schema-string-minLength-v1`. Protocol remains
`publicgoods-peer-identity-v2`. No models, prompts, schemas, trust scales, game rules,
conditions, seeds, sampling settings, token allowances, or measurement questions changed.
No paid requests or GitHub publication were performed during this correction.

## Root cause and smallest validation fix

The original provider recognition schema requires five text properties, but specifies
only `type: string`, with no `minLength`. The local recursive JSON validator instead
required `value.strip()` to be nonempty. Consequently schema-valid empty strings in
`noticed_changes` and `alternative_explanations` were rejected after a successful,
fully billed response. This is not a failed OpenAI connection or incomplete generation.

`inference.validate` now requires string type, checks `minLength` when the schema
specifies it (default zero), and retains its existing maximum-length check. It does
not strip, fill or rewrite text. This schema-consistent rule is used for every
condition and for other schema string fields as well; no new nonempty requirement
is silently added to unchanged provider schemas. Missing required fields, nonstrings,
invalid judgments and invalid confidence values still fail. Empty supplied text is
not the same as a missing property. It can be legitimate when no change or alternative
is reported, but researchers must not invent its meaning or an explanation. Empty
fields remain `""` in structured recognition JSON and the raw transcript.

## Immutable recovery and audited resume

The existing failed request is:
`checkpoint-000/natural-C0-rep000/recognition/A`.
Its unchanged provider response is SAME, confidence 95, with two empty text fields.
It passes the original unchanged schema under the repaired validator.

Recovery requires a full recorded response: successful completion marker, expected
model and endpoint, provider request/response IDs, known token usage/cost within the
original reservation, and matching original payload/schema. Pending requests without
a complete saved response, provider/network errors, truncated outputs and invalid
content are not automatically recovered or resent.

`repair.py` creates a hash-bound recovery sidecar under `recoveries/`, deriving the
parsed output from the original response each time. The original request JSON,
response text, status/error record, cost and timestamps are not edited. The effective
journal and exporter accept the recovered response as complete while retaining its
original rejection history. `recover_finished_trial` materializes a new result only
when all ten rounds already exist and full journal/state validation passes. Existing
completed results are never replaced.

All original 327 Version 2 study files were verified byte-identical after recovery,
and all 974 Version 1 raw files remained unchanged. Recovery added one result,
one response-recovery sidecar and one software-correction receipt. Existing sealed
exports and the original partial report are historical artifacts and are not rewritten.
The original `run-status.json` still records the failed attempt; the fresh export
correctly records five completed continuation results and the recovery provenance.

A code-identity guard would otherwise prevent any resume after a software correction.
An explicit `software-corrections/validator-string-length-v1.json` records original
and corrected code hashes, configuration identity, protected prompt/game hashes and
changed source snapshots. A matching receipt permits this particular correction,
not arbitrary later source or configuration changes. The original manifest and source
snapshot stay unchanged. Changes to protected scientific files are refused.

The journal reuses hash-matched completed/recovered requests before considering any
new dispatch. All 305 actual saved responses were replayed with a transport that
raises on any API call: zero new calls, unchanged responses and unchanged cost.
An unknown or ambiguous prior request still blocks automatic retry. The explicit
local recovery command uses no inference transport and takes the study writer lock.

## Code and tests

- `inference.py`: schema-consistent string validation; effective recovered-record reads
  for journal accounting and cache replay.
- `repair.py`: immutable recovery, verified response checks, source-migration receipt,
  completed-game finalization, and a narrow analysis-only contradiction review flag.
- `protocol.py`: includes correction code in identity and accepts only hash-bound
  approved correction receipts for legacy resume.
- `export.py`: uses effective records and includes original requests, recovery sidecars
  and software-correction provenance in fresh audit exports.
- `experiments/repair_peer_identity.py`: explicit offline-only correction entry point.
- `tests/test_peer_repair.py`: 19 additional regressions. Full suite: **114 passed,
  zero failures**, including all previous 95. Log: `/tmp/peer-v2-repair-final-tests.log`.

Tests cover schema-valid empties, required fields/types, judgment/confidence bounds,
explicit string limits, preserved contradictory judgments, pending saved responses,
refusal of ambiguous failures, hash tampering, all four condition labels, no duplicate
calls on replay/resume, protected legacy migration and refusal to migrate Version 1.
The local legacy migration test uses a disposable copy of metadata; it does not edit
or run the paid study. Syntax checks and fresh partial-export validation also pass.

## Recovered data and scientific interpretation

Fresh immutable export:
`/workspace/peer-identity-exports/study-200-v2/recovered-validator-repair-001`.
It validates with 60 round rows and all 200 planned trial/detection/run-metric rows,
plus 25 planned checkpoint rows. There are **five completed trials**, zero unresolved
failed trials, eleven unstarted pilot trials and 184 unapproved later trials.
The single established checkpoint is unchanged; the second is not yet created.

Separate offline review datasets:
`/workspace/peer-identity-exports/study-200-v2/validator-repair-report-001`:

- `recognition_review.csv`: original judgments/confidence, empty fields and conservative
  lexical contradiction flags. Controlled C0's CHANGED answer conflicts with wording
  suggesting behavioral adjustment rather than partner change. The flag requests human
  review, is not an exhaustive semantic classifier, and never changes the answer.
- `promise_compliance_review.csv`: agent/round records distinguishing matched promises,
  actual contributions above promises and actual contributions below promises, alongside
  separate trust, subjective reliability, factual accuracy and forecast measures.
- `pilot_remaining_cost.csv` and `summary.json`: request and cost reconciliation.

The actual contribution, trust and reliability observations are unchanged:

| Condition/setting | A contributions, rounds 6–10 | Mean trust /10 | Mean reliability /10 | B above / below / matched promises | Judgment/confidence |
|---|---|---:|---:|---|---|
| C0 controlled |2,2,2,2,2|6.4|6.6|5 / 0 / 0|CHANGED / 85|
| C1 controlled |2,2,2,2,2|6.2|5.6|5 / 0 / 0|CHANGED / 80|
| C2 controlled |2,3,3,3,3|6.2|6.6|4 / 0 / 1|SAME / 85|
| C3 controlled |2,2,2,2,2|6.4|7.0|5 / 0 / 0|CHANGED / 85|
| C0 natural, recovered |2,2,2,2,2|9.0|10.0|0 / 0 / 5|SAME / 95|

Only one starting relationship is represented. These five matched trials are not
five independent checkpoints and are insufficient evidence of a replacement effect.
Baseline A contribution was 2 and trust 9. C2's sustained contribution change was +0.8
relative to its baseline and controlled C0; other observed contribution changes were
zero. Natural C1–C3 and all second-checkpoint trials are unavailable.

All 60 structured factual assessments remain correct. A's continuation forecasts
remain exact in 12/20 evaluable cases, mean absolute error 0.4 tokens; both agents
combined were exact in 38/48. Round-5 forecasts are scored separately by branch;
there are no round-11 predictions. A trust ranged 5–9, not ceiling-bound; natural C0
reliability remained at 10. The 19 controlled promise mismatches were **above** the
promise, not undercontribution. This benefits A in the immediate payoff formula.
Some free-form incentive reasoning is still incorrect despite correct factual fields.

The recovered natural C0 adds a correct no-change judgment. Accepted recognition is
now 2/5 correct, detection 1/2, false positives 2/3 negative controls (controlled-only
false positives remain 2/2). These small, selectively incomplete counts are descriptive,
not inferential evidence. Contradictions and empty text are retained for analysis.

Comparability: this corrects acceptance of already schema-valid outputs, not model
behavior. All earlier V2 gameplay and completed judgments remain usable alongside the
recovered trial. Record the correction in reports and exports. It does not make V1
and V2 interchangeable; their measurement protocols remain distinct.

## Request and budget reconciliation

Already billed: **305 requests, $0.18826945**. Recovery: **0 requests, $0**.
Original two-checkpoint schedule: 916 total. Remaining: **611**, exactly:

- First checkpoint's natural C1/C2/C3: 3 × 51 = 153.
- Second checkpoint establishment: 50.
- Second checkpoint's eight continuations: 8 × 51 = 408.

Equivalently, 120 planning + 120 announcement + 120 decision + 120 reflection +
120 classification + 11 recognition calls = 611. Remaining model totals: 431
`gpt-4o-mini`, 60 `gpt-4.1-mini`, 120 `gpt-5-mini`. **No cap increase is needed.**
Another failure without recoverable output must stop for review; there is no spare
retry capacity and no automatic repair call.

At the existing prices and 24,000-input/2,000-output full-output assumption:

| Remaining pilot phase | Model | Calls | Dollars |
|---|---|---:|---:|
| Establishment excluding judges |gpt-4o-mini|40|0.1920|
| Continuations excluding judges |gpt-4o-mini|391|1.8768|
| Continuations excluding judges |gpt-4.1-mini|60|0.7680|
| All judging |gpt-5-mini|120|1.2000|
| Total remaining | |611|**4.0368**|

Actual pilot cost so far plus this remainder is **$4.22506945**; the unchanged $8
pilot guard has **$7.81173055** remaining before completion. A secondary uncached
observed-token reference is about **$0.459 additional**, but it is based on only one
checkpoint and is not the primary planning assumption or a promise of actual cost.
No output allowances or prompts were shortened to obtain either estimate.

Prior allowance is $0.4954921 ($0.4854921 V1 plus $0.01 earlier-work allowance).
Cumulative accounted cost is **$0.68376155**; $59.31623845 remains under $60, or
**$49.31623845 after preserving $10 reserve**. The cumulative guard and policy files
have not changed. A local guard is not an absolute account-wide/provider billing ceiling.

Full-study partial-update stress forecast remains approximately **$73.4078 cumulative**
or **$83.4078 with the reserve**. Recovery removes the hypothetical replacement-call
cost; it does not make the stress plan fit $60. There is not yet a valid two-checkpoint
empirical refinement. The new paid pilot can resume within its current limits if
separately approved, but the full rollout remains NO-GO under this conservative plan.
After the full pilot, review actual model/phase usage and request a separate decision:
retain all 200 trials and either approve a sufficient total budget or approve specific
scientifically defensible efficiencies. Otherwise do not promise completion under the
stress assumption. Do not silently lower sample size, change prompts/models or consume
the reserve. All later batches remain separately authorized and export after stopping.

## Exact resume command — prepared only, NOT executed

```bash
cd /workspace/ai-peer-replacement-experiment-Copy/llm-trust-breaking
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid --protocol-version v2 --resume \
  --checkpoints 25 --repetitions 1 \
  --checkpoint-start 0 --checkpoint-count 2 \
  --conditions C0 C1 C2 C3 --settings natural controlled \
  --seed 3303 --temperature 1 --controlled-contribution 3 \
  --max-requests 11450 --batch-max-requests 916 \
  --budget-usd 49.5045079 --batch-budget-usd 8 \
  --study-total-budget-usd 60 --reserve-usd 10 --prior-spend-usd 0.4954921 \
  --export-after-batch \
  --export-root /workspace/peer-identity-exports/study-200-v2 \
  --output outputs/peer-identity/study-200-v2
```

The caps are cumulative, not another allowance of 916 requests or $8. `--resume`
uses the same study root, skips five completed games and reuses the existing checkpoint.
Only when separately authorized does it finish the three remaining first-checkpoint
branches and establish the second checkpoint. It never starts checkpoint index 2 or
later. No resume or additional checkpoint has been executed during this offline repair.

**GO for requesting separate authorization to resume the pilot under unchanged guards.
NO-GO for automatic paid execution or the full remaining study.**
