"""CaptureMarket - home page and navigation hub."""
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.data_loader import DATA_PATH
from src.ui import inject_css

st.set_page_config(page_title="CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("CaptureMarket")
st.markdown(
    "Market analysis for the **Nifty Smallcap 250** universe across three levels: "
    "**Macro** (market-wide numbers), **Sectoral** (sector market map) and "
    "**Micro** (company-level bubble map)."
)

st.divider()

# --- data status ---------------------------------------------------------
if DATA_PATH.exists():
    df_mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime)
    try:
        from src.data_loader import get_data

        n_rows = len(get_data())
        st.success(f"Data loaded: **{n_rows} companies** | last refreshed {df_mtime:%d %b %Y, %H:%M}")
    except Exception as e:  # noqa: BLE001
        st.error(f"Data file exists but could not be loaded: {e}")
else:
    st.warning(
        "No data file found. Generate it first:\n"
        "```bash\npython scripts/fetch_data.py\n```\n"
        "This fetches all 250 constituents (~5-10 minutes)."
    )

st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### Macro Analysis")
    st.markdown(
        "Market-wide KPIs: median P/E, earnings growth, return distributions, "
        "and top/bottom performers."
    )
    st.page_link("pages/1_Macro_Analysis.py", label="Open Macro", icon=None)
with c2:
    st.markdown("#### Sectoral Analysis")
    st.markdown(
        "A quadrant market map of sectors (valuation vs growth), sector weights, "
        "and drill-down into any sector's companies."
    )
    st.page_link("pages/2_Sectoral_Analysis.py", label="Open Sectoral", icon=None)
with c3:
    st.markdown("#### Micro Analysis")
    st.markdown(
        "The full stock-level bubble map: valuation vs earnings growth, bubble size = "
        "|1Y return|, color = direction, with search, filters and percentiles."
    )
    st.page_link("pages/3_Micro_Analysis.py", label="Open Micro", icon=None)

st.divider()
st.caption("Data source: NSE Index Constituent list + Yahoo Finance. For research/education only.")
