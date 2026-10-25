# Experiment 3.3 Version 2 — checkpoints 007–011 completed

**Approved batch complete: five new checkpoints and 40 new continuation trials. Stopped after this batch.** No checkpoint 012 or later, paid retry, protocol/analysis-rule change, budget increase, or GitHub push occurred.

## Completion and preservation

New batch: **40 complete, 0 failed, 0 incomplete**. Cumulative Version 2: **12 independently established checkpoints and 96 completed continuations**. Remaining: **13 checkpoints and 104 unstarted trials**. The study design remains 25 checkpoints × four swap conditions × two behavior settings × one continuation = 200 trials.

Exactly **2290 new paid requests** were made; cumulative V2 requests are **5496**. The previous 3206 request files, seven checkpoint files and 56 completed result files remain byte-identical (3269 preserved files). All 974 Version 1 raw files are unchanged. The historical recovered response remains in its original raw form plus an audit sidecar; it was not requested again. There were no new request/validation errors or unknown-cost reservations. Generation and analysis-rule source hashes match their pre-batch baseline.

## Actual returned usage and recorded cost

All inference used direct OpenAI access. Costs are returned token usage valued at the versioned verified rates; a provider invoice was not queried. Cached input is included in input totals; reasoning is included in output. Every request has usage.

|Scope|Model|Requests|Input|Cached input|Output|Reasoning|Recorded USD|
|---|---|---:|---:|---:|---:|---:|---:|
|incremental_batch|gpt-4o-mini|1640|7,280,449|2,578,432|201,344|0|1.01949135|
|incremental_batch|gpt-4.1-mini|200|608,898|113,280|20,906|0|0.24302480|
|incremental_batch|gpt-5-mini|450|442,055|0|47,508|35,264|0.20552975|
|cumulative_v2|gpt-4o-mini|3936|17,652,293|6,247,680|485,660|0|2.47066395|
|cumulative_v2|gpt-4.1-mini|480|1,475,791|272,640|50,809|0|0.58981880|
|cumulative_v2|gpt-5-mini|1080|1,063,875|0|109,362|80,000|0.48469275|

Batch: **$1.4680459**, 8,331,402 input and 269,758 output tokens. Cumulative V2: **$3.5451755**, 20,191,959 input and 645,831 output tokens. Adding unchanged V1 $0.4854921 and earlier-work allowance $0.01 gives **$4.0406676 cumulative accounted spending**.

The $16 batch guard was not approached; its 2290-request cap was met exactly. The global request cap remains 11450, total spending limit $60 and reserve $10. Remaining under the total limit: **$55.9593324**, or **$45.9593324 after preserving the reserve**. No limits were increased. Local estimated guards are not provider-enforced account-wide billing ceilings.

## Cooperation, trust, reliability and forecasts by condition

A contribution change compares mean rounds 6–10 against that checkpoint's rounds-3–5 baseline. Each checkpoint has the same number of observations in each condition, so displayed means are equally checkpoint-weighted. Trust and reliability are generated 1–10 integer judgments; averages are descriptive ordinal summaries, not psychological interval measurements.

|Scope|Setting|Condition|Mean A contribution|Sustained change|Mean trust|Trust change|Mean reliability|A forecasts exact / evaluable|Forecast MAE|
|---|---|---|---:|---:|---:|---:|---:|---|---:|
|incremental_batch|natural|C0|2.000|+0.000|8.720|+0.053|10.000|20/20|0.000|
|incremental_batch|natural|C1|2.000|+0.000|8.840|+0.173|10.000|20/20|0.000|
|incremental_batch|natural|C2|2.000|+0.000|8.720|+0.053|10.000|20/20|0.000|
|incremental_batch|natural|C3|2.000|+0.000|8.800|+0.133|10.000|20/20|0.000|
|incremental_batch|controlled|C0|2.160|+0.160|6.160|-2.507|6.120|12/20|0.400|
|incremental_batch|controlled|C1|2.000|+0.000|5.920|-2.747|5.560|0/20|1.000|
|incremental_batch|controlled|C2|1.680|-0.320|6.400|-2.267|6.160|14/20|0.300|
|incremental_batch|controlled|C3|1.520|-0.480|5.840|-2.827|5.520|0/20|1.100|
|cumulative_v2|natural|C0|2.083|+0.056|8.900|-0.017|10.000|48/48|0.000|
|cumulative_v2|natural|C1|2.083|+0.056|8.883|-0.033|10.000|48/48|0.000|
|cumulative_v2|natural|C2|2.083|+0.056|8.767|-0.150|9.950|47/48|0.021|
|cumulative_v2|natural|C3|2.083|+0.056|8.950|+0.033|10.000|48/48|0.000|
|cumulative_v2|controlled|C0|2.100|+0.072|6.417|-2.500|6.250|25/48|0.479|
|cumulative_v2|controlled|C1|1.950|-0.078|6.033|-2.883|6.017|14/48|0.708|
|cumulative_v2|controlled|C2|1.967|-0.061|6.933|-1.983|7.133|27/48|0.438|
|cumulative_v2|controlled|C3|1.800|-0.228|6.500|-2.417|6.200|9/48|0.854|

In this batch all natural A contributions remained 2. Controlled conditions showed changes: mean contribution was 2.16 in C0, 2.00 in C1, 1.68 in C2 and 1.52 in C3. This illustrates behavioral variation, not proof of identity recognition. The cumulative controlled differences are smaller because earlier checkpoints show heterogeneous directions. All 96 raw A contribution/trust/reliability sequences appear in agent_a_sequences.csv; both agents' full data are in rounds.csv.

All 12 checkpoints remain in primary analysis. Only checkpoint 002 currently qualifies for the secondary combined cooperation/trust subset. There was no selection, regeneration or sample reduction. A/public starting-state hashes are matched across all eight branches within every checkpoint. Stateless same-model replacement may have no distinct observable identity, and C3 remains a categorical within-OpenAI model contrast.

## Objective promise keeping and factual accuracy

New batch B promises: **109/200 matched, 91/200 exceeded, 0 below**. Cumulative B promises: **282/480 matched, 197 exceeded, 1 below**. Natural B matched 239/240 and fell below once; controlled B matched 43/240 and exceeded in 197/240. Imposed B actions are not freely chosen dishonesty, and above-promise contributions benefit A at fixed A action.

Controlled B always actually contributes 3, while its public promises vary. C2 sometimes promises 3 and complies, while other branches keep promising 2. These differences in observed reliability evidence can affect trust and recognition even when actual B actions are identical; they should not be mistaken for a pure identity signal.

**450/450 new structured factual assessments were correct; 1080/1080 cumulatively, zero field errors.** These assess five immediate engine facts, not the truth or consistency of every free-form reflection and final explanation. Cumulative A continuation trust ranged 4–10, with 23/480 at 10; reliability remained ceiling-heavy with 280/480 at 10. No score was rescaled from Version 1 or forced to change after a promise mismatch.

## Prediction accuracy

|Scope|Agent|Phase|Exact / evaluable|Mean absolute error (tokens)|
|---|---|---|---|---:|
|incremental_batch|A|establishment|20/20|0.0000|
|incremental_batch|A|continuation|106/160|0.3500|
|incremental_batch|B|establishment|20/20|0.0000|
|incremental_batch|B|continuation|151/160|0.0563|
|cumulative_v2|A|establishment|44/48|0.1042|
|cumulative_v2|A|continuation|266/384|0.3125|
|cumulative_v2|B|establishment|43/48|0.1042|
|cumulative_v2|B|continuation|360/384|0.0625|

A continuation forecasts: **106/160 exact (66.25%)** in this batch, **266/384 (69.27%)** cumulatively; cumulative MAE **0.3125 tokens**. B was 151/160 in the batch and 360/384 (93.75%) cumulatively. Cumulative A natural forecasts were 191/192 exact, versus 75/192 controlled. Forecasts thus tracked ordinary natural conventions better than imposed actions. These are descriptive round counts, not independent relationship sample sizes. Round-5 forecasts remain separately branch-scored; round 10 has no round-11 outcome.

## Recognition decisions, confidence and contradictory evidence

Batch: **8/20 replacements detected (40%)**, **8/20 false positives (40%)**, **20/40 correct (50%)**. Cumulative: **16/48 detected (33.33%)**, **18/48 false positives (37.5%)**, **46/96 correct (47.92%)**. No natural-condition response selected CHANGED, so natural replacements were all missed while natural controls had no false positives.

|Scope|Setting|Condition|CHANGED / judgments|Correct|Mean confidence|
|---|---|---|---|---:|---:|
|incremental_batch|natural|C0|0/5|5|95.00|
|incremental_batch|natural|C1|0/5|5|95.00|
|incremental_batch|natural|C2|0/5|0|93.00|
|incremental_batch|natural|C3|0/5|0|96.00|
|incremental_batch|controlled|C0|3/5|2|84.00|
|incremental_batch|controlled|C1|5/5|0|85.00|
|incremental_batch|controlled|C2|3/5|3|82.00|
|incremental_batch|controlled|C3|5/5|5|85.00|
|cumulative_v2|natural|C0|0/12|12|94.58|
|cumulative_v2|natural|C1|0/12|12|94.58|
|cumulative_v2|natural|C2|0/12|0|93.75|
|cumulative_v2|natural|C3|0/12|0|95.83|
|cumulative_v2|controlled|C0|8/12|4|84.17|
|cumulative_v2|controlled|C1|10/12|2|82.92|
|cumulative_v2|controlled|C2|5/12|5|85.42|
|cumulative_v2|controlled|C3|11/12|11|83.75|

Controlled C3 was labeled CHANGED in 11/12 cases versus 5/12 for C2. However sham C1 was labeled CHANGED in 10/12 and no-swap C0 in 8/12. This pattern does not demonstrate reliable identity discrimination. Confidence remains model-reported and uncalibrated, including high confidence for natural misses.

The unchanged lexical review screen flagged **4** potential judgment/evidence contradictions cumulatively, including **one new case**. It is a non-destructive screen requiring human review, not exhaustive semantic adjudication. Original judgments, confidence, empty strings and evidence remain untouched.

New example: checkpoint 008 controlled C2 selected **CHANGED/85**, while its evidence begins, "The evidence suggesting that Agent B was not replaced" and later describes "a behavioral change in the same individual". The judgment matches the operational replacement label but contradicts the explanation. This is a measurement-quality concern separate from numeric fact extraction. Earlier controlled C0/C1 contradictions remain preserved. All verbatim structured evidence is in recognition_review.csv.

## Matched comparisons and uncertainty

Each contrast matches the same checkpoint, setting and repetition before averaging. Independent units are the **12 checkpoints**, not 96 games or 480 post-round A observations. The reviewed analysis rules are unchanged: pointwise 95% bounded-mean Hoeffding intervals, plus exact Clopper–Pearson intervals for one binary recognition outcome per checkpoint within condition/setting. These are conservative, assume checkpoint independence, and are not multiplicity-adjusted simultaneous claims.

|Setting|Contrast|Sustained contribution difference [95% interval]|Trust-change difference [95% interval]|Reliability difference [95% interval]|
|---|---|---|---|---|
|natural|C3−C2|+0.000 [-3.921, 3.921]|+0.183 [-6.874, 7.240]|+0.050 [-7.007, 7.107]|
|natural|C2−C1|+0.000 [-3.921, 3.921]|-0.117 [-7.174, 6.940]|-0.050 [-7.107, 7.007]|
|natural|C1−C0|+0.000 [-3.921, 3.921]|-0.017 [-7.074, 7.040]|+0.000 [-7.057, 7.057]|
|controlled|C3−C2|-0.167 [-4.087, 3.754]|-0.433 [-7.490, 6.624]|-0.933 [-7.990, 6.124]|
|controlled|C2−C1|+0.017 [-3.904, 3.937]|+0.900 [-6.157, 7.957]|+1.117 [-5.940, 8.174]|
|controlled|C1−C0|-0.150 [-4.071, 3.771]|-0.383 [-7.440, 6.674]|-0.233 [-7.290, 6.824]|

Intervals narrow relative to the two-checkpoint pilot but remain broad and include zero. No definitive effect, model ranking, equivalence or absence of effect is established. For natural recognition 0/12 CHANGED per condition has exact 95% interval [0,0.2646], not proof that the population rate is zero. Controlled C3 detection 11/12 has [0.6152,0.9979]; C2 detection 5/12 has [0.1517,0.7233]. These are separate condition intervals, not a significance test of their difference. Full matched recognition/compliance/forecast/factual contrasts and checkpoint-level differences are in the statistical CSVs.

## Remaining 104 trials: updated budget

13 checkpoints/104 continuations remain, requiring **5954 planned requests** under the unchanged protocol. Actual recorded costs of the completed 12 checkpoints replace their earlier forecasts. Observed usage extrapolates cumulative phase/model cost including cache discounts; higher usage uses uncached input/output prices and max(2×mean,observed maximum), with output planning capped at the unchanged 2000 allowance. Full-output stress retains 2000 outputs and at least 24000 input tokens, raised if observed maxima/1.5×mean require it. No actual response limit or prompt was reduced.

|Scenario|Additional remaining 13 checkpoints|Cumulative including V1/allowance|Including $10 reserve|
|---|---:|---:|---:|
|observed_usage|$3.8406|$7.8813|$17.8813|
|higher_usage|$10.5128|$14.5534|$24.5534|
|full_output_stress|$38.8232|$42.8639|$52.8639|

Full-output stress is now **$38.8232 additional**, **$42.8638676 cumulative spending**, or **$52.8638676 including reserve**. It fits the unchanged $60 planning limit with approximately **$7.1361 margin beyond the reserve**. This improvement comes from replacing stress allowances with actual completed costs, not changing assumptions, protocol or sample size. Scenarios are not provider billing guarantees; future prices, unusually long histories and errors can still affect cost. Local guards remain active, and no remaining trial is authorized automatically.

## Validated teammate datasets and reproducibility

Latest canonical sealed snapshot: `/workspace/peer-identity-exports/study-200-v2/attempt_94d8e57d9dd44086a2ec8f98fc62ecac`. It contains **1080 agent-round rows**, 200 planned trial/detection/run-metric rows (96 complete, 104 unstarted), and 25 planned checkpoint rows (12 established). It is one cumulative snapshot, not concatenated exports. The report's cumulative_completed_trials.csv is the 96-completed-trial view.

Excel: `/workspace/peer-identity-exports/study-200-v2/version-2-cumulative-through-checkpoint-011.xlsx`. It contains all canonical CSV sheets, incremental/cumulative costs, condition summaries, recognition evidence, matched intervals and cost scenarios. ZIP/XML integrity and exact worksheet-value readback against source CSVs passed. No graphical Excel application was used. CSV/JSON remain canonical for precision.

Authoritative updated statistics: `/workspace/peer-identity-exports/study-200-v2/statistics-after-checkpoints-007-011`. Budget scenarios: `/workspace/peer-identity-exports/study-200-v2/budget-after-checkpoints-007-011`. Source scripts use standard Python and no API key; the teammate package includes frozen copies and reproduction instructions. Version 1 is excluded, not rescaled or pooled.

Export validation covers unique identifiers, condition labels, joins, model/usage/cost consistency, payoff arithmetic, journal/state agreement, derived measurements, checksums and secret scans. Matched A/public starting states are verified in each checkpoint. Provider request/response IDs are unique; there were no paid duplicates. The generation and analysis-rule source hashes are unchanged. The statistical results remain exploratory; no evidence of harmful collusion is inferred from cooperation.

## Stop point

All approved work is finished. No checkpoint 012 or beyond was started. No additional paid run or publishing will occur without separate explicit approval.
