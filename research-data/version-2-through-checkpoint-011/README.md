# Experiment 3.3 Version 2 — cumulative results through checkpoint 011

Real paid data, not synthetic: 12 independent checkpoints and 96 completed matched
continuations. The newest data/ snapshot contains all 200 planned trial rows, with
96 complete and 104 unstarted. There are 1080 observed agent-round rows.
The report/cumulative_completed_trials.csv file is the 96-completed-trial-only view.
The approved 007–011 batch completed five new checkpoints and 40 trials. No later
checkpoint or publishing was started. Read report/REPORT.md first.

Open cumulative-data.xlsx for the same canonical data, incremental/cumulative
costs, condition summaries, recognition evidence, uncertainty intervals and budget
forecasts. CSV/JSON remain canonical for precision.

Reproduce offline with standard Python 3.10+ and no API keys or extra dependencies:

```bash
python matched_statistics.py data --output reproduced-statistics
python budget_review.py data --output reproduced-budget
```

Choose new output directories. These scripts never invoke API transports or change
policy files. Statistics use checksummed compact CSVs; budget reconstruction also
uses the included raw.jsonl.gz. Any hypothetical future-window fields in the budget
summary are calculations only, not authorization. No checkpoint 012 or beyond is
authorized. No paid call, retry or GitHub push occurs when reproducing analysis.

Use checkpoint_id as the independent relationship unit, not the 96 games or all
round rows. Match by run_id, keep natural/controlled separate, and do not pool V1.
The reviewed uncertainty method and analysis rules were not changed. Means of
ordinal 1–10 scores remain descriptive. Contradiction flags request human review
and never rewrite saved judgments, confidence or empty text.

Use this latest cumulative snapshot instead of concatenating overlapping old
exports. The $60 limit and $10 reserve remain unchanged. No keys or compute.env
are included. data/ preserves sealed original records and software-recovery audit.
