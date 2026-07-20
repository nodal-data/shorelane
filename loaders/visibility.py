"""
As-of visibility filter for the drip-feed pipeline.

The Parquet in data/raw is canonical and spans the full timeline (START_DATE..
END_DATE, which extends past "today"). A live warehouse must only see rows that
have "arrived" by a given as-of date. This module is the single definition of
that arrival rule, shared by every warehouse loader (BigQuery today, Redshift
later) so the drip stays warehouse-neutral.

Arrival rule: a row is visible when its own event date <= as_of. One exception:
an invoice whose collected_date is still in the future is visible (it was
billed) but its collected_date is masked to NULL — the Fivetran-style late
update. A NULL collected_date with is_bad_debt=False therefore reads as
"pending collection", which is the correct live semantics.

Parity property: for any period that lies fully <= as_of, the filtered tables
produce the same five revenues as generators/measures.py on the full Parquet.
"""
from __future__ import annotations

import pandas as pd

# Which column governs arrival for each raw table.
ARRIVAL_COLUMNS = {
    "app_db__orders": "order_date",
    "app_db__invoices": "billed_date",
    "app_db__revenue_recognition": "recognition_date",
    "stripe__refunds": "refund_date",
}


def visible_tables(tables: dict[str, pd.DataFrame], as_of) -> dict[str, pd.DataFrame]:
    """Return copies of the raw tables containing only rows visible at as_of."""
    cutoff = pd.Timestamp(as_of)
    out: dict[str, pd.DataFrame] = {}
    for name, df in tables.items():
        col = ARRIVAL_COLUMNS[name]
        vis = df[df[col] <= cutoff].copy()
        if name == "app_db__invoices":
            vis.loc[vis["collected_date"] > cutoff, "collected_date"] = pd.NaT
        out[name] = vis.reset_index(drop=True)
    return out
