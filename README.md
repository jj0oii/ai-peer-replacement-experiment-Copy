# Experiment 3.3: Can agents identify their peers?

Version 2 implementation and offline validation for the two-agent Public Goods study.
The planned study is 25 independent checkpoints × four replacement conditions ×
two behavior settings = 200 continuation trials. No paid run starts automatically.

- [Version 2 methodology](llm-trust-breaking/peer_identity/VERSION_2_METHODOLOGY.md)
- [Pilot proposal, costs and execution command](llm-trust-breaking/peer_identity/VERSION_2_PILOT.md)
- [Data dictionary](llm-trust-breaking/peer_identity/DATA_DICTIONARY.md)
- [GitHub sharing instructions](llm-trust-breaking/peer_identity/SHARING.md)
- [Validated synthetic example CSVs and transcripts](examples/version-2-mock)

The example data are **synthetic mock responses, not research findings**. Original
paid Version 1 results remain preserved in the research workspace; credentials,
local environments and unreviewed runtime outputs are not included here.

## Offline setup and tests

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
cd llm-trust-breaking
uv sync
uv run python -m unittest discover -s tests
```

From the repository root, reproduce the example analysis and charts:

```bash
uv run --project llm-trust-breaking python examples/version-2-mock/analyze.py --output local-analysis
uv run --project llm-trust-breaking python examples/version-2-mock/charts.py --output local-charts
```

Use new output directories for each analysis. API credentials are unnecessary for
these commands. Do not put keys in Git; use an ignored local `compute.env` only
when a paid run has been separately approved.

The included starter modules and `util` dependency originate from
[poseidon-research/collusion_hackathon](https://github.com/poseidon-research/collusion_hackathon),
commit `d585a7b3be50366cc2bdf5789bf8add5890b2abd`. The existing starter README is
retained inside `llm-trust-breaking`; Version 2 instructions take precedence for this study.

## Current code and real research data

The `experiment-3-3-v2-review` branch contains the latest local implementation,
validator repair, checkpoint-level statistics, and isolated C4 routing/recovery tools.
See [shared datasets and analysis instructions](research-data/README.md).

The original Version 2 snapshot has **96 completed trials across 12 checkpoints**.
The separate Gemini C4 smoke trial is **incomplete**, stopped on HTTP 429 during
round-6 reflection; it has no final recognition outcome. No additional paid
execution starts automatically. Publishing these files does not authorize retries.

For C4 audit and execution gates, read
[C4 recovery documentation](llm-trust-breaking/peer_identity/C4_EXPLICIT_RECOVERY.md).

- [Prompts used in Version 2: readable guide and exact recorded examples](llm-trust-breaking/peer_identity/PROMPTS_USED_V2.md).
