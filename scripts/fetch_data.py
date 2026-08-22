"""Fetch Nifty Smallcap 250 fundamentals and returns into data/nifty_smallcap_250_data.csv.

Based on the original capture script. Approved extensions over the original:
- EPS Growth 3Y (%): CAGR from annual income statements (>= 2 fiscal years).
- P/B: yfinance priceToBook.
- Profit Growth 1Y (%): Net Income latest FY vs prior FY (both positive).
- Profit Growth 3Y (%): Net Income CAGR over available span (>= 2 fiscal years).
The single stock.financials download is shared by all three statement metrics.
Everything else is kept exactly as before.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

URL = "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "nifty_smallcap_250_data.csv"


def _row(fin: pd.DataFrame | None, names: tuple[str, ...]):
    """Return the first matching index row (sorted chronologically) or None."""
    if fin is None or fin.empty:
        return None
    for name in names:
        if name in fin.index:
            s = fin.loc[name].dropna().sort_index()
            if len(s):
                return s
    return None


def _cagr(s) -> float:
    """CAGR % across the available span of a chronological series."""
    if s is None or len(s) < 2:
        return np.nan
    oldest, latest = float(s.iloc[0]), float(s.iloc[-1])
    span_years = (s.index[-1] - s.index[0]).days / 365.25
    if span_years < 2 or oldest <= 0 or latest <= 0:
        return np.nan
    return ((latest / oldest) ** (1 / span_years) - 1) * 100


def profit_growth_1y(fin) -> float:
    """Net Income latest FY vs prior FY growth %. NaN unless both positive."""
    ni = _row(fin, ("Net Income", "Net Income Common Stockholders"))
    if ni is None or len(ni) < 2:
        return np.nan
    prev, latest = float(ni.iloc[-2]), float(ni.iloc[-1])
    if prev <= 0 or latest <= 0:
        return np.nan
    return (latest / prev - 1) * 100


def profit_growth_3y(fin) -> float:
    """Net Income CAGR % across the available span. Graceful NaN if unavailable."""
    try:
        return _cagr(_row(fin, ("Net Income", "Net Income Common Stockholders")))
    except Exception:
        return np.nan


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_constituents = pd.read_csv(URL, storage_options=HEADERS)

    results = []
    total = len(df_constituents)
    print(f"Fetching {total} constituents...")

    for idx, row in df_constituents.iterrows():
        symbol = row["Symbol"]
        ticker = f"{symbol}.NS"
        base = {
            "Company": row["Company Name"],
            "NSE Symbol": symbol,
            "Sector": row.get("Industry", "N/A"),
            "Industry": np.nan,
            "Market Cap (Cr)": np.nan,
            "P/E": np.nan,
            "P/B": np.nan,
            "EPS Growth 1Y (%)": np.nan,
            "EPS Growth 3Y (%)": np.nan,
            "Profit Growth 1Y (%)": np.nan,
            "Profit Growth 3Y (%)": np.nan,
            "Revenue Growth (%)": np.nan,
            "ROCE (%)": np.nan,
            "ROE (%)": np.nan,
            "1Y Return (%)": np.nan,
            "3Y CAGR (%)": np.nan,
            "5Y CAGR (%)": np.nan,
            "FII Holding Change (%)": np.nan,
            "DII Holding Change (%)": np.nan,
            "Avg Daily Turnover (Cr)": np.nan,
        }
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="5y")
            try:
                fin = stock.financials
            except Exception:
                fin = None

            cmp_price = info.get("currentPrice", np.nan)
            ret_1y = ((cmp_price / hist["Close"].iloc[-252] - 1) * 100) if len(hist) >= 252 else np.nan
            ret_3y = (((cmp_price / hist["Close"].iloc[-756]) ** (1 / 3) - 1) * 100) if len(hist) >= 756 else np.nan
            ret_5y = (((cmp_price / hist["Close"].iloc[0]) ** (1 / 5) - 1) * 100) if len(hist) >= 1260 else np.nan

            turnover = (hist["Volume"] * hist["Close"]).tail(252)
            avg_turnover = round(float(turnover.mean()) / 1e7, 2) if not turnover.empty else np.nan

            base.update({
                "Industry": info.get("industry", "N/A"),
                "Market Cap (Cr)": round(info.get("marketCap", 0) / 1e7, 2),
                "P/E": info.get("trailingPE", np.nan),
                "P/B": info.get("priceToBook", np.nan),
                "EPS Growth 1Y (%)": info.get("earningsGrowth", np.nan) * 100 if info.get("earningsGrowth") else np.nan,
                "EPS Growth 3Y (%)": round(_cagr(_row(fin, ("Diluted EPS", "Basic EPS"))), 2),
                "Profit Growth 1Y (%)": round(profit_growth_1y(fin), 2),
                "Profit Growth 3Y (%)": round(profit_growth_3y(fin), 2),
                "Revenue Growth (%)": info.get("revenueGrowth", np.nan) * 100 if info.get("revenueGrowth") else np.nan,
                "ROCE (%)": np.nan,
                "ROE (%)": info.get("returnOnEquity", np.nan) * 100 if info.get("returnOnEquity") else np.nan,
                "1Y Return (%)": round(ret_1y, 2),
                "3Y CAGR (%)": round(ret_3y, 2),
                "5Y CAGR (%)": round(ret_5y, 2),
                "FII Holding Change (%)": np.nan,
                "DII Holding Change (%)": np.nan,
                "Avg Daily Turnover (Cr)": avg_turnover,
            })
        except Exception as e:
            print(f"Failed pulling {symbol}: {e}")
        results.append(base)

        done = idx + 1
        if done % 10 == 0 or done == total:
            print(f"[{done}/{total}] latest: {symbol}")
        time.sleep(0.3)

    df_final = pd.DataFrame(results)
    df_final.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df_final)} rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
