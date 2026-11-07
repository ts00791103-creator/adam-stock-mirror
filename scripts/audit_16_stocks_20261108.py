"""Read-only dated official OHLC versus the exact production history pipeline."""
import ast
import csv
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import yfinance as yf
from market_universe import SOURCES, read_json, number, trading_date
from quote_quality import invalid_price_rows

SAMPLES=[["2330","台積電","上市"],["2308","台達電","上市"],["2509","全坤建","上市"],["6405","悅城","上市"],["6695","芯鼎","上市"],["6756","威鋒電子","上市"],["5515","建國","上市"],["4770","上品","上市"],["8358","金居","上櫃"],["8240","華宏","上櫃"],["7767","仁大資訊","上櫃"],["5452","佶優","上櫃"],["6104","創惟","上櫃"],["8040","九暘","上櫃"],["3163","波若威","上櫃"],["6182","合晶","上櫃"]]
ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/"release-preview/v1.0.6/app.py").read_text(encoding="utf-8"))
definition=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="audit_ohlc_data")
namespace={"pd":pd,"np":np}
exec(compile(ast.Module(body=[definition],type_ignores=[]),"<production quality gate>","exec"),namespace)
audit=namespace["audit_ohlc_data"]
official={}
source_errors={}
for exchange in ("上市","上櫃"):
    try:
        raw=read_json(SOURCES[exchange][1])
        code_key="Code" if exchange=="上市" else "SecuritiesCompanyCode"
        official[exchange]={str(row.get(code_key,"")).strip():row for row in raw}
    except Exception as exc:
        source_errors[exchange]=type(exc).__name__+": "+str(exc)[:180]

report={"source":"official TWSE/TPEx public daily quotes versus Yahoo unadjusted daily history",
        "production_code":"40fe823215f8c5020bae9d041f41795c6a0bf9c2","source_errors":source_errors,
        "retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),"rows":[]}
for code,name,exchange in SAMPLES:
    out={"code":code,"name":name,"exchange":exchange,"symbol":code+(".TW" if exchange=="上市" else ".TWO")}
    try:
        raw=official.get(exchange,{}).get(code)
        if raw is None:
            raise ValueError("官方每日行情缺少此檔，不能判定價格正確")
        day=trading_date(raw.get("Date",""))
        keys=({"Open":"OpeningPrice","High":"HighestPrice","Low":"LowestPrice","Close":"ClosingPrice"}
              if exchange=="上市" else {k:k for k in ("Open","High","Low","Close")})
        values={}
        field_errors=[]
        for field,key in keys.items():
            try: values[field]=number(raw.get(key))
            except Exception: field_errors.append(key)
        out.update(official_date=day,official_ohlc=values,official_missing_fields=field_errors,
                   official_source=SOURCES[exchange][1])
        df=yf.download(out["symbol"],period="10y",interval="1d",auto_adjust=False,progress=False,threads=False)
        if isinstance(df.columns,pd.MultiIndex):
            df.columns=df.columns.get_level_values(0)
        if df.empty: raise ValueError("Yahoo無歷史資料")
        out["raw_duplicate_times"]=int(df.index.duplicated().sum())
        df=df.dropna(subset=["Close"]).sort_index().copy()
        df.index=pd.to_datetime(df.index)
        if df.index.tz is not None: df.index=df.index.tz_localize(None)
        df=df[~df.index.duplicated(keep="last")]
        out["history_10y_bars"]=len(df)
        out["history_10y_issues"]=audit(df)
        out["history_10y_invalid_rows"]=invalid_price_rows(df,limit=20)
        cutoff=pd.Timestamp.now(tz="Asia/Taipei").tz_localize(None)-pd.DateOffset(years=5)
        five=df.loc[df.index>=cutoff.normalize()]
        out["history_5y_slice_bars"]=len(five)
        out["history_5y_slice_issues"]=audit(five)
        out["history_5y_slice_invalid_rows"]=invalid_price_rows(five,limit=20)
        dated=df.loc[df.index.normalize()==pd.Timestamp(day)]
        if len(dated)!=1: raise ValueError("Yahoo缺少官方同日期的唯一日K")
        bar=dated.iloc[0]
        yahoo={field:float(bar[field]) for field in keys}
        out["yahoo_dated_ohlc"]=yahoo
        out["yahoo_latest_date"]=str(df.index[-1].date())
        out["close_match"]=bool("Close" in values and abs(yahoo["Close"]-values["Close"])<=.005)
        out["latest_ohlc_match"]=bool(not field_errors and all(abs(yahoo[k]-values[k])<=.005 for k in keys))
        out["status"]="dated OHLC matched" if out["latest_ohlc_match"] else "mismatch or missing official fields"
    except Exception as exc:
        out["error"]=type(exc).__name__+": "+str(exc)[:240]
        out["status"]="unconfirmed"
    report["rows"].append(out)
    print(json.dumps(out,ensure_ascii=False),flush=True)
    time.sleep(.4)
folder=ROOT/"audit-output";folder.mkdir(exist_ok=True)
(folder/"stock_sample_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
with (folder/"stock_sample_summary.csv").open("w",encoding="utf-8-sig",newline="") as handle:
    fields=["code","name","exchange","official_date","official_close","yahoo_close","close_match","latest_ohlc_match","history_10y_bars","history_10y_issues","history_5y_slice_issues","status","error"]
    writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
    for row in report["rows"]:
        row=dict(row)
        row["official_close"]=row.get("official_ohlc",{}).get("Close")
        row["yahoo_close"]=row.get("yahoo_dated_ohlc",{}).get("Close")
        writer.writerow({key:row.get(key,"") for key in fields})
print("PRICE_AUDIT_JSON="+json.dumps(report,ensure_ascii=False),flush=True)
