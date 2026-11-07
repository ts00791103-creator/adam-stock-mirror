"""Read-only 1815 full-request and official monthly basis investigation."""
import json
from pathlib import Path
import sys
import math
import pandas as pd
import yfinance as yf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from official_history import fetch_official_month, invalid_candles
out=ROOT/"candidate-market-output";out.mkdir(exist_ok=True)
report={"request":{"period":"10y","interval":"1d","auto_adjust":False,"actions":True},
        "retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),"stocks":[],"official_months":[]}
histories={}
for symbol in ("1815.TWO","2330.TW","2887.TW"):
    row={"symbol":symbol}
    try:
        raw=yf.download(symbol,period="10y",interval="1d",auto_adjust=False,actions=True,progress=False,threads=False)
        if isinstance(raw.columns,pd.MultiIndex):raw.columns=raw.columns.get_level_values(0)
        if raw.empty:raise ValueError("empty full-period response")
        row["raw_bars"]=len(raw);row["raw_duplicates"]=int(raw.index.duplicated().sum())
        raw.index=pd.to_datetime(raw.index)
        if raw.index.tz is not None:raw.index=raw.index.tz_localize(None)
        data=raw.dropna(subset=["Close"]).sort_index()
        data=data[~data.index.duplicated(keep="last")]
        histories[symbol]=data
        data.to_csv(out/(symbol+"_10y_source.csv"))
        row.update(bars=len(data),first=str(data.index[0].date()),last=str(data.index[-1].date()),
                   latest_close=float(data.Close.iloc[-1]),invalid_dates=invalid_candles(data))
        row["invalid_rows"]=[{"date":str(t.date()),**{c:float(data.loc[t,c]) for c in ("Open","High","Low","Close")}}
                             for t in data.index if str(t.date()) in row["invalid_dates"]]
        row["split_events"]=[{"date":str(t.date()),"value":float(v)} for t,v in data.get("Stock Splits",pd.Series(dtype=float)).items() if v!=0]
        row["status"]="full request inspected"
    except Exception as exc:row.update(status="unconfirmed",error=type(exc).__name__+": "+str(exc)[:240])
    report["stocks"].append(row)
for month,target in (("2017-07","2017-07-21"),("2018-07","2018-07-26")):
    item={"symbol":"1815.TWO","month":month,"target":target}
    try:
        official,evidence,payload=fetch_official_month("1815.TWO",month)
        (out/("official_1815_"+month+".json")).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        data=histories["1815.TWO"]
        stamp=pd.Timestamp(target)
        item["official"]={c:float(official.loc[stamp,c]) for c in ("Open","High","Low","Close")}
        item["source"]={c:float(data.loc[stamp,c]) for c in ("Open","High","Low","Close")}
        item["source_over_official"]={c:item["source"][c]/item["official"][c] for c in ("Open","High","Low","Close")}
        ratios=[float(data.loc[t,c])/float(official.loc[t,c]) for t in official.index if t in data.index
                for c in ("Open","High","Low")]
        item["month_ohl_ratio_range"]=[min(ratios),max(ratios)] if ratios else []
        split=data.loc[data.index>stamp,"Stock Splits"] if "Stock Splits" in data else pd.Series(dtype=float)
        events=[float(v) for v in split if float(v)!=0]
        item["provider_split_factor_after_date"]=1/math.prod(events) if events else 1
        item["basis_assessment"]="Compare observed OHL ratios with provider action metadata only; no official corporate-action conversion asserted or applied."
        item["evidence"]=evidence
        item["status"]="official queried; no price repair applied"
    except Exception as exc:item.update(status="unconfirmed",error=type(exc).__name__+": "+str(exc)[:240])
    report["official_months"].append(item)
(out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("CANDIDATE_MARKET_DIAGNOSTIC="+json.dumps(report,ensure_ascii=False),flush=True)
if any(x["status"]=="unconfirmed" for x in report["stocks"]+report["official_months"]):raise SystemExit("diagnostic incomplete")
