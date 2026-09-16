"""Fetch NSE index PE/PB/DivYield history for Smallcap 250 and Nifty 50.

Uses niftyindices.com Backpage API (no key). Saves to data/index_pepb/*.csv
Falls back to graceful empty file if NSE blocks.
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "index_pepb"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INDICES = ["NIFTY SMALLCAP 250", "NIFTY 50", "NIFTY MIDCAP 150"]
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.niftyindices.com/reports/historical-data",
}
URL_PEPB = "https://www.niftyindices.com/Backpage.aspx/getPEPBHistoryString"


def fetch_pepb(index_name: str, start: date, end: date) -> pd.DataFrame:
    sess = requests.Session()
    sess.get("https://www.niftyindices.com/reports/historical-data", headers={"User-Agent": HEADERS["User-Agent"]}, timeout=15)
    start_s = start.strftime("%d-%b-%Y")
    end_s = end.strftime("%d-%b-%Y")
    payload = json.dumps({"cinfo": json.dumps({"name": index_name, "startDate": start_s, "endDate": end_s, "indexName": index_name})})
    try:
        r = sess.post(URL_PEPB, data=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        j = r.json()
        raw = j.get("d", "[]")
        data = json.loads(raw) if isinstance(raw, str) else raw
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df.columns = [c.strip() for c in df.columns]
        col_map = {c: c for c in df.columns}
        for c in list(df.columns):
            lc = c.lower()
            if "date" in lc:
                col_map[c] = "Date"
            elif "p/e" in lc or "pe" == lc:
                col_map[c] = "PE"
            elif "p/b" in lc or "pb" == lc:
                col_map[c] = "PB"
            elif "div" in lc or "yield" in lc:
                col_map[c] = "DivYield"
        df = df.rename(columns=col_map)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        for col in ["PE", "PB", "DivYield"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date")
        return df[["Date", "PE", "PB", "DivYield"]] if set(["PE", "PB"]).issubset(df.columns) else df
    except Exception as e:
        print(f"  failed {index_name}: {e}")
        return pd.DataFrame(columns=["Date", "PE", "PB", "DivYield"])


def main():
    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    for idx in INDICES:
        print(f"Fetching {idx} {start} -> {end} ...")
        df = fetch_pepb(idx, start, end)
        fname = idx.replace(" ", "_").lower() + ".csv"
        out = OUT_DIR / fname
        if not df.empty:
            df.to_csv(out, index=False)
            print(f"  saved {len(df)} rows -> {out}")
        else:
            print(f"  no data for {idx}, writing empty placeholder")
            pd.DataFrame(columns=["Date", "PE", "PB", "DivYield"]).to_csv(out, index=False)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
