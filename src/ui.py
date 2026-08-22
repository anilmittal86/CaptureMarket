"""Shared UI helpers: CSS theme injections and KPI card rendering."""
import numpy as np
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
        .pos {color: #16A34A;} .neg {color: #DC2626;} .warn {color: #D97706;}
        .quad-badge {
            display: inline-block; padding: 4px 12px; border-radius: 999px;
            font-size: 0.85rem; font-weight: 600; color: #FFFFFF;
        }
        .insight-banner {
            border-radius: 8px; padding: 12px 16px; margin: 6px 0 14px 0;
            font-size: 0.95rem; color: #0F172A; line-height: 1.45;
        }
        .regime-pill {
            border-radius: 999px; padding: 6px 14px; font-size: 0.85rem;
            font-weight: 600; white-space: nowrap;
        }
        .section-title {font-size: 1.05rem; font-weight: 700; color: #0F172A;
                        margin: 0.4rem 0 0.2rem 0;}
        .verdict-banner {border-radius: 12px; padding: 16px 22px; margin: 2px 0 18px 0;
                         box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);}
        .verdict-headline {font-size: 1.3rem; font-weight: 800; letter-spacing: 0.01em;}
        .verdict-body {font-size: 0.95rem; color: #334155; margin-top: 6px; line-height: 1.55;}
        .hero-title {font-size: 0.85rem; font-weight: 700; color: #64748B;
                     text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;}
        .growth-row {display: flex; align-items: center; gap: 12px; margin: 9px 0;}
        .growth-row-label {width: 64px; font-weight: 700; font-size: 0.8rem; color: #475569;}
        .growth-row-meta {width: 240px; font-size: 0.82rem; color: #475569; line-height: 1.35;}
        .bar-track {flex: 1; height: 13px; background: #F1F5F9; border-radius: 7px; overflow: hidden;}
        .bar-fill {height: 100%; border-radius: 7px;}
        .muted-strip {display: flex; gap: 10px; flex-wrap: wrap; margin: 6px 0 14px 0;}
        .muted-card {background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;
                     padding: 8px 14px; font-size: 0.82rem; color: #64748B;}
        .muted-card b {color: #334155;}
        .quad-tile {border-radius: 12px; padding: 14px 16px; color: #FFFFFF; margin-bottom: 8px;
                    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.15);}
        .quad-count {font-size: 1.7rem; font-weight: 800; line-height: 1.1;}
        .quad-name {font-size: 0.85rem; font-weight: 600; opacity: 0.92;}
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


def cr_fmt(v: float) -> str:
    """Format market cap in Crores, switching to Lakh Crore when large."""
    lakh_cr = v / 1e5
    return f"{lakh_cr:,.1f} L Cr" if lakh_cr >= 1 else f"{v:,.0f} Cr"


_BANNER_TONES = {
    "pos": ("#DCFCE7", "#16A34A"),
    "neg": ("#FEE2E2", "#DC2626"),
    "warn": ("#FEF3C7", "#D97706"),
    "neutral": ("#EFF6FF", "#2563EB"),
}


def insight_banner(text: str, tone: str = "neutral") -> None:
    """Full-width callout that opens a section with a computed verdict."""
    bg, border = _BANNER_TONES.get(tone, _BANNER_TONES["neutral"])
    st.markdown(
        f'<div class="insight-banner" style="background:{bg};border-left:4px solid {border};">{text}</div>',
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, context: str = "", tone: str = "neutral") -> None:
    """KPI card where every number carries a context line and semantic tone."""
    value_class = {"pos": "pos", "neg": "neg", "warn": "warn"}.get(tone, "")
    sub_html = f'<div class="kpi-sub">{context}</div>' if context else ""
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


def regime_strip(verdicts: list) -> None:
    """Row of pills summarizing each lens: (lens, verdict, detail, tone)."""
    pills = ""
    for lens, verdict, detail, tone in verdicts:
        bg, fg = {
            "pos": ("#DCFCE7", "#166534"),
            "neg": ("#FEE2E2", "#991B1B"),
            "warn": ("#FEF3C7", "#92400E"),
            "neutral": ("#E2E8F0", "#334155"),
        }.get(tone, ("#E2E8F0", "#334155"))
        pills += (
            f'<span class="regime-pill" style="background:{bg};color:{fg};">'
            f'<span style="opacity:0.7;font-weight:500;">{lens}</span> &nbsp;{verdict}'
            f'<span style="opacity:0.65;font-weight:400;"> &nbsp;·&nbsp; {detail}</span></span>'
        )
    st.markdown(
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:2px 0 12px 0;">{pills}</div>',
        unsafe_allow_html=True,
    )


_VERDICT_ICONS = {"pos": "✅", "warn": "⚠️", "neg": "🔻"}


def verdict_banner(headline: str, body_html: str, foot_html: str, tone: str) -> None:
    """The Market Verdict block: does growth justify valuations, with MoS."""
    bg, border = _BANNER_TONES.get(tone, _BANNER_TONES["neutral"])
    icon = _VERDICT_ICONS.get(tone, "")
    st.markdown(
        f"""
        <div class="verdict-banner" style="background:{bg};border-left:6px solid {border};">
            <div class="verdict-headline" style="color:{border};">{icon} MARKET VERDICT — {headline}</div>
            <div class="verdict-body">{body_html}</div>
            <div class="verdict-body" style="margin-top:4px;"><b>{foot_html}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def growth_row(label: str, pos_pct: float, meta_html: str, tone: str) -> None:
    """One breadth bar: label | % growing bar | median + real-growth context."""
    color = {"pos": "#16A34A", "warn": "#D97706", "neg": "#DC2626"}.get(tone, "#94A3B8")
    val = float(pos_pct) if pos_pct is not None else np.nan
    pct = 0.0 if np.isnan(val) else max(0.0, min(100.0, val))
    st.markdown(
        f"""
        <div class="growth-row">
            <div class="growth-row-label">{label}</div>
            <div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{color};"></div></div>
            <div class="growth-row-meta"><b>{pct:.0f}%</b> growing · {meta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def muted_strip(items: list[tuple[str, str]]) -> None:
    """Second-order context: small muted cards of (title, value)."""
    cards = "".join(f'<span class="muted-card">{t}: <b>{v}</b></span>' for t, v in items)
    st.markdown(f'<div class="muted-strip">{cards}</div>', unsafe_allow_html=True)


def quad_tile(name: str, count: int, color: str, key: str) -> None:
    """Clickable quadrant tile that deep-links into the Micro map."""
    st.markdown(
        f"""
        <div class="quad-tile" style="background:{color};">
            <div class="quad-count">{count}</div>
            <div class="quad-name">{name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Explore →", key=key, use_container_width=True):
        st.session_state["micro_preset_quadrant"] = [name]
        try:
            st.switch_page("pages/3_Micro_Analysis.py")
        except Exception:
            pass  # non-app entry points cannot navigate; preset still applies
