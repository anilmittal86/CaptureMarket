import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from pathlib import Path


def render_micro_tab(df_universe: pd.DataFrame):
    if df_universe is None or df_universe.empty:
        st.warning("No universe data available.")
        return

    df = df_universe.copy()

    alias = {
        "EPS Growth 3Y": ["EPS Growth 3Y (%)"],
        "Revenue Growth": ["Revenue Growth (%)"],
        "1Y Return": ["1Y Return (%)"],
        "Market Cap": ["Market Cap (Cr)"],
        "ROCE": ["ROCE (%)"],
        "ROE": ["ROE (%)"],
        "ROA": ["ROA (%)"],
        "P/B": ["P/B"],
    }
    for spec, alts in alias.items():
        if spec not in df.columns:
            for a in alts:
                if a in df.columns:
                    df[spec] = df[a]
                    break
            else:
                if spec not in df.columns:
                    df[spec] = np.nan

    for c in ["CMP", "50 DMA", "200 DMA", "OCF_PAT", "Net_Debt_EBITDA", "Debt/Equity", "Current Ratio", "Interest Coverage", "P/E", "P/B", "EPS Growth 3Y", "Revenue Growth", "ROCE", "ROE", "ROA", "1Y Return"]:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["Profit Growth 1Y (%)", "Profit Growth 1Y"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["Company", "NSE Symbol", "Sector", "Industry"]:
        if c not in df.columns:
            df[c] = ""

    df_valid = df[df["P/E"] > 0].copy() if "P/E" in df.columns else df.iloc[0:0].copy()

    if df_valid.empty or df_valid["P/E"].notna().sum() == 0 or df_valid["EPS Growth 3Y"].notna().sum() == 0:
        st.warning("Insufficient valid P/E / EPS Growth 3Y data to build the quadrant map.")
        return

    MEDIAN_PE = float(df_valid["P/E"].median())
    MEDIAN_EPS_3Y = float(df_valid["EPS Growth 3Y"].median())

    def _assign_quadrant(row):
        pe = row.get("P/E")
        eps = row.get("EPS Growth 3Y")
        if pd.isna(pe) or pd.isna(eps):
            return np.nan
        if eps >= MEDIAN_EPS_3Y:
            return "Growth + Value" if pe < MEDIAN_PE else "Growth + Premium"
        else:
            return "Value / Low Growth" if pe < MEDIAN_PE else "Expensive / Low Growth"

    df["Quadrant"] = df.apply(_assign_quadrant, axis=1)
    df_valid["Quadrant"] = df_valid.apply(_assign_quadrant, axis=1)

    for col, new_col in [("P/E", "PE_Percentile"), ("EPS Growth 3Y", "EPS_Percentile"), ("1Y Return", "Return_Percentile")]:
        if col in df.columns:
            df[new_col] = df[col].rank(pct=True) * 100
            df_valid[new_col] = df_valid[col].rank(pct=True) * 100
        else:
            df[new_col] = np.nan

    df["PEG"] = np.where(
        (df["P/E"].notna()) & (df["EPS Growth 3Y"].notna()) & (df["EPS Growth 3Y"] > 0),
        df["P/E"] / df["EPS Growth 3Y"],
        np.nan,
    )

    def get_archetype_tag(row):
        sector = str(row.get("Sector", "")).lower()
        industry = str(row.get("Industry", "")).lower()
        combined = sector + " " + industry
        is_bfsi = any(k in combined for k in ["bank", "financial", "nbfc", "insurance", "housing"])
        pe = row.get("P/E")
        pb = row.get("P/B")
        roa = row.get("ROA")
        roe = row.get("ROE")
        roce = row.get("ROCE")
        rev = row.get("Revenue Growth")
        eps3 = row.get("EPS Growth 3Y")
        ocf = row.get("OCF_PAT")
        netdebt = row.get("Net_Debt_EBITDA")
        peg = row.get("PEG")

        if is_bfsi:
            if (pd.notna(roa) and 0 < roa < 1.10) or (pd.notna(roe) and 0 < roe < 10.0) or (pd.notna(pe) and pd.notna(pb) and pe > 25.0 and pb > 3.5):
                return "Multiple Compression Trap (BFSI)"
        else:
            peg_trap = pd.notna(peg) and peg > 2.5
            pe_eps_trap = pd.notna(pe) and pd.notna(eps3) and pe > 40.0 and eps3 < 15.0
            roce_trap = pd.notna(roce) and 0 < roce < 15.0
            debt_trap = pd.notna(netdebt) and netdebt > 1.5
            if peg_trap or pe_eps_trap or roce_trap or debt_trap:
                return "Multiple Compression Trap"

        if is_bfsi and pd.notna(roa) and pd.notna(roe) and pd.notna(pe):
            if roa >= 1.50 and roe >= 13.5 and pe <= 20.0:
                return "BFSI Quality Compounder"
        if is_bfsi and pd.notna(pe) and pd.notna(roa):
            if pe < 16.0 and roa >= 1.30:
                return "BFSI Deep Value"

        if pd.notna(pe) and pd.notna(rev) and pd.notna(roce):
            if pe > 45.0 and rev >= 25.0 and roce >= 18.0:
                return "Hyper-Growth Momentum"

        if not is_bfsi and pd.notna(roce):
            peg_ok = pd.notna(peg) and peg <= 1.50
            roce_ok = roce >= 20.0
            ocf_ok = pd.isna(ocf) or ocf == 0 or (pd.notna(ocf) and ocf >= 0.70)
            if peg_ok and roce_ok and ocf_ok:
                return "Core Quality Compounder"

        if pd.notna(pe) and pd.notna(roce) and pd.notna(rev):
            if pe < 20.0 and roce >= 15.0 and rev >= 12.0:
                return "Tactical Value Turnaround"

        return "Watchlist / Neutral"

    df["Archetype"] = df.apply(get_archetype_tag, axis=1)
    df_valid["Archetype"] = df_valid.apply(get_archetype_tag, axis=1)

    c1, c2 = st.columns([3, 1])
    with c2:
        log_toggle = st.toggle("Log P/E scale", value=False)

    label_col = "Company" if "Company" in df_valid.columns else df_valid.columns[0]
    symbol_col = "NSE Symbol" if "NSE Symbol" in df_valid.columns else label_col
    df["_label"] = df[label_col].astype(str) + " (" + df[symbol_col].astype(str) + ")"
    df_valid["_label"] = df_valid[label_col].astype(str) + " (" + df_valid[symbol_col].astype(str) + ")"
    options = ["-- Select a stock --"] + sorted(df_valid["_label"].dropna().unique().tolist())
    selected_label = st.selectbox("Search and select a stock", options, index=0)

    selected_row = None
    if selected_label != "-- Select a stock --":
        sel = df[df["_label"] == selected_label]
        if not sel.empty:
            selected_row = sel.iloc[0]
        else:
            sel = df_valid[df_valid["_label"] == selected_label]
            if not sel.empty:
                selected_row = sel.iloc[0]

    sizes = df_valid["1Y Return"].abs().fillna(10).clip(8, 80)

    def _color(v):
        if pd.isna(v):
            return "#9E9E9E"
        return "#4CAF50" if v >= 0 else "#EF5350"

    colors = df_valid["1Y Return"].apply(_color).tolist()

    hover_parts = []
    for _, r in df_valid.iterrows():
        parts = []
        for lbl, col, fmt in [
            ("Company", "Company", None),
            ("Symbol", "NSE Symbol", None),
            ("P/E", "P/E", "{:.1f}x"),
            ("P/B", "P/B", "{:.1f}x"),
            ("EPS 3Y", "EPS Growth 3Y", "{:+.1f}%"),
            ("Revenue", "Revenue Growth", "{:+.1f}%"),
            ("ROCE", "ROCE", "{:.1f}%"),
            ("ROE", "ROE", "{:.1f}%"),
            ("1Y Ret", "1Y Return", "{:+.1f}%"),
            ("Quadrant", "Quadrant", None),
            ("Archetype", "Archetype", None),
        ]:
            v = r.get(col)
            if pd.isna(v) or v == "":
                continue
            try:
                txt = fmt.format(v) if fmt else str(v)
            except Exception:
                txt = str(v)
            parts.append(f"{lbl}: {txt}")
        hover_parts.append("<br>".join(parts))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_valid["P/E"], y=df_valid["EPS Growth 3Y"], mode="markers", marker=dict(size=sizes, color=colors, line=dict(width=0.5, color="#333"), opacity=0.85), text=hover_parts, hoverinfo="text", name="Universe"))
    fig.add_shape(type="line", x0=MEDIAN_PE, x1=MEDIAN_PE, y0=df_valid["EPS Growth 3Y"].min(), y1=df_valid["EPS Growth 3Y"].max(), line=dict(color="#1f77b4", width=1.5, dash="dash"))
    fig.add_shape(type="line", x0=df_valid["P/E"].min(), x1=df_valid["P/E"].max(), y0=MEDIAN_EPS_3Y, y1=MEDIAN_EPS_3Y, line=dict(color="#1f77b4", width=1.5, dash="dash"))
    fig.add_annotation(xref="paper", yref="paper", x=0.25, y=0.95, showarrow=False, text="<b>Q1 GROWTH + VALUE</b><br>High EPS Growth \u2022 Low P/E", font=dict(size=10, color="#1a1a1a"), bgcolor="rgba(255,255,255,0.7)", borderpad=4, align="center")
    fig.add_annotation(xref="paper", yref="paper", x=0.75, y=0.95, showarrow=False, text="<b>Q2 GROWTH + PREMIUM</b><br>High EPS Growth \u2022 High P/E", font=dict(size=10, color="#1a1a1a"), bgcolor="rgba(255,255,255,0.7)", borderpad=4, align="center")
    fig.add_annotation(xref="paper", yref="paper", x=0.25, y=0.05, showarrow=False, text="<b>Q3 VALUE / LOW GROWTH</b><br>Low EPS Growth \u2022 Low P/E", font=dict(size=10, color="#1a1a1a"), bgcolor="rgba(255,255,255,0.7)", borderpad=4, align="center")
    fig.add_annotation(xref="paper", yref="paper", x=0.75, y=0.05, showarrow=False, text="<b>Q4 EXPENSIVE / LOW GROWTH</b><br>Low EPS Growth \u2022 High P/E", font=dict(size=10, color="#1a1a1a"), bgcolor="rgba(255,255,255,0.7)", borderpad=4, align="center")
    if selected_row is not None and pd.notna(selected_row.get("P/E")) and pd.notna(selected_row.get("EPS Growth 3Y")):
        sx = float(selected_row["P/E"])
        sy = float(selected_row["EPS Growth 3Y"])
        xmin = float(df_valid["P/E"].min())
        ymin = float(df_valid["EPS Growth 3Y"].min())
        fig.add_shape(type="line", x0=xmin, x1=sx, y0=sy, y1=sy, line=dict(color="black", width=1, dash="dot"))
        fig.add_shape(type="line", x0=sx, x1=sx, y0=ymin, y1=sy, line=dict(color="black", width=1, dash="dot"))
        fig.add_trace(go.Scatter(x=[sx], y=[sy], mode="markers", marker=dict(size=max(14, float(sizes.loc[selected_row.name]) if selected_row.name in sizes.index else 14) + 8, color=colors[df_valid.index.get_loc(selected_row.name)] if selected_row.name in df_valid.index else "#FFD54F", line=dict(color="black", width=3)), hoverinfo="skip", showlegend=False))

    fig.update_layout(title="Valuation vs Earnings Growth — Centered Quadrant Map", xaxis=dict(title="P/E (valuation)", type="log" if log_toggle else "linear", gridcolor="rgba(0,0,0,0.08)"), yaxis=dict(title="EPS Growth 3Y (%)", gridcolor="rgba(0,0,0,0.08)", zeroline=True, zerolinecolor="rgba(0,0,0,0.15)"), height=620, margin=dict(l=60, r=20, t=60, b=60), plot_bgcolor="#FAFAFA", paper_bgcolor="white", legend=dict(orientation="h", y=-0.12))
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Median P/E **{MEDIAN_PE:.1f}x** · Median EPS Growth 3Y **{MEDIAN_EPS_3Y:+.1f}%** · {len(df_valid)} / {len(df)} companies plotted (P/E > 0)")

    if selected_row is None:
        st.info("Select a stock above to see the 5-second decision cockpit.")
        try:
            from src.data_loader import DATA_PATH
            if DATA_PATH.exists():
                mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%d %b %Y, %H:%M")
                st.caption(f"Data snapshot: **{mtime}** · Source: Nifty Smallcap 250 constituents via **NSE India** + fundamentals via **Yahoo Finance (yfinance)**. Snapshot: `data/nifty_smallcap_250_data.csv` generated by `scripts/fetch_data.py`.")
            else:
                st.caption("Source: Nifty Smallcap 250 via NSE India + Yahoo Finance. No snapshot file found.")
        except Exception:
            pass
        st.caption("**N/A** = field not present in the current snapshot or not calculable (e.g., `CMP`/`50 DMA`/`200 DMA` need price history; `OCF_PAT`/`Net_Debt_EBITDA`/`ROA` need cash-flow/balance-sheet fields not yet ingested). Profitability fields `ROCE`/`ROE` are available for most of the universe; a specific stock may still be — if its source data was missing.")
        return

    archetype = str(selected_row.get("Archetype", "Watchlist / Neutral"))
    pe = selected_row.get("P/E")
    pb = selected_row.get("P/B")
    roa = selected_row.get("ROA")
    roe = selected_row.get("ROE")
    roce = selected_row.get("ROCE")
    rev = selected_row.get("Revenue Growth")
    eps3 = selected_row.get("EPS Growth 3Y")
    ocf = selected_row.get("OCF_PAT")
    netdebt = selected_row.get("Net_Debt_EBITDA")
    peg = selected_row.get("PEG")
    cmp_v = selected_row.get("CMP")
    dma50 = selected_row.get("50 DMA")
    dma200 = selected_row.get("200 DMA")
    quadrant = selected_row.get("Quadrant")

    if "Trap" in archetype:
        st.error("VERDICT: HARD PASS — Multiple Compression Trap / Weak Solvency")
        verdict = "HARD PASS"
    elif "Quality Compounder" in archetype:
        st.success("VERDICT: CORE BUY — High Capital Efficiency Compounder at Fair Valuation")
        verdict = "CORE BUY"
    elif "Hyper-Growth" in archetype or "Turnaround" in archetype:
        st.success("VERDICT: TACTICAL BUY — Operational Momentum Intact")
        verdict = "TACTICAL BUY"
    else:
        st.warning("VERDICT: WATCHLIST / WAIT — Awaiting Topline Acceleration or Base Breakout")
        verdict = "WATCHLIST"

    if pd.notna(pe):
        if pe < 25:
            base_w = 6.0
        elif pe <= 45:
            base_w = 4.5
        else:
            base_w = 3.0
    else:
        base_w = 4.5

    sector_str = str(selected_row.get("Sector", "")).lower() + " " + str(selected_row.get("Industry", "")).lower()
    is_bfsi_sel = any(k in sector_str for k in ["bank", "financial", "nbfc", "insurance", "housing"])

    def _ge(v, t):
        return pd.notna(v) and v >= t

    def _le(v, t):
        return pd.notna(v) and v <= t

    quality_boost = False
    if is_bfsi_sel and _ge(roa, 1.7) and _ge(roe, 15):
        quality_boost = True
    if not is_bfsi_sel and _ge(ocf, 0.8) and _le(netdebt, 0.3) and _ge(roce, 22):
        quality_boost = True

    soft_flag = False
    if (pd.notna(ocf) and ocf < 0.6) or (pd.notna(netdebt) and netdebt > 0.8) or (pd.notna(roa) and roa < 1.3):
        soft_flag = True

    if quality_boost:
        mult = 1.2
        mult_label = "1.2x (high quality)"
    elif soft_flag:
        mult = 0.7
        mult_label = "0.7x (soft fundamentals)"
    else:
        mult = 1.0
        mult_label = "1.0x (baseline)"

    prospective_Q = 0.0 if verdict == "HARD PASS" else min(base_w * mult, 8.0)
    active_Q = 0.0 if verdict in ("HARD PASS", "WATCHLIST") else prospective_Q

    col1, col2, col3 = st.columns(3)

    def _na_note(col_name):
        return f"— (not in current snapshot — requires `{col_name}`)"

    def _val_badge(v, good, warn_thr=None, invert=False):
        if pd.isna(v):
            return "—"
        if invert:
            return "\u2705" if v <= good else ("\u26a0\ufe0f" if warn_thr is None or v <= warn_thr else "\U0001f534")
        else:
            return "\u2705" if v >= good else ("\u26a0\ufe0f" if warn_thr is not None and v >= warn_thr else "\U0001f534")

    profit = selected_row.get("Profit Growth 1Y (%)") if "Profit Growth 1Y (%)" in df.columns else selected_row.get("Profit Growth 1Y")
    if pd.isna(profit) and "Profit Growth 1Y (%)" not in df.columns:
        profit = np.nan
    debt_eq = selected_row.get("Debt/Equity")
    curr_ratio = selected_row.get("Current Ratio")
    int_cov = selected_row.get("Interest Coverage")

    with col1:
        st.markdown("#### \U0001f3af Whether to Buy")
        st.markdown(f"**Quadrant:** {quadrant if pd.notna(quadrant) else 'N/A'}  ·  *invariant vs full universe*")
        st.markdown("**Valuations**")
        v1, v2, v3 = st.columns(3)
        with v1:
            pe_txt = f"{pe:.1f}x" if pd.notna(pe) else "—"
            pe_hint = "P/E" + (" \u2705 (<25x)" if pd.notna(pe) and pe < 25 else " \u26a0\ufe0f (25-45x)" if pd.notna(pe) and pe <= 45 else " \U0001f534 (>45x)" if pd.notna(pe) else "")
            st.metric("P/E", pe_txt, delta=pe_hint, delta_color="off")
            st.caption("Price ÷ Earnings")
        with v2:
            pb_txt = f"{pb:.1f}x" if pd.notna(pb) else "—"
            pb_hint = "P/B" + (" \u2705 (<3.5x)" if pd.notna(pb) and pb < 3.5 else " \U0001f534 (>3.5x)" if pd.notna(pb) else "")
            st.metric("P/B", pb_txt, delta=pb_hint, delta_color="off")
            st.caption("Price ÷ Book")
        with v3:
            peg_txt = f"{peg:.2f}" if pd.notna(peg) else "—"
            peg_hint = "PEG" + (" \u2705 (≤1.5)" if pd.notna(peg) and peg <= 1.5 else " \u26a0\ufe0f (>1.5)" if pd.notna(peg) and peg > 1.5 else " (needs P/E & EPS 3Y)")
            st.metric("PEG", peg_txt, delta=peg_hint, delta_color="off")
            st.caption("P/E ÷ EPS 3Y")

        st.markdown("**Growth**")
        g1, g2, g3 = st.columns(3)
        with g1:
            eps_txt = f"{eps3:+.1f}%" if pd.notna(eps3) else "—"
            st.metric("EPS 3Y CAGR", eps_txt, delta=("\u2705" if pd.notna(eps3) and eps3 >= 15 else "\u26a0\ufe0f" if pd.notna(eps3) else ""))
            st.caption("EPS Growth 3Y")
        with g2:
            rev_txt = f"{rev:+.1f}%" if pd.notna(rev) else "—"
            st.metric("Revenue YoY", rev_txt, delta=("\u2705 ≥12%" if pd.notna(rev) and rev >= 12 else "\U0001f534 <12%" if pd.notna(rev) else ""))
            st.caption("from `Revenue Growth (%)`")
        with g3:
            prof_txt = f"{profit:+.1f}%" if pd.notna(profit) else "—"
            st.metric("Profit YoY", prof_txt, delta=("\u2705" if pd.notna(profit) and profit > 0 else "\u26a0\ufe0f" if pd.notna(profit) else ""))
            st.caption("Profit Growth 1Y")

        st.markdown("**Solvency & Risk**  ·  *industry-aware*")
        if is_bfsi_sel:
            s1, s2, s3 = st.columns(3)
            with s1:
                roa_txt = f"{roa:.2f}%" if pd.notna(roa) else "—"
                roa_delta = "\u2705 ≥1.5% (strong)" if pd.notna(roa) and roa >= 1.5 else "\u26a0\ufe0f <1.1% trap" if pd.notna(roa) and roa < 1.1 else "\u2705 ≥1.3% ok" if pd.notna(roa) else "needs ROA"
                st.metric("ROA", roa_txt, delta=roa_delta, delta_color="off")
                st.caption("Return on Assets")
            with s2:
                de_txt = f"{debt_eq:.2f}x" if pd.notna(debt_eq) else "—"
                de_delta = "\u2705 ≤1.0x" if pd.notna(debt_eq) and debt_eq <= 1.0 else "\u26a0\ufe0f >1.5x" if pd.notna(debt_eq) else "—"
                st.metric("Debt/Equity", de_txt, delta=de_delta, delta_color="off")
                st.caption("Leverage")
            with s3:
                cr_txt = f"{curr_ratio:.2f}x" if pd.notna(curr_ratio) else "—"
                cr_delta = "\u2705 ≥1.5x" if pd.notna(curr_ratio) and curr_ratio >= 1.5 else "\u26a0\ufe0f <1.2x" if pd.notna(curr_ratio) else "—"
                st.metric("Current Ratio", cr_txt, delta=cr_delta, delta_color="off")
                st.caption("Liquidity")
        else:
            s1, s2, s3 = st.columns(3)
            with s1:
                de_txt = f"{debt_eq:.2f}x" if pd.notna(debt_eq) else "—"
                de_delta = "\u2705 ≤0.5x" if pd.notna(debt_eq) and debt_eq <= 0.5 else "\u2705 ≤1.0x" if pd.notna(debt_eq) and debt_eq <= 1.0 else "\U0001f534 >1.5x" if pd.notna(debt_eq) else "needs Debt/Equity"
                st.metric("Debt/Equity", de_txt, delta=de_delta, delta_color="off")
                st.caption("Leverage")
            with s2:
                nd_txt = f"{netdebt:.2f}x" if pd.notna(netdebt) else "—"
                nd_delta = "\u2705 ≤1.5x safe" if pd.notna(netdebt) and netdebt <= 1.5 else "\U0001f534 >1.5x stressed" if pd.notna(netdebt) else "needs Net Debt/EBITDA"
                st.metric("Net Debt/EBITDA", nd_txt, delta=nd_delta, delta_color="off")
                st.caption("Solvency")
            with s3:
                ic_txt = f"{int_cov:.1f}x" if pd.notna(int_cov) else "—"
                ic_delta = "\u2705 ≥3.0x" if pd.notna(int_cov) and int_cov >= 3 else "\u26a0\ufe0f <2.0x" if pd.notna(int_cov) else "needs Interest Coverage"
                if pd.isna(int_cov) and pd.notna(curr_ratio):
                    ic_txt = f"{curr_ratio:.2f}x"
                    ic_delta = "\u2705 ≥1.5x" if curr_ratio >= 1.5 else "\u26a0\ufe0f <1.2x"
                    st.metric("Current Ratio", ic_txt, delta=ic_delta, delta_color="off")
                    st.caption("Liquidity (fallback)")
                else:
                    st.metric("Interest Coverage", ic_txt, delta=ic_delta, delta_color="off")
                    st.caption("EBIT ÷ Interest")

        st.markdown("**Technical entry**")
        if pd.notna(cmp_v) and pd.notna(dma50):
            if cmp_v >= dma50:
                st.success(f"Above 50 DMA — CMP ₹{cmp_v:,.1f} vs 50 DMA ₹{dma50:,.1f} \u2705")
            else:
                st.warning(f"Below 50 DMA — wait for breakout above ₹{dma50:,.1f} (CMP ₹{cmp_v:,.1f})")
            if pd.notna(dma200):
                st.caption(f"200 DMA ₹{dma200:,.1f} · {'above' if cmp_v >= dma200 else 'below'} long trend")
        elif pd.notna(cmp_v):
            st.info(f"CMP ₹{cmp_v:,.1f} — 50 DMA {_na_note('50 DMA')}")
            st.caption("50 DMA not in current snapshot — requires price history.")
        elif pd.notna(dma50):
            st.info(f"50 DMA ₹{dma50:,.1f} — CMP {_na_note('CMP')}")
        else:
            st.warning("CMP / 50 DMA — not in current snapshot")
            st.caption("**N/A** = field absent from `data/nifty_smallcap_250_data.csv`. CMP and DMA need daily price history; now auto-fetched for new snapshots — re-run `python scripts/fetch_data.py` and reload.")

    with col2:
        st.markdown("#### \u2696\ufe0f How Much to Buy")
        if verdict in ("HARD PASS", "WATCHLIST"):
            st.metric(label="Active Allocation", value="0.0%", delta="On hold — awaiting confirmation / no buy")
            st.markdown(f"**Target on confirmation:** **{prospective_Q:.1f}%** (Base {base_w:.1f}% × {mult_label} → capped at 8.0%)")
            st.caption("Sizing is prospective only until the verdict flips to BUY.")
        else:
            st.metric(label="Target Allocation (Q)", value=f"{prospective_Q:.1f}%", delta=mult_label)
            st.caption(f"Base weight {base_w:.1f}% × multiplier {mult:.1f} — capped at 8.0%")
        missing_core = []
        if pd.isna(roce):
            missing_core.append("ROCE")
        if pd.isna(netdebt):
            missing_core.append("Net_Debt_EBITDA")
        if pd.isna(ocf):
            missing_core.append("OCF_PAT")
        if pd.isna(roa):
            missing_core.append("ROA")
        if is_bfsi_sel:
            st.markdown(f"**ROA:** {roa:.2f}%" if pd.notna(roa) else f"**ROA:** {_na_note('ROA')}")
            st.markdown(f"**ROE:** {roe:.1f}%" if pd.notna(roe) else f"**ROE:** {_na_note('ROE')}")
        else:
            if pd.notna(roce):
                st.markdown(f"**ROCE:** {roce:.1f}%")
            else:
                st.markdown(f"**ROCE:** {_na_note('ROCE (%) — this stock has no ROCE in Yahoo snapshot')}")
            nd_txt = f"{netdebt:.2f}x" if pd.notna(netdebt) else _na_note("Net_Debt_EBITDA — requires balance-sheet debt & EBITDA")
            ocf_txt = f"{ocf:.2f}x" if pd.notna(ocf) else _na_note("OCF_PAT — requires cash-flow statement")
            st.markdown(f"**Net Debt/EBITDA:** {nd_txt}")
            st.markdown(f"**OCF / PAT:** {ocf_txt}")
        if missing_core:
            st.caption(f"Note: {', '.join(missing_core)} not in current snapshot — quality multiplier falls back to baseline/excludes those checks. Extend `scripts/fetch_data.py` to ingest them.")
        pe_pct = df.loc[selected_row.name, "PE_Percentile"] if "PE_Percentile" in df.columns and selected_row.name in df.index else np.nan
        eps_pct = df.loc[selected_row.name, "EPS_Percentile"] if "EPS_Percentile" in df.columns and selected_row.name in df.index else np.nan
        ret_pct = df.loc[selected_row.name, "Return_Percentile"] if "Return_Percentile" in df.columns and selected_row.name in df.index else np.nan
        st.markdown(f"**Percentiles (universe, invariant):** P/E {pe_pct:.0f}th · EPS {eps_pct:.0f}th · Return {ret_pct:.0f}th" if pd.notna(pe_pct) else "")

    with col3:
        st.markdown("#### \U0001f6d1 When to Exit (Invalidation Rules)")
        if is_bfsi_sel:
            st.markdown("**Fundamental:** ROA < **1.40%** or ROE breakdown / margin compression.")
        else:
            st.markdown("**Fundamental:** YoY Revenue/EPS growth **<10%** for 2 consecutive quarters OR EBITDA margin drop **>200 bps**.")
        if verdict == "CORE BUY":
            dma_ref = dma200 if pd.notna(dma200) else dma50
            dma_lbl = "200 DMA" if pd.notna(dma200) else "50 DMA"
            if pd.notna(dma_ref):
                st.markdown(f"**Technical trend:** Weekly close **below {dma_lbl}** (₹{dma_ref:,.1f}).")
            else:
                st.markdown("**Technical trend:** Weekly close below 200 DMA (Core) — DMA N/A (no DMA in snapshot).")
        else:
            if pd.notna(dma50):
                st.markdown(f"**Technical trend:** Daily close **below 50 DMA** (₹{dma50:,.1f}).")
            else:
                st.markdown("**Technical trend:** Daily close below 50 DMA — DMA not in snapshot.")
        if pd.notna(cmp_v):
            stop = cmp_v * 0.88
            st.markdown(f"**Capital loss floor:** Hard stop **₹{stop:,.1f}** (−12% from ₹{cmp_v:,.1f}).")
        else:
            st.markdown("**Capital loss floor:** −12% from CMP — CMP not in current snapshot, hard stop unavailable.")

    st.divider()
    try:
        from src.data_loader import DATA_PATH
        if DATA_PATH.exists():
            mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%d %b %Y, %H:%M")
            st.caption(f"Data as of **{mtime}** · Universe **Nifty Smallcap 250** via **NSE India** (`niftyindices.com`) + fundamentals via **Yahoo Finance (`yfinance`)** · File `data/nifty_smallcap_250_data.csv` · Generated by `scripts/fetch_data.py` · Medians/percentiles are invariant (full valid universe, not filtered view).")
        else:
            st.caption("Source: Nifty Smallcap 250 via NSE India + Yahoo Finance. No local snapshot file found.")
    except Exception:
        st.caption("Source: Nifty Smallcap 250 via NSE India + Yahoo Finance.")
    st.caption("**N/A / —** = field not present in the current snapshot. Available snapshot columns: `Market Cap (Cr)`, `P/E`, `P/B`, `EPS Growth 1Y/3Y (%)`, `Profit Growth 1Y/3Y (%)`, `Revenue Growth (%)`, `ROCE (%)`, `ROE (%)`, `1Y/3Y/5Y Returns`. Not yet ingested: `ROA`, `OCF_PAT`, `Net_Debt_EBITDA`, `CMP`, `50/200 DMA` — extend the fetch script to enable those gates.")
