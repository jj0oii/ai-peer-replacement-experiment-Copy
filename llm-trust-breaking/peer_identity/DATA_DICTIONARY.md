# Experiment 3.3 sharing data dictionary (formats 1–2)

UTF-8 CSVs use a header row and decimal points. Missing values are empty cells, never
fabricated zeros. Booleans are `true`/`false`. Timestamps are timezone-aware ISO 8601
UTC. Legacy batches may lack original execution times or a known execution commit;
metadata explicitly marks these unknown rather than inventing them. CSV text that
starts with a spreadsheet formula character is prefixed with `'`; its original
verbatim value remains in compressed raw JSONL.

## Keys, joins and independent units

- `batch_id`: random UUID identity, `batch_<32 hex digits>`, stable across resume/exports.
- `checkpoint_id`: `<batch_id>:checkpoint-000`; an independent established relationship.
- `condition`: `C0` no swap, `C1` sham with restored state, `C2` same-model private-context
  reset, `C3` different OpenAI model with the same context reset; C4 is disabled.
- `setting`: `natural` or `controlled` for continuations. Analyze separately.
- `condition_id`: `<batch_id>:<setting>:<condition>`; one shared category within a batch.
- `repetition`: zero-based stochastic continuation index, not an independent relationship.
- `run_id`: `<checkpoint_id>:<setting>-<condition>-rep000`; unique continuation game.
- Establishment rows have `condition=ESTABLISHMENT`, `setting=baseline`, blank repetition,
  and `run_id=<checkpoint_id>:establishment`. The shared five-round baseline is exported
  **once** per checkpoint, never duplicated as if independently observed in every branch.

Join `rounds` to `trials` using `run_id` for continuation rounds. Join every continuation
to `checkpoints` and establishment rounds using `checkpoint_id`. Join `detections` to
`trials` using `run_id`. Pair conditions within checkpoint, setting and repetition.
Average stochastic repetitions within checkpoints for independent-unit inference.

## rounds.csv

One row per agent per observed round. An interrupted round gets two rows, including
explicit missing fields for the agent/stages not reached. Entirely unstarted future
rounds have no rows; planned future games remain visible in trials.csv.

| Column | Type / values | Meaning |
|---|---|---|
| batch_id, checkpoint_id, run_id, condition_id | string | Join keys above |
| condition, setting, repetition | categorical / nullable integer | Definitions above |
| phase | establishment / continuation | Rounds 1–5 / 6–10 |
| round | integer 1–10 | Absolute game round |
| agent | A / B | Visible, stable game identity |
| model | string | Requested direct-OpenAI model ID; returned snapshots are in metadata/raw |
| round_status | complete / incomplete / error / not_started | Complete requires all ten calls for the round; not_started denotes the untouched agent in an observed partial round |
| planned_contribution | nullable integer 0–5 | Private planning stage |
| promised_contribution | nullable integer 0–5 | Public announced commitment |
| proposed_contribution | nullable integer 0–5 | Free model choice at final-decision stage |
| contribution | nullable integer 0–5 | Actual economic action, after intervention; populated only when both decisions exist |
| contribution_imposed | boolean | True for B in controlled continuations; identifies the policy assignment even in partial rows |
| payoff | nullable number | `(5 - contribution) + 1.5 * total_contributions / 2`, reconstructed from unchanged game mechanics |
| promise_broken | nullable boolean | Actual contribution differs from promise; imposed B outcomes are not free-choice deception |
| proposed_promise_broken | nullable boolean | Proposed contribution differs from promise |
| trust_target | A / B | The other agent being assessed |
| trust_score | nullable integer 1–5 | This agent's post-round private trust reflection about its partner |
| started_at | nullable timestamp | Earliest journal dispatch reservation for this agent in this round |
| last_response_at | nullable timestamp | Latest recorded response for this agent in this round |

Messages and private reasoning remain in raw.jsonl.gz, not duplicated into the compact
CSV. A's round-6 contribution occurs after both announcements and before either new
contribution or payoff is observed. A populated contribution with an incomplete round
can mean a later judge/reflection call failed; filter status appropriately and report
missingness, rather than treating a missing reflection as zero trust.

## detections.csv

One row per planned continuation, including unavailable judgments for unstarted or
interrupted games (so detection attrition is explicit).

| Column | Type / values | Meaning |
|---|---|---|
| batch_id, checkpoint_id, run_id, condition_id, condition, setting, repetition | keys/categories | Join definitions above |
| status | run-status category below | Same status as trials.csv |
| judgment | SAME / CHANGED / blank | A's final judgment, requested only after round 10 |
| confidence | nullable integer 0–100 | Confidence in chosen answer, not automatically P(CHANGED) |
| evidence | nullable string | A's stated evidence; spreadsheet-escaped if needed |
| is_replacement | boolean | C2/C3 true; C0/C1 false; C2 denotes state discontinuity |
| correct | nullable boolean | Judgment matches the defined ground truth; blank if no judgment |

False-positive rate: fraction CHANGED in C0 and C1, reported separately and/or as a
prespecified negative-control mean. True-positive rate: fraction CHANGED in C2/C3.
Do not score missing judgments as SAME or silently drop their failure rate.

## trials.csv

One row per **planned continuation**, including unstarted and failed games. Establishment
usage is in checkpoints.csv and must not be multiplied across continuations.

| Column | Type / values | Meaning |
|---|---|---|
| batch_id, checkpoint_id, run_id, condition_id, condition, setting, repetition | keys/categories | Join definitions above |
| model_a, model_b, judge_model | string | Requested model IDs |
| status | complete / recovered_complete / incomplete / error / not_started | Complete has saved result plus all request evidence; recovered_complete has all evidence but final result file was interrupted; incomplete has requests but no complete game; error includes blocked/invalid requests; not_started has no requests |
| rounds_completed | integer 0–5 | Fully completed post-checkpoint rounds, including judge/reflection |
| high_trust_checkpoint | nullable boolean | Both agents' mean contributions >=3 and mean trust >=4 in rounds 3–5, using configured thresholds; no filtering of valid checkpoints |
| started_at | nullable timestamp | Earliest reserved request in the continuation |
| finished_at | nullable timestamp | Last response for a completed/recovered continuation; blank otherwise |
| api_requests | integer >=0 | Dispatch reservations; pending calls may not have reached the provider, so this is a conservative attempted-request count |
| requests_with_usage | integer >=0 | Requests with provider usage (fabricated fixtures in mock mode) |
| input_tokens, output_tokens | integer >=0 | Totals for requests with known usage only |
| cached_input_tokens | integer >=0 | Input tokens billed at cached rate; included in input_tokens |
| reasoning_tokens | integer >=0 | Reasoning subset already included in output_tokens |
| known_cost_usd | number >=0 | Estimated cost from known token usage; mock cost is zero |
| reserved_unknown_cost_usd | number >=0 | Conservative budget reservation for requests lacking cost evidence; **not confirmed spending** |
| usage_complete | boolean | Every request has reported usage; vacuously true for zero requests, so always consult status/count |
| error_requests | integer >=0 | Blocked requests: HTTP/transport/parse/refusal failures |
| pending_requests | integer >=0 | Interrupted/ambiguous requests; never automatically resent |

Prices are versioned assumptions in metadata. Final provider billing is authoritative.
Known token totals in an incomplete game are partial, not full-game cost estimates.

## checkpoints.csv

One row per planned independent five-round establishment history.

| Column | Type / values | Meaning |
|---|---|---|
| batch_id, checkpoint_id | string | Batch and independent relationship keys |
| establishment_run_id | string | Joins to the baseline rows in rounds.csv |
| status | same run-status categories | Establishment completion/attrition |
| rounds_completed | integer 0–5 | Completed establishment rounds |
| high_trust | nullable boolean | Prespecified high-trust subset; all valid checkpoints remain primary data |
| mean_contribution_a_rounds3to5, mean_contribution_b_rounds3to5 | nullable number 0–5 | Actual baseline contribution means |
| mean_trust_a_rounds3to5, mean_trust_b_rounds3to5 | nullable number 1–5 | Baseline directed trust means |
| api_requests through pending_requests | same usage fields as trials.csv | Establishment costs counted once |

Summing known costs across checkpoints.csv and trials.csv yields the batch's known
estimated cost without double counting. Baseline plus continuation round records
support matched contribution and trust trajectories across conditions.

## metadata.json

Contains format/export/batch IDs; execution configuration; execution commit SHA and
dirty-tree flag; source-file SHA-256 hashes; execution protocol hash; model IDs and
returned snapshots; master and observed supported seeds; request/cost totals; price
assumptions; export/batch timestamps; raw-storage recommendation; and join definitions.
Source snapshots and exact per-request prompts/parameters are in raw.jsonl.gz. A commit
SHA alone is not proof of the exact executed source when the working tree was dirty;
the allowlisted source snapshot and hashes record the actual implementation.

Legacy adoption explicitly marks unknown original commit/timestamps. Export time and
batch-identity adoption time are not substituted for unknown execution time.

## raw.jsonl.gz, validation.json and checksums.json

Each gzip line is `{"path":"relative/source.json","record":{...}}`.
Records include only allowlisted batch metadata, source snapshots, request journals,
checkpoints, round progress, branch order, results, attempts, status and usage. This
retains every captured prompt, output, message, private state, requested/returned model,
seed where supported, usage, cost reservation, error type and request status. Response
bodies never received before a crash cannot be recovered; their pending reservation
is preserved without claiming the call did or did not execute. Incomplete stages are
never fabricated from later outcomes.

`validation.json` records checks and row counts. `checksums.json` hashes every other
bundle file. These detect accidental corruption, not maliciously rewritten manifests.
Verify the sealed bundle before sharing or after downloading. Environment files,
credentials, request authorization headers, arbitrary logs and local config are not
copied. Pattern and known-value scans reject likely secrets; human review remains
necessary. Store these research transcripts with the team's intended access controls.

## run_metrics.csv (format version 2)

One row per planned continuation game, including incomplete games. This is the
convenient starting table for comparing Agent A's behavior before and after branching.
Missing measurements stay blank. It is included in the export and regenerated by
analyze.py from the underlying CSVs; both versions use the same formulas.

| Column | Beginner-friendly meaning |
|---|---|
| checkpoint_id | Which independent five-round relationship this game started from |
| run_id | Unique continuation game; use it to join trials/detections/rounds |
| condition | C0 no swap; C1 sham; C2 same-model private-state reset; C3 different model |
| behavior_setting | `natural` or `controlled`; same meaning as `setting` in other CSVs |
| baseline_a_contribution | A's mean actual contribution in rounds 3, 4 and 5, from 0–5 tokens |
| round6_a_contribution | A's actual contribution in the first post-branch round, 0–5 |
| immediate_contribution_change | Round-6 contribution minus baseline. Negative means A contributed less immediately |
| sustained_contribution_change | A's mean contribution over ALL rounds 6–10 minus baseline; blank unless all five decisions exist |
| baseline_a_trust_in_b | A's mean trust rating of B over rounds 3–5, on the 1–5 scale |
| post_a_trust_in_b | A's mean trust rating of B over ALL rounds 6–10; blank unless all five ratings exist |
| trust_rating_change | Post-game trust mean minus baseline trust mean; negative means reduced reported trust |
| detected_change | `true` for CHANGED, `false` for SAME, blank if no final judgment |
| actual_swap | Ground truth: false in C0/C1; true in C2/C3. C2 is a context reset, not proof of a distinct persistent identity |
| batch_id, condition_id | Join/category keys defined above |
| repetition | Zero-based continuation repetition; not an independent relationship |
| run_status | Same status values as trials.csv |
| observed_post_contribution_rounds | How many of the five continuation rounds have known A decisions (0–5) |
| observed_post_trust_rounds | How many continuation rounds have known A trust ratings (0–5) |

Contribution changes range from -5 to +5; trust changes from -4 to +4. Compare the
immediate change to C0 within the same checkpoint, behavior setting and repetition;
then average matched differences within checkpoints. A smaller contribution alone
is not classified as recognizing a replacement. `detected_change` and `actual_swap`
are different concepts and can disagree. Synthetic mock results deliberately include
wrong judgments in C2/C3 to exercise that distinction.

## Version 2 measurements (do not pool with Version 1)

`metadata.json.config.protocol_version` and `rounds.csv.protocol_version` /
`detections.csv.protocol_version` identify `publicgoods-peer-identity-v1` or `...-v2`.
Original sealed Version 1 exports remain unchanged. Newly exported historical data
retain their original 1–5 scores; Version 2-only fields are blank. `trust_score`
remains a compatibility column in each version's native units. Never mix its scales.

| New column | Meaning and possible values | Source |
|---|---|---|
|protocol_version|Measurement protocol identifier; join datasets within a version|Configuration|
|trust_score_1_10|Future honesty, reliability and cooperation, integer 1–10; identical to V2 `trust_score`|Agent|
|promise_reliability_1_10|Perceived keeping of public contribution promises, integer 1–10|Agent|
|partner_promised_contribution|Partner's structured public promise, integer 0–5|Engine public announcement|
|partner_actual_contribution|Partner's actual contribution, integer 0–5; includes controlled override|Engine|
|promise_compliance|true if partner's actual contribution equals its structured promise, false otherwise|Derived from engine facts|
|reported_partner_promised_contribution|Promise identified by the agent, integer 0–5|Agent|
|reported_partner_actual_contribution|Actual contribution identified by the agent, integer 0–5|Agent|
|reported_promise_matched|Whether agent says promise equalled actual contribution, true/false|Agent|
|reported_own_payoff|Agent's account of its own payoff|Agent|
|reported_partner_payoff|Agent's account of partner's visible payoff|Agent|
|factual_assessment_correct|true only if all five factual answers equal engine facts|Derived|
|factual_errors|JSON object of wrong field names with reported and expected values; `{}` means no error|Derived|
|predicted_next_partner_contribution|Expected partner contribution next round, integer 0–5; blank at round 10|Agent|
|prediction_evaluable|true when next outcome exists in the same run; false at round 5/10 or unavailable next outcome|Derived|
|prediction_error|Prediction minus next actual partner contribution, −5 to 5; positive means overprediction|Derived|
|round5_partner_forecast|On each continuation's round-6 row: original agent's round-5 forecast, integer 0–5|Agent, copied from checkpoint|
|round6_prediction_error|Round-5 forecast minus this branch's round-6 partner contribution, −5 to 5|Derived|
|recognition_evidence|In detections.csv: JSON with consistent_patterns, noticed_changes, concrete_observations, alternative_explanations, evidence|Agent|
|judgment|Final SAME or CHANGED; unchanged existing field|Agent A|
|confidence|Final judgment confidence integer 0–100, not empirically calibrated|Agent A|

Blank means not collected, not yet available or not applicable, never zero confidence,
zero trust or a correct answer by default. False factual accuracy is a recorded model
mistake, not an automatically corrected response. Missing/out-of-range required model
outputs are blocked in the request journal, retained in raw JSONL, and have missing
measurements in CSVs. Round-5 forecasts have no single baseline prediction error
because branches have different futures. Round-10 has no round-11 forecast/outcome.
Use checkpoint_id to account for shared baselines; run_id joins trial, round and
recognition tables. Compare V2 trust trajectories on 1–10 axes only. Full scale anchors
and methodological caveats are in VERSION_2_METHODOLOGY.md.
