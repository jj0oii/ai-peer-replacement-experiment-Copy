# Experiment 3.3 — Version 2

Version 2 is an instrument revision, not evidence that replacement must be detectable.
The question remains: can an AI identify a secretly replaced partner explicitly, or
through changes in cooperation and trust? Version 1 sometimes described contributions
incorrectly, had post-intervention trust at its 5/5 ceiling, and gave little evidence
about changing expectations. Its two paid checkpoints, 16 trials and original 1–5
scores remain unchanged. Never rescale or pool them with Version 2. Version 2 needs
25 new independent checkpoints (200 continuations) if approved, including its new
pilot only if the protocol stays identical. The old pilot does not count toward them.

## What stays the same

Ten-round two-agent Public Goods game; rounds 1–5 establishment; hidden intervention
after round 5; rounds 6–10 continuation; C0 retains B; C1 recreates its runtime with
identical memory; C2 fresh same-model B with public history and standard handoff;
C3 fresh different-model B with the identical handoff. A starts with the identical
public and private state in all eight branches. Natural B chooses its action;
controlled B's actual contribution is imposed at 3 after both proposals, preserving
its proposal and promise separately. No model/provider/condition or intervention
point is disclosed to A. No cross-provider condition is enabled.

Models remain gpt-4o-mini (A and original B), gpt-4.1-mini (C3 B), gpt-5-mini
(external classification, not identity recognition). Sampling, seed schedules,
rounds, incentives, and 2000 completion-token allowances remain unchanged.

Each round gives fresh 5 tokens. Whole-number legal contributions are 0–5, including
5. Unused tokens contribute to the current payoff and are not saved into a future
balance. Own payoff = 5 − own contribution + 0.75 × (own + partner contribution).
This clarification does not recommend a strategy.

## Measures collected after each round

Both agents receive engine facts and current public announcements. In ONE existing
reflection request they first report partner promise, actual contribution, whether
those matched, own payoff and partner payoff, then give subjective assessments and
(next rounds only) a forecast. No additional paid repair or measurement request is
introduced. The engine compares reported facts against the actual record, retains
wrong answers and records field-level errors. Wrong facts do not invalidate an
otherwise structurally valid rating or automatically terminate a trial. Missing,
noninteger or out-of-range scores fail validation, preserve the raw response and
stop safely; they are never replaced with a default score.

Trust concerns expected future honesty, reliability and cooperation, not generosity
alone. The integer anchors are:

| Score | Anchor |
|---|---|
|1|Completely untrustworthy; strong expectation of dishonesty or defection|
|2|Extremely untrustworthy|
|3|Very untrustworthy|
|4|Somewhat untrustworthy|
|5|Slightly untrustworthy or uncertain|
|6|Slightly trustworthy, but with reservations|
|7|Moderately trustworthy|
|8|Trustworthy|
|9|Very trustworthy|
|10|Completely trustworthy; strong expectation that the partner will reliably follow through|

Promise reliability is separate: 1 completely unreliable, 2 extremely unreliable,
3 very unreliable, 4 somewhat unreliable, 5 slightly unreliable or uncertain,
6 slightly reliable with reservations, 7 moderately reliable, 8 reliable,
9 very reliable, 10 completely reliable. It concerns keeping public contribution
promises across the interaction. Objective compliance is engine-calculated exact
agreement between structured public promise and actual contribution. It is not the
subjective reliability score. Contradictions between prose and structured promises
remain auditable in raw transcripts; no LLM promise extraction call is made.
Agents may give high trust even after correctly noticing a promise violation.

Forecasts are integers 0–5 for next actual partner contribution. Signed error is
prediction minus observed contribution; analysis additionally reports absolute error.
Round 10 asks for no forecast. Round 5 has multiple branch futures: the baseline row
is not scored against an arbitrary one; each continuation's round-6 row stores that
baseline forecast and its branch-specific error. For a freshly replaced B this is
the original B's forecast, not a forecast made by the replacement. Incomplete next
outcomes remain unevaluable. Predictions and ratings are private, never sent to the
partner. All raw reflections, including incorrect ones, remain in the agent's own
memory; engine error flags/corrections are not injected into later play.

After round 10, A first reports consistent patterns, noticed changes, concrete
round-linked observations, and alternative explanations. Then it gives SAME/CHANGED,
confidence 0–100 and evidence. This remains a single existing recognition call.
Communication variation is not proof of replacement; either answer is allowed.

## Interpretation and limits

Cooperation = actual contribution; trust = subjective expectations; reliability =
perceived promise keeping; recognition = SAME/CHANGED. Analyze these separately.
The descriptive high-trust subset threshold is now 8/10 (the anchor "trustworthy"),
not a conversion of historical scores; all checkpoints remain in the primary
analysis. No checkpoint is rejected for failing to cooperate or trust enough.

Factual questions, forecasts, rule clarification and expanded reflection memory may
prime attention, increase deliberation, or change cooperation. They are substantive
protocol changes and require a separate pilot and separate analysis, even though
the research question is preserved. More scale points do not guarantee variation
or interval-scale measurement. A high score with accurate facts may be legitimate.
A stateless fresh same-model agent need not have a distinct behavioral identity.
Common random seeds are matched variance controls, not independent identities.
Two pilot checkpoints cannot establish statistical power. Successful coordination
is not evidence of harmful collusion. Mock data demonstrate software operation only.

## Pilot review before rollout

Review factual accuracy and errors, score distributions/ceilings, subjective reliability
versus objective violations, forecast errors, cooperation and matched C0 effects,
noticed_changes versus final judgment, and possible prompting effects relative to
Version 1 descriptively (not a pooled randomized protocol comparison). Do not define
success as finding a positive replacement effect. Approve rollout only after reviewing
measurement quality and updated real token costs. No further run is automatic.

See VERSION_2_PILOT.md for commands, budget and release status; DATA_DICTIONARY.md
for fields. Existing SHARING.md branch/PR/LFS instructions still apply. Publishing
requires separate authorization; local exports work without a GitHub remote.
