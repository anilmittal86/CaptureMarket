"""Macro Analysis: market-wide KPIs, distributions, top/bottom performers."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import macro_summary
from src.data_loader import get_data
from src.ui import inject_css, kpi_card, sign_class

st.set_page_config(page_title="Macro | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Macro Analysis")
st.caption("Universe-wide statistics for the Nifty Smallcap 250.")

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

s = macro_summary(df)


def cr_fmt(v: float) -> str:
    lakh_cr = v / 1e5
    return f"{lakh_cr:,.1f} L Cr" if lakh_cr >= 1 else f"{v:,.0f} Cr"


# --- KPI cards -----------------------------------------------------------
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
with r1c1:
    kpi_card("Universe Size", f"{s['universe_size']}", f"{s['plotted_pe']} with valid P/E")
with r1c2:
    kpi_card("Total Market Cap", cr_fmt(s["total_mktcap_cr"]))
with r1c3:
    kpi_card("Median P/E", f"{s['median_pe']:.1f}x" if not np.isnan(s["median_pe"]) else "N/A")
with r1c4:
    kpi_card(
        "Median EPS Growth 3Y",
        f"{s['median_eps_g3']:.1f}%" if not np.isnan(s["median_eps_g3"]) else "N/A",
    )

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    kpi_card(
        "Average 1Y Return",
        f"{s['avg_ret_1y']:+.1f}%",
        f"Median {s['median_ret_1y']:+.1f}%",
        sign_class(s["avg_ret_1y"]),
    )
with r2c2:
    kpi_card("% Stocks Positive (1Y)", f"{s['pct_positive_1y']:.0f}%", "of universe")
with r2c3:
    kpi_card("% Stocks Negative (1Y)", f"{s['pct_negative_1y']:.0f}%", "of universe", "neg" if s["pct_negative_1y"] > s["pct_positive_1y"] else "")
with r2c4:
    kpi_card(
        "Avg CAGR 3Y / 5Y",
        f"{s['avg_ret_3y']:+.1f}% / {s['avg_ret_5y']:+.1f}%",
        sign_class(s["avg_ret_3y"]),
    )

st.divider()

# --- distributions -------------------------------------------------------
left, mid, right = st.columns(3)

with left:
    st.markdown('<div class="section-title">P/E Distribution</div>', unsafe_allow_html=True)
    pe = df["P/E"].dropna()
    pe = pe[pe > 0]
    fig = go.Figure(go.Histogram(x=np.log10(pe), nbinsx=36, marker_color="#2563EB"))
    ticks = [5, 10, 25, 50, 100, 250, 500, 1000]
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            title="P/E (log scale)",
            tickvals=[np.log10(t) for t in ticks],
            ticktext=[str(t) for t in ticks],
        ),
        yaxis_title="Companies",
    )
    st.plotly_chart(fig, width="stretch")

with mid:
    st.markdown('<div class="section-title">EPS Growth 3Y Distribution</div>', unsafe_allow_html=True)
    eps = df["EPS Growth 3Y (%)"].dropna()
    fig = go.Figure(go.Histogram(x=eps, nbinsx=36, marker_color="#7C3AED"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="EPS Growth 3Y (%)", yaxis_title="Companies")
    st.plotly_chart(fig, width="stretch")

with right:
    st.markdown('<div class="section-title">1Y Return Distribution</div>', unsafe_allow_html=True)
    ret = df["1Y Return (%)"].dropna()
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=ret[ret >= 0], nbinsx=30, marker_color="#16A34A", name="Positive", opacity=0.75))
    fig.add_trace(go.Histogram(x=ret[ret < 0], nbinsx=30, marker_color="#DC2626", name="Negative", opacity=0.75))
    fig.update_layout(
        barmode="overlay", height=300, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="1Y Return (%)", yaxis_title="Companies",
    )
    st.plotly_chart(fig, width="stretch")

st.divider()

# --- top / bottom performers ---------------------------------------------
table_cols = ["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "EPS Growth 3Y (%)", "1Y Return (%)"]
num_fmt = {
    "Market Cap (Cr)": st.column_config.NumberColumn(format="comma"),
    "P/E": st.column_config.NumberColumn(format="%.1fx"),
    "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
}

t1, t2 = st.columns(2)
with t1:
    st.markdown('<div class="section-title">Top 10 Performers (1Y)</div>', unsafe_allow_html=True)
    top = df.nlargest(10, "1Y Return (%)")[table_cols]
    st.dataframe(top, hide_index=True, width="stretch", column_config=num_fmt)
with t2:
    st.markdown('<div class="section-title">Bottom 10 Performers (1Y)</div>', unsafe_allow_html=True)
    bottom = df.nsmallest(10, "1Y Return (%)")[table_cols]
    st.dataframe(bottom, hide_index=True, width="stretch", column_config=num_fmt)
