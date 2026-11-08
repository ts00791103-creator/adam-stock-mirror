"""Read-only full-period OHLC evidence for four stocks; never repairs prices."""
import json
import math
import sys
from pathlib import Path
import pandas as pd
import yfinance as yf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from official_history import fetch_official_month, invalid_candles, request_spec
out=ROOT/"candidate-market-output";out.mkdir(exist_ok=True)
report={"retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),
        "request":{"period":"10y","interval":"1d","auto_adjust":False,"actions":False},
        "policy":"Read-only evidence; no guessed prices, removed candles, shortened request, mixed-basis replacements or weakened gate.",
        "stocks":[],"official_months":[]}
for symbol in ("6488.TWO","5347.TWO","8069.TWO","6147.TWO"):
    row={"symbol":symbol}
    try:
        raw=yf.download(symbol,period="10y",interval="1d",auto_adjust=False,progress=False,threads=False)
        if isinstance(raw.columns,pd.MultiIndex):raw.columns=raw.columns.get_level_values(0)
        if raw.empty:raise ValueError("empty full-period response")
        raw.index=pd.to_datetime(raw.index)
        if raw.index.tz is not None:raw.index=raw.index.tz_localize(None)
        raw.to_csv(out/(symbol+"_10y_source.csv"))
        row.update(bars=len(raw),first=str(raw.index[0].date()),last=str(raw.index[-1].date()),
                   duplicate_dates=int(raw.index.duplicated().sum()),missing_ohlc=int(raw[["Open","High","Low","Close"]].isna().any(axis=1).sum()),
                   latest_close=float(raw.Close.iloc[-1]),invalid_dates=invalid_candles(raw))
        row["invalid_rows"]=[{"date":str(t.date()),**{c:float(raw.loc[t,c]) for c in ("Open","High","Low","Close")}}
                             for t in raw.index if str(t.date()) in row["invalid_dates"]]
        metadata=yf.download(symbol,period="10y",interval="1d",auto_adjust=False,actions=True,progress=False,threads=False)
        if isinstance(metadata.columns,pd.MultiIndex):metadata.columns=metadata.columns.get_level_values(0)
        metadata.index=pd.to_datetime(metadata.index)
        if metadata.index.tz is not None:metadata.index=metadata.index.tz_localize(None)
        cols=["Open","High","Low","Close"]
        row["action_metadata_matches_primary_prices"]=bool(raw[cols].equals(metadata[cols]))
        row["split_events"]=[{"date":str(t.date()),"value":float(v)} for t,v in metadata.get("Stock Splits",pd.Series(dtype=float)).items() if v!=0]
        row["status"]="unresolved source OHLC anomalies" if row["invalid_dates"] else "no OHLC anomaly in this response; not a historical repair claim"
        for month in sorted(set(day[:7] for day in row["invalid_dates"])):
            item={"symbol":symbol,"month":month,"request_spec":request_spec(symbol,month),"targets":[]}
            try:
                official,evidence,payload=fetch_official_month(symbol,month)
                (out/("official_"+symbol+"_"+month+".json")).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                item["evidence"]=evidence
                ratios=[float(raw.loc[t,c])/float(official.loc[t,c]) for t in official.index if t in raw.index
                        for c in ("Open","High","Low") if float(official.loc[t,c])!=0]
                item["month_ohl_ratio_range"]=[min(ratios),max(ratios)] if ratios else []
                for source in row["invalid_rows"]:
                    if source["date"][:7]!=month:continue
                    stamp=pd.Timestamp(source["date"]);target={"date":source["date"],"source":source}
                    if stamp in official.index:
                        target["official_raw"]={c:float(official.loc[stamp,c]) for c in cols}
                        target["source_over_official"]={c:source[c]/target["official_raw"][c] if target["official_raw"][c] else None for c in cols}
                    else:target["official_status"]="date unavailable in official ordinary OHLC rows"
                    split=metadata.loc[metadata.index>stamp,"Stock Splits"] if "Stock Splits" in metadata else pd.Series(dtype=float)
                    events=[float(v) for v in split if float(v)!=0]
                    target["provider_inverse_split_product_after_date"]=1/math.prod(events) if events else 1
                    target["basis_status"]="Official is unadjusted raw price; Yahoo auto_adjust=False may still have split-adjusted OHLC. Provider action metadata is not an official complete adjustment chain. No conversion or replacement applied."
                    item["targets"].append(target)
                item["status"]="official month queried; basis unresolved; no repair"
            except Exception as exc:item.update(status="official verification incomplete",error=type(exc).__name__+": "+str(exc)[:240])
            report["official_months"].append(item)
    except Exception as exc:row.update(status="source verification incomplete",error=type(exc).__name__+": "+str(exc)[:240])
    report["stocks"].append(row)
(out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("CANDIDATE_MARKET_DIAGNOSTIC="+json.dumps(report,ensure_ascii=False),flush=True)
