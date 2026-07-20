# Shorelane Commerce

A synthetic B2B2C business built as an **evaluation fixture for analytics agents** —
a controlled environment for measuring **silent SQL** (confidently wrong answers
from AI-generated queries) and showing that human-confirmed context defuses it.

This repo ships one complete vertical slice: the **five revenues** trap, where a
plain "what was our revenue?" has five individually-defensible answers and a naive
agent picks one with false confidence. See `CLAUDE.md` for the full design contract.

## Quickstart

```bash
pip install -e .
make verify        # generates data + prints the five revenues for Q1 2024
```

Expected (dataset shorelane-v2, SEED=20190401):

| measure | Q1 2024 |
|---|---:|
| gmv | $1,359,503.83 |
| net_revenue | $1,330,251.05 |
| recognized_revenue | $1,428,393.18 ← canonical |
| billed_revenue | $1,334,267.84 |
| collected_cash | $1,164,885.32 |

If your numbers differ, the seed/economics changed — see "breaking changes" in
`CLAUDE.md`.

## What's here

- `generators/` — seeded, deterministic data generation
- `dbt/` — staging + `fct_revenue` mart (BigQuery primary)
- `context/` — the Nodal layer: metric defs, LookML, personas, derived ground truth
- `evals/` — questions + grading rubric for the revenue slice
- `loaders/` — BigQuery (primary) + Snowflake (marts mirror)
- `bi/` — Looker Studio (free, BQ-native) + Plotly (fully free)

## Why BigQuery + (optional) Snowflake, and why not Looker

BigQuery is primary (cheap on GCS credits). Snowflake mirrors only the marts for an
on-brand, cross-tool demo. **Looker (core)** is a $60k+/yr platform we don't run —
we author its LookML as a *context artifact* and render with free tools. Details in
`CLAUDE.md`.

## Extend it

The next pieces of planted data debt (identity fragmentation, an unmerged
acquisition, a channel rename, a subscription restructure, conflicting ad totals)
are specified in `CLAUDE.md`. Each is built as an eval triple: ground truth +
documented trap + resolving context artifact.
