# Shared research snapshots

- **version-2-through-checkpoint-011/**: real Version 2 data from 12 independent
  checkpoints and 96 completed C0–C3 continuations. The planned-trial table also
  contains 104 unstarted rows; filter status before analysis.
- **c4-checkpoint-000-partial/**: separate exploratory Gemini extension, incomplete
  after HTTP 429. **Zero completed C4 trials.** Do not pool it with completed games.

These are compact copies; the canonical local datasets were not changed. Large raw
transcripts stay local pending a separately configured LFS/external-storage route.
The original snapshot checksum manifests are preserved and refer to full bundles,
including omitted raw transcripts; full-bundle verification and budget reconstruction
therefore need those transcripts. `SHARED_CHECKSUMS.json` verifies every included
file in this compact publication. CSV and metadata bytes are copied unchanged.

Open `version-2-through-checkpoint-011/cumulative-data.xlsx` in Excel, or use CSVs
in its `data/` directory. Read `data/DATA_DICTIONARY.md` and `report/REPORT.md`.
Reproduce matched statistical analysis without keys or API calls:

```bash
python research-data/version-2-through-checkpoint-011/matched_statistics.py \
  research-data/version-2-through-checkpoint-011/data \
  --output /tmp/peer-shared-reproduced-statistics
```

Use a new output directory. Analyze natural and controlled behavior separately,
and use checkpoint IDs for independent relationships. Do not concatenate overlapping
snapshots or treat the eight matched conditions as independent relationships.
