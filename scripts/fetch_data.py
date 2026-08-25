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
            "ROA (%)": np.nan,
            "OCF_PAT": np.nan,
            "Net_Debt_EBITDA": np.nan,
            "Debt/Equity": np.nan,
            "Current Ratio": np.nan,
            "Interest Coverage": np.nan,
            "CMP": np.nan,
            "50 DMA": np.nan,
            "200 DMA": np.nan,
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
            try:
                bs = stock.balance_sheet
            except Exception:
                bs = None
            try:
                cf = stock.cashflow
            except Exception:
                cf = None

            def _latest(df_, names_):
                s = _row(df_, names_)
                if s is None or s.empty:
                    return np.nan
                try:
                    return float(s.iloc[-1])
                except Exception:
                    return np.nan

            cmp_price = info.get("currentPrice", np.nan)
            if pd.isna(cmp_price) and len(hist):
                try:
                    cmp_price = float(hist["Close"].iloc[-1])
                except Exception:
                    cmp_price = np.nan
            ret_1y = ((cmp_price / hist["Close"].iloc[-252] - 1) * 100) if len(hist) >= 252 and pd.notna(cmp_price) else np.nan
            ret_3y = (((cmp_price / hist["Close"].iloc[-756]) ** (1 / 3) - 1) * 100) if len(hist) >= 756 and pd.notna(cmp_price) else np.nan
            ret_5y = (((cmp_price / hist["Close"].iloc[0]) ** (1 / 5) - 1) * 100) if len(hist) >= 1260 and pd.notna(cmp_price) else np.nan
            dma50 = float(hist["Close"].rolling(50).mean().iloc[-1]) if len(hist) >= 50 else np.nan
            dma200 = float(hist["Close"].rolling(200).mean().iloc[-1]) if len(hist) >= 200 else np.nan

            roa = info.get("returnOnAssets", np.nan)
            if pd.notna(roa):
                roa = round(float(roa) * 100, 2)
            else:
                ni_roa = _latest(fin, ("Net Income", "Net Income Common Stockholders"))
                ta = _latest(bs, ("Total Assets", "Total Asset"))
                roa = round(ni_roa / ta * 100, 2) if pd.notna(ni_roa) and pd.notna(ta) and ta != 0 else np.nan

            debt_to_equity = info.get("debtToEquity", np.nan)
            if pd.notna(debt_to_equity):
                debt_to_equity = round(float(debt_to_equity) / 100 if float(debt_to_equity) > 5 else float(debt_to_equity), 2)
            else:
                td = _latest(bs, ("Total Debt",))
                if pd.isna(td):
                    ltd = _latest(bs, ("Long Term Debt", "Long Term Debt And Capital Lease Obligation"))
                    std = _latest(bs, ("Short Term Debt", "Current Debt", "Short Long Term Debt"))
                    td = (ltd if pd.notna(ltd) else 0) + (std if pd.notna(std) else 0)
                    if td == 0 and pd.isna(ltd) and pd.isna(std):
                        td = np.nan
                te = _latest(bs, ("Total Stockholder Equity", "Total Stockholders Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"))
                debt_to_equity = round(td / te, 2) if pd.notna(td) and pd.notna(te) and te != 0 else np.nan

            curr_ratio = info.get("currentRatio", np.nan)
            if pd.isna(curr_ratio):
                ca = _latest(bs, ("Current Assets", "Total Current Assets"))
                cl = _latest(bs, ("Current Liabilities", "Total Current Liabilities"))
                curr_ratio = round(ca / cl, 2) if pd.notna(ca) and pd.notna(cl) and cl != 0 else np.nan
            else:
                try:
                    curr_ratio = round(float(curr_ratio), 2)
                except Exception:
                    curr_ratio = np.nan

            ebit_ic = _latest(fin, ("EBIT", "Ebit"))
            int_exp = _latest(fin, ("Interest Expense", "Interest Expense Non Operating"))
            if pd.notna(ebit_ic) and pd.notna(int_exp) and int_exp != 0:
                int_cov = round(ebit_ic / abs(int_exp), 2)
            else:
                int_cov = np.nan

            ebitda = _latest(fin, ("EBITDA", "Ebitda", "Normalized EBITDA"))
            td_nd = _latest(bs, ("Total Debt",))
            if pd.isna(td_nd):
                ltd2 = _latest(bs, ("Long Term Debt",))
                std2 = _latest(bs, ("Short Term Debt",))
                td_nd = (ltd2 if pd.notna(ltd2) else 0) + (std2 if pd.notna(std2) else 0)
                if td_nd == 0 and pd.isna(ltd2) and pd.isna(std2):
                    td_nd = np.nan
            cash = _latest(bs, ("Cash And Cash Equivalents", "Cash And Cash Equivalents At Carrying Value", "Cash"))
            if pd.notna(td_nd) and pd.notna(cash) and pd.notna(ebitda) and ebitda != 0:
                net_debt_ebitda = round((td_nd - cash) / ebitda, 2)
            else:
                info_td = info.get("totalDebt", np.nan)
                info_cash = info.get("totalCash", np.nan)
                info_ebitda = info.get("ebitda", np.nan)
                if pd.notna(info_td) and pd.notna(info_cash) and pd.notna(info_ebitda) and info_ebitda != 0:
                    net_debt_ebitda = round((float(info_td) - float(info_cash)) / float(info_ebitda), 2)
                else:
                    net_debt_ebitda = np.nan

            ocf = _latest(cf, ("Total Cash From Operating Activities", "Operating Cash Flow", "Operating Cashflow"))
            ni_ocf = _latest(fin, ("Net Income", "Net Income Common Stockholders"))
            ocf_pat = round(ocf / ni_ocf, 2) if pd.notna(ocf) and pd.notna(ni_ocf) and ni_ocf != 0 else np.nan

            ebit_roce = _latest(fin, ("EBIT", "Ebit"))
            ta_roce = _latest(bs, ("Total Assets",))
            cl_roce = _latest(bs, ("Current Liabilities", "Total Current Liabilities"))
            if pd.notna(ebit_roce) and pd.notna(ta_roce) and pd.notna(cl_roce) and (ta_roce - cl_roce) != 0:
                roce_calc = round(ebit_roce / (ta_roce - cl_roce) * 100, 2)
            else:
                roce_calc = np.nan

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
                "ROCE (%)": roce_calc if pd.notna(roce_calc) else np.nan,
                "ROE (%)": info.get("returnOnEquity", np.nan) * 100 if info.get("returnOnEquity") else np.nan,
                "ROA (%)": roa,
                "OCF_PAT": round(ocf_pat, 2) if pd.notna(ocf_pat) else np.nan,
                "Net_Debt_EBITDA": round(net_debt_ebitda, 2) if pd.notna(net_debt_ebitda) else np.nan,
                "Debt/Equity": round(debt_to_equity, 2) if pd.notna(debt_to_equity) else np.nan,
                "Current Ratio": round(curr_ratio, 2) if pd.notna(curr_ratio) else np.nan,
                "Interest Coverage": round(int_cov, 2) if pd.notna(int_cov) else np.nan,
                "CMP": round(float(cmp_price), 2) if pd.notna(cmp_price) else np.nan,
                "50 DMA": round(float(dma50), 2) if pd.notna(dma50) else np.nan,
                "200 DMA": round(float(dma200), 2) if pd.notna(dma200) else np.nan,
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
