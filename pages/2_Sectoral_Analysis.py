"""Sectoral Analysis: sector-level quadrant market map + table + drill-down."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import sector_summary
from src.data_loader import get_data
from src.ui import cr_fmt, inject_css, kpi_card
from src.visualization import build_bubble_figure, sector_hover_fields

st.set_page_config(page_title="Sectoral | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Sectoral Analysis")
st.caption(
    "Each bubble is a sector: position = median valuation vs median earnings growth, "
    "size = |avg 1Y return|, color = return direction. Boundaries = sector-universe medians."
)

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

sec = sector_summary(df)
sec_plot = sec.reset_index()
sec_plot["Company"] = sec_plot["Sector"]  # generic name column for the shared builder
# Canonical metric column names so the shared builder resolves them via the registry
sec_plot = sec_plot.rename(columns={"Median P/E": "P/E", "Median EPS Growth 3Y (%)": "EPS Growth 3Y (%)"})

config = {"x": "pe", "y": "eps_g_3y", "size": "avg_ret_1y_abs", "color": "avg_ret_1y_sign"}

c_map, c_side = st.columns([3, 1])

with c_map:
    fig = build_bubble_figure(
        sec_plot,
        sec_plot,
        config,
        name_col="Company",
        symbol_col="Company",
        hover_fields=sector_hover_fields(sec_plot),
        log_x=False,
        title="Sector Market Map",
        height=560,
    )
    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=("points",),
        key="sector_map",
    )

with c_side:
    st.markdown('<div class="section-title">Sector Snapshot</div>', unsafe_allow_html=True)
    best = sec.sort_values("Avg 1Y Return (%)", ascending=False)
    top_sector = best.index[0] if len(best) else None
    if top_sector is not None:
        row = best.iloc[0]
        kpi_card("Best Avg 1Y Return", top_sector, f"{row['Avg 1Y Return (%)']:+.1f}% | {int(row['Companies'])} companies",
                 value_class="pos" if row["Avg 1Y Return (%)"] > 0 else "neg")
    heaviest = sec.iloc[0]
    kpi_card("Heaviest Sector", str(heaviest.name), f"{heaviest['Weight (%)']:.1f}% weight | {int(heaviest['Companies'])} companies")
    kpi_card("Sector Universe Mkt Cap", cr_fmt(float(sec["Market Cap (Cr)"].sum())), f"across {len(sec)} sectors")

# --- sector table --------------------------------------------------------
st.markdown('<div class="section-title">All Sectors</div>', unsafe_allow_html=True)
st.dataframe(
    sec.reset_index(),  # sector name as a real column (hide_index would hide it otherwise)
    hide_index=True,
    width="stretch",
    column_config={
        "Market Cap (Cr)": st.column_config.NumberColumn(format="comma"),
        "Weight (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "Median P/E": st.column_config.NumberColumn(format="%.1fx"),
        "Median EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        "Avg 1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        "Avg 3Y CAGR (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    },
)

st.divider()

# --- drill-down ----------------------------------------------------------
st.markdown('<div class="section-title">Sector Drill-down</div>', unsafe_allow_html=True)

selected_sector = None
points = []
if isinstance(event, dict):
    points = event.get("selection", {}).get("points", []) or []
if points:
    idx = points[0].get("point_index")
    if idx is not None and 0 <= int(idx) < len(sec_plot):
        selected_sector = sec_plot.iloc[int(idx)]["Sector"]

pick_from_chart = st.session_state.get("sector_pick")
options = ["Select a sector..."] + list(sec.index)
default_idx = options.index(selected_sector) if selected_sector in options else 0
choice = st.selectbox("Sector", options, index=default_idx, key="sector_pick_box")
if choice != "Select a sector...":
    selected_sector = choice

if selected_sector:
    sub = df[df["Sector"] == selected_sector].sort_values("Market Cap (Cr)", ascending=False)
    cols = ["Company", "NSE Symbol", "Industry", "Market Cap (Cr)", "P/E", "EPS Growth 3Y (%)", "1Y Return (%)"]
    st.markdown(f"**{selected_sector}** - {len(sub)} companies")
    st.dataframe(
        sub[cols],
        hide_index=True,
        width="stretch",
        column_config={
            "Market Cap (Cr)": st.column_config.NumberColumn(format="comma"),
            "P/E": st.column_config.NumberColumn(format="%.1fx"),
            "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )
    if st.button("Analyze this sector in Micro Analysis"):
        st.session_state["micro_preset_sectors"] = [selected_sector]
        st.switch_page("pages/3_Micro_Analysis.py")
