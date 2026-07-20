# CLAUDE.md — Shorelane Commerce

> Read this first. It is the design contract for this repo. Follow it when extending
> the project; the guardrails exist to keep the dataset trustworthy as an eval fixture.

## What this is

**Shorelane Commerce** is a synthetic B2B2C office-supplies business, built as an
**evaluation fixture for analytics agents**. It is not a fake-data toy. It is a
controlled environment for measuring **silent SQL** — confidently wrong,
plausible-looking answers from AI-generated queries.

Inspired by Hex's "Shorelane Commerce" eval lab, but built for a different purpose:
here the point is to demonstrate that **human-confirmed context defuses traps that
auto-generated context and raw model capability do not.** The data is a means; the
context layer and the eval traps are the product.

Profile: B2B2C office supplies, founded 2019, three revenue streams (direct-to-
consumer, net-30 business subscriptions, and a 15–25%-take marketplace), with six
years of accumulated data debt.

## The one idea that governs everything: the eval triple

Every piece of intentional mess in this repo ships as a **triple**. If you add mess
without all three legs, you are adding noise, not an eval. Do not do that.

1. **Ground truth** — the correct answer, *derived from the generated data* (never
   hand-waved), living in `context/ground_truth/`.
2. **The plausible-wrong path** — the specific silent-SQL failure the mess invites,
   documented in the eval's `trap:` field. There must be a believable wrong answer.
3. **The context artifact** — the human-confirmed metric def / semantic model /
   guide in `context/` that resolves the ambiguity. This is the Nodal surface.

The currently-built slice (the **five revenues**) is the worked example of the
triple. Copy its shape when you add the next piece of debt.

## Non-negotiable invariants

- **Determinism.** All randomness derives from `config.SEED` via
  `generators/common.make_rng(stream=N)`. **Every new generator must use a NEW
  `stream` int** so it cannot perturb existing output. If output for an existing
  table changes, you have silently invalidated ground truth.
- **Ground truth is derived, not authored.** Numbers in `context/ground_truth/`
  come from running the generators + `generators/measures.py`. Never type a figure
  by hand. Re-derive after any change and update the file in the same commit.
- **Breaking changes bump the version.** Changing `SEED`, any economic constant in
  `config.py`, or a measure definition changes the planted trap. Bump
  `DATASET_VERSION` and re-derive all ground truth.
- **dbt must match the reference.** `dbt/models/marts/fct_revenue.sql` must agree
  with `generators/measures.py` for any period. That parity is the contract between
  the warehouse and the eval. If you change one, change the other and confirm.
- **Generate once, load many.** Generators write Parquet to `data/raw` (and
  optionally GCS). Loaders read that Parquet. Never let a loader or warehouse
  become a second source of generation logic.

## Architecture / data flow

```
generators/ (seeded Python)
      │  emit Parquet
      ▼
  data/raw/*.parquet  ──(optional)──►  GCS  (canonical artifact store)
      │                                  │
      │ loaders/bigquery_load.py         │ loaders/snowflake_load.py (marts only)
      ▼                                  ▼
  BigQuery (PRIMARY)                 Snowflake (on-brand + cross-tool demo)
      │
      │ dbt: staging → marts
      ▼
  fct_revenue  ◄── must match generators/measures.py
      │
      ├── context/  (metrics, LookML, guides, ground_truth)  ← the Nodal layer
      ├── evals/    (questions + rubrics)
      └── bi/       (Looker Studio = free/BQ-native; Plotly = fully free)
```

### Warehouse policy
- **BigQuery is primary** (cheap on GCS credits; free tier covers this scale).
- **Snowflake mirrors marts only** — it's the on-brand demo surface and proves
  Nodal's cross-tool, format-agnostic claim. Do not dual-maintain the full stack.
- Keep generation warehouse-neutral (Parquet). If you make dbt dual-warehouse, use
  `dbt_utils` cross-db macros; otherwise keep dbt BigQuery-only for now.

### BI policy — read this to avoid a $60k mistake
- **Looker (core)** is a $60k+/yr enterprise platform. We do **not** run an instance.
- We author **LookML as a context artifact** (`context/semantic/*.lkml`) — it's a
  semantic layer, exactly what Nodal reads/evaluates — without paying for Looker.
- Render dashboards with **Looker Studio** (free, BigQuery-native) or **Plotly**
  (fully free). Never assume GCP credits make Looker-core free; they don't.

## Current state (built)

The **five-revenues** vertical slice is complete and runnable:
- generators for orders/invoices/recognition/refunds with the planted divergence
- `generators/measures.py` reference implementation of all five measures
- `fct_revenue` dbt mart (tidy long table) mirroring the reference
- context: metric defs, personas, LookML, derived ground truth for Q1 2024
- evals: three questions (unqualified, marketing-persona, cash) + rubric
- loaders (BQ working, Snowflake stub), Plotly dashboard, Looker Studio guide

Verify it: `make verify` prints the five revenues for Q1 2024. They diverge, and
notably `recognized_revenue` > `gmv` (ratable recognition from prior-period subs)
— the signature trap.

## How to extend — the debt catalog roadmap

Add these next, each as a full eval triple, smallest-blast-radius first. For each:
generate the mess (new RNG stream) → document raw schema → build staging/mart →
author the resolving context artifact → derive ground truth → write eval + rubric.

1. **Identity fragmentation** — 2–4 IDs per customer across stripe / salesforce /
   shopify / app_db; a 2021 migration drops a fraction of the crosswalk. Trap:
   joins silently drop or double-count. Context: identity-resolution model + null-rate.
2. **OfficeMax acquisition** — an unmerged cohort with cents-vs-dollars and
   different status enums. Trap: unit/enum mismatch in sums and filters.
3. **Channel rename 2022** — "direct" → "d2c" without backfill. Trap: one channel
   splits in two. Context: coalescing rule.
4. **Subscription restructure 2023** — three plan generations grandfathered. Trap:
   "active subscribers" miscounts. Context: plan-generation mapping.
5. **Three ad conversion totals** — google/meta/tiktok self-reported vs warehouse-
   attributed. Trap: CAC uses the wrong source. Context: source-of-truth guide.
6. **Soft deletes / test accounts / internal orders** unfiltered everywhere. Trap:
   inflated counts. Context: documented exclusion predicates.

Also add the missing source systems as you go (Salesforce, Shopify-legacy red
herring, ad platforms, Zendesk) so prompts can read like real Slack messages.

## Live infrastructure (v2)

The v2 timeline runs past "today" (`END_DATE = 2027-12-31`) so a live pipeline
can drip-feed the warehouse daily while the Parquet stays canonical:

- **Arrival rule** lives in `loaders/visibility.py` (`visible_tables`): a row is
  visible when its own event date ≤ as-of (`order_date`, `billed_date`,
  `recognition_date`, `refund_date`). Exception: an invoice collected in the
  future is visible but its `collected_date` is masked to NULL (Fivetran-style
  late update; NULL + `is_bad_debt=false` = "pending").
- **Parity property**: for any period fully ≤ as-of, the filtered tables produce
  the same five revenues as `generators/measures.py` on the full Parquet. Never
  validate ground truth against a window that straddles the as-of date.
- `loaders/bigquery_load.py --as-of YYYY-MM-DD|today` loads only visible rows
  (WRITE_TRUNCATE — idempotent; backfill is just a normal run). Omit `--as-of`
  for the full-fixture load.
- Companion repos: **shorelane-dbt** (the dbt project, daily GitHub Actions run
  as `sa-dbt-runner`; it is the canonical home of `fct_revenue` and the parity
  counterpart of `measures.py`) and **shorelane-pipeline** (fake-Fivetran daily
  loader as `sa-fivetran`, scheduled BigQuery Plotly dashboards as
  `sa-bi-dashboards`, GCP bootstrap runbook). Both pin this repo's git tag —
  retag whenever generators/config change.
- The local `bi/` dashboards remain the offline fixture (they read local
  Parquet); the scheduled warehouse-querying dashboards live in
  shorelane-pipeline.
- Ground-truth windows must be **fully elapsed calendar windows** (see
  `--anchor` in `bi/dashboard_data.py`) so they stay valid on the live
  warehouse.

## Nodal integration (the payoff)

Run the `nodal-context` interview against this warehouse; its ACF output for each
concept should reduce to the artifacts in `context/`. The publishable demo is:
agent gets a deceptively-easy question → produces a confident wrong number →
Nodal plan-review / context surfaces the disambiguation → correct answer. All on a
business we fabricated, so nothing is under NDA and everything can be published.

## Commands

```
make verify      # generate + print the five revenues (sanity check)
make generate    # write data/raw/*.parquet
make load-bq PROJECT=your-gcp-project
make dbt         # staging + marts (needs ~/.dbt/profiles.yml)
make dashboard   # free Plotly HTML
```

## Repo map

```
config.py                 seed, timeline, economics (the trap constants)
generators/               seeded data generation
  common.py               make_rng(stream) — the determinism boundary
  orders.py               the five-revenues raw tables
  measures.py             reference impl of the five measures (CANONICAL)
  emit.py                 → Parquet (+ optional GCS), derive ground truth
raw_schema/               documented landing schemas
dbt/                      staging → marts; fct_revenue mirrors measures.py
context/                  THE NODAL LAYER
  metrics/                disambiguated metric defs
  semantic/               LookML as context artifact (authored, not rendered)
  guides/                 personas + source-of-truth rules
  ground_truth/           derived answers, keyed to evals
evals/                    questions.yaml + rubrics/
loaders/                  bigquery_load.py (primary), snowflake_load.py (marts)
bi/                       looker_studio/ (free) + plotly/ (free)
```
