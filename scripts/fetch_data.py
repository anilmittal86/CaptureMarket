"""Fetch Nifty Smallcap 250 fundamentals and returns into data/nifty_smallcap_250_data.csv.

Based on the original capture script. One approved extension: EPS Growth 3Y (%)
is computed from yfinance annual income statements (EPS CAGR over the available
span, requiring >= 2 fiscal years). Everything else is kept exactly as before.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

URL = "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "nifty_smallcap_250_data.csv"


def eps_growth_3y(stock) -> float:
    """3-year EPS CAGR from annual income statements. Graceful NaN if unavailable."""
    try:
        fin = stock.financials
        if fin is None or fin.empty:
            return np.nan
        eps = None
        for row_name in ("Diluted EPS", "Basic EPS"):
            if row_name in fin.index:
                eps = fin.loc[row_name].dropna()
                break
        if eps is None or len(eps) < 2:
            return np.nan
        eps = eps.sort_index()
        oldest, latest = float(eps.iloc[0]), float(eps.iloc[-1])
        span_years = (eps.index[-1] - eps.index[0]).days / 365.25
        if span_years < 2 or oldest <= 0 or latest <= 0:
            return np.nan
        return ((latest / oldest) ** (1 / span_years) - 1) * 100
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
            "EPS Growth 1Y (%)": np.nan,
            "EPS Growth 3Y (%)": np.nan,
            "Revenue Growth (%)": np.nan,
            "ROCE (%)": np.nan,
            "ROE (%)": np.nan,
            "1Y Return (%)": np.nan,
            "3Y CAGR (%)": np.nan,
            "5Y CAGR (%)": np.nan,
            "FII Holding Change (%)": np.nan,
            "DII Holding Change (%)": np.nan,
        }
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="5y")

            cmp_price = info.get("currentPrice", np.nan)
            ret_1y = ((cmp_price / hist["Close"].iloc[-252] - 1) * 100) if len(hist) >= 252 else np.nan
            ret_3y = (((cmp_price / hist["Close"].iloc[-756]) ** (1 / 3) - 1) * 100) if len(hist) >= 756 else np.nan
            ret_5y = (((cmp_price / hist["Close"].iloc[0]) ** (1 / 5) - 1) * 100) if len(hist) >= 1260 else np.nan

            base.update({
                "Industry": info.get("industry", "N/A"),
                "Market Cap (Cr)": round(info.get("marketCap", 0) / 1e7, 2),
                "P/E": info.get("trailingPE", np.nan),
                "EPS Growth 1Y (%)": info.get("earningsGrowth", np.nan) * 100 if info.get("earningsGrowth") else np.nan,
                "EPS Growth 3Y (%)": round(eps_growth_3y(stock), 2),
                "Revenue Growth (%)": info.get("revenueGrowth", np.nan) * 100 if info.get("revenueGrowth") else np.nan,
                "ROCE (%)": np.nan,
                "ROE (%)": info.get("returnOnEquity", np.nan) * 100 if info.get("returnOnEquity") else np.nan,
                "1Y Return (%)": round(ret_1y, 2),
                "3Y CAGR (%)": round(ret_3y, 2),
                "5Y CAGR (%)": round(ret_5y, 2),
                "FII Holding Change (%)": np.nan,
                "DII Holding Change (%)": np.nan,
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
