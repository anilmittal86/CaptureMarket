"""Macro Analysis - Market Scorecard.

Single screen, no tabs:
  1. Market Verdict banner: valuations vs history and vs Nifty 50, growth intact?
  2. Snapshot: Index P/E/PB vs history/peer + growth.
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
# Zone 1b: SNAPSHOT — valuations vs history + vs Nifty 50
# ===========================================================================
if vd.get("available"):
    hist = vd.get("hist_ctx", {})
    st.markdown('<div class="hero-title">Market Snapshot — Smallcap 250 as one index</div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        prem5 = hist.get("premium_5y", float("nan")) if isinstance(hist, dict) else float("nan")
        med5 = hist.get("median_5y", float("nan")) if isinstance(hist, dict) else float("nan")
        pct5 = hist.get("pct_5y")
        sub = f"{prem5:+.0f}% vs 5Y median {med5:.1f}x · {pct5:.0f}th %ile" if hist.get("available") and pct5 is not None else "history collecting"
        tone = "warn" if hist.get("available") and (prem5 > 20 or (pct5 is not None and pct5 > 80)) else ("pos" if hist.get("available") and prem5 < 0 else "neutral")
        stat_card("Index P/E vs History", f"{vd['idx_pe']:.1f}x", sub, tone)
    with s2:
        pb_txt = f"{vd.get('pb_med', float('nan')):.1f}x" if vd.get("pb_med") == vd.get("pb_med") else "—"
        hist_pb = hist.get("premium_5y", 0) if isinstance(hist, dict) else 0
        stat_card("P/B vs History", pb_txt, f"{hist_pb:+.0f}% vs 5Y P/B median" if hist.get("available") else "history collecting", "neutral")
    with s3:
        peer_pe = vd.get("peer_pe", float("nan"))
        peer_prem = vd.get("peer_premium", float("nan"))
        sub_peer = f"{peer_prem:+.0f}% premium — Nifty 50 {peer_pe:.1f}x" if peer_pe == peer_pe else "peer collecting"
        tone_peer = "warn" if peer_prem == peer_prem and peer_prem > 25 else ("pos" if peer_prem == peer_prem and peer_prem < 0 else "neutral")
        stat_card("Smallcap vs Nifty 50", f"{peer_prem:+.0f}%", sub_peer, tone_peer)
    with s4:
        sg = vd.get("structural_growth", float("nan"))
        stat_card("Real Growth", f"{sg:+.1f}%", f"nominal {vd.get('nominal_growth', 0):+.1f}% − {vd.get('inflation', 5):.0f}% infl", "pos" if sg == sg and sg > 0 else "warn")

    st.markdown('<div class="section-title">Valuation check — vs own history and vs broad market</div>', unsafe_allow_html=True)
    peer_pe = vd.get("peer_pe", float("nan"))
    hist_available = hist.get("available", False) if isinstance(hist, dict) else False
    evaluation_table(
        [
            {
                "title": "1. Valuation vs History (5Y)",
                "subtitle": f"Index P/E {vd['idx_pe']:.1f}x vs 5Y median {hist.get('median_5y', 0):.1f}x" if hist_available else "Index P/E vs own 5Y history",
                "math": f"{hist.get('premium_5y', 0):+.0f}% premium<br><span style='font-size:0.8em;font-weight:normal;color:#64748B;'>({hist.get('pct_5y', 0):.0f}th %ile)</span>" if hist_available else "collecting",
                "target": "Must be < +20% and < 80th %ile to be reasonable",
                "passed": vd.get("val_hist_pass", True),
            },
            {
                "title": "2. Valuation vs Nifty 50",
                "subtitle": "Smallcap premium over largecap",
                "math": f"{vd.get('peer_premium', 0):+.0f}% premium<br><span style='font-size:0.8em;font-weight:normal;color:#64748B;'>({vd['idx_pe']:.1f}x vs {peer_pe:.1f}x)</span>" if peer_pe == peer_pe else "collecting",
                "target": "Must be < +25% premium to be reasonable",
                "passed": vd.get("peer_pass", True),
            },
            {
                "title": "3. Growth (real)",
                "subtitle": f"Median EPS 3-yr CAGR deflated by ~{vd.get('inflation', 5):.0f}% inflation",
                "math": f"{vd.get('structural_growth', 0):+.1f}% / yr real<br><span style='font-size:0.8em;font-weight:normal;color:#64748B;'>({vd.get('nominal_growth', 0):+.1f}% nominal)</span>",
                "target": "Must be > 0% real and breadth improving vs history",
                "passed": vd.get("growth_pass", True),
            },
        ]
    )
    st.caption(f"{vd['loss_making']} loss-making / unpriced companies excluded from cap-weighted P/E. History: NSE P/E/PB daily 5Y (synthetic seed, will be replaced by live NSE fetch).")
else:
    insight_banner("Snapshot unavailable: too few companies have a positive P/E in this snapshot.", "warn")

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
