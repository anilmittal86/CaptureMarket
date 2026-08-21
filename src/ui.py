"""Shared UI helpers: CSS theme injections and KPI card rendering."""
import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1400px;}
        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            height: 100%;
        }
        .kpi-label {font-size: 0.78rem; font-weight: 600; color: #64748B;
                   text-transform: uppercase; letter-spacing: 0.04em;}
        .kpi-value {font-size: 1.55rem; font-weight: 700; color: #0F172A; margin-top: 2px;}
        .kpi-sub {font-size: 0.8rem; color: #94A3B8; margin-top: 2px;}
        .pos {color: #16A34A;} .neg {color: #DC2626;}
        .quad-badge {
            display: inline-block; padding: 4px 12px; border-radius: 999px;
            font-size: 0.85rem; font-weight: 600; color: #FFFFFF;
        }
        .section-title {font-size: 1.05rem; font-weight: 700; color: #0F172A;
                        margin: 0.4rem 0 0.2rem 0;}
        div[data-testid="stDataFrame"] {border: 1px solid #E2E8F0; border-radius: 10px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "", value_class: str = "") -> None:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value {value_class}">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def sign_class(value: float) -> str:
    if value is None:
        return ""
    return "pos" if value > 0 else ("neg" if value < 0 else "")
