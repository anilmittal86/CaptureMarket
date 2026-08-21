"""Micro Analysis: stock-level quadrant market map (the core 'market map')."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import QUADRANT_COLORS, QUADRANTS, assign_quadrants, percentile_rank, quadrant_summary, universe_medians
from src.data_loader import get_data
from src.metrics import COLOR_OPTIONS, DEFAULT_CHART_CONFIG, METRICS, SIZE_OPTIONS, TOOLTIP_FIELDS, fmt_metric
from src.ui import cr_fmt, inject_css, kpi_card
from src.visualization import build_bubble_figure

st.set_page_config(page_title="Micro | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Micro Analysis")
st.caption(
    "Where does each stock sit relative to the entire universe? "
    "X = valuation, Y = earnings growth, bubble size = |1Y return|, color = return direction."
)

try:
    df_full = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

ss = st.session_state
ss.setdefault("selected_symbol", None)

# --- chart configuration (axes are config, not hard-coded) ----------------
available = [k for k, m in METRICS.items() if m.column in df_full.columns and df_full[m.column].notna().any()]
size_avail = [k for k, (col, _, _) in SIZE_OPTIONS.items() if col in df_full.columns and df_full[col].notna().any()]
color_avail = [k for k, (col, _) in COLOR_OPTIONS.items() if col in df_full.columns]

with st.expander("Chart settings (axes & bubble encodings)"):
    sc1, sc2, sc3, sc4 = st.columns(4)
    cfg = {
        "x": sc1.selectbox("X axis", available, index=available.index(DEFAULT_CHART_CONFIG["x"]), format_func=lambda k: METRICS[k].label),
        "y": sc2.selectbox("Y axis", available, index=available.index(DEFAULT_CHART_CONFIG["y"]), format_func=lambda k: METRICS[k].label),
        "size": sc3.selectbox("Bubble size", size_avail, index=size_avail.index(DEFAULT_CHART_CONFIG["size"]), format_func=lambda k: SIZE_OPTIONS[k][1]),
        "color": sc4.selectbox("Bubble color", color_avail, index=color_avail.index(DEFAULT_CHART_CONFIG["color"]), format_func=lambda k: COLOR_OPTIONS[k][1]),
    }

x_col, y_col = METRICS[cfg["x"]].column, METRICS[cfg["y"]].column
med_x, med_y = universe_medians(df_full, x_col, y_col)

# --- search ---------------------------------------------------------------
q = st.text_input("Search company or NSE symbol...", placeholder="Search company or NSE symbol...")
if q.strip():
    ql = q.strip().lower()
    matches = df_full[
        df_full["Company"].astype(str).str.lower().str.contains(ql, na=False)
        | df_full["NSE Symbol"].astype(str).str.lower().str.contains(ql, na=False)
    ]
    def _opt(r: pd.Series) -> str:
        mc = r.get("Market Cap (Cr)")
        mc_s = f" | {mc:,.0f} Cr" if pd.notna(mc) else ""
        return f"{r['Company']} ({r['NSE Symbol']}){mc_s}"

    options = [_opt(r) for _, r in matches.iterrows()]
    pick = st.selectbox(f"{len(matches)} match(es)", ["-- select to locate on chart --"] + options[:50])
    if not pick.startswith("--") and "(" in pick:
        ss.selected_symbol = pick.split("(")[1].split(")")[0]

# --- sidebar filters ------------------------------------------------------
st.sidebar.header("Filters")
preset = ss.pop("micro_preset_sectors", None)
all_sectors = sorted(df_full["Sector"].dropna().unique())
sel_sectors = st.sidebar.multiselect("Sector", all_sectors, default=[s for s in (preset or []) if s in all_sectors])

sector_pool = df_full[df_full["Sector"].isin(sel_sectors)] if sel_sectors else df_full
all_industries = sorted(sector_pool["Industry"].dropna().unique())
sel_industries = st.sidebar.multiselect("Industry", all_industries)


def bounds(col: str) -> tuple[float, float]:
    s = df_full[col].dropna()
    lo, hi = float(s.min()), float(s.max())
    return (lo, hi + 1.0) if lo == hi else (lo, hi)


cap_lo, cap_hi = bounds("Market Cap (Cr)")
pe_lo, pe_hi = bounds("P/E")
eps_lo, eps_hi = bounds("EPS Growth 3Y (%)")
ret_lo, ret_hi = bounds("1Y Return (%)")

cap_rng = st.sidebar.slider("Market Cap (Cr)", cap_lo, cap_hi, (cap_lo, cap_hi))
pe_rng = st.sidebar.slider("P/E", pe_lo, pe_hi, (pe_lo, pe_hi))
eps_rng = st.sidebar.slider("EPS Growth 3Y (%)", eps_lo, eps_hi, (eps_lo, eps_hi))
ret_rng = st.sidebar.slider("1Y Return (%)", ret_lo, ret_hi, (ret_lo, ret_hi))

ret_mode = st.sidebar.radio("Returns", ["All stocks", "Positive return", "Negative return"], horizontal=True)
quad_sidebar = st.sidebar.multiselect("Quadrant", QUADRANTS)

view = df_full.copy()
if sel_sectors:
    view = view[view["Sector"].isin(sel_sectors)]
if sel_industries:
    view = view[view["Industry"].isin(sel_industries)]
view = view[view["Market Cap (Cr)"].between(*cap_rng)]
view = view[view["P/E"].between(*pe_rng)]
view = view[view["EPS Growth 3Y (%)"].between(*eps_rng)]
view = view[view["1Y Return (%)"].between(*ret_rng)]
if ret_mode == "Positive return":
    view = view[view["1Y Return (%)"] > 0]
elif ret_mode == "Negative return":
    view = view[view["1Y Return (%)"] < 0]

plotted = view.dropna(subset=[x_col, y_col]).copy()
plotted["Quadrant"] = assign_quadrants(plotted, x_col, y_col, med_x, med_y)

# --- quadrant selection state (the widget itself renders below the chart) ----
qs = quadrant_summary(plotted)
rows_sel = []
if isinstance(st.session_state.get("quadrant_table"), dict):
    rows_sel = st.session_state["quadrant_table"].get("selection", {}).get("rows", []) or []
rows_sel = [r for r in rows_sel if isinstance(r, int) and 0 <= r < len(qs)]
table_quads = {qs.iloc[r]["Quadrant"] for r in rows_sel}
effective_quads = set(quad_sidebar) | table_quads
if effective_quads:
    plotted = plotted[plotted["Quadrant"].isin(effective_quads)]

# --- axis scale toggle -------------------------------------------------------
log_mode = st.radio("P/E scale", ["Log P/E", "Linear P/E"], horizontal=True, label_visibility="collapsed")
log_x = log_mode == "Log P/E"

# --- the market map -----------------------------------------------------------
fig = build_bubble_figure(
    plotted,
    df_full,
    cfg,
    selected_label=ss.get("selected_symbol"),
    log_x=log_x,
    title="Stock Market Map - Valuation vs Earnings Growth",
    height=660,
)
chart_event = st.plotly_chart(
    fig,
    width="stretch",
    on_select="rerun",
    selection_mode=("points",),
    key="micro_map",
)

points = chart_event.get("selection", {}).get("points", []) if isinstance(chart_event, dict) else []
if points:
    idx = points[0].get("point_index")
    if idx is not None and 0 <= int(idx) < len(plotted):
        ss.selected_symbol = plotted.iloc[int(idx)]["NSE Symbol"]

# --- selected stock panel -----------------------------------------------------
sym = ss.get("selected_symbol")
if sym:
    row_df = df_full[df_full["NSE Symbol"] == sym]
    if not row_df.empty:
        row = row_df.iloc[0]
        quadrant = assign_quadrants(row_df, x_col, y_col, med_x, med_y).iloc[0]
        st.divider()

        head_l, head_r = st.columns([3, 1])
        with head_l:
            st.markdown(f"### {row['Company']} ({row['NSE Symbol']})")
            if pd.notna(quadrant):
                st.markdown(
                    f'<span class="quad-badge" style="background:{QUADRANT_COLORS.get(quadrant, "#64748B")}">{quadrant}</span>',
                    unsafe_allow_html=True,
                )
        with head_r:
            if st.button("Clear selection"):
                ss.selected_symbol = None
                st.rerun()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            kpi_card("P/E", fmt_metric("P/E", row.get("P/E")))
        with m2:
            kpi_card("EPS Growth 3Y", fmt_metric("EPS Growth 3Y (%)", row.get("EPS Growth 3Y (%)")))
        with m3:
            kpi_card("1Y Return", fmt_metric("1Y Return (%)", row.get("1Y Return (%)")))
        with m4:
            mc = row.get("Market Cap (Cr)")
            kpi_card("Market Cap", cr_fmt(float(mc)) if pd.notna(mc) else "N/A")

        p1, p2, p3 = st.columns(3)
        with p1:
            pct_pe = percentile_rank(df_full[x_col], row.get(x_col))
            kpi_card(f"{METRICS[cfg['x']].label} percentile", f"{pct_pe:.0f}th" if pct_pe is not None else "N/A", "vs complete universe")
        with p2:
            pct_y = percentile_rank(df_full[y_col], row.get(y_col))
            kpi_card(f"{METRICS[cfg['y']].label} percentile", f"{pct_y:.0f}th" if pct_y is not None else "N/A", "vs complete universe")
        with p3:
            pct_r = percentile_rank(df_full["1Y Return (%)"], row.get("1Y Return (%)"))
            kpi_card("1Y Return percentile", f"{pct_r:.0f}th" if pct_r is not None else "N/A", "vs complete universe")

        with st.expander("All available details"):
            details = [
                (label, fmt_metric(column, row.get(column)))
                for label, column, _fmt in TOOLTIP_FIELDS
                if fmt_metric(column, row.get(column)) != "N/A"
            ]
            half = (len(details) + 1) // 2
            d1, d2 = st.columns(2)
            for col_box, chunk in ((d1, details[:half]), (d2, details[half:])):
                with col_box:
                    for label, value in chunk:
                        st.markdown(f"**{label}:** {value}")

        if sym not in plotted["NSE Symbol"].values:
            st.caption("Selected stock is hidden by current filters - clear filters to see it on the map.")

# --- quadrant summary (below the chart; click row(s) to filter) ---------------
st.divider()
st.markdown('<div class="section-title">Quadrants - click row(s) to filter the map</div>', unsafe_allow_html=True)
st.dataframe(
    qs,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="multi-row",
    key="quadrant_table",
)

# --- companies in the selected quadrant(s) -----------------------------------
if effective_quads:
    st.divider()
    n_q = len(effective_quads)
    st.markdown(
        f'<div class="section-title">Companies in selected quadrant{"s" if n_q > 1 else ""} ({len(plotted)})</div>',
        unsafe_allow_html=True,
    )
    q_cols = [
        "Company", "NSE Symbol", "Sector", "Industry", "Market Cap (Cr)",
        "P/E", "EPS Growth 3Y (%)", "Revenue Growth (%)", "ROE (%)",
        "1Y Return (%)", "Quadrant",
    ]
    q_tbl = plotted.sort_values("Market Cap (Cr)", ascending=False)
    st.dataframe(
        q_tbl[q_cols],
        hide_index=True,
        width="stretch",
        column_config={
            "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
            "P/E": st.column_config.NumberColumn(format="%.1fx"),
            "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            "Revenue Growth (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            "ROE (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )
