# Local export and authorized GitHub sharing

**Active 200-trial study:** use [FINAL_STUDY_PLAN.md](FINAL_STUDY_PLAN.md) for paid commands.
All checkpoint windows share one canonical raw directory and cumulative ledger. Unique
export directories represent immutable snapshots, not new independent studies. Do not
use a fresh raw directory to restart the spending allowance.


All steps below are local/offline unless explicitly marked **network/publication**.
No experiment is approved by this document. Paid inference still requires approval
of its scope, model access/current prices, request count and dollar budget. No push,
PR, credit purchase, remote-setting change or LFS setup has been performed.

## 1. Create a batch (only when its paid pilot is approved)

From `/workspace/collusion_hackathon/llm-trust-breaking`:

```bash
BATCH_DIR=outputs/peer-identity/study-200-v1
.venv/bin/python experiments/run_peer_identity.py \
  --mode paid --approve-paid --checkpoints 25 --repetitions 1 \
  --checkpoint-start 0 --checkpoint-count 2 \
  --max-requests 11450 --batch-max-requests 916 \
  --budget-usd 50 --batch-budget-usd 8 \
  --study-total-budget-usd 60 --reserve-usd 10 --prior-spend-usd 0.01 \
  --export-after-batch --export-root /workspace/peer-identity-exports/study-200 \
  --output "$BATCH_DIR"
```

This is still the two-checkpoint, eight-condition pilot (916 maximum inference
requests), not the full study. Use `--mode mock` instead of `--mode paid --approve-paid`
for a free test. For unrelated standalone workflows omitting `--output` creates a unique directory;
do NOT omit it for this study, whose windows must share the canonical ledger. Every batch receives a stable independent UUID even when a custom directory
name is supplied. Nonempty directories are rejected unless `--resume` is explicit.

To resume an **incomplete** approved batch, repeat exactly its original settings with
`--resume --output "$BATCH_DIR"`. Completed outputs are not overwritten, even on resume.
A resume keeps the same batch/run IDs; it is not an independent experimental replication.
Requests blocked/pending after ambiguous failures require review and are not silently
resent. The manifest refuses execution-code/config changes on resume; do not modify
old manifests to bypass this check. Old-version batches remain exportable.

Each dispatch reservation is fsynced before sending. Completed and blocked responses,
atomic round snapshots and all unique execution attempts remain local. SIGINT/SIGTERM
record an interrupted attempt; an uncatchable kill/power loss leaves the last durable
pending request rather than pretending the call completed. Data never received from
the provider cannot be recovered. Back up batch directories using your team's storage
policy; no local filesystem can guarantee survival of disk loss.

## 2. Validate and export locally (free)

Exports do not require GitHub, credentials, or a network connection. The CLI reads
known credential values only in memory to scan for accidental inclusion; it never
prints or exports them.

```bash
EXPORT_DIR="/workspace/peer-identity-exports/$(basename "$BATCH_DIR")-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
.venv/bin/python experiments/export_peer_identity.py "$BATCH_DIR" --output "$EXPORT_DIR"
.venv/bin/python experiments/export_peer_identity.py "$EXPORT_DIR" --verify-export
```

An existing export destination is always rejected. Exports are assembled in a temporary
sibling directory and atomically renamed only after validation. The source batch is
read-locked against the CLI writer. Full-state results are cross-checked against
request journals, including models, labels, actions and payoffs. Missing fields,
duplicate IDs, invalid values, wrong condition ground truth, mismatched usage/costs,
corrupt hashes and likely secrets block export. Incomplete but internally consistent
runs are valid exports with missing values/statuses explicitly represented.

Bundle contents:

- `rounds.csv`: per-agent observed rounds; baseline rows appear once per checkpoint.
- `detections.csv`: all planned continuations, with missing judgments explicit.
- `trials.csv`: all planned continuations, statuses and known/unknown usage accounting.
- `checkpoints.csv`: independent establishment histories and their costs, counted once.
- `metadata.json`: execution config/commit/source hashes, models, seeds, UTC timestamps,
  price assumptions, batch status, join definitions and raw-source hashes.
- `raw.jsonl.gz`: streamed, compressed allowlisted source snapshots, exact prompts,
  outputs, journals, checkpoints, progress, attempts, results, errors and pending calls.
- `DATA_DICTIONARY.md`: every column, value range, join and missing-data convention.
- `analyze.py`: standalone standard-library analysis for compact downloads.
- `validation.json`, `checksums.json`: validation evidence and content hashes.

A dirty execution tree is reported honestly. The execution commit SHA alone does not
identify uncommitted code: the allowlisted source snapshot and per-file hashes do.
Legacy batches get a stable adopted identity, but unknown original commit/timestamps
remain unknown; the current HEAD is not relabeled as the historical execution commit.

Only explicitly selected JSON data/source files are archived. `compute.env`, `.env`,
HTTP authorization headers, arbitrary logs, credentials and local configuration are
excluded. Pattern scans cover common provider/GitHub/AWS keys, bearer strings/private
keys, sensitive structured fields, and exact known local credential values. CSV text
is protected against spreadsheet formula execution. Automated scans can have false
negatives/positives: review the concrete bundle before sharing. On a scan failure,
retain original local evidence; fix the accidental logging source and prepare a
reviewed sanitized copy rather than deleting original research data.

## 3. Teammate download and immediate independent analysis

A teammate can download the compact bundle from GitHub without credentials for inference
or the original runtime. They need only Python 3.10+ (no packages). Raw transcripts/LFS
are not required for CSV analysis:

```bash
python3 /path/to/downloaded/bundle/analyze.py /path/to/downloaded/bundle \
  --output /tmp/peer-analysis-$(date -u +%Y%m%dT%H%M%SZ)
```

This verifies compact-file checksums and emits per-run metrics, checkpoint-level
matched contribution/trust changes, and condition-specific changed/accuracy rates.
C0/C1 changed rates are false-positive rates. Repetitions are paired before averaging
within checkpoints. Natural and controlled settings stay separate. Missing judgments
and unfinished games are counted explicitly. Outputs are descriptive; choose
inferential models/multiplicity handling separately.

CSV readers such as pandas/R can use the same join keys. Join baseline to continuations
by `checkpoint_id`, detections to trials by `run_id`, and match conditions by checkpoint,
setting and repetition. Do not count three continuations as three independent
relationships. Do not concatenate multiple export snapshots of the same batch as new
data: select a single intended export per batch (typically the final complete one),
or deduplicate deliberately by stable run IDs while respecting status/version history.

For full audit, download raw transcripts too and run `--verify-export` using the source
repository's exporter. Checksums detect accidental corruption, not an attacker who
rewrites both content and manifests. Raw JSONL includes enough request/state/source
records to audit and replay local protocol computation; fresh API generations are
stochastic and cannot be guaranteed to reproduce the same model outputs.

## 4. Prepare a dedicated GitHub results branch (only when authorized)

Choose your **team's repository**, not the starter's upstream remote by accident.
The current `collusion_hackathon` checkout originates from the starter project; no
push destination is inferred here. A separate ordinary checkout avoids moving your
working experiment onto a results branch. No Git worktree is required.

The following commands clone/read GitHub and make local branch/commit changes. Replace
`YOUR_TEAM_OWNER/YOUR_TEAM_REPOSITORY` and use an unused checkout directory. Run only
when authorized to prepare that repository; do not paste access tokens into commands.
Use existing platform/GitHub authentication.

```bash
TEAM_REPO=YOUR_TEAM_OWNER/YOUR_TEAM_REPOSITORY
TEAM_CHECKOUT=/workspace/team-peer-results
# EXPORT_DIR remains the validated immutable bundle from step 2.
.venv/bin/python experiments/export_peer_identity.py "$EXPORT_DIR" --verify-export

gh repo clone "$TEAM_REPO" "$TEAM_CHECKOUT"
BASE_BRANCH=$(gh repo view "$TEAM_REPO" --json defaultBranchRef --jq '.defaultBranchRef.name')
BATCH_ID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["batch"]["batch_id"])' "$EXPORT_DIR/metadata.json")
EXPORT_ID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["export_id"])' "$EXPORT_DIR/metadata.json")
RESULTS_BRANCH="results/experiment-3.3/$EXPORT_ID"
RESULTS_PATH="research-data/experiment-3.3/$BATCH_ID/$EXPORT_ID"

test -z "$(git -C "$TEAM_CHECKOUT" status --porcelain)" || exit 1
git -C "$TEAM_CHECKOUT" switch -c "$RESULTS_BRANCH" "$BASE_BRANCH"
mkdir -p "$TEAM_CHECKOUT/$(dirname "$RESULTS_PATH")"
mkdir "$TEAM_CHECKOUT/$RESULTS_PATH"  # fails rather than overwriting existing data
cp -R "$EXPORT_DIR/." "$TEAM_CHECKOUT/$RESULTS_PATH/"
.venv/bin/python experiments/export_peer_identity.py "$TEAM_CHECKOUT/$RESULTS_PATH" --verify-export
```

Review `validation.json`, metadata/mock status, all CSVs and compressed research
transcripts before committing. Only stage the selected bundle path; never `git add .`
or force-add the runtime `outputs/` tree. If the team repository ignores this path,
stop and review its policy instead of bypassing it.

## 5. Large raw transcripts: LFS or external storage

The exporter streams raw records rather than loading the whole study into RAM. If
`metadata.raw_storage.use_lfs_or_external_storage` is true (raw gzip >20 MiB), do not
commit the raw blob as normal Git content. Compact CSVs/metadata should stay in Git.
GitHub's hard normal-file limit is larger, but the 20 MiB threshold protects clone
size. Full-study transcripts can still be large despite compression.

**Optional Git LFS, only after explicit approval of availability/quotas:** install LFS
in the team checkout, track the raw file and commit its pointer with `.gitattributes`.
These are local commands; subsequent push uploads the LFS object and can consume quota.
No LFS installation or repository/server setting is changed automatically.

```bash
git -C "$TEAM_CHECKOUT" lfs install --local
git -C "$TEAM_CHECKOUT" lfs track "$RESULTS_PATH/raw.jsonl.gz"
git -C "$TEAM_CHECKOUT" add .gitattributes
```

Alternatively, propose an approved team bucket, private repository storage, OSF or
Zenodo destination for the immutable raw gzip. Upload requires separate authorization.
Keep compact CSVs, metadata and original checksums in Git; record the approved raw
object URL/version and SHA-256 in a sidecar README **outside** the sealed bundle.
If raw is omitted from Git, complete bundle verification requires retrieving it first;
compact-only `analyze.py` still works. Do not include signed URLs with credentials.
No external storage upload is implemented or performed automatically.

## 6. Commit, push and create the PR (publication requires explicit approval)

Before staging, ensure raw size is acceptable or LFS/external storage was approved.
For the ordinary small-bundle/LFS case:

```bash
git -C "$TEAM_CHECKOUT" add -- "$RESULTS_PATH"
git -C "$TEAM_CHECKOUT" diff --cached --stat
git -C "$TEAM_CHECKOUT" diff --cached --check
git -C "$TEAM_CHECKOUT" commit -m "Add Experiment 3.3 dataset $EXPORT_ID"
```

**STOP before the next commands unless push/PR publication is explicitly authorized.**
Do not change branch protections, remotes, GitHub visibility or server settings.

```bash
git -C "$TEAM_CHECKOUT" push -u origin "$RESULTS_BRANCH"
cat > /tmp/peer-results-pr-body.md <<'EOF'
Add a validated Experiment 3.3 sharing bundle with analysis-ready CSVs, execution
metadata, a data dictionary, checksums, and an offline analysis script. Raw transcripts
are included or linked under the separately reviewed storage policy. Review mock/real
status, incomplete-run counts, executed source hashes, and data-access policy before merge.
EOF
gh pr create --repo "$TEAM_REPO" --base "$BASE_BRANCH" --head "$RESULTS_BRANCH" \
  --title "Experiment 3.3 results: $EXPORT_ID" --body-file /tmp/peer-results-pr-body.md
```

This prepares a PR for review instead of committing directly to main/default. It does
not merge the PR. Publish mock validation only if deliberately labeled as mock; it is
not research evidence. Do not purchase API/OpenRouter credits as part of sharing.

## Format-2 teammate review package

New exports also include `run_metrics.csv` with all requested baseline/post/change
fields, `charts.py`, and `REVIEW_README.md`. The publication commands above copy these
alongside the CSVs and preserve the same checksum/secret-validation gates. Existing
format-1 bundles remain immutable and verifiable; create a new export to get format 2.

For mock examples, make the PR title explicitly say **synthetic mock example** and
state that charts are pipeline checks, not findings. The target team repository is
still an explicit user choice; do not push to the starter upstream by inference.

Precomputed charts can be committed as an adjacent review directory outside the
sealed bundle (so its validation file list is unchanged):

```bash
# Local preparation only; use the existing authorized team checkout and branch.
python3 "$EXPORT_DIR/charts.py" "$EXPORT_DIR" --output /tmp/peer-mock-review-figures
mkdir "$TEAM_CHECKOUT/$RESULTS_PATH-review"
for artifact in /tmp/peer-mock-review-figures/*.png /tmp/peer-mock-review-figures/*.svg /tmp/peer-mock-review-figures/*.csv /tmp/peer-mock-review-figures/summary.json /tmp/peer-mock-review-figures/README.md; do
  cp "$artifact" "$TEAM_CHECKOUT/$RESULTS_PATH-review/"
done
git -C "$TEAM_CHECKOUT" add -- "$RESULTS_PATH" "$RESULTS_PATH-review"
```

Skip `.matplotlib`/`.cache` plotting-cache directories when copying charts into Git;
copy only PNG/SVG figures, CSVs, summary JSON and review README. Do not run the push
or `gh pr create` commands until publication is authorized. Paid pilot approval and
GitHub publication approval are separate.
