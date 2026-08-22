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
    market_regime,
    market_verdict,
    quadrant_counts,
)
from src.data_loader import get_data
from src.ui import cr_fmt, evaluation_table, inject_css, insight_banner, muted_strip, quad_tile, stat_card, verdict_banner

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
# Zone 1b: REALITY CHECK - the universe as one index, two hard gates
# ===========================================================================
if vd.get("available"):
    st.markdown('<div class="hero-title">Market Snapshot - the universe as one index</div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        stat_card("Index P/E", f"{vd['idx_pe']:.1f}x", f"cap-weighted · {vd['priced_n']} priced cos")
    with s2:
        stat_card(
            "Earnings Yield",
            f"{vd['ey']:.1f}%",
            f"G-Sec pays {vd['risk_free']:.1f}% risk-free",
            "pos" if vd['buffer_pass'] else "warn",
        )
    with s3:
        stat_card("Nominal Growth", f"{vd['nominal_growth']:+.1f}%", "median EPS 3-yr CAGR")
    with s4:
        stat_card(
            "Real Growth",
            f"{vd['structural_growth']:+.1f}%",
            f"after ~{vd['inflation']:.0f}% inflation",
            "pos" if vd['structural_growth'] > 0 else "neg",
        )

    st.markdown('<div class="section-title">The Reality Check - two hard gates at your required return</div>', unsafe_allow_html=True)
    evaluation_table(
        [
            {
                "title": "1. The Growth Hurdle",
                "subtitle": "Growth needed forever to justify today's price.",
                "math": f"~{vd['implied_growth'] * 100:.1f}% / yr",
                "target": (
                    f"Real growth must beat it. "
                    f"({vd['required_return']:.0f}% required − {vd['ey']:.1f}% yield)."
                ),
                "passed": vd["growth_pass"],
            },
            {
                "title": "2. Structural Growth (real)",
                "subtitle": f"Median EPS 3-yr CAGR deflated by ~{vd['inflation']:.0f}% inflation.",
                "math": (
                    f"{vd['structural_growth']:+.1f}% / yr real"
                    f"<br><span style='font-size:0.8em;font-weight:normal;color:#64748B;'>"
                    f"({vd['nominal_growth']:+.1f}% nominal)</span>"
                ),
                "target": "Must comfortably clear the hurdle.",
                "passed": vd["growth_pass"],
            },
            {
                "title": "3. Safety Buffer",
                "subtitle": "Index earnings yield vs the risk-free bank rate.",
                "math": (
                    f"{vd['safety_buffer'] * 100:+.1f}%"
                    f"<br><span style='font-size:0.8em;font-weight:normal;color:#64748B;'>"
                    f"({vd['ey']:.1f}% vs {vd['risk_free']:.1f}%)</span>"
                ),
                "target": "Must be positive - equity yield above the G-Sec.",
                "passed": vd["buffer_pass"],
            },
        ]
    )
    st.caption(f"{vd['loss_making']} loss-making / unpriced companies are excluded from index earnings.")
else:
    insight_banner(
        "Reality Check unavailable: too few companies have a positive P/E in this snapshot.",
        "warn",
    )

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
