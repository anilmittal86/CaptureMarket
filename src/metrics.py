"""Metric registry: single source of truth for columns, labels and formatting.

Chart axes/bubble encodings are configuration (keys into this registry), never
hard-coded, so the bubble map can be re-pointed at other metrics later.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    key: str
    column: str
    label: str
    fmt: str
    log_ok: bool = False


METRICS = {
    "pe": Metric("pe", "P/E", "P/E", "{:.1f}x", log_ok=True),
    "eps_g_1y": Metric("eps_g_1y", "EPS Growth 1Y (%)", "EPS Growth 1Y", "{:.1f}%"),
    "eps_g_3y": Metric("eps_g_3y", "EPS Growth 3Y (%)", "EPS Growth 3Y", "{:.1f}%"),
    "rev_g": Metric("rev_g", "Revenue Growth (%)", "Revenue Growth", "{:.1f}%"),
    "roce": Metric("roce", "ROCE (%)", "ROCE", "{:.1f}%"),
    "roe": Metric("roe", "ROE (%)", "ROE", "{:.1f}%"),
    "ret_1y": Metric("ret_1y", "1Y Return (%)", "1Y Return", "{:+.1f}%"),
    "ret_3y": Metric("ret_3y", "3Y CAGR (%)", "3Y CAGR", "{:+.1f}%"),
    "ret_5y": Metric("ret_5y", "5Y CAGR (%)", "5Y CAGR", "{:+.1f}%"),
    "mktcap": Metric("mktcap", "Market Cap (Cr)", "Market Cap", "{:,.0f} Cr"),
    "fii_chg": Metric("fii_chg", "FII Holding Change (%)", "FII Holding Change", "{:+.1f}%"),
    "dii_chg": Metric("dii_chg", "DII Holding Change (%)", "DII Holding Change", "{:+.1f}%"),
}

# Bubble size candidates: key -> (source column, label, use absolute value)
SIZE_OPTIONS = {
    "ret_1y_abs": ("1Y Return (%)", "|1Y Return|", True),
    "ret_3y_abs": ("3Y CAGR (%)", "|3Y CAGR|", True),
    "ret_5y_abs": ("5Y CAGR (%)", "|5Y CAGR|", True),
    "mktcap": ("Market Cap (Cr)", "Market Cap", False),
}

# Bubble color candidates: key -> (source column, label)
COLOR_OPTIONS = {
    "ret_1y_sign": ("1Y Return (%)", "1Y Return direction"),
    "ret_3y_sign": ("3Y CAGR (%)", "3Y CAGR direction"),
    "avg_ret_1y_sign": ("Avg 1Y Return (%)", "Avg 1Y Return direction"),
}

# Sector-aggregate candidates (used by the sectoral market map)
SIZE_OPTIONS["avg_ret_1y_abs"] = ("Avg 1Y Return (%)", "|Avg 1Y Return|", True)

DEFAULT_CHART_CONFIG = {
    "x": "pe",
    "y": "eps_g_3y",
    "size": "ret_1y_abs",
    "color": "ret_1y_sign",
}

# Tooltip fields for the micro-level stock map (unavailable fields are skipped).
TOOLTIP_FIELDS = [
    ("Company", "Company", None),
    ("NSE Symbol", "NSE Symbol", None),
    ("Market Cap", "Market Cap (Cr)", METRICS["mktcap"].fmt),
    ("P/E", "P/E", METRICS["pe"].fmt),
    ("EPS Growth 1Y", "EPS Growth 1Y (%)", METRICS["eps_g_1y"].fmt),
    ("EPS Growth 3Y", "EPS Growth 3Y (%)", METRICS["eps_g_3y"].fmt),
    ("Revenue Growth", "Revenue Growth (%)", METRICS["rev_g"].fmt),
    ("ROCE", "ROCE (%)", METRICS["roce"].fmt),
    ("ROE", "ROE (%)", METRICS["roe"].fmt),
    ("1Y Return", "1Y Return (%)", METRICS["ret_1y"].fmt),
    ("3Y Return", "3Y CAGR (%)", METRICS["ret_3y"].fmt),
    ("5Y Return", "5Y CAGR (%)", METRICS["ret_5y"].fmt),
    ("FII Holding Change", "FII Holding Change (%)", METRICS["fii_chg"].fmt),
    ("DII Holding Change", "DII Holding Change (%)", METRICS["dii_chg"].fmt),
    ("Sector", "Sector", None),
    ("Industry", "Industry", None),
]


def fmt_metric(column: str, value) -> str:
    """Format a raw metric value by its column; 'N/A' when missing."""
    import math

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    for m in METRICS.values():
        if m.column == column:
            return m.fmt.format(value)
    return str(value)
