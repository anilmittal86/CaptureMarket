"""Macro Analysis: universe-wide stats organized into five lenses -
Companies & Cap, Valuations, Growth, Liquidity, Returns."""
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
from src.ui import cr_fmt, inject_css, kpi_card, sign_class

st.set_page_config(page_title="Macro | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Macro Analysis")
st.caption("Universe-wide statistics for the Nifty Smallcap 250, organized by lens.")

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

s = macro_summary(df)
TURN_COL = "Avg Daily Turnover (Cr)"
has_turnover = TURN_COL in df.columns and df[TURN_COL].notna().any()

# --- overview strip -------------------------------------------------------
o1, o2, o3, o4, o5 = st.columns(5)
with o1:
    kpi_card("Companies", f"{s['universe_size']}", f"{df['Sector'].nunique()} sectors")
with o2:
    kpi_card("Total Market Cap", cr_fmt(s["total_mktcap_cr"]))
with o3:
    kpi_card("Median P/E", f"{s['median_pe']:.1f}x" if not np.isnan(s["median_pe"]) else "N/A")
with o4:
    kpi_card("Median EPS Growth 3Y", f"{s['median_eps_g3']:.1f}%" if not np.isnan(s["median_eps_g3"]) else "N/A")
with o5:
    kpi_card("Avg 1Y Return", f"{s['avg_ret_1y']:+.1f}%", "", sign_class(s["avg_ret_1y"]))

tab_cap, tab_val, tab_gro, tab_liq, tab_ret = st.tabs(
    ["Companies & Cap", "Valuations", "Growth", "Liquidity", "Returns"]
)

# ===========================================================================
# Tab 1: Companies & Cap
# ===========================================================================
with tab_cap:
    total_cap = float(df["Market Cap (Cr)"].sum())
    top10_share = float(df.nlargest(10, "Market Cap (Cr)")["Market Cap (Cr)"].sum() / total_cap * 100)
    top25_share = float(df.nlargest(25, "Market Cap (Cr)")["Market Cap (Cr)"].sum() / total_cap * 100)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Companies", f"{len(df)}")
    with c2:
        kpi_card("Sectors", f"{df['Sector'].nunique()}")
    with c3:
        kpi_card("Top-10 Weight", f"{top10_share:.0f}%", "of universe cap")
    with c4:
        kpi_card("Top-25 Weight", f"{top25_share:.0f}%", "of universe cap")

    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="section-title">Largest Companies</div>', unsafe_allow_html=True)
        top15 = df.nlargest(15, "Market Cap (Cr)")
        fig = go.Figure(go.Bar(
            x=top15["Market Cap (Cr)"][::-1],
            y=top15["NSE Symbol"][::-1],
            orientation="h",
            marker_color="#2563EB",
        ))
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="Market Cap (Cr)", yaxis=dict(automargin=True))
        st.plotly_chart(fig, width="stretch")
    with right:
        st.markdown('<div class="section-title">Top 15 by Market Cap</div>', unsafe_allow_html=True)
        st.dataframe(
            top15[["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "1Y Return (%)"]],
            hide_index=True,
            width="stretch",
            column_config={
                "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
                "P/E": st.column_config.NumberColumn(format="%.1fx"),
                "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            },
        )

# ===========================================================================
# Tab 2: Valuations
# ===========================================================================
with tab_val:
    pe = df["P/E"].dropna()
    pe_pos = pe[pe > 0]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Median P/E", f"{pe.median():.1f}x" if len(pe) else "N/A")
    with c2:
        kpi_card("25th Percentile", f"{pe_pos.quantile(0.25):.1f}x" if len(pe_pos) else "N/A", "cheap end")
    with c3:
        kpi_card("75th Percentile", f"{pe_pos.quantile(0.75):.1f}x" if len(pe_pos) else "N/A", "expensive end")
    with c4:
        kpi_card("With Valid P/E", f"{len(pe)} / {len(df)}", "rest are loss-making / N.A.")

    ticks = [5, 10, 25, 50, 100, 250, 500, 1000]
    fig = go.Figure(go.Histogram(x=np.log10(pe_pos), nbinsx=36, marker_color="#2563EB"))
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="P/E (log scale)", tickvals=[np.log10(t) for t in ticks], ticktext=[str(t) for t in ticks]),
        yaxis_title="Companies",
    )
    st.plotly_chart(fig, width="stretch")

    cheap, rich = st.columns(2)
    val_cols = ["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "EPS Growth 3Y (%)"]
    val_cfg = {
        "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
        "P/E": st.column_config.NumberColumn(format="%.1fx"),
        "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    }
    with cheap:
        st.markdown('<div class="section-title">Cheapest 10</div>', unsafe_allow_html=True)
        st.dataframe(df[df["P/E"] > 0].nsmallest(10, "P/E")[val_cols], hide_index=True, width="stretch", column_config=val_cfg)
    with rich:
        st.markdown('<div class="section-title">Most Expensive 10</div>', unsafe_allow_html=True)
        st.dataframe(df[df["P/E"] > 0].nlargest(10, "P/E")[val_cols], hide_index=True, width="stretch", column_config=val_cfg)

# ===========================================================================
# Tab 3: Growth
# ===========================================================================
with tab_gro:
    eps = df["EPS Growth 3Y (%)"]
    rev = df["Revenue Growth (%)"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Median EPS G 3Y", f"{eps.median():+.1f}%" if eps.notna().any() else "N/A")
    with c2:
        kpi_card("Median Revenue G", f"{rev.median():+.1f}%" if rev.notna().any() else "N/A", "(YoY)")
    with c3:
        kpi_card("Growing EPS", f"{(eps > 0).sum()} / {eps.notna().sum()}", "companies with data")
    with c4:
        kpi_card("Growing Revenue", f"{(rev > 0).sum()} / {rev.notna().sum()}", "companies with data")

    g1, g2 = st.columns(2)
    with g1:
        fig = go.Figure(go.Histogram(x=eps.dropna(), nbinsx=32, marker_color="#7C3AED"))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), title="EPS Growth 3Y (%)", xaxis_title="%", yaxis_title="Companies")
        st.plotly_chart(fig, width="stretch")
    with g2:
        fig = go.Figure(go.Histogram(x=rev.dropna(), nbinsx=32, marker_color="#0891B2"))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), title="Revenue Growth YoY (%)", xaxis_title="%", yaxis_title="Companies")
        st.plotly_chart(fig, width="stretch")

    st.markdown('<div class="section-title">Fastest Growers (EPS 3Y)</div>', unsafe_allow_html=True)
    gro_cols = ["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "Revenue Growth (%)", "EPS Growth 3Y (%)"]
    gro_cfg = {
        "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
        "P/E": st.column_config.NumberColumn(format="%.1fx"),
        "Revenue Growth (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    }
    st.dataframe(df.nlargest(12, "EPS Growth 3Y (%)")[gro_cols], hide_index=True, width="stretch", column_config=gro_cfg)

# ===========================================================================
# Tab 4: Liquidity
# ===========================================================================
with tab_liq:
    if not has_turnover:
        st.info(
            "Liquidity data not present in this snapshot. Re-run `python scripts/fetch_data.py` "
            "to add Avg Daily Turnover for every company."
        )
    else:
        turn = df[TURN_COL].dropna()
        top10_turn_share = float(df.nlargest(10, TURN_COL)[TURN_COL].sum() / turn.sum() * 100)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("Universe Daily Turnover", cr_fmt(float(turn.sum())), "avg across companies")
        with c2:
            kpi_card("Median Turnover", f"{turn.median():,.1f} Cr", "per company per day")
        with c3:
            kpi_card("Top-10 Turnover Share", f"{top10_turn_share:.0f}%", "liquidity concentration")
        with c4:
            kpi_card("Under 5 Cr/Day", f"{(turn < 5).sum()}", "hard-to-exit names", "neg")

        fig = go.Figure(go.Histogram(x=np.log10(turn[turn > 0]), nbinsx=32, marker_color="#D97706"))
        turn_ticks = [0.5, 1, 5, 20, 100, 500]
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            title="Avg Daily Turnover (Cr, log scale)",
            xaxis=dict(tickvals=[np.log10(t) for t in turn_ticks], ticktext=[str(t) for t in turn_ticks]),
            yaxis_title="Companies",
        )
        st.plotly_chart(fig, width="stretch")

        st.markdown('<div class="section-title">Most Liquid Names</div>', unsafe_allow_html=True)
        liq_cols = ["Company", "NSE Symbol", "Market Cap (Cr)", TURN_COL, "P/E", "1Y Return (%)"]
        liq_cfg = {
            "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
            TURN_COL: st.column_config.NumberColumn(format="%.1f"),
            "P/E": st.column_config.NumberColumn(format="%.1fx"),
            "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        }
        st.dataframe(df.nlargest(12, TURN_COL)[liq_cols], hide_index=True, width="stretch", column_config=liq_cfg)

# ===========================================================================
# Tab 5: Returns
# ===========================================================================
with tab_ret:
    ret = df["1Y Return (%)"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Average 1Y Return", f"{s['avg_ret_1y']:+.1f}%", f"Median {s['median_ret_1y']:+.1f}%", sign_class(s["avg_ret_1y"]))
    with c2:
        kpi_card("% Positive (1Y)", f"{s['pct_positive_1y']:.0f}%", "market breadth", "pos" if s["pct_positive_1y"] >= 50 else "")
    with c3:
        kpi_card("% Negative (1Y)", f"{s['pct_negative_1y']:.0f}%", "market breadth", "neg" if s["pct_negative_1y"] > s["pct_positive_1y"] else "")
    with c4:
        kpi_card("Avg CAGR 3Y / 5Y", f"{s['avg_ret_3y']:+.1f}% / {s['avg_ret_5y']:+.1f}%", sign_class(s["avg_ret_3y"]))

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=ret[ret >= 0].dropna(), nbinsx=30, marker_color="#16A34A", name="Positive", opacity=0.75))
    fig.add_trace(go.Histogram(x=ret[ret < 0].dropna(), nbinsx=30, marker_color="#DC2626", name="Negative", opacity=0.75))
    fig.update_layout(barmode="overlay", height=320, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="1Y Return (%)", yaxis_title="Companies")
    st.plotly_chart(fig, width="stretch")

    t1, t2 = st.columns(2)
    ret_cols = ["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "EPS Growth 3Y (%)", "1Y Return (%)"]
    ret_cfg = {
        "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
        "P/E": st.column_config.NumberColumn(format="%.1fx"),
        "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    }
    with t1:
        st.markdown('<div class="section-title">Top 10 Performers (1Y)</div>', unsafe_allow_html=True)
        st.dataframe(df.nlargest(10, "1Y Return (%)")[ret_cols], hide_index=True, width="stretch", column_config=ret_cfg)
    with t2:
        st.markdown('<div class="section-title">Bottom 10 Performers (1Y)</div>', unsafe_allow_html=True)
        st.dataframe(df.nsmallest(10, "1Y Return (%)")[ret_cols], hide_index=True, width="stretch", column_config=ret_cfg)
