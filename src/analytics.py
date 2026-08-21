"""Analytics layer: universe statistics, quadrants, percentiles, summaries.

All universe-level statistics (medians, percentiles) are computed on the FULL
stock universe and must remain unaffected by any user-applied filters.
"""
import numpy as np
import pandas as pd

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


def market_regime(df: pd.DataFrame) -> list[dict]:
    """One verdict per lens for the top-of-page strip."""
    ret = df["1Y Return (%)"]
    pct_pos = float((ret > 0).mean() * 100)
    breadth_v, breadth_t = _breadth_verdict(pct_pos)

    eps = df["EPS Growth 3Y (%)"]
    valid_eps = int(eps.notna().sum())
    eps_pos_pct = float((eps > 0).mean() * 100) if valid_eps else np.nan
    growth_v, growth_t = _breadth_verdict(eps_pos_pct) if valid_eps else ("Unknown", "neutral")

    pe = df["P/E"].dropna()
    pe_pos = pe[pe > 0]
    p25, p75 = float(pe_pos.quantile(0.25)), float(pe_pos.quantile(0.75))
    spread_ratio = p75 / p25 if p25 > 0 else np.nan
    val_v = "Wide dispersion" if spread_ratio > 2.5 else ("Moderate dispersion" if spread_ratio > 1.8 else "Tight dispersion")

    regime = [
        {"lens": "Valuation", "verdict": f"{pe.median():.0f}x median", "detail": f"p25 {p25:.0f}x – p75 {p75:.0f}x", "tone": "neutral"},
        {"lens": "Growth", "verdict": growth_v, "detail": f"{eps_pos_pct:.0f}% growing EPS (3Y)", "tone": growth_t},
    ]
    if TURN_COL in df.columns and df[TURN_COL].notna().any():
        turn = df[TURN_COL].dropna()
        illiq_n = int((turn < 5).sum())
        illiq_pct = illiq_n / len(turn) * 100
        liq_v, liq_t = ("Stressed", "neg") if illiq_pct > 40 else (("Tight", "warn") if illiq_pct > 20 else ("Healthy", "pos"))
        regime.append({"lens": "Liquidity", "verdict": liq_v, "detail": f"{illiq_n} names <5 Cr/day", "tone": liq_t})
    regime.append({"lens": "Breadth", "verdict": breadth_v, "detail": f"{pct_pos:.0f}% positive 1Y", "tone": breadth_t})
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
    pe = df["P/E"].dropna()
    pe_pos = pe[pe > 0]
    p25, med, p75 = float(pe_pos.quantile(0.25)), float(pe_pos.median()), float(pe_pos.quantile(0.75))
    loss_making = len(df) - len(pe)
    wide = (p75 / p25) > 2.5 if p25 > 0 else True
    tone = "warn" if wide else "neutral"
    disp = "wide" if wide else "tight"
    sentence = (
        f"The universe trades at a median <b>{med:.1f}x</b> P/E; half of it sits between "
        f"<b>{p25:.1f}x</b> and <b>{p75:.1f}x</b> - <b>{disp}</b> dispersion. "
        f"{loss_making} companies are excluded (loss-making / no P/E)."
    )
    return {
        "sentence": sentence, "tone": tone,
        "median": med, "p25": p25, "p75": p75,
        "valid": len(pe), "loss_making": loss_making,
    }


def growth_insights(df: pd.DataFrame) -> dict:
    eps, rev = df["EPS Growth 3Y (%)"], df["Revenue Growth (%)"]
    eps_valid, rev_valid = int(eps.notna().sum()), int(rev.notna().sum())
    eps_pos_pct = float((eps > 0).mean() * 100) if eps_valid else np.nan
    rev_pos_pct = float((rev > 0).mean() * 100) if rev_valid else np.nan
    v, t = _breadth_verdict(eps_pos_pct) if eps_valid else ("Unknown", "neutral")
    word = {"Strong": "broadly growing", "Mixed": "mixed", "Weak": "stalling"}[v]
    sentence = (
        f"Earnings breadth is <b>{v.lower()}</b>: <b>{eps_pos_pct:.0f}%</b> of companies grew EPS over 3Y "
        f"(median <b>{eps.median():+.1f}%</b>). Revenue breadth: <b>{rev_pos_pct:.0f}%</b> growing YoY."
    )
    return {
        "sentence": sentence, "tone": t, "verdict_word": word,
        "median_eps": float(eps.median()), "eps_pos_pct": eps_pos_pct,
        "median_rev": float(rev.median()), "rev_pos_pct": rev_pos_pct,
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
