# Version 2 offline review

Status: ready for explicit approval of a small paid pilot; no paid execution or
GitHub publication authorized or performed during this implementation.

- Final unittest run: 95 passed, zero failures/errors (75 existing + 20 new).
  Log: `/tmp/peer-v2-final-tests.log`.
- Python syntax checks passed for peer_identity modules and experiment entry points.
- Complete mock pilot: two checkpoints, 16 completed continuations, 916 mocked
  inference responses, zero paid requests and $0 actual cost.
- Immutable validated export:
  `/workspace/peer-identity-exports/v2-review/attempt_15a0f01db1b54c22822736e1b57a5284`
- Export rows: rounds 180; trials 16; detections 16; run_metrics 16; checkpoints 2.
  Zero incomplete continuations. Re-verified after executing portable analysis and
  charts. CSV value checks, journal agreement, derived measures, checksums and
  automated secret scans passed.
- Standalone analysis: `/workspace/peer-identity-exports/v2-review/analysis`.
  Four PNG/SVG charts: `/workspace/peer-identity-exports/v2-review/charts`.
  Synthetic scores/behavior are fixtures, not scientific evidence or real usage.
- Version 1: all 974 raw-root files byte-identical across implementation validation;
  historical sealed export payload checksums intact. No V1 scores were converted.
- No paid V2 root exists. Budget remains $60; no remote push or settings change.

Implemented: 1–10 trust/reliability, factual answer/error recording, objective promise
compliance, next-round forecasts (including branch-specific round-5 scoring), neutral
structured recognition, rule clarification, versioned configuration/schema, native
scale exports/analysis/charts, interruption-safe persistence, existing sharing path.
Invalid scores are blocked and raw responses retained; wrong valid facts are retained
and flagged without extra calls. Tests cover both cases and no network is permitted
in integration fixtures. A's starting states and C0/C1/C2/C3 invariants are verified.

Initial integration checks exposed a new-document allowlist mismatch and a portable
chart bytecode-cache issue. Both are fixed; chart imports now suppress cache writes
into sealed bundles. The final complete mock,
standalone charts, re-verification and full suite passed after this correction.

GO for requesting approval of the two-checkpoint pilot ($5.9728 provisional full-output
planning estimate, $8/916 local guards). NO-GO for automatically continuing the full
study: $74.66 V2 full-output study forecast plus $0.4954921 prior allowance and $10
reserve is $85.1554921, above the unchanged $60 policy. Review real V2 pilot usage,
measurement quality and methodological effects before any further decision.

See VERSION_2_PILOT.md for exact command, assumptions and budget limitations;
VERSION_2_METHODOLOGY.md for definitions and protocol trade-offs. No findings from
Version 1 or synthetic tests establish that the new measurements will vary or that
replacement can be detected. Version 1 and Version 2 must remain separate analyses.
