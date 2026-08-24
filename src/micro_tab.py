import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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

    for c in ["CMP", "50 DMA", "200 DMA", "OCF_PAT", "Net_Debt_EBITDA", "P/E", "P/B", "EPS Growth 3Y", "Revenue Growth", "ROCE", "ROE", "ROA", "1Y Return"]:
        if c not in df.columns:
            df[c] = np.nan
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

    quadrant_map = {
        "Growth + Value": "Q1 (Growth + Value)",
        "Growth + Premium": "Q2 (Growth + Premium)",
        "Value / Low Growth": "Q3 (Value / Low Growth)",
        "Expensive / Low Growth": "Q4 (Expensive / Low Growth)",
    }

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

        def _gt0(v):
            return pd.notna(v) and v > 0

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

    fig.add_trace(
        go.Scatter(
            x=df_valid["P/E"],
            y=df_valid["EPS Growth 3Y"],
            mode="markers",
            marker=dict(size=sizes, color=colors, line=dict(width=0.5, color="#333"), opacity=0.85),
            text=hover_parts,
            hoverinfo="text",
            name="Universe",
        )
    )

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
        fig.add_trace(
            go.Scatter(
                x=[sx],
                y=[sy],
                mode="markers",
                marker=dict(size=max(14, float(sizes.loc[selected_row.name]) if selected_row.name in sizes.index else 14) + 8, color=colors[df_valid.index.get_loc(selected_row.name)] if selected_row.name in df_valid.index else "#FFD54F", line=dict(color="black", width=3)),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Valuation vs Earnings Growth — Centered Quadrant Map",
        xaxis=dict(title="P/E (valuation)", type="log" if log_toggle else "linear", gridcolor="rgba(0,0,0,0.08)"),
        yaxis=dict(title="EPS Growth 3Y (%)", gridcolor="rgba(0,0,0,0.08)", zeroline=True, zerolinecolor="rgba(0,0,0,0.15)"),
        height=620,
        margin=dict(l=60, r=20, t=60, b=60),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.12),
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(f"Median P/E **{MEDIAN_PE:.1f}x** · Median EPS Growth 3Y **{MEDIAN_EPS_3Y:+.1f}%** · {len(df_valid)} / {len(df)} companies plotted (P/E > 0)")

    if selected_row is None:
        st.info("Select a stock above to see the 5-second decision cockpit.")
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

    if verdict == "HARD PASS":
        Q = 0.0
    else:
        Q = min(base_w * mult, 8.0)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### \U0001f3af When to Buy")
        st.markdown(f"**Archetype:** `{archetype}`")
        st.markdown(f"**Quadrant:** {quadrant if pd.notna(quadrant) else 'N/A'}")
        if is_bfsi_sel:
            pb_txt = f"{pb:.1f}x" if pd.notna(pb) else "N/A"
            pe_txt = f"{pe:.1f}x" if pd.notna(pe) else "N/A"
            st.markdown(f"**Valuation gate (BFSI):** P/E {pe_txt} · P/B {pb_txt}")
            roa_txt = f"{roa:.2f}%" if pd.notna(roa) else "N/A"
            st.markdown(f"**Fundamental gate (BFSI):** ROA {roa_txt} — {'✅' if _ge(roa, 1.3) else '⚠️ soft'}")
        else:
            peg_txt = f"{peg:.2f}" if pd.notna(peg) else "N/A"
            peg_ok = pd.notna(peg) and peg <= 1.5
            st.markdown(f"**Valuation gate:** PEG {peg_txt} — {'✅ fair' if peg_ok else '⚠️ stretched' if pd.notna(peg) else 'N/A'}")
            rev_txt = f"{rev:+.1f}%" if pd.notna(rev) else "N/A"
            st.markdown(f"**Fundamental gate:** Revenue growth {rev_txt} — {'✅' if pd.notna(rev) and rev >= 12 else '⚠️ needs >12%' if pd.notna(rev) else 'N/A'}")

        if pd.notna(cmp_v) and pd.notna(dma50):
            if cmp_v >= dma50:
                st.markdown(f"**Technical entry:** Trading **above 50 DMA** (₹{cmp_v:,.1f} vs ₹{dma50:,.1f}) ✅")
            else:
                st.markdown(f"**Technical entry:** Wait for breakout **above ₹{dma50:,.1f}** (CMP ₹{cmp_v:,.1f})")
        elif pd.notna(cmp_v):
            st.markdown(f"**Technical entry:** CMP ₹{cmp_v:,.1f} — 50 DMA N/A")
        else:
            st.markdown("**Technical entry:** CMP / 50 DMA N/A")

    with col2:
        st.markdown("#### \u2696\ufe0f How Much to Buy")
        st.metric(label="Target Allocation (Q)", value=f"{Q:.1f}%", delta=mult_label)
        st.caption(f"Base weight {base_w:.1f}% × multiplier {mult:.1f} — capped at 8.0%")
        if is_bfsi_sel:
            st.markdown(f"**ROA:** {roa:.2f}%" if pd.notna(roa) else "**ROA:** N/A")
            st.markdown(f"**ROE:** {roe:.1f}%" if pd.notna(roe) else "**ROE:** N/A")
        else:
            st.markdown(f"**ROCE:** {roce:.1f}%" if pd.notna(roce) else "**ROCE:** N/A")
            nd_txt = f"{netdebt:.2f}x" if pd.notna(netdebt) else "N/A"
            ocf_txt = f"{ocf:.2f}x" if pd.notna(ocf) else "N/A"
            st.markdown(f"**Net Debt/EBITDA:** {nd_txt}")
            st.markdown(f"**OCF / PAT:** {ocf_txt}")
        pe_pct = df.loc[selected_row.name, "PE_Percentile"] if "PE_Percentile" in df.columns and selected_row.name in df.index else np.nan
        eps_pct = df.loc[selected_row.name, "EPS_Percentile"] if "EPS_Percentile" in df.columns and selected_row.name in df.index else np.nan
        ret_pct = df.loc[selected_row.name, "Return_Percentile"] if "Return_Percentile" in df.columns and selected_row.name in df.index else np.nan
        st.markdown(f"**Percentiles (universe):** P/E {pe_pct:.0f}th · EPS {eps_pct:.0f}th · Return {ret_pct:.0f}th" if pd.notna(pe_pct) else "")

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
                st.markdown("**Technical trend:** Weekly close below 200 DMA (Core) — DMA N/A.")
        else:
            if pd.notna(dma50):
                st.markdown(f"**Technical trend:** Daily close **below 50 DMA** (₹{dma50:,.1f}).")
            else:
                st.markdown("**Technical trend:** Daily close below 50 DMA — DMA N/A.")
        if pd.notna(cmp_v):
            stop = cmp_v * 0.88
            st.markdown(f"**Capital loss floor:** Hard stop **₹{stop:,.1f}** (−12% from ₹{cmp_v:,.1f}).")
        else:
            st.markdown("**Capital loss floor:** −12% stop — CMP N/A.")
