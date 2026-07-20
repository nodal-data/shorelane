"""
Free BI path: render the five revenues as an interactive Plotly HTML, straight
from the local Parquet. No warehouse, no BI license required — good enough to
publish alongside a blog post or demo.

    pip install plotly pandas pyarrow
    python -m bi.plotly.revenue_dashboard
    open bi/plotly/revenue_dashboard.html

For the Looker Studio path (also free, BigQuery-native) see bi/looker_studio/.
"""
from __future__ import annotations

import os

import pandas as pd

import config
from generators import orders
from generators.measures import five_revenues

MEASURES = ["gmv", "net_revenue", "recognized_revenue", "billed_revenue", "collected_cash"]


def monthly_series(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    months = pd.date_range(config.START_DATE, config.END_DATE, freq="MS")
    rows = []
    for m in months:
        end = (m + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        rev = five_revenues(tables, m.strftime("%Y-%m-%d"), end)
        rev["month"] = m
        rows.append(rev)
    return pd.DataFrame(rows)


def main() -> None:
    import plotly.graph_objects as go

    tables = orders.generate()
    df = monthly_series(tables)

    fig = go.Figure()
    for measure in MEASURES:
        fig.add_trace(go.Scatter(x=df.month, y=df[measure], mode="lines", name=measure))
    fig.update_layout(
        title="Shorelane Commerce — five revenues, monthly (they never agree)",
        xaxis_title="Month",
        yaxis_title="USD",
        hovermode="x unified",
    )
    out = os.path.join("bi", "plotly", "revenue_dashboard.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.write_html(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
