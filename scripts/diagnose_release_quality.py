"""Read-only replay of seven newly reported OTC cases with unchanged candidate rules."""
import ast, hashlib, json, sys, types
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from curl_cffi import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import verified_daily_history as verified
from official_history import fetch_official_month, invalid_candles
OUT=ROOT/"release-quality-output";OUT.mkdir(exist_ok=True)
CASES={"5483.TWO":["2017-07-21"],"6146.TWO":["2017-08-01","2018-07-18","2021-04-22"],
"8086.TWO":["2017-06-23","2018-06-25","2019-06-24"],"3324.TWO":["2017-07-06","2018-07-23"],
"6121.TWO":["2017-07-12","2018-07-11"],"6223.TWO":["2017-09-06"],"3552.TWO":["2017-08-23","2018-08-15"]}
report={"retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),"sample":"New seven only; separate from previous twelve and original thirty.",
"request":{"period":"10y","interval":"1d","auto_adjust":False,"repair":False},
"runtime_source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ("production_quality_preview.py","verified_daily_history.py","analysis_availability.py")},
"stocks":[],"official_months":[]}
tree=ast.parse((ROOT/"production_quality_preview.py").read_text(encoding="utf-8"))
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("get_data","raw_quote_summary","audit_ohlc_data","get_analysis_data")]
for n in nodes:n.decorator_list=[]
scope={"pd":pd,"np":np,"PRODUCTION_MODE":True}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"exact_candidate_daily_pipeline","exec"),scope)
def flat(data):
    frame=data.copy(deep=True)
    if isinstance(frame.columns,pd.MultiIndex):frame.columns=frame.columns.get_level_values(0)
    frame.index=pd.to_datetime(frame.index)
    if frame.index.tz is not None:frame.index=frame.index.tz_localize(None)
    return frame
def values(row):
    return {c:float(row[c]) if pd.notna(row[c]) else None for c in ("Open","High","Low","Close","Adj Close","Volume") if c in row}
month_cache={};action_cache={}
original_action_fetch=verified.fetch_official_actions
def record_month(symbol,month):
    key=(symbol,month)
    if key not in month_cache:
        result=fetch_official_month(symbol,month)
        (OUT/("official_"+symbol+"_"+month+".json")).write_text(json.dumps(result[2],ensure_ascii=False,indent=2),encoding="utf-8")
        month_cache[key]=result
    return month_cache[key]
def record_actions(month):
    if month not in action_cache:
        bundle=original_action_fetch(month)
        (OUT/("official_actions_"+month+".json")).write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding="utf-8")
        action_cache[month]=bundle
    return action_cache[month]
verified.fetch_official_month=record_month
verified.fetch_official_actions=record_actions
for symbol,reported_dates in CASES.items():
    row={"symbol":symbol,"reported_dates":reported_dates}
    try:
        raw=flat(yf.download(symbol,period="10y",interval="1d",auto_adjust=False,progress=False,threads=False))
        if raw.empty:raise ValueError("empty primary response; not passed")
        raw.to_csv(OUT/(symbol+"_raw.csv"))
        scope["yf"]=types.SimpleNamespace(download=lambda *args,**kw:raw.copy(deep=True))
        processed=scope["get_data"](symbol,"10y","1d")
        processed.to_csv(OUT/(symbol+"_processed.csv"))
        before=invalid_candles(processed)
        candidate=scope["get_analysis_data"](symbol,"10y","1d")
        candidate.to_csv(OUT/(symbol+"_candidate.csv"))
        after=invalid_candles(candidate)
        verification=candidate.attrs.get("official_close_verification",{})
        row.update(raw_bars=len(raw),processed_bars=len(processed),candidate_bars=len(candidate),
          first=str(raw.index[0].date()),last=str(raw.index[-1].date()),raw_gate=scope["audit_ohlc_data"](processed),
          candidate_gate=scope["audit_ohlc_data"](candidate),raw_invalid_dates=before,candidate_invalid_dates=after,
          reported_not_reproduced=[d for d in reported_dates if d not in before],
          additional_raw_invalid_dates=[d for d in before if d not in reported_dates],
          original_processed_prices_identical=raw[["Open","High","Low","Close"]].equals(processed[["Open","High","Low","Close"]]),
          non_close_fields_unchanged=processed.drop(columns="Close").equals(candidate.drop(columns="Close")),
          original_frame_restorable=verified.original_frame(candidate).equals(processed),verification=verification)
        targets=sorted(set(reported_dates+before))
        row["prices"]=[{"date":d,"original":values(raw.loc[pd.Timestamp(d)]) if pd.Timestamp(d) in raw.index else None,
          "processed":values(processed.loc[pd.Timestamp(d)]) if pd.Timestamp(d) in processed.index else None,
          "candidate":values(candidate.loc[pd.Timestamp(d)]) if pd.Timestamp(d) in candidate.index else None} for d in targets]
        try:
            metadata=flat(yf.download(symbol,period="10y",interval="1d",auto_adjust=False,actions=True,repair=False,progress=False,threads=False))
            if metadata.empty:raise ValueError("empty metadata response")
            row["provider_actions"]=[{"date":str(t.date()),"dividend":float(r.get("Dividends",0)),"split":float(r.get("Stock Splits",0))}
                 for t,r in metadata.iterrows() if r.get("Dividends",0)!=0 or r.get("Stock Splits",0)!=0]
        except Exception as exc:row["provider_action_error"]=type(exc).__name__+": "+str(exc)[:220]
        try:
            params={"period1":int((raw.index[0]-pd.Timedelta(days=1)).tz_localize("Asia/Taipei").timestamp()),
                    "period2":int(pd.Timestamp.now(tz="UTC").timestamp()),"interval":"1d","events":"div,splits","includeAdjustedClose":"true"}
            endpoint="https://query1.finance.yahoo.com/v8/finance/chart/"+symbol
            response=requests.get(endpoint,params=params,impersonate="chrome",timeout=25);response.raise_for_status()
            payload=response.json();(OUT/(symbol+"_yahoo_chart.json")).write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
            result=payload["chart"]["result"][0];quote=result["indicators"]["quote"][0]
            dates=pd.to_datetime(result["timestamp"],unit="s",utc=True).tz_convert("Asia/Taipei").tz_localize(None).normalize()
            direct=pd.DataFrame({c:quote[c.lower()] for c in ("Open","High","Low","Close")},index=dates)
            compared=[{"date":d,**values(direct.loc[pd.Timestamp(d)])} for d in targets if pd.Timestamp(d) in direct.index]
            row["direct_yahoo"]={"endpoint":endpoint,"request":params,"target_rows":compared,
             "all_reported_targets_present":len(compared)==len(targets),
             "matches_library":len(compared)==len(targets) and all(all(abs(float(direct.loc[pd.Timestamp(d),c])-float(raw.loc[pd.Timestamp(d),c]))<1e-8 for c in ("Open","High","Low","Close")) for d in targets)}
        except Exception as exc:row["direct_yahoo"]={"error":type(exc).__name__+": "+str(exc)[:220]}
        for month in sorted(set(d[:7] for d in targets)):
            item={"symbol":symbol,"month":month,"targets":[]}
            try:
                official,evidence,payload=record_month(symbol,month)
                item["evidence"]=evidence
                sm=processed.loc[processed.index.strftime("%Y-%m")==month]
                item["source_missing_dates"]=[str(t.date()) for t in official.index.difference(sm.index)]
                item["source_extra_dates"]=[str(t.date()) for t in sm.index.difference(official.index)]
                item["month_ohl_max_difference"]=max(abs(float(sm.loc[t,c])-float(official.loc[t,c])) for t in sm.index.intersection(official.index) for c in ("Open","High","Low"))
                for d in targets:
                    if d[:7]!=month:continue
                    stamp=pd.Timestamp(d);target={"date":d,"official":values(official.loc[stamp]) if stamp in official.index else None}
                    target["original"]=values(processed.loc[stamp]) if stamp in processed.index else None
                    target["candidate"]=values(candidate.loc[stamp]) if stamp in candidate.index else None
                    if stamp in processed.index:
                        pos=processed.index.get_loc(stamp)
                        if pos+1<len(processed):
                            ex_date=processed.index[pos+1];bundle=record_actions(ex_date.strftime("%Y-%m"))
                            expected=f"{ex_date.year-1911:03}/{ex_date.month:02}/{ex_date.day:02}"
                            records=[]
                            for table in bundle["payload"].get("tables",[]):
                                for vals in table.get("data",[]):
                                    entry=dict(zip(table.get("fields",[]),vals))
                                    if str(entry.get("代號","")).strip()==symbol.split(".")[0]:records.append(entry)
                            target["official_corporate_actions"]={"expected_next_source_date":str(ex_date.date()),"records":records,"evidence":{k:v for k,v in bundle.items() if k!="payload"}}
                    item["targets"].append(target)
                item["status"]="official queried; unchanged candidate rules"
            except Exception as exc:item.update(status="unconfirmed",error=type(exc).__name__+": "+str(exc)[:220])
            report["official_months"].append(item)
        row["status"]="blocked" if row["candidate_gate"] else "available"
    except Exception as exc:row.update(status="unconfirmed",error=type(exc).__name__+": "+str(exc)[:240])
    report["stocks"].append(row)
(OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("ADDITIONAL_SEVEN="+json.dumps(report,ensure_ascii=False),flush=True)
