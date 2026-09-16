"""Guide: what every number in CaptureMarket means and how to read it."""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import EQUITY_PREMIUM, INFLATION, REQUIRED_RETURN, RISK_FREE_RATE
from src.data_loader import get_data
from src.ui import inject_css

st.set_page_config(page_title="Guide | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Guide - how to read every number")
st.caption("Plain definitions, how this app uses each term, and a worked example from today's data.")

# Live numbers for the worked example; fall back to static text if data missing.
try:
    _df = get_data()
    _pe_pos = _df.loc[_df["P/E"] > 0, "P/E"]
    _med_pe = float(_pe_pos.median())
    from src.analytics import _load_hist, _hist_context
    _hist = _load_hist("nifty_smallcap_250")
    _hist50 = _load_hist("nifty_50")
    _idx_pe = float((_df.loc[_df["P/E"] > 0, "Market Cap (Cr)"].fillna(0).sum()) / (_df.loc[_df["P/E"] > 0, "Market Cap (Cr)"].fillna(0) / _df.loc[_df["P/E"] > 0, "P/E"]).sum()) if len(_df.loc[_df["P/E"] > 0]) else _med_pe
    _ctx = _hist_context(_idx_pe, _hist, "PE") if _hist is not None else {"available": False}
    _peer_pe = float(_hist50["PE"].iloc[-1]) if _hist50 is not None and not _hist50.empty and "PE" in _hist50.columns else 22.1
    EXAMPLE = {
        "pe": f"{_idx_pe:.1f}x",
        "med_pe": f"{_med_pe:.1f}x",
        "hist_med": f"{_ctx.get('median_5y', 28.3):.1f}x" if _ctx.get("available") else "28.3x",
        "premium": f"{_ctx.get('premium_5y', 16):+.0f}%" if _ctx.get("available") else "+16%",
        "pct": f"{_ctx.get('pct_5y', 72):.0f}" if _ctx.get("available") else "72",
        "peer_pe": f"{_peer_pe:.1f}x",
        "peer_prem": f"{(_idx_pe/_peer_pe-1)*100:+.0f}%" if _peer_pe else "+16%",
    }
except Exception:
    EXAMPLE = {"pe": "25.7x", "med_pe": "28.4x", "hist_med": "28.3x", "premium": "+16%", "pct": "72", "peer_pe": "22.1x", "peer_prem": "+16%"}

E = EXAMPLE

with st.expander("Start here - how this app is organized", expanded=True):
    st.markdown(
        f"""
        CaptureMarket reads the **Nifty Smallcap 250** at three levels:

        - **Macro** - the whole universe in one screen: is it expensive, is it growing,
          and does growth justify valuations at your required return?
        - **Sectoral** - the same questions per sector, using *medians and distributions*
          (averages mislead when a few giants dominate).
        - **Micro** - each stock plotted against the whole universe. Quadrant boundaries
          are always computed on the **full 250-company universe**, so they never move
          when you filter.

        All numbers come from a **snapshot** (`python scripts/fetch_data.py` via yfinance),
        not live prices. Missing financials stay blank ("N/A") - never zero-filled.
        """
    )

with st.expander("The Market Verdict - the math behind the headline", expanded=True):
    st.markdown(
        f"""
        A P/E alone tells you nothing ("is 28x good?"). The Verdict compares **current vs own history and vs Nifty 50**.

        **Step 1 - Valuation vs own history (5Y).**
        Smallcap 250 at **{E['pe']}** (cap-weighted) vs 5Y median **{E['hist_med']}** ({E['premium']} premium, {E['pct']}th %ile). Expensive = >+20% premium or >80th %ile.

        **Step 2 - Valuation vs Nifty 50 (peer).**
        Smallcap **{E['pe']}** vs Nifty 50 **{E['peer_pe']}** ({E['peer_prem']} premium). Smallcaps usually trade at a modest premium to largecaps; >+25% without growth justification is stretched.

        **Step 3 - Growth intact?**
        Real growth = median EPS 3Y − {INFLATION:.0f}% inflation. Must be >0% and breadth not weak. Growth gates the valuation — cheap but stalling is still a wait.

        Verdicts: ✅ **PASS** (fair vs history + vs peer + growth intact) · ⚠️ **MIXED** (rich on one lens) · 🔻 **FAIL** (rich vs both or growth stalled).

        **Index basis.** Cap-weighted P/E = `sum(cap) / sum(cap / P/E)` — big names count more than median.
        """
    )

with st.expander("Valuation terms"):
    st.markdown(
        """
        - **P/E (price-to-earnings)** - price per share ÷ yearly profit per share.
          Higher = paying more per rupee of profit. Trailing basis; loss-makers have none.
        - **Median P/E / Index P/E** - median is the middle company (robust to 1000x outliers); Index P/E is cap-weighted `sum(cap)/sum(cap/P/E)`.
        - **P/B (price-to-book)** - price ÷ net worth per share. Key when profits are cyclical/negative (banks, metals). Shown alongside P/E everywhere.
        - **vs History** - current P/E/PB vs own 5Y median and percentile (80th+ = expensive, 30th- = cheap).
        - **vs Nifty 50** - same metrics for Nifty 50 (large-cap peer) — smallcap premium >25% is stretched without faster growth.
        """
    )

with st.expander("Quadrants (the map & tiles)"):
    st.markdown(
        """
        Every priced company is split at the **universe median P/E** (cheap/expensive)
        and **median EPS 3-yr growth** (growing/stalled):

        | | Cheap (below median P/E) | Expensive (above median) |
        |---|---|---|
        | **Growing EPS** | Growth + Value | Growth + Premium |
        | **Stalled EPS** | Value + Low Growth | Expensive + Low Growth |

        These are *relative* labels within smallcaps, not absolute judgments -
        "Value" here can still be expensive by large-cap standards.
        """
    )

with st.expander("Growth terms"):
    st.markdown(
        f"""
        - **Revenue growth (YoY)** - sales vs same quarter last year (trailing). Compare vs own 3Y median growth and vs Nifty 50 revenue breadth.
        - **Profit growth 1Y / 3Y** - net income YoY and 3-yr CAGR (needs both years profitable).
        - **EPS growth** - profit ÷ shares. Same vs-history and vs-peer lens as valuations.
        - **Breadth (% growing)** - share with data that rose — vs history breadth and vs Nifty 50 breadth.
        - **Nominal vs real** - subtract ~{INFLATION:.0f}% inflation: "+14% sales" ≈ "+9% real". Real growth is judged vs 0% and vs peer real growth.
        """
    )

with st.expander("Second-order context terms"):
    st.markdown(
        """
        - **Breadth (1Y positive)** - % of stocks with a positive 1-year return. Wide
          participation = healthy market; narrow = few winners carrying everything.
        - **Returns (1Y / 3Y / 5Y CAGR)** - compounded annual growth from past price to
          current price. History, not expectation - it contextualizes sentiment.
        - **Avg Daily Turnover** - value traded per day (₹ Cr, 252-day average).
          Below ~5 Cr/day = hard to exit in size.
        - **Top-10 weight** - share of total market cap in the 10 biggest names;
          measures concentration.
        """
    )

with st.expander("Assumptions in force right now"):
    st.markdown(
        f"""
        | Assumption | Value | Where used |
        |---|---|---|
        | Inflation anchor | {INFLATION:.0f}% | Nominal → real growth (EPS − infl) |
        | Overvalued threshold | +20% vs 5Y median / 80th %ile | Valuation vs history |
        | Peer premium threshold | +25% vs Nifty 50 | Valuation vs Nifty 50 |
        | History window | 5Y daily P/E,P/B (NSE, synthetic seed) | All vs-history verdicts |

        Change thresholds in `src/analytics.py` (`_hist_context` / `market_verdict`). History files: `data/index_pepb/nifty_*.csv` — will be replaced by live NSE fetch when available.
        """
    )
