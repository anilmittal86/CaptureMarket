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
    _ey = 100.0 / _med_pe
    _needed = REQUIRED_RETURN - _ey
    _eps3 = _df["EPS Growth 3Y (%)"].dropna()
    _actual = float(_eps3.median())
    _fair_pe = 100.0 / (REQUIRED_RETURN - _actual) if REQUIRED_RETURN > _actual else float("inf")
    EXAMPLE = {
        "pe": f"{_med_pe:.1f}x",
        "ey": f"{_ey:.1f}%",
        "needed": f"~{_needed:.1f}%/yr",
        "actual": f"{_actual:+.1f}%",
        "fair_pe": f"{_fair_pe:.1f}x",
    }
except Exception:
    EXAMPLE = {"pe": "28.4x", "ey": "3.5%", "needed": "~11.5%/yr", "actual": "+11.1%", "fair_pe": "25.6x"}

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
        A P/E ratio alone tells you nothing ("is 28x good?"). The Verdict answers the
        only question that matters: **can growth deliver the return you demand?**

        **Step 1 - Invert the price into an earnings yield.**
        At {E['pe']} median P/E, ₹100 of price buys ₹{E['ey'].rstrip('%')} of yearly profit,
        i.e. an earnings yield of **{E['ey']}** - vs **{RISK_FREE_RATE:.1f}% risk-free**
        in a 10-year Government of India bond (G-Sec). You accept half the risk-free return;
        growth must close the gap.

        **Step 2 - Convert your required return into needed growth.**

        `Expected return ≈ Earnings Yield + perpetual EPS growth`

        So to earn your assumed **{REQUIRED_RETURN:.0f}%**, EPS must compound at
        `{REQUIRED_RETURN:.0f}% − {E['ey']}` ≈ **{E['needed']} forever**.

        **Step 3 - Compare with actual growth.** The universe's real 3-yr EPS pace is
        **{E['actual']}**. Three outcomes:

        | Outcome | Meaning |
        |---|---|
        | ✅ Justified + margin of safety | Expected return beats your bar by ≥2 pp |
        | ⚠️ Fully priced | Within ±2 pp - zero cushion for disappointment |
        | 🔻 Doesn't justify | Shortfall >2 pp - growth must accelerate or prices fall |

        **Step 4 - Margin of safety as a fair P/E.**
        At actual growth, the P/E that exactly delivers {REQUIRED_RETURN:.0f}% is
        `100 ÷ ({REQUIRED_RETURN:.0f}% − {E['actual']})` = **{E['fair_pe']}**. Today's {E['pe']}
        vs fair {E['fair_pe']} tells you how much price excess (or cushion) you're carrying.
        """
    )

with st.expander("Valuation terms"):
    st.markdown(
        """
        - **P/E (price-to-earnings)** - price per share ÷ yearly profit per share.
          Higher = paying more per rupee of profit. Trailing basis; loss-makers have none.
        - **Median P/E** - the middle company's P/E. Used instead of the average because
          a few absurd multiples (1000x) would distort the mean.
        - **Earnings yield** - `1 ÷ P/E`. What the business earns you per year at today's
          price, before growth. The honest way to compare stocks against bonds.
        - **G-Sec (risk-free rate)** - 10-year Indian government bond yield. Money with
          zero credit risk; equity must beat it to justify the risk.
        - **Required return** - your personal hurdle ({rr}% here). Not observed data -
          an assumption, editable in `src/config.py`.
        - **P/B (price-to-book)** - price ÷ net worth per share. Useful when profits are
          cyclical or near zero (banks, capital-heavy firms).
        """.replace("{rr}", f"{REQUIRED_RETURN:.0f}")
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
        - **Revenue growth (YoY)** - sales vs the same quarter last year (yfinance trailing basis).
        - **Profit growth 1Y / 3Y** - net income latest fiscal year vs prior year, and its
          3-yr CAGR. Requires both years profitable (growth from a loss base is meaningless).
        - **EPS growth** - profit ÷ shares outstanding. Similar to profit growth but also
          moves with buybacks/issuance.
        - **Breadth (% growing)** - share of companies *with data* whose metric rose.
          Breadth says how widespread growth is; the median says how fast the typical grower is.
        - **Nominal vs real** - all figures are nominal rupees. Subtracting ~{INFLATION:.0f}%
          inflation gives *real* growth - the "+14% sales" you read is roughly "+9% real".
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
        | Risk-free (10Y G-Sec) | {RISK_FREE_RATE:.1f}% | Earnings-yield comparison, Verdict |
        | Required return | {REQUIRED_RETURN:.0f}% | Needed growth, margin of safety |
        | Inflation anchor | {INFLATION:.0f}% | Nominal → real conversions |
        | Equity premium | {EQUITY_PREMIUM:.0f} pp | Context for how demanding the hurdle is |

        Change these in `src/config.py`; every verdict updates on reload.
        Update the G-Sec value manually from RBI publications before major reviews.
        """
    )
