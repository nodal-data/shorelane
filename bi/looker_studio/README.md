# Looker Studio dashboards (free, BigQuery-native)

**Looker Studio**, not **Looker**. The former is free and connects natively to
BigQuery; the latter is a $60k+/yr enterprise platform we are deliberately not
running (we author its LookML as a *context artifact* instead — see
`context/semantic/shorelane.view.lkml`).

## Setup

1. Build the warehouse: load raw to BigQuery (`loaders/bigquery_load.py`) and run
   dbt so `shorelane.fct_revenue` exists.
2. In Looker Studio: **Create → Data source → BigQuery →** your project →
   `shorelane.fct_revenue`.
3. Because `fct_revenue` is tidy (one row per measure_name), add a control on
   `measure_name` and a single time-series on `SUM(amount)` by `activity_date`.
   Flipping the control shows each revenue — making the five-way ambiguity the
   visual point of the dashboard.

## Suggested charts

- Time series: `SUM(amount)` by `activity_date`, broken out by `measure_name`.
- Scorecard row: one card per measure for the selected period (shows the spread).
- A "which revenue?" annotation linking back to `context/metrics/revenue.yml`.

Keep raw scans down: Looker Studio re-queries BigQuery per chart load, and BQ
bills per TiB scanned (first 1 TiB/month free). `fct_revenue` is tiny, so this is
free in practice — but partition by `activity_date` before scaling up the data.
