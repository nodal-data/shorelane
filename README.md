# Shorelane Commerce

A synthetic B2B2C business built as an **evaluation fixture for analytics agents** —
a controlled environment for measuring **silent SQL** (confidently wrong answers
from AI-generated queries) and showing that human-confirmed context defuses it.

Built and maintained by **[Nodal](https://nodaldata.io)** as the public companion
fixture to **[nodal-context](https://github.com/nodal-data/nodal-context)**, the
open-source interview-built context layer for analytics agents.

Shorelane is based on **Shorelane Commerce**, the synthetic company Hex built to
evaluate its data agents — a fake B2B2C office-supplies business whose warehouse
deliberately plants realistic data debt (migration-era ID loss, an unmerged
acquisition, renamed channels, and "five columns that could plausibly be called
revenue"). See Hex's write-up:
[How we evaluate data agents](https://hex.tech/blog/evaluate-data-agents/). This
repo is an independent, open reimplementation of that idea as a public fixture.

This repo ships one complete vertical slice: the **five revenues** trap, where a
plain "what was our revenue?" has five individually-defensible answers and a naive
agent picks one with false confidence. See `CLAUDE.md` for the full design contract.

## Public demo

- **Fictional company site + live dashboard** — published via GitHub Pages
  (`.github/workflows/pages.yml`):
  [the marketing homepage](https://nodal-data.github.io/shorelane/),
  [an explore-the-data page](https://nodal-data.github.io/shorelane/explore.html),
  the [five-revenues dashboard](https://nodal-data.github.io/shorelane/dashboard/),
  and the [executive dashboard](https://nodal-data.github.io/shorelane/business/)
  (KPIs + five charts across four period views), all re-rendered daily
  `--as-of today` so they match the live warehouse without any credentials in CI.
- **Public BigQuery datasets** — `nodal-shorelane.shorelane_raw` (landing tables)
  and `nodal-shorelane.shorelane` (dbt marts incl. `fct_revenue`) are readable by
  **any Google account, including a personal Gmail** — no invite, no paid plan.
  You just log in and query from your own (free) GCP project; BigQuery's free
  tier covers this dataset thousands of times over.

## Try it yourself (the silent-SQL demo)

1. **Connect an agent to the warehouse** — see
   [Connect an agent over MCP](#connect-an-agent-over-mcp) below. Any Google
   account (a personal Gmail works) can read the public `nodal-shorelane`
   datasets; queries run in your own GCP project, and the free tier is plenty.
2. **Ask the deceptively easy question.** *"What was revenue in Q1 2024?"* —
   note the confident answer and which of the five measures it silently picked.
   The seductive wrong answers are documented per-question in `evals/questions.yaml`.
3. **Build the context.** Run the
   [nodal-context](https://github.com/nodal-data/nodal-context) ~30-minute
   test-drive interview against the same warehouse. This repo's `dbt/` folder is
   a ready-made dbt extraction input: fetch the pre-parsed
   [manifest.json](https://nodal-data.github.io/shorelane/dbt/manifest.json)
   from the demo site, or build it yourself with `make manifest` — `dbt parse`
   needs no warehouse credentials. (Query-history mining needs project-level
   permissions, so that input isn't available on the public dataset — expected.)
4. **Ask again with context loaded** and check the answer against
   `context/ground_truth/`. The correct Q1 2024 canonical answer is below.

## Connect an agent over MCP

The warehouse connection runs through Google's
[MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox)
(`toolbox`) and its pre-built BigQuery tool set. This repo ships a
project-scoped `.mcp.json`, so in Claude Code the connection works as soon as
the binary and credentials are in place.

1. **Install the `toolbox` binary.**

   ```bash
   brew install mcp-toolbox
   ```

   Or grab a release binary from the
   [releases page](https://github.com/googleapis/mcp-toolbox/releases),
   `chmod +x` it, and put it on your `PATH` as `toolbox`.

2. **Authenticate to Google Cloud.** Any Google account works — a personal
   Gmail is fine; you don't need a work account or an invite from us. The
   toolbox uses Application Default Credentials, so log in with:

   ```bash
   gcloud auth application-default login
   ```

3. **Point it at your own GCP project.** Query jobs run in the project named by
   `BIGQUERY_PROJECT`, and querying is effectively **free**: BigQuery's free
   tier includes 1 TB of query processing per month — no credit card required —
   and this dataset is small enough that you'd need thousands of runs to dent
   it. If you've never used GCP, create a free project at
   [console.cloud.google.com](https://console.cloud.google.com) (a minute of
   clicking), then set it in the shell you launch your agent from:

   ```bash
   export BIGQUERY_PROJECT=your-gcp-project-id
   ```

   (Nodal team members with `nodal-shorelane` access can skip this — it's the
   default in `.mcp.json`.)

4. **Start your agent in this repo.** Claude Code picks up `.mcp.json`
   automatically and asks you to approve the `bigquery` server on first run.
   For any other MCP client, configure a stdio server with command
   `toolbox --prebuilt bigquery --stdio` and the `BIGQUERY_PROJECT` env var.

5. **Verify.** `claude mcp list` should show `bigquery: ✔ Connected`; then ask
   the agent to list the tables in `nodal-shorelane.shorelane` — you should see
   `fct_revenue` and the four staging views.

If auth later starts failing with `invalid_rapt` / `invalid_grant`, your Google
session expired — rerun `gcloud auth application-default login` and restart the
MCP server (`/mcp` → reconnect in Claude Code).

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
- `dbt/` — staging + `fct_revenue` mart, one model set for both warehouses
- `context/` — the Nodal layer: metric defs, LookML, personas, derived ground truth
- `evals/` — questions + grading rubric for the revenue slice
- `loaders/` — BigQuery (primary, public), Redshift (private second warehouse),
  Snowflake (stub); `visibility.py` holds the warehouse-neutral arrival rule
- `bi/` — Looker Studio (free, BQ-native) + Plotly (fully free)
- `site/` — the explore page for the public GitHub Pages site

## Two warehouses, and why not Looker

BigQuery is primary and public. Redshift Serverless runs the same generators, dbt
models and parity contract as a full private second warehouse, proving the fixture
isn't BigQuery-shaped. **Looker (core)** is a $60k+/yr platform we don't run —
we author its LookML as a *context artifact* and render with free tools. Details in
`CLAUDE.md`.

## Extend it

The next pieces of planted data debt (identity fragmentation, an unmerged
acquisition, a channel rename, a subscription restructure, conflicting ad totals)
are specified in `CLAUDE.md`. Each is built as an eval triple: ground truth +
documented trap + resolving context artifact. 
