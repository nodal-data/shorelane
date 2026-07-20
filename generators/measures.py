"""
Reference implementation of the FIVE REVENUES, in pandas.

This is the canonical definition. The dbt mart (dbt/models/marts/fct_revenue.sql)
must agree with this for any period; the eval harness derives ground truth from it.
If you change a definition here, you change the planted trap — bump DATASET_VERSION
and re-derive ground truth.
"""
from __future__ import annotations

import pandas as pd


def _in_period(s: pd.Series, start: str, end: str) -> pd.Series:
    return (s >= pd.Timestamp(start)) & (s <= pd.Timestamp(end))


def five_revenues(tables: dict[str, pd.DataFrame], start: str, end: str) -> dict[str, float]:
    orders = tables["app_db__orders"]
    invoices = tables["app_db__invoices"]
    recognition = tables["app_db__revenue_recognition"]
    refunds = tables["stripe__refunds"]

    in_orders = orders[_in_period(orders.order_date, start, end)]
    refunds_in = refunds[_in_period(refunds.refund_date, start, end)]

    # 1. GMV — full ticket, incl. full marketplace price, GROSS of refunds.
    gmv = float(in_orders.gross_amount.sum())

    # 2. Net revenue — what we earn (marketplace -> take only), NET of refunds.
    net_revenue = float(in_orders.net_amount.sum() - refunds_in.refund_amount.sum())

    # 3. Recognized revenue — ratable schedule landing in the period.
    rec_in = recognition[_in_period(recognition.recognition_date, start, end)]
    recognized_revenue = float(rec_in.amount.sum())

    # 4. Billed revenue — invoiced in period. d2c/marketplace billed at order date;
    #    subscriptions billed at invoice billed_date (== order date). Gross of refunds.
    non_sub = in_orders[in_orders.channel != "business_subscription"]
    billed_subs = invoices[_in_period(invoices.billed_date, start, end)]
    billed_revenue = float(non_sub.net_amount.sum() + billed_subs.amount.sum())

    # 5. Collected cash — cash actually received in period, minus refunds out.
    collected_non_sub = non_sub.net_amount.sum()  # paid immediately
    collected_subs = invoices[_in_period(invoices.collected_date, start, end)].amount.sum()
    collected_cash = float(collected_non_sub + collected_subs - refunds_in.refund_amount.sum())

    return {
        "gmv": round(gmv, 2),
        "net_revenue": round(net_revenue, 2),
        "recognized_revenue": round(recognized_revenue, 2),
        "billed_revenue": round(billed_revenue, 2),
        "collected_cash": round(collected_cash, 2),
    }
