"""Macro Analysis: five lenses, each answering one question.

Fixed skeleton per tab: question headline -> insight banner -> 4 stat cards
(each with context) -> one primary visual -> one supporting table block.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import (
    TURN_COL,
    cap_insights,
    growth_insights,
    liquidity_insights,
    market_regime,
    returns_insights,
    valuation_insights,
)
from src.data_loader import get_data
from src.ui import cr_fmt, inject_css, insight_banner, regime_strip, stat_card

st.set_page_config(page_title="Macro | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Macro Analysis")
st.caption("Nifty Smallcap 250 - five lenses, each answering one question.")

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

regime = market_regime(df)
regime_strip([(r["lens"], r["verdict"], r["detail"], r["tone"]) for r in regime])

tab_cap, tab_val, tab_gro, tab_liq, tab_ret = st.tabs(
    ["Companies & Cap", "Valuations", "Growth", "Liquidity", "Returns"]
)

# ===========================================================================
# Tab 1: Companies & Cap - "What dominates this universe?"
# ===========================================================================
with tab_cap:
    st.markdown("### What dominates this universe?")
    ci = cap_insights(df)
    insight_banner(ci["sentence"], ci["tone"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Companies", f"{ci['n']}", f"across {ci['sectors']} sectors")
    with c2:
        stat_card("Total Market Cap", cr_fmt(ci["total_cap"]), f"avg {cr_fmt(ci['total_cap'] / ci['n'])} per company")
    with c3:
        stat_card("Median Company", cr_fmt(ci["median_cap"]), "half of the universe is smaller")
    with c4:
        stat_card("Top-10 Weight", f"{ci['top10_share']:.0f}%", f"{ci['concentration']} concentration", ci["concentration_tone"])

    sec_agg = df.groupby("Sector").agg(
        cap=("Market Cap (Cr)", "sum"),
        med_ret=("1Y Return (%)", "median"),
        n=("Company", "count"),
    ).reset_index()

    fig = go.Figure(
        go.Treemap(
            labels=sec_agg["Sector"],
            parents=[""] * len(sec_agg),
            values=sec_agg["cap"],
            customdata=np.stack([sec_agg["med_ret"], sec_agg["n"]], axis=-1),
            marker=dict(
                colors=sec_agg["med_ret"],
                colorscale="RdYlGn",
                cmid=0,
                showscale=True,
                colorbar=dict(title="Median 1Y %"),
            ),
            texttemplate="<b>%{label}</b><br>%{value:,.0f} Cr",
            hovertemplate="<b>%{label}</b><br>Cap: %{value:,.0f} Cr<br>Companies: %{customdata[1]:.0f}<br>Median 1Y: %{customdata[0]:+.1f}%<extra></extra>",
        )
    )
    fig.update_layout(height=440, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("Tile size = sector market cap; color = median 1Y return of its companies (green positive, red negative).")

    st.markdown('<div class="section-title">Largest 15 Companies</div>', unsafe_allow_html=True)
    top15 = df.nlargest(15, "Market Cap (Cr)")
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
# Tab 2: Valuations - "How expensive is the universe?"
# ===========================================================================
with tab_val:
    st.markdown("### How expensive is the universe?")
    vi = valuation_insights(df)
    insight_banner(vi["sentence"], vi["tone"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Median P/E", f"{vi['median']:.1f}x", "half the universe trades below this")
    with c2:
        stat_card("Cheap Half Starts", f"{vi['p25']:.1f}x", "25th percentile")
    with c3:
        stat_card("Expensive Half Starts", f"{vi['p75']:.1f}x", "75th percentile")
    with c4:
        stat_card("Priced & Profitable", f"{vi['valid']} / {len(df)}", f"{vi['loss_making']} excluded (loss-making)")

    pe_pos = df["P/E"].dropna()
    pe_pos = pe_pos[pe_pos > 0]
    ticks = [5, 10, 25, 50, 100, 250, 500, 1000]
    fig = go.Figure(go.Histogram(x=np.log10(pe_pos), nbinsx=36, marker_color="#2563EB"))
    fig.add_vline(
        x=np.log10(vi["median"]),
        line_width=1.6, line_dash="dash", line_color="#DC2626",
        annotation_text=f"Median {vi['median']:.0f}x", annotation_position="top",
    )
    fig.update_layout(
        height=340, margin=dict(l=10, r=10, t=30, b=10),
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
# Tab 3: Growth - "Is the universe growing?"
# ===========================================================================
with tab_gro:
    st.markdown("### Is the universe growing?")
    gi = growth_insights(df)
    insight_banner(gi["sentence"], gi["tone"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Median EPS Growth 3Y", f"{gi['median_eps']:+.1f}%", "companies with data")
    with c2:
        stat_card("EPS Breadth", f"{gi['eps_pos_pct']:.0f}%", "share growing EPS", gi["tone"])
    with c3:
        stat_card("Median Revenue Growth", f"{gi['median_rev']:+.1f}%", "YoY")
    with c4:
        stat_card("Revenue Breadth", f"{gi['rev_pos_pct']:.0f}%", "share growing revenue")

    eps, rev = df["EPS Growth 3Y (%)"], df["Revenue Growth (%)"]
    rows = []
    for name, s in [("EPS Growth 3Y", eps), ("Revenue Growth YoY", rev)]:
        valid = int(s.notna().sum())
        if valid:
            pos, neg = int((s > 0).sum()), int((s <= 0).sum())
            rows.append((name, -neg / valid * 100, pos / valid * 100, neg, pos))
    bdf = pd.DataFrame(rows, columns=["metric", "neg_pct", "pos_pct", "neg_n", "pos_n"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=bdf["metric"], x=bdf["neg_pct"], orientation="h",
        marker_color="#DC2626", name="Shrinking",
        text=[f"{n} ({abs(p):.0f}%)" for n, p in zip(bdf["neg_n"], bdf["neg_pct"])],
        textposition="inside", insidetextanchor="middle",
    ))
    fig.add_trace(go.Bar(
        y=bdf["metric"], x=bdf["pos_pct"], orientation="h",
        marker_color="#16A34A", name="Growing",
        text=[f"{n} ({p:.0f}%)" for n, p in zip(bdf["pos_n"], bdf["pos_pct"])],
        textposition="inside", insidetextanchor="middle",
    ))
    fig.update_layout(
        barmode="relative", height=240, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="% of companies with data", range=[-105, 105], zeroline=True),
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Left of zero = shrinking, right = growing. Labels show company counts.")

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
# Tab 4: Liquidity - "Can you exit easily?"
# ===========================================================================
with tab_liq:
    li = liquidity_insights(df)
    if li is None:
        st.markdown("### Can you exit easily?")
        st.info(
            "Liquidity data not present in this snapshot. Re-run `python scripts/fetch_data.py` "
            "to add Avg Daily Turnover for every company."
        )
    else:
        st.markdown("### Can you exit easily?")
        insight_banner(li["sentence"], li["tone"])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            stat_card("Universe Daily Turnover", cr_fmt(li["total"]), "sum of avg daily turnover")
        with c2:
            stat_card("Median Name", f"{li['median']:,.0f} Cr", "traded per day")
        with c3:
            stat_card("Hard-to-Exit Tail", f"{li['illiquid_n']}", f"{li['illiquid_pct']:.0f}% trade <5 Cr/day", "neg" if li["illiquid_n"] else "pos")
        with c4:
            stat_card("Top-10 Turnover Share", f"{li['top10_share']:.0f}%", "liquidity is concentrated")

        turn = df[TURN_COL].dropna()
        turn = turn[turn > 0]
        turn_ticks = [0.5, 1, 5, 20, 100, 500]
        fig = go.Figure(go.Histogram(x=np.log10(turn), nbinsx=32, marker_color="#D97706"))
        fig.add_vline(
            x=np.log10(5), line_width=1.6, line_dash="dash", line_color="#DC2626",
            annotation_text="5 Cr/day", annotation_position="top",
        )
        fig.update_layout(
            height=340, margin=dict(l=10, r=10, t=30, b=10),
            title="Avg Daily Turnover (log scale)",
            xaxis=dict(tickvals=[np.log10(t) for t in turn_ticks], ticktext=[str(t) for t in turn_ticks]),
            yaxis_title="Companies",
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("Names to the left of the red line may be difficult to exit in size.")

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
# Tab 5: Returns - "How did the universe perform?"
# ===========================================================================
with tab_ret:
    st.markdown("### How did the universe perform?")
    ri = returns_insights(df)
    insight_banner(ri["sentence"], ri["tone"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Median 1Y Return", f"{ri['median_1y']:+.1f}%", "typical stock", "pos" if ri["median_1y"] > 0 else "neg")
    with c2:
        stat_card("Breadth", f"{ri['pct_pos']:.0f}%", "share positive over 1Y", ri["tone"])
    with c3:
        stat_card("Avg CAGR 3Y", f"{ri['avg_3y']:+.1f}%", "", "pos" if ri["avg_3y"] > 0 else "neg")
    with c4:
        stat_card("Avg CAGR 5Y", f"{ri['avg_5y']:+.1f}%", "", "pos" if ri["avg_5y"] > 0 else "neg")

    ret = df["1Y Return (%)"].dropna()
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=ret[ret >= 0], nbinsx=30, marker_color="#16A34A", name="Positive", opacity=0.75))
    fig.add_trace(go.Histogram(x=ret[ret < 0], nbinsx=30, marker_color="#DC2626", name="Negative", opacity=0.75))
    fig.add_vline(
        x=0, line_width=1.6, line_color="#0F172A",
        annotation_text=f"{ri['pct_pos']:.0f}% positive", annotation_position="top right",
    )
    fig.update_layout(
        barmode="overlay", height=340, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="1Y Return (%)", yaxis_title="Companies",
        legend=dict(orientation="h", y=1.12),
    )
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
