"""Read-only evidence capture; never repair or remove OHLC anomalies."""
import json
from pathlib import Path
import pandas as pd
import yfinance as yf

data = yf.download("6148.TWO", period="10y", interval="1d", auto_adjust=False,
                   progress=False, threads=False, timeout=15)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna(subset=["Close"]).sort_index()
if data.empty:
    raise ValueError("No live data; cannot diagnose")
prices = data[["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
high_gap = prices[["Open", "Low", "Close"]].max(axis=1) - prices.High
low_gap = prices.Low - prices[["Open", "High", "Close"]].min(axis=1)
bad = (high_gap > 0) | (low_gap > 0)
print("DIAGNOSTIC_SUMMARY", json.dumps({"symbol": "6148.TWO", "period": "10y", "bars": len(data),
      "last_date": str(data.index[-1].date()), "bad_rows": int(bad.sum())}), flush=True)
records = []
for day, row in data.loc[bad].iterrows():
    item = {"date": str(day.date()), **{key: float(row[key]) for key in ("Open", "High", "Low", "Close", "Volume")},
            "high_gap": float(high_gap.loc[day]), "low_gap": float(low_gap.loc[day]),
            "max_relative_violation": max(float(high_gap.loc[day]), float(low_gap.loc[day]), 0)/float(row.Close)}
    records.append(item)
    print("DIAGNOSTIC_ROW", json.dumps(item), flush=True)
Path("diagnostics").mkdir(exist_ok=True)
pd.DataFrame(records).to_csv("diagnostics/6148_raw_ohlc_anomalies.csv", index=False)
