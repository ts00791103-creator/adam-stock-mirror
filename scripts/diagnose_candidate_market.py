"""Read-only raw/provider/adjustment/official corporate-action diagnosis."""
import ast, hashlib, json, sys, types, calendar
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import pandas as pd
import numpy as np
import yfinance as yf
from curl_cffi import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from official_history import fetch_official_month, invalid_candles, request_spec
OUT=ROOT/"candidate-market-output";OUT.mkdir(exist_ok=True)
SUBJECTS=["3105.TWO","3260.TWO","5274.TWO","8299.TWO","3227.TWO","6182.TWO","4123.TWO","6274.TWO","1565.TWO","3211.TWO","3529.TWO","8358.TWO"]
CONTROLS=["2330.TW","2002.TW","6643.TWO","6530.TWO"]
REPORT={"retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),"request":{"period":"10y","interval":"1d","auto_adjust":False,"actions":False},"subjects":SUBJECTS,"controls":CONTROLS,"stocks":[],"official_months":[],"policy":"Read only; no source repairs or deletion. Original and actual get_data-normalized frames retained."}
# Execute only the repository's real daily-normalization and audit functions.
tree=ast.parse((ROOT/"app.py").read_text(encoding="utf-8"))
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("get_data","raw_quote_summary","audit_ohlc_data")]
for n in nodes:n.decorator_list=[]
scope={"pd":pd,"np":np}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"app_daily_pipeline","exec"),scope)
def flat(df):
    df=df.copy()
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    df.index=pd.to_datetime(df.index)
    if df.index.tz is not None:df.index=df.index.tz_localize(None)
    return df
def vals(row):
    return {c:float(row[c]) if pd.notna(row[c]) else None for c in ("Open","High","Low","Close","Adj Close") if c in row}
def post(endpoint,params):
    req=Request(endpoint,data=urlencode(params).encode(),headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urlopen(req,timeout=25) as response:return json.load(response)
actions={}
def official_actions(month):
    if month not in actions:
        year,mon=map(int,month.split("-"))
        params={"startDate":f"{year}/{mon:02}/01","endDate":f"{year}/{mon:02}/{calendar.monthrange(year,mon)[1]}","response":"json"}
        payload=post("https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ",params)
        (OUT/("official_actions_"+month+".json")).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        records=[]
        for table in payload.get("tables",[]):
            fields=table.get("fields",[])
            for values in table.get("data",[]):records.append(dict(zip(fields,values)))
        actions[month]={"records":records,"endpoint":"https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ","request":params,"sha256":hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    return actions[month]
for symbol in SUBJECTS+CONTROLS:
    row={"symbol":symbol,"sample":"subject" if symbol in SUBJECTS else "control"}
    try:
        raw=flat(yf.download(symbol,period="10y",interval="1d",auto_adjust=False,progress=False,threads=False))
        if raw.empty:raise ValueError("empty primary response")
        raw.to_csv(OUT/(symbol+"_raw.csv"))
        scope["yf"]=types.SimpleNamespace(download=lambda *a,**kw:raw.copy(deep=True))
        processed=scope["get_data"](symbol,"10y","1d")
        processed.to_csv(OUT/(symbol+"_processed.csv"))
        bad=invalid_candles(processed)
        row.update(bars=len(raw),processed_bars=len(processed),first=str(raw.index[0].date()),last=str(raw.index[-1].date()),
            invalid_dates=bad,gate_messages=scope["audit_ohlc_data"](processed),
            finite_ohlc_unchanged=bool(raw[["Open","High","Low","Close"]].equals(processed[["Open","High","Low","Close"]])),
            invalid_rows=[{"date":str(t.date()),"original":vals(raw.loc[t]),"processed":vals(processed.loc[t])} for t in processed.index if str(t.date()) in bad])
        variants={}
        meta=None
        for mode,kwargs in (("actions_metadata",{"auto_adjust":False,"actions":True}),("auto_adjust",{"auto_adjust":True}),("back_adjust",{"auto_adjust":False,"back_adjust":True}),("repair",{"auto_adjust":False,"repair":True})):
            try:
                frame=flat(yf.download(symbol,period="10y",interval="1d",progress=False,threads=False,**kwargs))
                if frame.empty:raise ValueError("empty adjusted or repair response; verification incomplete")
                frame.to_csv(OUT/(symbol+"_"+mode+".csv"))
                if mode=="actions_metadata":meta=frame
                variants[mode]={"bars":len(frame),"invalid_count":len(invalid_candles(frame)),"invalid_dates":invalid_candles(frame)[:20],"target_rows":[{"date":d,**vals(frame.loc[pd.Timestamp(d)])} for d in bad if pd.Timestamp(d) in frame.index]}
            except Exception as exc:variants[mode]={"error":type(exc).__name__+": "+str(exc)[:220]}
        row["variants"]=variants
        if meta is not None:
            row["provider_actions"]=[{"date":str(t.date()),"dividend":float(r.get("Dividends",0)),"split":float(r.get("Stock Splits",0))}
                for t,r in meta.iterrows() if r.get("Dividends",0)!=0 or r.get("Stock Splits",0)!=0]
        try:
            params={"period1":int((raw.index[0]-pd.Timedelta(days=1)).tz_localize("Asia/Taipei").timestamp()),"period2":int(pd.Timestamp.now(tz="UTC").timestamp()),"interval":"1d","events":"div,splits","includeAdjustedClose":"true"}
            url="https://query1.finance.yahoo.com/v8/finance/chart/"+symbol
            response=requests.get(url,params=params,impersonate="chrome",timeout=25);response.raise_for_status()
            payload=response.json();(OUT/(symbol+"_yahoo_chart.json")).write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
            result=payload["chart"]["result"][0];quote=result["indicators"]["quote"][0]
            dates=pd.to_datetime(result["timestamp"],unit="s",utc=True).tz_convert("Asia/Taipei").tz_localize(None).normalize()
            direct=pd.DataFrame({c:quote[c.lower()] for c in ("Open","High","Low","Close")},index=dates)
            row["direct_yahoo"]={"endpoint":url,"request":params,"target_rows":[{"date":d,**vals(direct.loc[pd.Timestamp(d)])} for d in bad if pd.Timestamp(d) in direct.index],
                "matches_library_at_targets":all(all(abs(float(direct.loc[pd.Timestamp(d),c])-float(raw.loc[pd.Timestamp(d),c]))<1e-8 for c in ("Open","High","Low","Close")) for d in bad if pd.Timestamp(d) in direct.index)}
        except Exception as exc:row["direct_yahoo"]={"error":type(exc).__name__+": "+str(exc)[:220]}
        for month in sorted(set(d[:7] for d in bad)):
            item={"symbol":symbol,"month":month,"targets":[]}
            try:
                official,evidence,payload=fetch_official_month(symbol,month)
                (OUT/("official_"+symbol+"_"+month+".json")).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                item["evidence"]=evidence
                item["month_ohl_max_difference"]=max(abs(float(raw.loc[t,c])-float(official.loc[t,c])) for t in official.index if t in raw.index for c in ("Open","High","Low"))
                event_months=[month,(pd.Timestamp(month+"-01")+pd.DateOffset(months=1)).strftime("%Y-%m")]
                event_records=[]
                for event_month in event_months:
                    evidence_actions=official_actions(event_month)
                    event_records.extend([{**event,"_source_endpoint":evidence_actions["endpoint"],"_payload_sha256":evidence_actions["sha256"]} for event in evidence_actions["records"] if str(event.get("代號","")).strip()==symbol.split(".")[0]])
                for d in bad:
                    if d[:7]!=month:continue
                    stamp=pd.Timestamp(d);target={"date":d,"original":vals(raw.loc[stamp]),"processed":vals(processed.loc[stamp])}
                    if stamp in official.index:target["official"]=vals(official.loc[stamp])
                    target["official_corporate_actions"]=event_records
                    item["targets"].append(target)
                item["status"]="official prices and action records queried; no source change"
            except Exception as exc:item.update(status="official verification incomplete",error=type(exc).__name__+": "+str(exc)[:220])
            REPORT["official_months"].append(item)
        from verified_daily_history import verify_daily_closes
        verified=verify_daily_closes(symbol,processed)
        verified.to_csv(OUT/(symbol+"_candidate.csv"))
        row["candidate"]={"bars":len(verified),"gate_messages":scope["audit_ohlc_data"](verified),"invalid_dates":invalid_candles(verified),"verification":verified.attrs.get("official_close_verification"),"all_non_close_fields_unchanged":bool(processed.drop(columns="Close").equals(verified.drop(columns="Close")))}
        row["status"]="blocked" if row["gate_messages"] else "price quality passed"
    except Exception as exc:row.update(status="unconfirmed",error=type(exc).__name__+": "+str(exc)[:240])
    REPORT["stocks"].append(row)
(OUT/"report.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding="utf-8")
print("CANDIDATE_MARKET_DIAGNOSTIC="+json.dumps(REPORT,ensure_ascii=False),flush=True)
