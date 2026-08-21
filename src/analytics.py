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
