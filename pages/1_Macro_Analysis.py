"""Macro Analysis - Market Scorecard.

Single screen, no tabs:
  1. Market Verdict banner: does growth justify valuations at the required return?
  2. Two hero panels (Valuation via earnings-yield lens, Growth via breadth).
  3. Quadrant synthesis tiles that deep-link into the Micro map.
  4. Second-order context strip (muted).
  5. Detail tables collapsed behind expanders.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import (
    QUADRANTS,
    QUADRANT_COLORS,
    cap_insights,
    growth_insights,
    market_regime,
    market_verdict,
    quadrant_counts,
    valuation_insights,
)
from src.data_loader import get_data
from src.ui import cr_fmt, inject_css, insight_banner, muted_strip, quad_tile, stat_card, verdict_banner, growth_row

st.set_page_config(page_title="Macro | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Macro - Market Scorecard")
cap_l, cap_r = st.columns([3, 1])
with cap_l:
    st.caption("Nifty Smallcap 250 · one screen: does growth justify the price?")
with cap_r:
    st.markdown("[📖 What do these numbers mean?](/Guide)", unsafe_allow_html=False)

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

# ===========================================================================
# Zone 1a: MARKET VERDICT - the one-line answer at the very top
# ===========================================================================
vd = market_verdict(df)
if vd.get("available"):
    verdict_banner(vd["headline"], vd["sentence"], vd["mos_line"], vd["tone"])
else:
    insight_banner(
        "Market Verdict unavailable: too few companies have both a positive P/E "
        "and an earnings-growth history in this snapshot.",
        "warn",
    )

# ===========================================================================
# Zone 1b: HERO PANELS - Valuation | Growth
# ===========================================================================
hero_val, hero_gro = st.columns(2, gap="medium")

with hero_val:
    st.markdown('<div class="hero-title">Valuation</div>', unsafe_allow_html=True)
    vi = valuation_insights(df)
    if vi.get("available"):
        insight_banner(vi["sentence"], vi["tone"])
        c1, c2 = st.columns(2)
        with c1:
            pb_txt = f"{vi['pb_med']:.1f}x" if vi["pb_med"] == vi["pb_med"] else "N/A"
            stat_card("Median P/E", f"{vi['median_pe']:.1f}x", f"median P/B {pb_txt}")
        with c2:
            stat_card(
                "Earnings Yield",
                f"{vi['ey']:.1f}%",
                f"G-Sec pays {vi['risk_free']:.1f}% risk-free",
                "warn" if vi["ey"] < vi["risk_free"] else "pos",
            )
        c3, c4 = st.columns(2)
        with c3:
            stat_card("Needed EPS Growth", f"~{vi['needed']:.1f}%/yr", f"to earn your {vi['required_return']:.0f}%, forever")
        with c4:
            gap = vi["gap"]
            gap_word = "covers it" if gap >= 2 else ("just covers it" if gap >= -2 else "falls short")
            stat_card(
                "Actual EPS Growth (3Y)",
                f"{vi['actual']:+.1f}%",
                f"vs needed ~{vi['needed']:.1f}% → {gap_word}",
                vi["gap_tone"],
            )
    else:
        st.info(f"Not enough priced companies ({vi['valid']} valid P/E) to compute the valuation lens.")

with hero_gro:
    st.markdown('<div class="hero-title">Growth</div>', unsafe_allow_html=True)
    gi = growth_insights(df)
    insight_banner(gi["sentence"], gi["tone"])
    infl = gi["inflation"]
    sales, profit, eps = gi["sales"], gi["profit"], gi["eps"]

    def _meta(d: dict) -> str:
        if not d["valid"]:
            return "no data"
        return (
            f"median <b>{d['median']:+.1f}%</b> nominal"
            f"<br>≈ <b>{d['real_median']:+.1f}% real</b> after ~{infl:.0f}% inflation"
        )

    growth_row("Sales", sales["pos_pct"], _meta(sales), sales["tone"])
    growth_row("Profit", profit["pos_pct"], _meta(profit), profit["tone"])
    growth_row("EPS 3Y", eps["pos_pct"], _meta(eps), eps["tone"])
    st.caption(f"Bar = share of companies with data that grew · medians are YoY unless labelled 3Y.")

# ===========================================================================
# Zone 2: WHERE VALUE MEETS GROWTH - quadrant synthesis, click to explore
# ===========================================================================
st.divider()
qc = quadrant_counts(df)
st.markdown('<div class="section-title">Where value meets growth — click to explore on the map</div>', unsafe_allow_html=True)
st.caption("Split at universe medians (P/E × EPS 3Y). Counts cover the full 250-company universe.")
row1, row2 = st.columns(2, gap="small"), st.columns(2, gap="small")
for i, qname in enumerate(QUADRANTS):
    with (row1 if i < 2 else row2)[i % 2]:
        quad_tile(qname, qc[qname], QUADRANT_COLORS[qname], key=f"quad_{i}")

# ===========================================================================
# Zone 3: SECOND-ORDER CONTEXT - deliberately small and muted
# ===========================================================================
regime = {r["lens"]: r for r in market_regime(df)}
ci = cap_insights(df)
items = []
if "Breadth" in regime:
    items.append(("Breadth", regime["Breadth"]["detail"]))
if "Returns" in regime:
    items.append(("Returns", f"{regime['Returns']['verdict']} · {regime['Returns']['detail']}"))
if "Liquidity" in regime:
    items.append(("Liquidity", f"{regime['Liquidity']['verdict']} ({regime['Liquidity']['detail']})"))
items += [
    ("Median company", cr_fmt(ci["median_cap"])),
    ("Top-10 weight", f"{ci['top10_share']:.0f}% of cap"),
]
muted_strip(items)

# ===========================================================================
# Zone 4: DETAIL TABLES - collapsed until asked for
# ===========================================================================
val_cols = ["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "P/B", "EPS Growth 3Y (%)"]
val_cfg = {
    "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
    "P/E": st.column_config.NumberColumn(format="%.1fx"),
    "P/B": st.column_config.NumberColumn(format="%.1fx"),
    "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
}
pe_pos = df[df["P/E"] > 0]

with st.expander(f"Cheapest 10 stocks (of {len(pe_pos)} priced)"):
    st.dataframe(pe_pos.nsmallest(10, "P/E")[val_cols], hide_index=True, width="stretch", column_config=val_cfg)

with st.expander("Most expensive 10 stocks"):
    st.dataframe(pe_pos.nlargest(10, "P/E")[val_cols], hide_index=True, width="stretch", column_config=val_cfg)

gro_cols = ["Company", "NSE Symbol", "Sector", "Market Cap (Cr)", "P/E", "Revenue Growth (%)", "Profit Growth 1Y (%)", "EPS Growth 3Y (%)"]
gro_cfg = {
    "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
    "P/E": st.column_config.NumberColumn(format="%.1fx"),
    "Revenue Growth (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    "Profit Growth 1Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
    "EPS Growth 3Y (%)": st.column_config.NumberColumn(format="%+.1f%%"),
}
with st.expander("Fastest growers (by EPS 3Y)"):
    st.dataframe(df.nlargest(12, "EPS Growth 3Y (%)")[gro_cols], hide_index=True, width="stretch", column_config=gro_cfg)

liq_col = "Avg Daily Turnover (Cr)"
if liq_col in df.columns and df[liq_col].notna().any():
    with st.expander("Most liquid names"):
        st.dataframe(
            df.nlargest(12, liq_col)[["Company", "NSE Symbol", "Market Cap (Cr)", liq_col, "P/E", "1Y Return (%)"]],
            hide_index=True,
            width="stretch",
            column_config={
                "Market Cap (Cr)": st.column_config.NumberColumn(format="%.0f"),
                liq_col: st.column_config.NumberColumn(format="%.1f"),
                "P/E": st.column_config.NumberColumn(format="%.1fx"),
                "1Y Return (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            },
        )
