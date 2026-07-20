"""
Order + revenue event generator.

Produces four RAW landing tables (Fivetran-shaped) whose interaction makes the
FIVE REVENUES genuinely diverge for any period:

  gmv               full ticket value, incl. full price of marketplace goods, gross of refunds
  net_revenue       what Shorelane earns (marketplace -> take only), net of refunds
  recognized_revenue subscriptions recognized ratably over the term
  billed_revenue    invoiced in period (net-30 billed at order date)
  collected_cash    cash actually received in period (net-30 timing + bad debt + refunds out)

Raw tables emitted:
  app_db__orders                one row per order (gross, take_rate, net)
  app_db__invoices              subscription net-30 billing + collection (bad debt = null collected)
  app_db__revenue_recognition   ratable schedule (subs) / immediate (d2c, marketplace)
  stripe__refunds               refunds, lagged after the order

Determinism: every draw uses a fixed RNG stream from config.SEED. Adding a new
generator must use a NEW stream int so existing output is untouched.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from generators.common import make_rng, random_dates, triangular


def _channels(rng: np.random.Generator, n: int) -> np.ndarray:
    labels = list(config.CHANNEL_MIX.keys())
    probs = np.array([config.CHANNEL_MIX[k] for k in labels])
    probs = probs / probs.sum()
    return rng.choice(labels, size=n, p=probs)


def generate() -> dict[str, pd.DataFrame]:
    rng = make_rng(stream=1)
    n = config.N_ORDERS

    channel = _channels(rng, n)
    order_date = random_dates(rng, config.START_DATE, config.END_DATE, n)

    # Gross (full ticket) amount per channel.
    gross = np.empty(n, dtype=float)
    for ch, (lo, mode, hi) in config.ORDER_VALUE_USD.items():
        mask = channel == ch
        gross[mask] = triangular(rng, lo, mode, hi, mask.sum())
    gross = np.round(gross, 2)

    # Take rate applies only to marketplace; net_amount is what Shorelane earns.
    take_rate = np.full(n, np.nan)
    mk = channel == "marketplace"
    take_rate[mk] = rng.uniform(*config.MARKETPLACE_TAKE_RATE_RANGE, size=mk.sum())

    net_amount = gross.copy()
    net_amount[mk] = np.round(gross[mk] * take_rate[mk], 2)  # marketplace: keep only the take

    orders = pd.DataFrame(
        {
            "order_id": [f"ord_{i:07d}" for i in range(n)],
            "customer_id": [f"cust_{j:06d}" for j in rng.integers(0, n // 3 + 1, size=n)],
            "channel": channel,
            "order_date": pd.to_datetime(order_date),
            "gross_amount": gross,
            "take_rate": np.round(take_rate, 4),
            "net_amount": net_amount,
        }
    )

    # ---- Invoices: business subscriptions are net-30, some never collected ----
    subs = orders[orders.channel == "business_subscription"].copy()
    rng_inv = make_rng(stream=2)
    collected_offset = np.full(len(subs), config.NET_TERMS_DAYS)
    # add a little collection jitter
    collected_offset = collected_offset + rng_inv.integers(-3, 12, size=len(subs))
    bad_debt = rng_inv.random(len(subs)) < config.BAD_DEBT_RATE
    billed_date = subs.order_date.values
    collected_date = billed_date + collected_offset.astype("timedelta64[D]")
    collected_date = np.where(bad_debt, np.datetime64("NaT"), collected_date)

    invoices = pd.DataFrame(
        {
            "invoice_id": [f"inv_{i:07d}" for i in range(len(subs))],
            "order_id": subs.order_id.values,
            "billed_date": pd.to_datetime(billed_date),
            "due_date": pd.to_datetime(billed_date + np.timedelta64(config.NET_TERMS_DAYS, "D")),
            "collected_date": pd.to_datetime(collected_date),
            "amount": subs.net_amount.values,
            "is_bad_debt": bad_debt,
        }
    )

    # ---- Revenue recognition schedule ----
    # Subscriptions recognized ratably over the term; everything else immediate.
    rec_rows = []
    for _, o in orders.iterrows():
        if o.channel == "business_subscription":
            monthly = round(o.net_amount / config.SUBSCRIPTION_TERM_MONTHS, 2)
            for m in range(config.SUBSCRIPTION_TERM_MONTHS):
                rec_rows.append(
                    (o.order_id, o.order_date + pd.DateOffset(months=m), monthly)
                )
        else:
            rec_rows.append((o.order_id, o.order_date, o.net_amount))
    recognition = pd.DataFrame(
        rec_rows, columns=["order_id", "recognition_date", "amount"]
    )
    recognition["recognition_date"] = pd.to_datetime(recognition["recognition_date"])

    # ---- Refunds: d2c + marketplace, lagged ----
    rng_ref = make_rng(stream=3)
    refundable = orders[orders.channel.isin(["d2c", "marketplace"])]
    refund_mask = rng_ref.random(len(refundable)) < config.REFUND_RATE
    refunded = refundable[refund_mask].copy()
    lag = rng_ref.integers(*config.REFUND_LAG_DAYS_RANGE, size=len(refunded))
    refunds = pd.DataFrame(
        {
            "refund_id": [f"ref_{i:07d}" for i in range(len(refunded))],
            "order_id": refunded.order_id.values,
            "refund_date": pd.to_datetime(refunded.order_date.values + lag.astype("timedelta64[D]")),
            "refund_amount": refunded.net_amount.values,
        }
    )

    return {
        "app_db__orders": orders,
        "app_db__invoices": invoices,
        "app_db__revenue_recognition": recognition,
        "stripe__refunds": refunds,
    }
