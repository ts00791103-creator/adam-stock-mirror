"""Bounded official source research; no app, alert, or production mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from official_series import OfficialArchive, assemble_official_series, aggregate_official_weeks, compare_provider, month_range, parse_series_month
from official_history import invalid_candles, parse_official_month
from market_universe import read_json
from live_tw_mirror_smoke import load_mirror_engine, validate_projection
from wave_settings import wave_windows

OUT=ROOT/"official-series-output"
OUT.mkdir(exist_ok=True)
ARCHIVE=OfficialArchive(OUT/"months",delay=3)
GAPS=[("3105.TWO","2025-08","2025-08-01"),("3211.TWO","2017-06","2017-06-03"),
      ("5274.TWO","2017-06","2017-06-03"),("8086.TWO","2017-06","2017-06-03"),
      ("4123.TWO","2017-09","2017-09-30"),("6223.TWO","2017-09","2017-09-30"),
      ("6146.TWO","2021-04","2021-04-06")]
BASIS=[("6146.TWO","2017-08"),("6146.TWO","2018-07"),("8086.TWO","2018-06"),
       ("8086.TWO","2019-06"),("6121.TWO","2017-07"),("6121.TWO","2018-07"),
       ("3552.TWO","2017-08"),("3552.TWO","2018-08"),("3260.TWO","2017-07"),
       ("3260.TWO","2018-07"),("5274.TWO","2019-06"),("6182.TWO","2018-08"),
       ("4123.TWO","2018-08"),("2330.TW","2017-06"),("2330.TW","2017-09"),("2330.TW","2010-01")]

def save(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding="utf8")

def provider(symbol):
    frame=yf.download(symbol,period="10y",interval="1d",auto_adjust=False,repair=False,actions=True,threads=False,progress=False)
    if isinstance(frame.columns,pd.MultiIndex):frame.columns=frame.columns.get_level_values(0)
    frame.index=pd.to_datetime(frame.index)
    if frame.index.tz is not None:frame.index=frame.index.tz_localize(None)
    if frame.empty or frame.index.has_duplicates:raise ValueError("provider empty or duplicate, not treated as passed")
    frame.to_csv(OUT/f"{symbol}_provider_original.csv")
    return frame

def company(symbol):
    endpoint=("https://openapi.twse.com.tw/v1/opendata/t187ap03_L" if symbol.endswith(".TW") else "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O")
    key="公司代號" if symbol.endswith(".TW") else "SecuritiesCompanyCode"
    rows=read_json(endpoint)
    selected=[r for r in rows if str(r.get(key,"")).strip()==symbol.split(".")[0]]
    if len(selected)!=1:raise ValueError("current official directory identity not unique")
    row=selected[0]
    selected_fields={k:v for k,v in row.items() if any(p in k.lower() for p in ("date","日期","companycode","abbreviation","公司代號","公司簡稱","isin"))}
    result={"symbol":symbol,"endpoint":endpoint,"retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),
            "selected_fields":selected_fields,"raw_directory_sha256":hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            "scope":"Current identity/listing-date evidence only; not a complete transfer/delisting/relisting history."}
    save(f"{symbol}_company_identity.json",result)
    # Share the same host throttle with later monthly calls.
    from urllib.parse import urlparse
    ARCHIVE.last_request[urlparse(endpoint).netloc]=time.monotonic()
    return result

def gap_probe():
    report={"scope":"seven known date gaps plus explicitly named basis/control months only", "stocks":[],"errors":[]}
    original={}
    for symbol,month in list(dict.fromkeys([(s,m) for s,m,_ in GAPS]+BASIS)):
        row={"symbol":symbol,"month":month}
        try:
            data=ARCHIVE.get(symbol,month)
            official,evidence=parse_series_month(data["payload"],symbol,month)
            official.to_csv(OUT/f"{symbol}_{month}_official.csv")
            if symbol not in original:original[symbol]=provider(symbol)
            left=pd.Timestamp(month+"-01");right=left+pd.offsets.MonthBegin(1)
            primary=original[symbol].loc[(original[symbol].index>=left)&(original[symbol].index<right)]
            comparison=compare_provider(primary,official) if len(primary) else {"not_comparable":"month outside provider ten-year request or provider empty; not counted as a confirmed provider gap"}
            expected=[d for s,m,d in GAPS if s==symbol and m==month]
            row.update(status="compared",official_bars=len(official),provider_bars=len(primary),
                       expected_gaps=[{"date":d,"official_has_date":pd.Timestamp(d) in official.index,"provider_has_date":pd.Timestamp(d) in primary.index,
                                       "official_row":official.loc[d].to_dict() if pd.Timestamp(d) in official.index else None} for d in expected],
                       evidence=evidence,comparison=comparison,
                       provider_events=original[symbol].loc[(original[symbol].get("Stock Splits",pd.Series(0,index=original[symbol].index))!=0)].reset_index().to_dict("records"),
                       cause="Exact price/volume/date differences recorded; company-action causal chain is not inferred from ratios.")
        except Exception as exc:
            row.update(status="unconfirmed",error=type(exc).__name__+": "+str(exc)[:300])
            report["errors"].append({"symbol":symbol,"month":month,"error":row["error"]})
            if isinstance(exc,HTTPError) and exc.code in (403,429):
                report["stocks"].append(row);save("gap-report.json",report);raise
        report["stocks"].append(row)
        save("gap-report.json",report)
        print(json.dumps({k:row.get(k) for k in ("symbol","month","status","expected_gaps","error")},ensure_ascii=False,default=str),flush=True)
    if report["errors"]:raise SystemExit("Some source comparisons unresolved; see preserved report")

def acquire(symbol,first,last):
    for month in month_range(first+"-01",last+"-01"):
        try:
            data=ARCHIVE.get(symbol,month)
            print(json.dumps({"symbol":symbol,"month":month,"status":"archived","bars":data["evidence"]["bars"]}),flush=True)
        except Exception as exc:
            save(f"{symbol}_acquisition-error.json",{"symbol":symbol,"month":month,"type":type(exc).__name__,"error":str(exc),"no_fallback":True})
            raise

def finalize(symbol):
    start,end="2016-11-07","2026-11-06"
    identity=company(symbol)
    bundles=[ARCHIVE.get(symbol,m) for m in month_range(start,end)]
    frame,manifest=assemble_official_series(symbol,start,end,bundles,route_evidence=identity)
    frame.to_csv(OUT/f"{symbol}_official_daily.csv")
    save(f"{symbol}_manifest.json",manifest)
    if invalid_candles(frame):raise AssertionError("official daily quality failed")
    weekly=aggregate_official_weeks(frame)
    weekly.to_csv(OUT/f"{symbol}_official_weekly.csv")
    primary=provider(symbol)
    comparison=compare_provider(primary,frame)
    save(f"{symbol}_provider_comparison.json",comparison)
    engine,_=load_mirror_engine()
    checks=[]
    for interval,data in (("1d",frame),("1wk",weekly)):
        settings=wave_windows(interval)
        engine.__globals__["WAVES"]=settings
        for name,(_,needed) in settings.items():
            result=engine(data,name,3.,interval)
            item={"interval":interval,"wave":name,"bars":len(data),"reference_bars":needed,"status":"no_pivots"}
            if len(data)<needed:raise AssertionError("Reference history insufficient; do not hide long-wave limitation")
            if result is not None:
                validate_projection(result,float(data.Close.iloc[-1]))
                item.update(status="formula_pass",history_segment=len(result["segment"]),first_projection=float(result["projection"][0]),last_projection=float(result["projection"][-1]))
            checks.append(item)
    # Independent group replay confirms Saturday sessions and exact OHLC/volume aggregation.
    for stamp,row in weekly.iterrows():
        group=frame.loc[(frame.index>=stamp)&(frame.index<stamp+pd.Timedelta(days=7))]
        assert row.Open==group.Open.iloc[0] and row.Close==group.Close.iloc[-1]
        assert row.High==group.High.max() and row.Low==group.Low.min()
        assert row.Volume==group.Volume.sum()
    save(f"{symbol}_validation.json",{"symbol":symbol,"daily_bars":len(frame),"weekly_bars":len(weekly),
          "month_coverage_complete":True,"weekly_aggregation_pass":True,"mirror":checks,
          "no_raw_ohlc_contradictions":True,"production_ready":False,
          "limitations":["Raw unadjusted: capital actions can create non-market price gaps.","Monthly publication is not an independently certified calendar or historical market-transfer chain.","TPEx monthly volume retains published thousand-share precision; no exact single-share claim.","Weekly boundary may be partial; mirror formula pass is not strategy or return validation."]})
    print(json.dumps({"symbol":symbol,"daily_bars":len(frame),"weekly_bars":len(weekly),"mirror":checks},ensure_ascii=False),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=["gaps","acquire","finalize"])
    parser.add_argument("--symbol");parser.add_argument("--first");parser.add_argument("--last");args=parser.parse_args()
    if args.mode=="gaps":gap_probe()
    elif args.mode=="acquire":acquire(args.symbol,args.first,args.last)
    else:finalize(args.symbol)
