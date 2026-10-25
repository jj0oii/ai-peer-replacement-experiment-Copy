# Version 2 checkpoint-level statistics and three-scenario budget review

These are offline analysis additions, not changes to the experimental protocol.
They were implemented after examining the two-checkpoint pilot and are exploratory,
not retroactively preregistered. Version 1 is rejected by the new scripts: do not
rescale its trust scores or pool it with Version 2. No paid requests, policy changes
or GitHub publication are part of this review.

## Run the analysis

From `llm-trust-breaking`, using a NEW analysis output directory:

```bash
.venv/bin/python experiments/analyze_peer_checkpoint_stats.py \
  /workspace/peer-identity-exports/study-200-v2/attempt_be4a2ec42f9c44fdaca1b5ed09e722f4 \
  --output /workspace/peer-identity-exports/study-200-v2/my-new-statistics
.venv/bin/python experiments/review_peer_budget.py \
  /workspace/peer-identity-exports/study-200-v2/attempt_be4a2ec42f9c44fdaca1b5ed09e722f4 \
  --output /workspace/peer-identity-exports/study-200-v2/my-new-budget-review
```

The underlying `matched_statistics.py` and `budget_review.py` files can also be
copied and run directly with standard Python 3.10+; no external package, API key,
provider SDK or model call is needed. The statistical analysis reads checksummed
compact CSVs; the budget review additionally reads `raw.jsonl.gz` for stage/model
usage and the immutable recovery evidence. Source data are never overwritten.

## Matching and independent units

The planned contrasts are treatment minus reference: **C3−C2, C2−C1 and C1−C0**.
Analyze natural and controlled settings separately. Match identical repetition IDs
within each checkpoint/setting before averaging any repetitions. Each checkpoint
contributes ONE difference per contrast and measure. Missing pairs are reported,
not imputed; incomplete and unstarted trials are listed separately.

The current pilot has **two independent checkpoints**, not 16 independent starting
relationships or 80 independent continuation rounds. Baselines are rounds 3–5.
For matched contribution/trust/reliability changes, the identical baseline cancels
between branches. C3−C2 isolates the model-change contrast conditional on the common
fresh handoff; C2−C1 compares lost private continuity with restored private continuity;
C1−C0 compares runtime recreation with continuing the saved state.

Both agents' cooperation, trust, reliability, partner promise-compliance rates,
above/below-promise rates, forecast errors and factual accuracy are summarized.
Recognition measures exist only for A. For B rows, partner compliance refers to A;
for A rows it refers to B. Confidence/accuracy contrasts are descriptive. In particular,
C2−C1 changes the recognition ground truth, so an accuracy difference alone is not
a replacement-recognition mechanism. The CHANGED response and false positives must
be examined separately from accuracy.

## Uncertainty intervals

The primary intervals are **95% pointwise Hoeffding bounded-mean intervals** over
checkpoint means/differences. For independent bounded checkpoint values X in [L,U],
use mean ± (U−L)√(log(2/0.05)/(2n)), intersected with [L,U]. Known outcome bounds are
specified in the code, not chosen after observing effects. Matched contribution
changes are bounded −5 to 5 because their common baseline cancels; matched trust
and reliability changes are bounded −9 to 9. Intervals are withheld for n<2.

This finite-sample approach does not assume normally distributed effects or infer
precision from zero observed variance. **With two checkpoints the intervals are
extremely broad, often the entire feasible range.** For example all six paired
mean-contribution contrasts have intervals [−5,5]. This is honest uncertainty,
not proof of equivalence or a null effect. Bootstrap over two equal observed values
can collapse to a misleading point interval, so it is not used here.

For a condition/setting with exactly one binary recognition outcome per checkpoint,
we additionally provide exact **Clopper–Pearson** intervals. They are NOT computed
by pretending pooled correlated trials are independent. With two checkpoints:
0/2 has [0,0.8419], 1/2 has [0.0126,0.9874], and 2/2 has [0.1581,1]. Aggregate
recognition rates across conditions use one averaged rate per checkpoint and the
bounded interval, preserving the cluster unit.

These are pointwise, not multiplicity-adjusted simultaneous intervals; there are
many exploratory outcomes. No significance claims, p-value fishing, power guarantee,
or confirmation of a zero effect is supported. Mean ordinal trust/reliability scores
are descriptive numeric summaries, not proof of equal psychological distances.
Checkpoint independence is an assumption about separately established relationships;
shared model infrastructure and systematic behavior limit generalization.

## Files and meanings

| File | Unit and interpretation |
|---|---|
| run_measurements.csv | One row per agent per completed continuation; baseline/post measures and forecasts |
| matched_checkpoint_differences.csv | One matched difference per checkpoint/setting/agent/contrast/measure, repetitions averaged only after matching |
| matched_contrasts.csv | Equal-checkpoint mean differences and uncertainty bounds; n_checkpoints is the sample size |
| condition_measurements.csv | Condition-specific checkpoint means, bounded intervals and applicable exact binary intervals |
| score_distributions_by_checkpoint.csv | Counts/fractions for every trust/reliability rating 1–10; preserves ordinal distribution and ceiling information |
| recognition_review.csv | Original SAME/CHANGED, confidence and evidence, with non-destructive lexical contradiction flags |
| recognition_cluster_intervals.csv | Accuracy, detection and false-positive rates per setting, with checkpoint-level intervals |
| unmatched_checkpoints.csv | Missing counterpart/repetition coverage; absent when none are missing |
| unstarted_or_incomplete_trials.csv | Explicit unfinished planned records; not all are failed experiments |
| scenario_phase_model_costs.csv | Three scenarios split into disjoint phases/models; judge calls counted once |
| scenario_totals.csv | Remaining-study and next-batch costs including observed costs and prior allowance |
| summary.json | Scope, assumptions, version, provenance hashes, warnings and proposed-only status |

Forecast summaries score rounds 6→7 through 9→10 within continuation games. Round-5
forecasts are separately branch-scored in the source `rounds.csv`; no round-11 outcome
is fabricated. Factual accuracy concerns structured fields, not all narrative claims.
The lexical evidence flag is only a screening aid, not exhaustive semantic coding.
It never changes judgments, confidence or empty text. Human review remains necessary.

## Budget assumptions

Observed scenario extrapolates the actual phase/model paid unit cost, retaining the
pilot's cache discounts. Higher usage uses uncached input/output prices, input at
max(2×mean, observed max) and output at min(2000,max(2×mean, observed max)). The full-output
stress scenario retains 2000 outputs and input at max(24000, observed max,1.5×mean).
These are forecasts, not output-limit changes, confidence intervals or billing ceilings.
Reasoning output is included in completion usage. Original verified prices and dates
are recorded in source metadata; future price or cache behavior can change costs.

## Combining later batches

Keep the SAME canonical `outputs/peer-identity/study-200-v2` root and 25-checkpoint
configuration. Use disjoint global checkpoint windows (next: indices 2–6), the same
seed schedule and a persistent global ledger. `--resume` skips completed results and
hash-matched requests; unresolved/changed requests stop rather than retry. Do not
increase prior-spend allowance by V2 pilot costs: those already exist in this ledger.

Each new validated export is a CUMULATIVE SNAPSHOT, not a file to append to older
snapshots. Use the newest snapshot, or upsert by stable primary keys. Do not concatenate
pilot and later cumulative exports, which would duplicate shared checkpoints/trials.
The validator checks unique IDs, joins, condition labels, journal identity and costs.
The final full dataset will contain 25 checkpoints, 200 trials/detections/run-metric
rows and 2250 agent-round rows (250 establishment + 2000 continuation).

The two completed V2 pilot checkpoints are eligible for inclusion because the model
prompts, game, settings and measurements remain identical; the recorded validator
correction accepted the original schema-valid response without a new model call.
All V1 results remain separate. Before any later execution, the existing code-identity
receipt must still match and no protocol change may be silently introduced.

## Legacy analysis caution

The runtime's older `analysis/summary.json` contains exploratory percentile-bootstrap
outputs retained for historical compatibility. Do not use those small-n bootstrap
intervals as the uncertainty results of this review. The new matched_statistics.py
outputs, with explicitly stated units and conservative intervals, are authoritative
for this analysis. Run the new script against each newest validated export after an
approved batch; it does not execute automatically as another paid experiment.
