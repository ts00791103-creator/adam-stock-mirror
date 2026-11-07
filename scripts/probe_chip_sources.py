"""Read-only official schema probe: no credentials and no trading."""
import json
from pathlib import Path
import requests

urls = {
 "twse_institution": "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date=20261106&selectType=ALLBUT0999",
 "twse_margin": "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN",
 "tpex_institution": "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading",
 "tpex_margin": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance",
 "twse_margin_dated": "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20261106&selectType=ALL&response=json",
 "twse_margin_past": "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20261030&selectType=ALL&response=json",
 "tpex_margin_dated": "https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php?l=zh-tw&d=115/11/06&o=json",
}
out = {}
for name, url in urls.items():
 try:
  response=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
  response.raise_for_status()
  body=response.json()
  if isinstance(body,list):
   out[name]={"count":len(body),"rows":body[:2]}
  elif name=="tpex_schema":
   paths=body.get("paths",{})
   out[name]={p:v for p,v in paths.items() if any(x in p.lower() for x in ("3inst","margin_balance"))}
  else:
   out[name]={"stat":body.get("stat"),"date":body.get("date"),"fields":body.get("fields"),"sample":body.get("data",[])[:2],"keys":list(body),"tables":[{"title":t.get("title"),"fields":t.get("fields"),"rows":t.get("data",[])[:1]} for t in body.get("tables",[])],"aaData":body.get("aaData",[])[:1],"reportDate":body.get("reportDate"),"reports":[{"title":t.get("title"),"fields":t.get("fields"),"rows":t.get("data",[])[:1]} for t in body.get("reports",[])]}
 except Exception as exc:
  out[name]={"error":str(exc)[:250]}
Path("diagnostics").mkdir(exist_ok=True)
Path("diagnostics/chip_sources.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False))
