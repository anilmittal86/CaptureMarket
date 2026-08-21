# CaptureMarket

An interactive web app to analyze the **Nifty Smallcap 250** universe at three levels:

| Level | What you get |
|---|---|
| **Macro** | Market-wide KPI cards (median P/E, EPS growth, returns, breadth), distributions, top/bottom performers |
| **Sectoral** | A quadrant *market map of sectors* (valuation vs growth), sector weights table, drill-down into any sector |
| **Micro** | The full stock-level bubble map: valuation vs earnings growth, bubble size = \|1Y return\|, color = return direction, search, filters, quadrants and percentiles |

## The Micro "Market Map"

Each company is one bubble on a quadrant chart:

- **X axis**: P/E (log scale by default, toggleable; outliers preserved)
- **Y axis**: EPS Growth 3Y
- **Bubble size**: magnitude of 1Y return (sign ignored)
- **Bubble color**: green = positive 1Y return, red = negative, grey = missing
- **Quadrants**: defined by the **full-universe median P/E and median EPS growth**
  - Growth + Value · Growth + Premium · Value + Low Growth · Expensive + Low Growth
- Boundaries and percentile ranks are always computed on the **complete universe**, even when filters are applied
- Click a bubble or use search to select a stock: highlight ring, guide lines, dimmed peers, info panel with quadrant and percentiles ("where does this stock sit in the entire market?")
- Axes/size/color are **configuration, not hard-coded** - switch X to ROE, Y to Revenue Growth, size to Market Cap, etc. from Chart settings

## Quickstart

```bash
pip install -r requirements.txt

# 1. Fetch data (~5-10 min for all 250 constituents)
python scripts/fetch_data.py

# 2. Launch the app
streamlit run app.py
```

## Data Pipeline

`scripts/fetch_data.py` pulls the official Nifty Smallcap 250 constituent list from
niftyindices.com and per-stock fundamentals/returns from Yahoo Finance into
`data/nifty_smallcap_250_data.csv`. Re-run it any time to refresh.

Notes:
- `EPS Growth 3Y (%)` is computed from annual income statements (EPS CAGR over the available span)
- Missing financials stay `NaN` and render as `N/A` - they are never zero-filled
- Companies without valid P/E or EPS growth remain searchable but cannot be positioned on the map (the header shows `X / 250 companies plotted`)

## Architecture

```
data/nifty_smallcap_250_data.csv   # generated (gitignored)
scripts/fetch_data.py              # data pipeline
src/
    data_loader.py                 # load/clean; missing data never zero-filled
    metrics.py                     # metric registry -> configurable axes & encodings
    analytics.py                   # medians, quadrants, percentiles, summaries
    visualization.py               # shared Plotly bubble-chart builder
app.py                             # home / navigation
pages/
    1_Macro_Analysis.py
    2_Sectoral_Analysis.py
    3_Micro_Analysis.py
```

Data processing, analytics and visualization are deliberately kept separate.
To re-point the chart at different metrics, edit `DEFAULT_CHART_CONFIG` in
`src/metrics.py` - no visualization code needs to change.

## Roadmap

- Separate the data layer from the app (dedicated data service / scheduled refresh, instead of a committed CSV snapshot)
- P/B, EV/EBITDA, PEG columns (registry already supports them once present in the CSV)
- ROCE derivation and FII/DII holding-change tracking
- Other index universes (Nifty 50, Midcap 150) via the same pipeline

## Disclaimer

For research and education only. Not investment advice.
