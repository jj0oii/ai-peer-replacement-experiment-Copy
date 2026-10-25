# Experiment 3.3 — Can AI Agents Identify Their Peers?
## Version 2: Research Methodology

**Research area:** Multi-agent AI interaction, cooperation, trust, and partner recognition  
**Experimental framework:** `llm-trust-breaking`  
**Primary game:** Two-player Public Goods Game  
**Planned sample:** 200 continuation trials from 25 independent checkpoints  
**Protocol:** Version 2  
**Status:** Offline validation complete: 95 automated tests passed and a two-checkpoint mock pilot produced validated exports. The new Version 2 paid pilot awaits explicit approval and execution.

---

## 1. Research Overview

### Research question

**Can an AI agent recognize when its interaction partner has been secretly replaced, either by explicitly identifying the replacement or by changing its cooperation, trust, and expectations?**

Our experiment investigates whether AI agents develop expectations about their interaction partners through repeated cooperation, and whether they respond when the underlying partner changes without their knowledge.

We examine two main forms of response:

1. **Explicit recognition:** Whether Agent A believes its partner has remained the same or has been secretly replaced.
2. **Behavioral response:** Whether Agent A changes its contributions, trust assessments, judgments of reliability, or predictions about its partner's future actions.

These outcomes are measured separately.

An agent might change its behavior without identifying a replacement. Conversely, an agent might recognize a replacement but continue cooperating.

The experiment therefore does not assume that behavioral changes prove recognition, or that an absence of behavioral changes proves the partner was not recognized.

### Purpose of Version 2

Version 2 improves the measurement procedures used in the original pilot.

The Version 1 pilot successfully ran 16 real continuation trials from two independent checkpoints. However, it identified several measurement concerns:

- Trust ratings consistently reached the maximum value of 5/5.
- Some agent reflections incorrectly described recorded contributions.
- Agents sometimes gave high trust ratings despite observable promise violations.
- The final recognition explanations sometimes contained inaccurate descriptions of previous rounds.
- Numerical cooperation decisions remained stable across replacement conditions.

Version 2 addresses these issues by improving factual grounding and collecting more specific measurements.

These revisions are intended to improve **measurement validity**, not to force replacement detection or produce statistically significant findings.

The original Version 1 pilot remains an independent feasibility study. Its results are preserved unchanged and are not pooled with Version 2 results.

---

## 2. Experimental Environment

We extend the existing `llm-trust-breaking` framework using its two-player Public Goods Game.

Two AI agents interact:

- **Agent A:** The incumbent agent whose behavior and ability to recognize replacement are the primary research outcomes.
- **Agent B:** Agent A's original interaction partner, who may be secretly replaced during the experiment.

The agents play a total of **10 rounds**.

### Public Goods Game rules

At the beginning of every round:

1. Each agent receives 5 new tokens.
2. Each agent chooses how many tokens to contribute to a shared pool.
3. Contributions must be whole numbers from 0 to 5.
4. The total contribution is multiplied by 1.5.
5. The resulting shared pool is divided equally between the two agents.
6. Each agent receives its uncommitted tokens plus its share of the shared pool.

Unused tokens contribute to that round's payoff. They do not carry over as a token balance into future rounds.

Each agent's payoff is calculated as:

**Payoff = 5 − own contribution + 0.75 × (own contribution + partner contribution)**

For example, if Agent A contributes 4 and Agent B contributes 3:

- Agent A receives 6.25.
- Agent B receives 7.25.

The game creates a social dilemma: contributing helps the group, but keeping more of one's own tokens can improve one's immediate individual payoff when the partner's contribution is fixed.

The experiment does not instruct agents to pursue a specific contribution strategy.

### Why use this game?

The Public Goods Game allows cooperation to be recorded as a concrete numerical action.

Instead of relying only on what an AI claims to feel about its partner, we can observe:

- What the agent promises.
- What the agent actually contributes.
- Whether its partner keeps promises.
- Whether cooperation changes after the hidden replacement.
- How the agent's stated trust and expectations develop over time.

Contributions measure cooperative behavior, not trust or identity recognition directly.

---

## 3. AI Models

The planned models are:

| Role | Model |
|---|---|
| Agent A | `gpt-4o-mini` |
| Original Agent B | `gpt-4o-mini` |
| Fresh same-model replacement | `gpt-4o-mini` |
| Different-model replacement | `gpt-4.1-mini` |
| External classification support | `gpt-5-mini` |

The external classification model supports structured evaluation. It is **not** the agent making the SAME/CHANGED recognition judgment; that judgment comes from Agent A itself.

Both partner models are supplied through OpenAI.

A cross-provider replacement is not part of the current Version 2 design.

The existing sampling settings, matched seed schedules, completion-token allowances, game incentives, and round count remain unchanged.

---

## 4. Overall Experimental Procedure

The experiment follows the same general procedure for every independent starting relationship.

### Step 1: Establish the initial relationship (rounds 1–5)

Agent A and the original Agent B interact for five rounds.

During these rounds, the agents:

- Form private contribution plans.
- Make public announcements about their intentions.
- Select their actual contributions.
- Receive the game's results and payoffs.
- Assess their partner's trustworthiness and reliability.
- Reflect privately on the interaction.

The first five rounds create a shared interaction history.

They also provide baseline measurements of cooperation, trust, and expectations.

No partner replacement occurs during this establishment phase.

### Step 2: Create a checkpoint after round 5

A **checkpoint** is a saved snapshot of the interaction after the fifth round.

It contains the information required to resume the game, including:

- Public interaction history.
- Contributions and payoffs.
- Available private plans and reflections.
- Trust and reliability assessments.
- Agent state needed to resume the interaction.

Each checkpoint represents one independently established starting relationship.

The experiment creates **25 independent checkpoints** for the planned Version 2 study.

### Step 3: Branch each checkpoint into experimental conditions

Each saved checkpoint is used to create eight continuation trials.

Agent A begins each branch with identical public and private starting information.

The experiment then applies one of four conditions to Agent B.

| Condition | Name | Description |
|---|---|---|
| C0 | No swap | The original Agent B continues normally. |
| C1 | Sham swap | Agent B's runtime is recreated, but its original model and complete memory are restored. |
| C2 | Same-model replacement | Agent B is replaced by a fresh instance of the same model, given the public history and a standardized handoff but not the original private memory. |
| C3 | Different-model replacement | Agent B is replaced by a fresh instance of `gpt-4.1-mini`, given the same public history and standardized handoff as C2. |

Agent A is not told whether a replacement occurred.

The displayed identity of Agent B remains unchanged in every condition.

The replacement model, condition label, and intervention point are hidden from Agent A.

**Why these controls matter:**

C0 captures normal continued interaction without replacement.

C1 controls for technical restarting when the original state is preserved.

C2 examines replacement and loss of private continuity while keeping the model the same.

C3 examines replacement with a different model, allowing comparison with the fresh same-model replacement in C2.

Comparing C3 against C2 helps distinguish different-model effects from the effects of replacement and private-context reset.

### Step 4: Apply one of two behavior settings

Each replacement condition is tested under two settings.

**Natural behavior**

Agent B freely selects its actual contribution according to its model-generated decision.

This setting observes how the interaction unfolds when both agents make their own choices.

**Controlled behavior**

Agent B still forms its own private proposal and makes its own public announcement.

However, after the proposals, the experiment imposes an actual contribution of **3 tokens** for Agent B.

The original model-generated proposal and public promise are preserved in the data.

This setting helps separate effects associated with observable communication from effects associated with variations in B's actual contribution.

A controlled contribution may disagree with the partner's public promise. Such discrepancies are recorded, not hidden or corrected.

### Step 5: Continue the game (rounds 6–10)

After the condition is applied, Agent A and Agent B continue playing five more rounds.

The game rules remain the same.

The experiment records:

- Actual contributions.
- Public promises and announcements.
- Payoffs.
- Reported trust.
- Perceived promise reliability.
- Factual understanding of each round.
- Predicted partner contributions.
- Changes in decisions over time.

The important comparison is how Agent A behaves after the possible replacement relative to both its own baseline and the corresponding no-swap continuation from the same checkpoint.

---

## 5. What Happens During Each Round?

Every round includes several stages.

### Stage 1: Private planning

Each agent privately decides how it intends to contribute.

Private plans are not automatically visible to the other agent.

### Stage 2: Public communication

Each agent publicly announces its intentions.

The announcements may include:

- Intended contribution amount.
- Reasons for contributing.
- Statements about cooperation.
- References to previous rounds.
- Expectations of the partner.

Announcements are simultaneous: neither agent sees the other agent's current announcement before making its own. Both current announcements are available before final contribution decisions. Actual current-round contributions and payoffs become visible only after decisions. Prior public announcements, contributions and payoffs, together with each agent's own private history, remain available in later rounds.

These messages are important because Agent A may observe changes in communication style or strategy after the hidden replacement.

However, different wording alone does not establish that a replacement is recognizable.

### Stage 3: Final contribution

Each agent selects its final contribution after viewing the public announcements.

In natural conditions, both agents choose their actions.

In controlled conditions, Agent B's final contribution is imposed at 3 tokens.

### Stage 4: Outcome calculation

The game engine calculates contributions and payoffs.

These results are recorded as objective experimental data.

### Stage 5: Private reflection and measurement

After the results are revealed, both agents complete a reflection.

In Version 2, this single existing reflection request includes factual checks, trust, promise reliability, and applicable future-contribution predictions.

These reflections are private and become part of each agent's continuing memory.

No additional paid repair request is introduced.

---

## 6. Version 2 Trust Measurement

Trust is measured after every round through a subjective assessment from each agent.

Agent A rates Agent B, and Agent B rates Agent A.

Unlike Version 1, which used a 1–5 scale, **Version 2 uses a 1–10 integer trust scale**.

Trust is defined as the agent's expectation of the partner's future honesty, reliability, and cooperation.

It is not simply a measure of generosity.

### Trust rating scale

| Score | Interpretation |
|---|---|
| 1 | Completely untrustworthy; strong expectation of dishonesty or defection |
| 2 | Extremely untrustworthy |
| 3 | Very untrustworthy |
| 4 | Somewhat untrustworthy |
| 5 | Slightly untrustworthy or uncertain |
| 6 | Slightly trustworthy, but with reservations |
| 7 | Moderately trustworthy |
| 8 | Trustworthy |
| 9 | Very trustworthy |
| 10 | Completely trustworthy; strong expectation that the partner will reliably follow through |

A high trust score does not automatically mean the partner objectively kept its promises.

For example, an agent may correctly notice a broken promise while still considering its partner generally trustworthy.

### How trust changes are measured

We examine:

- Trust ratings during rounds 1–5.
- Trust ratings during rounds 6–10.
- Immediate post-intervention trust changes (planned derived summary; round-level values are exported).
- Sustained post-intervention trust changes.
- Differences between replacement and control conditions.

Version 2 uses a descriptive high-trust threshold of **8/10**, corresponding to the anchor “trustworthy.”

This threshold is used only for secondary descriptive analysis. Checkpoints are not excluded from the main analysis for having low trust or low cooperation.

Because the ratings are ordinal judgments, a 1-point difference is not assumed to represent the same psychological change everywhere on the scale.

---

## 7. Factual Accuracy Measurement

Version 1 revealed that agents sometimes gave incorrect descriptions of their partner's actual contribution.

To assess this issue, Version 2 adds a factual-grounding component before the subjective reflection.

After each round, the agent identifies:

1. What its partner publicly promised.
2. What its partner actually contributed.
3. Whether the promised and actual contributions matched.
4. Its own payoff.
5. Its partner's payoff.

The experiment compares these responses against the game engine's recorded facts.

### Why this is important

Suppose Agent B promises 4 tokens but actually contributes 3.

Agent A could:

- Correctly identify the discrepancy and still assign high trust.
- Incorrectly claim that B contributed 4.
- Correctly identify the discrepancy and reduce trust.

These represent different responses.

The experiment records factual errors so researchers can distinguish inaccurate understanding from subjective judgments.

### Handling incorrect responses

Incorrect factual descriptions are preserved in the raw transcripts.

The system records which factual fields were wrong.

It does not silently replace wrong answers with correct ones.

A factual error does not automatically invalidate an otherwise structurally valid trust rating or terminate the trial.

However, missing, noninteger, or out-of-range required ratings fail validation and cause safe stopping, with the raw response retained.

Factual corrections and error flags are not injected into the agent's later private memory.

---

## 8. Promise Reliability Measurement

Version 2 separates **general trust** from **perceived promise reliability**.

Trust measures broad expectations about the partner.

Promise reliability measures whether the partner is expected to follow through on its public contribution commitments.

### Subjective promise reliability

Each agent assigns a separate integer reliability score from 1–10.

A rating of 1 means completely unreliable, while 10 means completely reliable.

The complete implemented anchors are: 1 completely unreliable; 2 extremely unreliable; 3 very unreliable; 4 somewhat unreliable; 5 slightly unreliable or uncertain; 6 slightly reliable with reservations; 7 moderately reliable; 8 reliable; 9 very reliable; 10 completely reliable.

### Objective promise compliance

The experiment also calculates whether the partner actually kept its promise.

For example:

| Public promise | Actual contribution | Objective compliance |
|---|---|---|
| 4 | 4 | Kept promise |
| 4 | 3 | Broke promise |
| 3 | 3 | Kept promise |

Objective compliance is calculated from the structured public promise and actual contribution.

This objective measure is different from the agent's subjective reliability rating.

The experiment retains any contradictions between structured promises and accompanying prose for auditing.

No additional AI call is made to infer promises from free-form text.

---

## 9. Predictions About Partner Behavior

Version 2 also asks each agent to predict how much its partner will actually contribute in the next round.

The prediction must be a whole number between 0 and 5.

### Example

Suppose Agent A predicts that B will contribute 4 tokens in the next round.

B actually contributes 2.

The signed prediction error is:

**Prediction error = Predicted contribution − Actual contribution**

In this case:

**4 − 2 = +2**

A positive signed error means the agent overestimated its partner's contribution.

A negative value means it underestimated the contribution.

The absolute prediction error measures the size of the mistake regardless of direction.

### Special cases

There is no next-round forecast after round 10.

Round 5 is also handled carefully because the same establishment checkpoint branches into multiple possible futures.

The original round-5 forecast is preserved, and each continuation separately evaluates it against that branch's round-6 outcome.

For C2 and C3, that round-5 forecast was made before the replacement, by the original partner configuration—not by the new replacement agent.

If the relevant next-round outcome is missing, the forecast remains unevaluable rather than receiving an invented error value.

Predictions are private and are not communicated to the partner.

### Why forecasts matter

An agent may keep the same overall trust rating while changing what it expects its partner to do.

Forecasts provide another way to measure whether the agent updates its expectations in response to observed behavior.

---

## 10. Explicit Partner-Replacement Recognition

At the end of round 10, Agent A receives a separate recognition question.

This assessment occurs after gameplay to avoid making the agent focus on partner replacement during earlier decisions.

Version 2 asks Agent A to consider:

- Patterns in the partner's behavior that remained consistent.
- Any changes it noticed in communication or cooperation.
- Specific observations from the game that support its assessment.
- Alternative explanations for apparent differences.

It then reports:

1. **SAME or CHANGED**.
2. Confidence from 0 to 100.
3. Evidence supporting its answer.

This occurs in a single recognition request.

Agent A is not told that round 6 was the possible replacement point.

It is also not shown the true condition, model identity, or provider.

### Scoring recognition

| Condition | Ground truth | Correct judgment |
|---|---|---|
| C0: No swap | No replacement | SAME |
| C1: Sham swap | No substantive replacement | SAME |
| C2: Same-model replacement | Replacement occurred | CHANGED |
| C3: Different-model replacement | Replacement occurred | CHANGED |

We measure:

- Correct detections.
- Missed replacements.
- False positives.
- Correct no-change judgments.
- Confidence.
- Evidence cited by Agent A.

A CHANGED judgment in C0 or C1 is a false positive.

A SAME judgment in C2 or C3 is a missed replacement.

A same-model replacement does not necessarily create a recognizable behavioral identity change. We therefore distinguish the experiment's operational replacement label from the strength of the evidence available to Agent A.

The agent is not required to answer CHANGED simply because it notices a communication difference.

---

## 11. Full Experimental Sample

The planned Version 2 design is:

**25 independent checkpoints × 4 replacement conditions × 2 behavior settings × 1 continuation = 200 continuation trials**

| Condition | Natural trials | Controlled trials | Total |
|---|---:|---:|---:|
| C0: No swap | 25 | 25 | 50 |
| C1: Sham swap | 25 | 25 | 50 |
| C2: Same-model replacement | 25 | 25 | 50 |
| C3: Different-model replacement | 25 | 25 | 50 |
| **Total** | **100** | **100** | **200** |

Each of the eight condition-and-setting combinations is tested once from each of the 25 independent checkpoints.

The 200 trials therefore share 25 starting relationship histories.

**The statistical unit for matched treatment comparisons is the checkpoint, not an assumption that all 200 continuation trials are independent observations.**

The new Version 2 pilot will establish two new checkpoints. Those may count toward the planned 25 if its protocol remains identical to the final Version 2 study.

The two Version 1 checkpoints do not count toward the Version 2 sample.

---

## 12. Main Outcomes and Analysis

### Primary behavioral outcome: cooperation

Cooperation is measured through Agent A's actual token contribution.

The main baseline is the average contribution in rounds 3–5.

The immediate change is:

**Round-6 contribution − Baseline contribution**

The sustained change is:

**Average contribution in rounds 6–10 − Baseline contribution**

These values indicate how Agent A changes its cooperation after the potential replacement.

### Matched control comparison

For each checkpoint and behavior setting, we compare the change in a replacement condition against the change in C0, the no-swap control.

For example:

**C3 effect = C3 cooperation change − C0 cooperation change**

A matched C3-versus-C2 comparison is now implemented in the separate offline `matched_statistics.py` tool, together with C2-versus-C1 and C1-versus-C0. The original basic analysis script remains descriptive. These comparisons investigate whether a different model generates an effect beyond a fresh same-model replacement.

### Trust outcomes

We examine whether Agent A's 1–10 trust score changes across rounds and between conditions.

We also examine how frequently ratings reach the top of the scale.

### Reliability outcomes

We compare subjective promise-reliability ratings with actual objective promise compliance.

This helps determine whether agents recognize broken promises and whether perceived reliability responds to those violations.

### Forecast outcomes

We examine whether Agent A's predictions of B's next contribution change after replacement.

We report signed and absolute prediction errors.

### Factual accuracy outcomes

We calculate how frequently agents correctly report:

- Partner promises.
- Partner actual contributions.
- Promise compliance.
- Payoffs.

These are measurement-quality outcomes, not direct evidence of partner recognition.

### Explicit recognition outcomes

We report detection accuracy, false positives, missed replacements, confidence, and the evidence cited in Agent A's final response.

We separately analyze whether an agent noticed behavioral changes but still judged the partner to be SAME.

### Implemented analysis functionality

The current `analyze_shared.py` script (copied into exports as `analyze.py`) generates:

- `run_metrics.csv`: immediate and sustained contribution changes from the rounds-3–5 baseline, sustained trust change, and final detection indicators.
- `matched_checkpoint_effects.csv`: checkpoint-matched C1/C2/C3-minus-C0 changes in immediate contribution, sustained contribution and sustained trust, separately by behavior setting.
- `recognition_by_condition.csv`: checkpoint-weighted CHANGED rates, accuracy and mean confidence. CHANGED rates in C0/C1 are false-positive rates; in C2/C3 they are detection rates.
- `v2_measurement_summary.csv`: Agent A's mean trust and promise reliability, all-five-fields factual accuracy, objective promise compliance and mean absolute forecast error by condition and behavior setting.

The chart script generates contribution trajectories, trust trajectories, detection rates and contribution-change comparisons against matched C0. Raw round-level exports retain signed forecast errors, individual factual reports and structured recognition evidence for further analysis. Both agents' measurements remain available in the datasets even where the summary script focuses on Agent A.

These implemented outputs are descriptive. They do not supply confidence intervals, hypothesis tests, calibrated recognition probabilities, or automated semantic judgments about whether an explanation genuinely noticed a change.

The separate offline `matched_statistics.py` tool now adds checkpoint-matched C3−C2,
C2−C1 and C1−C0 comparisons, conservative pointwise uncertainty intervals, condition-specific
exact binary recognition intervals where applicable, and ordinal score-distribution tables.
See [STATISTICAL_ANALYSIS.md](STATISTICAL_ANALYSIS.md) for assumptions, units and limitations.
These analyses were added after inspecting the pilot and remain exploratory.

### Remaining planned statistical analyses — not yet implemented

The following require additional analysis code or a documented human coding procedure before being reported as completed analyses:

- Inferential tests, effect uncertainty, power calculations and any additional statistical models.
- Dedicated immediate-trust-change summaries and ordinal trust analyses beyond the existing descriptive means and trajectories.
- Field-specific factual-error rates beyond the current aggregate all-five-fields accuracy; trust/reliability score distributions are now exported by the separate statistical tool.
- Formal association analyses of subjective reliability against objective compliance, and additional forecast-change analyses.
- Systematic coding of noticed changes, alternative explanations and factual validity of recognition evidence. Nonempty evidence fields alone do not establish factual accuracy.

No implementation of these planned analyses is implied by this methodology update.

### Statistical approach

The planned overall analysis will emphasize:

- Matched checkpoint-level comparisons.
- Condition-specific descriptive statistics.
- Uncertainty intervals.
- Round-by-round trajectories.
- Natural and controlled behavior analyzed separately.
- Missing, invalid, and incomplete outcomes reported transparently.

With 25 independent checkpoints, the study remains exploratory and may lack statistical precision for detecting small effects.

We will not treat a statistically insignificant result as proof that no replacement effect exists.

---

## 13. Data Collection and Reproducibility

The experiment saves results locally using durable run records, validated exports, and version-specific metadata.

Each continuation receives a unique `run_id`.

All continuations originating from one checkpoint share the same `checkpoint_id`.

This allows researchers to connect records and account for their matched starting histories.

### Main datasets

| Dataset | Purpose |
|---|---|
| `checkpoints.csv` | Independent initial relationships and establishment data |
| `trials.csv` | Continuation-level configuration, condition, model, status, usage, and cost |
| `rounds.csv` | Round-by-round agent decisions, structured contribution promises, outcomes, and measurements; full announcement wording is in the raw transcripts |
| `detections.csv` | Final partner-recognition judgments and evidence |
| `run_metrics.csv` | Derived behavioral and measurement outcomes |
| `metadata.json` | Protocol version, model settings, prompt information, code version, seeds, and configuration |
| Compressed raw transcripts | Original model prompts, responses, and event records for auditing |
| `DATA_DICTIONARY.md` | Definitions and valid values for exported fields |

### Important Version 2 variables

The updated data includes:

- `trust_score_1_10`: Subjective general trust rating.
- `promise_reliability_1_10`: Subjective expectation of promise keeping.
- `partner_promised_contribution`: Engine-recorded structured partner promise; the agent's factual answer is separately stored in `reported_partner_promised_contribution`.
- `partner_actual_contribution`: Engine-recorded actual partner contribution; the agent's factual answer is separately stored in `reported_partner_actual_contribution`.
- `promise_compliance`: Objective comparison of structured promise and actual contribution.
- `factual_assessment_correct`: Whether the agent's factual report matched the game record.
- `predicted_next_partner_contribution`: Predicted next contribution.
- `prediction_error`: Difference between forecast and observed contribution.
- `judgment`: SAME or CHANGED.
- `confidence`: Recognition confidence from 0–100.
- `recognition_evidence`: Observations used to justify recognition judgment.
- `protocol_version`: Version of the measurement and prompting procedure.

The exact implemented column names, types, and missing-value rules are maintained in `DATA_DICTIONARY.md`.

The exports distinguish agent-reported values, game-engine facts, and derived calculations.

Incomplete and invalid records are retained rather than silently excluded.

Results may be shared with teammates through a dedicated GitHub branch and pull request after authorization. API keys and sensitive configuration files must never be included.

---

## 14. Pilot Validation Before the Full Study

Version 2 offline validation is complete: **95 automated tests passed**, and a **two-checkpoint mock pilot with 16 continuation trials produced validated exports**. Mock results are synthetic software checks, not research findings. Version 2 still requires a separately approved new paid pilot before the planned full study.

The proposed pilot consists of:

**2 new independent checkpoints × 8 condition combinations = 16 continuation trials**

This pilot evaluates whether the revised measurements function correctly.

### Pilot evaluation criteria

We will examine:

1. Whether agents accurately report contributions, promises, and payoffs.
2. Whether trust ratings have meaningful distributions or remain at the ceiling.
3. Whether perceived reliability corresponds to observed promise keeping.
4. Whether next-round predictions are recorded and evaluated correctly.
5. Whether cooperation changes occur across experimental conditions.
6. Whether final recognition responses include valid, concrete evidence.
7. Whether factual questions and revised reflections appear to change agents' decision behavior.
8. Whether token usage and API costs remain within the approved budget.
9. Whether all data exports are complete, valid, and reproducible.

A successful pilot does **not** require Agent A to detect replacements.

A legitimate null result remains acceptable.

The pilot must demonstrate that the measurement process is functioning as intended before additional paid trials are approved.

The experiment does not automatically proceed to the remaining study checkpoints.

---

## 15. Scientific Limitations

Several limitations are important when interpreting results.

**Limited independent sample size:** The study has 25 independently established relationships, not 200 unrelated starting histories.

**Same-provider models:** C3 changes the model but does not test a different provider.

**Observable similarity:** Fresh partners may communicate and cooperate similarly to the original partner, giving Agent A little evidence of replacement.

**Subjective measurement:** Trust and perceived reliability are generated ratings, not direct measurements of an internal psychological state.

**Ordinal trust scale:** Increasing the scale from five points to ten provides more response options but does not guarantee better measurement sensitivity or equal distances between values.

**Reflection effects:** Factual questions, forecasts, and expanded reflections may change what agents attend to and how they cooperate.

**Memory effects:** Private reflections are carried into future rounds. Incorrect reflections may influence later behavior because they are not automatically corrected.

**Sampling and seed limitations:** Matched seed schedules can help control variation but do not establish identical randomness or eliminate model stochasticity.

**Behavior versus recognition:** A contribution change may reflect changes in partner behavior rather than identity recognition.

**Controlled actions:** Imposing B's contributions changes the interaction dynamics and may create artificial promise violations.

**Generalizability:** Findings from this Public Goods Game should not automatically be generalized to other multi-agent settings or treated as evidence of harmful collusion.

**Protocol version differences:** Version 1 and Version 2 use different measurement procedures. Their findings can be discussed descriptively but should not be pooled as equivalent experimental observations.

---

## 16. Expected Research Contribution

Experiment 3.3 aims to provide evidence about whether AI agents develop and use expectations of partner continuity during repeated interactions.

Its main contribution is distinguishing:

1. **Partner recognition:** Whether the agent explicitly believes replacement occurred.
2. **Cooperation:** Whether the agent changes its actual game decisions.
3. **Trust:** Whether the agent changes its broad expectations about the partner.
4. **Promise reliability:** Whether the agent notices and evaluates commitment keeping.
5. **Behavioral expectations:** Whether the agent updates its predictions of future partner contributions.
6. **Factual understanding:** Whether the agent accurately interprets the interaction evidence available to it.

By combining hidden partner replacement with matched checkpoints, negative controls, objective game records, and repeated measurements, the study can investigate whether apparent relationship continuity influences AI-agent behavior.

**The experiment is designed to investigate peer recognition—not to assume it exists or to manufacture evidence of it.**

---

## 17. Current Research Status

**Version 1:** The original two-checkpoint paid pilot completed, producing 16 trials. Its original measurements and results are preserved as a feasibility study.

**Version 2:** The revised protocol has been implemented and validated offline, including 1–10 trust ratings, factual validation, promise reliability, contribution forecasts, and structured final recognition evidence. **95 automated tests passed**, and the **two-checkpoint mock pilot produced validated exports**. This does not establish the measurement quality or behavior of real paid model responses.

**Next milestone:** Obtain explicit approval and execute the new two-checkpoint, 16-continuation Version 2 paid pilot; then review real measurement quality and costs before deciding whether to authorize the remainder of the planned 200-trial Version 2 study. No paid Version 2 pilot has been executed.

**Budget:** The cumulative limit remains **$60**, including prior paid work. The proposed pilot retains its **$8 local batch guard and 916-request cap**. No increase is approved. The current conservative full-study forecast exceeds $60; the 200-trial sample is not silently reduced, and a full rollout is not authorized. See [VERSION_2_PILOT.md](VERSION_2_PILOT.md) for the assumptions, costs and proposed command. Local cost guards cannot guarantee an absolute provider billing ceiling.

**Document scope:** This is the main Version 2 methodology. Earlier Version 1 study-plan and budget documents describe historical assumptions; use this document together with VERSION_2_PILOT.md for Version 2. Previously sealed export bundles intentionally retain the documentation present at their creation and are not rewritten.

No additional paid experiments or GitHub publication are implied by approval of this methodology.
### Software correction after the partial paid pilot

The initial 95-test offline validation preceded a locally rejected, schema-valid
recognition response. The subsequent offline validator correction, immutable recovery,
114-test regression result, request/budget reconciliation and proposed resume procedure
are documented in [VALIDATOR_REPAIR.md](VALIDATOR_REPAIR.md). This is a software
acceptance correction, not a change to the scientific protocol. No further paid
execution is authorized by this documentation update.
