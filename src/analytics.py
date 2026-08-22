"""Analytics layer: universe statistics, quadrants, percentiles, summaries.

All universe-level statistics (medians, percentiles) are computed on the FULL
stock universe and must remain unaffected by any user-applied filters.
"""
import numpy as np
import pandas as pd

from src.config import INFLATION, REQUIRED_RETURN, RISK_FREE_RATE

PE_COL = "P/E"
PB_COL = "P/B"
EPS_G3_COL = "EPS Growth 3Y (%)"
PROFIT_G1_COL = "Profit Growth 1Y (%)"
PROFIT_G3_COL = "Profit Growth 3Y (%)"
REV_G_COL = "Revenue Growth (%)"

QUADRANTS = [
    "Growth + Value",
    "Growth + Premium",
    "Value + Low Growth",
    "Expensive + Low Growth",
]

QUADRANT_COLORS = {
    "Growth + Value": "#16A34A",
    "Growth + Premium": "#2563EB",
    "Value + Low Growth": "#CA8A04",
    "Expensive + Low Growth": "#DC2626",
}


def universe_medians(df: pd.DataFrame, x_col: str, y_col: str) -> tuple[float, float]:
    valid = df[[x_col, y_col]].dropna()
    return float(valid[x_col].median()), float(valid[y_col].median())


def assign_quadrants(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    med_x: float | None = None,
    med_y: float | None = None,
) -> pd.Series:
    """Quadrant per row using FULL-universe medians (pass them in explicitly)."""
    if med_x is None or med_y is None:
        med_x, med_y = universe_medians(df, x_col, y_col)

    def quadrant(x, y) -> str:
        if pd.isna(x) or pd.isna(y):
            return np.nan
        if y >= med_y:
            return "Growth + Value" if x < med_x else "Growth + Premium"
        return "Value + Low Growth" if x < med_x else "Expensive + Low Growth"

    return df.apply(lambda r: quadrant(r[x_col], r[y_col]), axis=1)


def percentile_rank(full_series: pd.Series, value) -> float | None:
    """Percentile of `value` within the complete universe (0-100)."""
    s = pd.Series(full_series).dropna()
    if s.empty or value is None or pd.isna(value):
        return None
    return float((s < value).mean() * 100)


def scale_bubble_sizes(values: pd.Series, min_size: float = 7.0, max_size: float = 58.0) -> pd.Series:
    """Scale magnitude of returns (or any metric) to marker sizes.

    Sign is ignored (magnitude only); missing values get the minimum size.
    """
    v = pd.Series(values, dtype=float).abs().fillna(0)
    lo, hi = float(v.min()), float(v.max())
    if hi == lo:
        return pd.Series(np.full(len(v), (min_size + max_size) / 2), index=v.index)
    return min_size + (v - lo) / (hi - lo) * (max_size - min_size)


def macro_summary(df: pd.DataFrame) -> dict:
    ret_1y = df["1Y Return (%)"]
    return {
        "universe_size": int(len(df)),
        "plotted_pe": int(df["P/E"].notna().sum()),
        "total_mktcap_cr": float(df["Market Cap (Cr)"].sum()),
        "median_pe": float(df["P/E"].median()),
        "median_eps_g3": float(df["EPS Growth 3Y (%)"].median()),
        "avg_ret_1y": float(ret_1y.mean()),
        "median_ret_1y": float(ret_1y.median()),
        "pct_positive_1y": float((ret_1y > 0).mean() * 100),
        "pct_negative_1y": float((ret_1y < 0).mean() * 100),
        "avg_ret_3y": float(df["3Y CAGR (%)"].mean()),
        "avg_ret_5y": float(df["5Y CAGR (%)"].mean()),
    }


def sector_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-sector stats built on MEDIANS and breadth - averages are misleading
    when intra-sector return dispersion is wide."""
    g = df.groupby("Sector", dropna=False)

    def iqr(s: pd.Series) -> float:
        return float(s.quantile(0.75) - s.quantile(0.25)) if s.notna().any() else np.nan

    out = pd.DataFrame(
        {
            "Companies": g.size(),
            "Market Cap (Cr)": g["Market Cap (Cr)"].sum(),
            "Median P/E": g["P/E"].median(),
            "Median EPS Growth 3Y (%)": g["EPS Growth 3Y (%)"].median(),
            "Median 1Y Return (%)": g["1Y Return (%)"].median(),
            "% Positive (1Y)": g["1Y Return (%)"].apply(lambda s: (s > 0).mean() * 100 if s.notna().any() else np.nan),
            "1Y Return IQR (pp)": g["1Y Return (%)"].apply(iqr),
        }
    )
    total_cap = out["Market Cap (Cr)"].sum()
    out["Weight (%)"] = out["Market Cap (Cr)"] / total_cap * 100 if total_cap else np.nan
    return out.sort_values("Median 1Y Return (%)", ascending=False)


def quadrant_summary(df_plotted: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q in QUADRANTS:
        sub = df_plotted[df_plotted["Quadrant"] == q]
        rows.append(
            {
                "Quadrant": q,
                "Companies": int(len(sub)),
                "Avg 1Y Return (%)": round(float(sub["1Y Return (%)"].mean()), 2) if len(sub) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def quadrant_counts(df: pd.DataFrame) -> dict[str, int]:
    """Company count per quadrant on the FULL universe (P/E vs EPS G3 medians)."""
    if PE_COL not in df.columns or EPS_G3_COL not in df.columns:
        return {q: 0 for q in QUADRANTS}
    med_x, med_y = universe_medians(df, PE_COL, EPS_G3_COL)
    assigned = assign_quadrants(df, PE_COL, EPS_G3_COL, med_x, med_y)
    counts = assigned.value_counts().to_dict()
    return {q: int(counts.get(q, 0)) for q in QUADRANTS}


# ===========================================================================
# Insight engine: every number gets a verdict derived from the distribution.
# ===========================================================================
TURN_COL = "Avg Daily Turnover (Cr)"


def _breadth_verdict(pct_pos: float) -> tuple[str, str]:
    if pct_pos >= 55:
        return "Strong", "pos"
    if pct_pos >= 45:
        return "Mixed", "warn"
    return "Weak", "neg"


def _median_pe_pos(df: pd.DataFrame) -> tuple[float, int, int]:
    """Median P/E over positive-P/E names plus valid and loss-making counts."""
    pe = df[PE_COL].dropna()
    pe_pos = pe[pe > 0]
    return (float(pe_pos.median()) if len(pe_pos) else np.nan), len(pe), len(df) - len(pe)


def market_verdict(df: pd.DataFrame) -> dict:
    """Reality Check: treat the whole universe as one index and demand it pass
    two hard gates at the required return.

      Gate 1 - Growth Hurdle:  needed growth = REQUIRED_RETURN - earnings yield;
               real historical growth must beat it.
      Gate 2 - Safety Buffer:  earnings yield must exceed the risk-free G-Sec
               yield; otherwise equities pay less than a riskless bond.

    Index aggregates: total earnings are summed across priced companies
    (earnings_i = cap_i / PE_i), so the index P/E is cap-weighted, not the
    median multiple. Structural growth uses the median EPS 3-yr CAGR as the
    best available long-run proxy, deflated by the inflation anchor.
    """
    out = {"available": False}
    priced = df[df[PE_COL] > 0] if PE_COL in df.columns else df.iloc[0:0]
    if priced.empty:
        return out

    caps = priced["Market Cap (Cr)"].fillna(0).astype(float)
    earnings = caps / priced[PE_COL].astype(float)
    total_cap, total_earnings = float(caps.sum()), float(earnings.sum())
    if total_earnings <= 0 or total_cap <= 0:
        return out

    idx_pe = total_cap / total_earnings
    ey = total_earnings / total_cap * 100  # percent
    implied_growth = REQUIRED_RETURN - ey
    safety_buffer = ey - RISK_FREE_RATE

    eps3 = df[EPS_G3_COL].dropna() if EPS_G3_COL in df.columns else pd.Series(dtype=float)
    profit3 = df[PROFIT_G3_COL].dropna() if PROFIT_G3_COL in df.columns else pd.Series(dtype=float)
    base = eps3 if len(eps3) >= len(profit3) else profit3
    src_label = "median EPS 3-yr CAGR" if base is eps3 and len(eps3) else "median profit 3-yr CAGR"
    if base.empty or np.isnan(implied_growth):
        return out
    nominal_growth = float(base.median())
    structural_growth = nominal_growth - INFLATION

    growth_pass = structural_growth > implied_growth
    buffer_pass = safety_buffer > 0
    n_pass = int(growth_pass) + int(buffer_pass)
    if n_pass == 2:
        tier, headline, tone = "pass", "PASS - GROWTH JUSTIFIES VALUATIONS, WITH A MARGIN OF SAFETY", "pos"
    elif n_pass == 1:
        failed = "the safety buffer" if buffer_pass else "the growth hurdle"
        tier, headline, tone = (
            "mixed",
            f"MIXED - REAL GROWTH CLEARS THE HURDLE BUT {failed.upper()} FAILS" if not buffer_pass
            else "MIXED - THE SAFETY BUFFER HOLDS BUT GROWTH MISSES THE HURDLE",
            "warn",
        )
    else:
        tier, headline, tone = "fail", "FAIL - PRICED FOR PERFECTION, ZERO MARGIN OF SAFETY", "neg"

    sentence = (
        f"As one index, the universe trades at <b>{idx_pe:.1f}x</b> (earnings yield <b>{ey:.1f}%</b>). "
        f"Earning your <b>{REQUIRED_RETURN:.0f}%</b> demands <b>~{implied_growth * 100:.1f}%/yr</b> perpetual "
        f"growth; the best long-run proxy ({src_label}) is <b>{nominal_growth:+.1f}%</b> nominal "
        f"(≈<b>{structural_growth:+.1f}% real</b>). Meanwhile a risk-free G-Sec already pays "
        f"<b>{RISK_FREE_RATE:.1f}%</b> vs this market's {ey:.1f}%."
    )
    mos_line = (
        f"Gates passed: <b>{n_pass}/2</b>. Growth hurdle {'✅' if growth_pass else '❌'} · "
        f"Safety buffer ({ey:.1f}% vs {RISK_FREE_RATE:.1f}%) {'✅' if buffer_pass else '❌'}."
    )

    out.update(
        {
            "available": True,
            "tier": tier,
            "headline": headline,
            "tone": tone,
            "sentence": sentence,
            "mos_line": mos_line,
            "idx_pe": idx_pe,
            "ey": ey,
            "implied_growth": implied_growth,
            "nominal_growth": nominal_growth,
            "structural_growth": structural_growth,
            "safety_buffer": safety_buffer,
            "growth_pass": growth_pass,
            "buffer_pass": buffer_pass,
            "gates_passed": n_pass,
            "priced_n": len(priced),
            "loss_making": len(df) - len(priced),
            "required_return": REQUIRED_RETURN,
            "risk_free": RISK_FREE_RATE,
            "inflation": INFLATION,
        }
    )
    return out


def market_regime(df: pd.DataFrame) -> list[dict]:
    """One verdict per lens for the second-order strip."""
    ret = df["1Y Return (%)"]
    pct_pos = float((ret > 0).mean() * 100)
    breadth_v, breadth_t = _breadth_verdict(pct_pos)

    regime = [
        {"lens": "Breadth", "verdict": breadth_v, "detail": f"{pct_pos:.0f}% positive 1Y", "tone": breadth_t},
        {
            "lens": "Returns",
            "verdict": f"{df['3Y CAGR (%)'].mean():+.0f}% avg 3Y",
            "detail": f"5Y {df['5Y CAGR (%)'].mean():+.0f}%",
            "tone": "pos" if df["3Y CAGR (%)"].mean() > 0 else "neg",
        },
    ]

    med_pe, _, _ = _median_pe_pos(df)
    if not np.isnan(med_pe):
        ey = 100.0 / med_pe
        regime.insert(
            0,
            {
                "lens": "Valuation",
                "verdict": f"{med_pe:.0f}x · EY {ey:.1f}%",
                "detail": f"vs G-Sec {RISK_FREE_RATE:.1f}%",
                "tone": "warn" if ey < RISK_FREE_RATE else "pos",
            },
        )

    if TURN_COL in df.columns and df[TURN_COL].notna().any():
        turn = df[TURN_COL].dropna()
        illiq_n = int((turn < 5).sum())
        illiq_pct = illiq_n / len(turn) * 100
        liq_v, liq_t = ("Stressed", "neg") if illiq_pct > 40 else (("Tight", "warn") if illiq_pct > 20 else ("Healthy", "pos"))
        regime.append({"lens": "Liquidity", "verdict": liq_v, "detail": f"{illiq_n} names <5 Cr/day", "tone": liq_t})
    return regime


def cap_insights(df: pd.DataFrame) -> dict:
    total_cap = float(df["Market Cap (Cr)"].sum())
    top10_share = float(df.nlargest(10, "Market Cap (Cr)")["Market Cap (Cr)"].sum() / total_cap * 100)
    conc_v, conc_t = ("High", "warn") if top10_share > 35 else (("Moderate", "neutral") if top10_share > 20 else ("Low", "pos"))
    sentence = (
        f"<b>{len(df)}</b> companies across <b>{df['Sector'].nunique()}</b> sectors worth "
        f"<b>{total_cap / 1e5:,.1f} L Cr</b>. The 10 largest names hold <b>{top10_share:.0f}%</b> "
        f"of total cap - concentration is <b>{conc_v}</b>."
    )
    return {
        "sentence": sentence, "tone": "neutral",
        "n": len(df), "sectors": df["Sector"].nunique(), "total_cap": total_cap,
        "median_cap": float(df["Market Cap (Cr)"].median()), "top10_share": top10_share,
        "concentration": conc_v, "concentration_tone": conc_t,
    }


def valuation_insights(df: pd.DataFrame) -> dict:
    """Earnings-yield framing: what each rupee buys vs bonds, what growth the
    required return demands, and whether actual growth covers it."""
    med_pe, valid, loss_making = _median_pe_pos(df)
    out = {"available": False, "valid": valid, "loss_making": loss_making}
    if np.isnan(med_pe) or med_pe <= 0:
        return out

    ey = 100.0 / med_pe
    needed = REQUIRED_RETURN - ey
    eps3 = df[EPS_G3_COL].dropna() if EPS_G3_COL in df.columns else pd.Series(dtype=float)
    profit3 = df[PROFIT_G3_COL].dropna() if PROFIT_G3_COL in df.columns else pd.Series(dtype=float)
    base = eps3 if len(eps3) >= len(profit3) and len(eps3) else profit3
    actual = float(base.median()) if len(base) else np.nan
    gap = actual - needed if not np.isnan(actual) else np.nan

    pb = df[PB_COL].dropna() if PB_COL in df.columns else pd.Series(dtype=float)
    pb_med = float(pb.median()) if len(pb) else np.nan

    tone, gap_word = ("pos", "covers it") if gap >= 2 else (("warn", "just about covers it") if gap >= -2 else ("neg", "falls short"))
    sentence = (
        f"Each <b>₹100</b> of price buys <b>₹{ey:.1f}</b> of yearly profit - vs <b>₹{RISK_FREE_RATE:.1f}</b> "
        f"risk-free in a G-Sec. To earn your <b>{REQUIRED_RETURN:.0f}%</b>, EPS must compound "
        f"<b>~{needed:.1f}%/yr forever</b>; the universe's 3-yr pace of <b>{actual:+.1f}%</b> {gap_word}."
    )
    out.update(
        {
            "available": True,
            "sentence": sentence,
            "tone": tone,
            "median_pe": med_pe,
            "ey": ey,
            "needed": needed,
            "actual": actual,
            "gap": gap,
            "gap_tone": tone,
            "pb_med": pb_med,
            "pb_valid": len(pb),
            "required_return": REQUIRED_RETURN,
            "risk_free": RISK_FREE_RATE,
        }
    )
    return out


def growth_insights(df: pd.DataFrame) -> dict:
    """Sales / Profit / EPS rows: % growing + median, anchored as real growth."""
    def row(s: pd.Series) -> dict:
        valid = int(s.notna().sum())
        pos_pct = float((s > 0).mean() * 100) if valid else np.nan
        median = float(s.median()) if valid else np.nan
        return {
            "valid": valid,
            "pos_pct": pos_pct,
            "median": median,
            "real_median": median - INFLATION if not np.isnan(median) else np.nan,
            "tone": _breadth_verdict(pos_pct)[1] if valid else "neutral",
        }

    sales = row(df[REV_G_COL]) if REV_G_COL in df.columns else row(pd.Series(dtype=float))
    profit = row(df[PROFIT_G1_COL] if PROFIT_G1_COL in df.columns else pd.Series(dtype=float))
    eps = row(df[EPS_G3_COL] if EPS_G3_COL in df.columns else pd.Series(dtype=float))

    primary = profit if profit["valid"] >= 30 and profit["valid"] >= eps["valid"] * 0.8 else eps
    verdict_v, verdict_t = _breadth_verdict(primary["pos_pct"]) if primary["valid"] else ("Unknown", "neutral")
    word = {"Strong": "broadly growing", "Mixed": "mixed", "Weak": "stalling"}[verdict_v]
    src_name = "profit" if primary is profit else "EPS"

    sentence = (
        f"The bottom line is <b>{word}</b>: only <b>{primary['pos_pct']:.0f}%</b> of companies grew "
        f"{src_name} (median <b>{primary['median']:+.1f}% nominal ≈ {primary['real_median']:+.1f}% real</b> "
        f"after ~{INFLATION:.0f}% inflation). Sales breadth: <b>{sales['pos_pct']:.0f}%</b>; "
        f"EPS-3Y breadth: <b>{eps['pos_pct']:.0f}%</b>."
    )
    return {
        "sentence": sentence,
        "tone": verdict_t,
        "verdict_word": word,
        "sales": sales,
        "profit": profit,
        "eps": eps,
        "inflation": INFLATION,
    }


def liquidity_insights(df: pd.DataFrame) -> dict | None:
    if TURN_COL not in df.columns or not df[TURN_COL].notna().any():
        return None
    turn = df[TURN_COL].dropna()
    illiq_n = int((turn < 5).sum())
    illiq_pct = illiq_n / len(turn) * 100
    liq_v, liq_t = ("Stressed", "neg") if illiq_pct > 40 else (("Tight", "warn") if illiq_pct > 20 else ("Healthy", "pos"))
    sentence = (
        f"The universe turns over <b>{turn.sum() / 1e5:,.1f} L Cr</b> per day (median "
        f"<b>{turn.median():,.0f} Cr</b> per name). <b>{illiq_n}</b> companies trade under "
        f"<b>5 Cr/day</b> ({illiq_pct:.0f}%) - the hard-to-exit tail. Liquidity is <b>{liq_v}</b>."
    )
    return {
        "sentence": sentence, "tone": liq_t, "verdict": liq_v,
        "total": float(turn.sum()), "median": float(turn.median()),
        "illiquid_n": illiq_n, "illiquid_pct": illiq_pct,
        "top10_share": float(df.nlargest(10, TURN_COL)[TURN_COL].sum() / turn.sum() * 100),
    }


def returns_insights(df: pd.DataFrame) -> dict:
    ret = df["1Y Return (%)"]
    pct_pos = float((ret > 0).mean() * 100)
    v, t = _breadth_verdict(pct_pos)
    sentence = (
        f"Breadth is <b>{v}</b>: only <b>{pct_pos:.0f}%</b> of stocks are positive over 1Y "
        f"(median <b>{ret.median():+.1f}%</b>, mean <b>{ret.mean():+.1f}%</b> - a fat tail means "
        f"the average flatters reality). Longer horizons: 3Y <b>{df['3Y CAGR (%)'].mean():+.1f}%</b>, "
        f"5Y <b>{df['5Y CAGR (%)'].mean():+.1f}%</b> avg CAGR."
    )
    return {
        "sentence": sentence, "tone": t, "verdict": v,
        "pct_pos": pct_pos, "median_1y": float(ret.median()),
        "avg_3y": float(df["3Y CAGR (%)"].mean()), "avg_5y": float(df["5Y CAGR (%)"].mean()),
    }
