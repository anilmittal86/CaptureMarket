"""Sectoral Analysis: intra-sector dispersion view + median-based sector table.

Smallcap sectors have wide return dispersion, so sectors are compared on
medians and breadth - never averages.
"""
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import sector_summary
from src.data_loader import get_data
from src.ui import inject_css

st.set_page_config(page_title="Sectoral | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Sectoral Analysis")
st.caption(
    "Return dispersion within a smallcap sector is huge, so each sector is shown as a "
    "distribution - not a single bubble or average. Compare medians and breadth."
)

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

# --- dispersion view -------------------------------------------------------
metric = st.radio(
    "Distribution of",
    ["1Y Return (%)", "3Y CAGR (%)", "EPS Growth 3Y (%)", "Revenue Growth (%)"],
    horizontal=True,
)

d = df[["Sector", metric]].dropna()
medians = d.groupby("Sector")[metric].median().sort_values(ascending=False)
sector_order = medians.index.tolist()[::-1]  # best median at top

fig = go.Figure(
    go.Box(
        x=d[metric],
        y=d["Sector"],
        orientation="h",
        boxpoints="outliers",
        marker_color="#2563EB",
        line_color="#0F172A",
        fillcolor="rgba(37, 99, 235, 0.25)",
    )
)
fig.add_vline(x=0, line_width=1.2, line_dash="dash", line_color="#94A3B8")
fig.update_layout(
    height=max(440, 36 * len(sector_order)),
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis=dict(title=f"{metric} distribution per sector", zeroline=False),
    yaxis=dict(categoryorder="array", categoryarray=sector_order, automargin=True),
    template="plotly_white",
)
st.plotly_chart(fig, width="stretch")
st.caption(f"Sectors ordered by median {metric}. Boxes span p25-p75; whiskers 1.5x IQR; dots are outliers.")

st.divider()

# --- sector table (medians + breadth) ---------------------------------------
sec = sector_summary(df)
st.markdown('<div class="section-title">All Sectors (medians & breadth)</div>', unsafe_allow_html=True)
st.dataframe(
    sec.reset_index(),
    hide_index=True,
    width="stretch",
    column_config={
        "Companies": st.column_config.NumberColumn(format="%d"),
        "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
        "Weight (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "Median P/E": st.column_config.NumberColumn(format="%.1fx"),
        "Median EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        "Median 1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        "% Positive (1Y)": st.column_config.ProgressColumn(
            "Breadth (% Positive)", min_value=0, max_value=100, format="%.0f%%"
        ),
        "1Y Return IQR (pp)": st.column_config.NumberColumn(format="%.0f"),
    },
)

st.divider()

# --- drill-down ---------------------------------------------------------------
st.markdown('<div class="section-title">Sector Drill-down</div>', unsafe_allow_html=True)
options = ["Select a sector..."] + list(sec.index)
choice = st.selectbox("Sector", options, index=0)

if choice != "Select a sector...":
    sub = df[df["Sector"] == choice].sort_values("Market Cap (Cr)", ascending=False)
    cols = ["Company", "NSE Symbol", "Industry", "Market Cap (Cr)", "P/E", "EPS Growth 3Y (%)", "1Y Return (%)"]
    st.markdown(f"**{choice}** - {len(sub)} companies | median 1Y return {sub['1Y Return (%)'].median():+.1f}%")
    st.dataframe(
        sub[cols],
        hide_index=True,
        width="stretch",
        column_config={
            "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
            "P/E": st.column_config.NumberColumn(format="%.1fx"),
            "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )
    if st.button("Analyze this sector in Micro Analysis"):
        st.session_state["micro_preset_sectors"] = [choice]
        st.switch_page("pages/3_Micro_Analysis.py")
