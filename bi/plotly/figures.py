"""
Shared Plotly figure builders for the executive dashboard.

Pure plotly — no Dash import — so the same five charts serve both surfaces:
the interactive Dash app (bi/plotly/business_dashboard.py) and the static
export published on the Pages site (bi/plotly/business_dashboard_static.py).
All figures are derived from bi/dashboard_data.py frames.
"""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from bi import dashboard_data as dd

# ---- palette -------------------------------------------------------------
PRIMARY = "#2563eb"   # blue   — revenue
TEAL = "#0d9488"      # teal   — customers / cash
AMBER = "#f59e0b"     # amber  — orders / marketplace
SLATE = "#64748b"
GREEN = "#059669"
RED = "#dc2626"
CHANNEL_COLORS = {
    "Business Subscriptions": PRIMARY,
    "Direct-to-Consumer": TEAL,
    "Marketplace": AMBER,
}


# ---- formatting ----------------------------------------------------------
def fmt_money(v: float) -> str:
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:,.0f}"


def fmt_int(v: float) -> str:
    return f"{int(round(v)):,}"


def fmt_pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def style_fig(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=12, r=12, t=12, b=12),
        font=dict(family="Inter, -apple-system, sans-serif", size=12, color="#334155"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hoverlabel=dict(font_size=12, font_family="Inter, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="#e2e8f0")
    fig.update_yaxes(showgrid=True, gridcolor="#eef2f7", zeroline=False)
    return fig


# ---- figure builders -----------------------------------------------------
def fig_revenue(df) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=df.month, y=df.recognized_revenue, marker_color=PRIMARY,
            hovertemplate="%{x|%b %Y}<br>Revenue: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_yaxes(tickprefix="$", tickformat="~s")
    return style_fig(fig, 320)


def fig_channel(tables, start, end) -> go.Figure:
    ch = dd.revenue_by_channel(tables, start, end)
    fig = go.Figure(
        go.Pie(
            labels=ch.channel_label, values=ch.amount, hole=0.58,
            marker_colors=[CHANNEL_COLORS.get(c, SLATE) for c in ch.channel_label],
            sort=False, textinfo="percent", textfont_size=12,
            hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        annotations=[dict(text="Recognized<br>revenue", x=0.5, y=0.5, font_size=12, showarrow=False, font_color=SLATE)]
    )
    return style_fig(fig, 300)


def fig_customers(df) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df.month, y=df.new_customers, name="New customers", marker_color=TEAL,
               hovertemplate="%{x|%b %Y}<br>New: %{y}<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df.month, y=df.cumulative_customers, name="Total customers", mode="lines",
                   line=dict(color=SLATE, width=2.5),
                   hovertemplate="%{x|%b %Y}<br>Total: %{y:,}<extra></extra>"),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="", secondary_y=False)
    fig.update_yaxes(showgrid=False, secondary_y=True)
    return style_fig(fig, 300)


def fig_orders_aov(df) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df.month, y=df.orders, name="Orders", marker_color=AMBER, opacity=0.85,
               hovertemplate="%{x|%b %Y}<br>Orders: %{y}<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df.month, y=df.aov, name="Avg order value", mode="lines",
                   line=dict(color=PRIMARY, width=2.5),
                   hovertemplate="%{x|%b %Y}<br>AOV: $%{y:,.0f}<extra></extra>"),
        secondary_y=True,
    )
    fig.update_yaxes(tickprefix="$", tickformat="~s", showgrid=False, secondary_y=True)
    return style_fig(fig, 300)


def fig_cash_health(df) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.month, y=df.recognized_revenue, name="Recognized revenue", mode="lines",
        line=dict(color=PRIMARY, width=2.5),
        hovertemplate="%{x|%b %Y}<br>Recognized: $%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=df.month, y=df.collected_cash, name="Collected cash", mode="lines",
        line=dict(color=TEAL, width=2.5), fill="tonexty", fillcolor="rgba(13,148,136,0.08)",
        hovertemplate="%{x|%b %Y}<br>Collected: $%{y:,.0f}<extra></extra>"))
    fig.update_yaxes(tickprefix="$", tickformat="~s")
    return style_fig(fig, 300)
