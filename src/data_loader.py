"""Data loading and cleaning. Missing financial data is NEVER zero-filled."""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "nifty_smallcap_250_data.csv"

NUMERIC_COLUMNS = [
    "Market Cap (Cr)",
    "P/E",
    "EPS Growth 1Y (%)",
    "EPS Growth 3Y (%)",
    "Revenue Growth (%)",
    "ROCE (%)",
    "ROE (%)",
    "1Y Return (%)",
    "3Y CAGR (%)",
    "5Y CAGR (%)",
    "FII Holding Change (%)",
    "DII Holding Change (%)",
    "Avg Daily Turnover (Cr)",
]


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}. Run `python scripts/fetch_data.py` first."
        )
    df = pd.read_csv(path)
    present = [c for c in NUMERIC_COLUMNS if c in df.columns]
    for col in present:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[present] = df[present].replace([np.inf, -np.inf], np.nan)
    return df


@st.cache_data(ttl=600)
def get_data() -> pd.DataFrame:
    return load_data()
