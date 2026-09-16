"""Micro Analysis: self-contained invariant quadrant cockpit."""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_loader import get_data
from src.micro_tab import render_micro_tab
from src.ui import inject_css

st.set_page_config(page_title="Micro | CaptureMarket", page_icon=None, layout="wide")
inject_css()

st.title("Micro Analysis")
st.caption("Invariant universe medians · archetype engine · centered quadrant map · 5-second decision cockpit.")

try:
    df = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

if "micro_preset_quadrant" in st.session_state:
    preset = st.session_state.get("micro_preset_quadrant")
    if preset:
        st.info(f"Deep-linked quadrant filter from Macro: {', '.join(preset)} — table below is pre-filtered; clear the multiselect to see all quadrants.")

render_micro_tab(df)
