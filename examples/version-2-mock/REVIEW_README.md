# Experiment 3.3: teammate review

**If metadata.json says `mock: true`, all model outputs and token counts are synthetic
fixtures. They validate the pipeline and are NOT research findings.** The included
mock fixture always proposes four tokens, reports trust 4/5, and answers SAME.
Consequently the flat lines and zero detection rates are intentional test inputs.

Open `rounds.csv`, `run_metrics.csv`, `detections.csv`, `trials.csv` and `checkpoints.csv`
in a spreadsheet, pandas, R or another CSV reader. Empty cells mean missing data,
not zero. See DATA_DICTIONARY.md for plain-language definitions. Join games by run_id;
join their shared pre-swap relationship by checkpoint_id. Never count repeated
continuations as independent relationships. Select one export version per batch.

## Reproduce the tables without installing packages

```bash
python3 /path/to/bundle/analyze.py /path/to/bundle --output /tmp/peer-tables-review
```

## Reproduce the four charts

Requires Python 3.10+ and matplotlib. The experiment's existing `.venv` already has it;
teammates can install matplotlib in their own virtual environment with `python -m pip
install matplotlib`. This installs a plotting library, not an API client or model.

```bash
python3 /path/to/bundle/charts.py /path/to/bundle --output /tmp/peer-charts-review
```

Use a new output directory each time. Raw transcripts/LFS, API keys and network
access are unnecessary. The script checks the compact CSV/metadata checksums and writes:

- `contributions.png/.svg`: A's average contribution by round and condition.
- `trust.png/.svg`: A's average trust in B by round and condition.
- `detection_rates.png/.svg`: fraction answering CHANGED; C0/C1 rates are false positives.
- `matched_changes.png/.svg`: A's round-6 change minus the matched no-swap change.
- `plot_data.csv`: plotting values and independent-checkpoint counts.
- `run_metrics.csv`, matched-checkpoint tables and a labelled summary.

Natural and controlled behavior get separate panels. Means average repetitions within
a checkpoint first. Shared baseline rounds 1–5 are displayed identically across
condition curves but are stored only once in rounds.csv. All fields and formulas
are in the data dictionary. Two checkpoints validate engineering, not statistical
power. Trust/cooperation changes alone do not demonstrate peer recognition or harmful
collusion. For auditing, raw.jsonl.gz retains model prompts/responses and saved state.

## Version 2

Check `metadata.json` for protocol version before interpreting trust. V2 trust and
promise reliability run from 1 to 10; V1 trust remains 1–5. Open rounds.csv in a
spreadsheet, filter agent=A and keep natural/controlled separate. Detection evidence
is JSON text in detections.csv. Run `python analyze.py --output ../my-v2-analysis`
from the exported directory for matched changes, detection rates, and the new
`v2_measurement_summary.csv` (facts, compliance, reliability, forecasts). Run
`python charts.py --output ../my-v2-charts` to reproduce the four charts; matplotlib
is required for charts only. These commands make no API calls. Output directories
must be new and outside the sealed export. Forecast error means prediction minus
next observed contribution, not a trust rating. Read the dictionary before joining
round-5 forecasts across branches. Synthetic mock datasets are software examples,
not research findings. Do not pool protocols.
