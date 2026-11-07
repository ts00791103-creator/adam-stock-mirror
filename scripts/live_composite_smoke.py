"""Read-only live acceptance on two named stocks; not a whole-market ranking."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import yfinance as yf
from market_universe import fetch_universe, history_as_of
from chip_sources import fetch_institution, fetch_margin
from composite_strategy import combine_factors, price_factors, rank_rows

results, errors=fetch_universe(("上市","上櫃"))
out={"scope":"僅2308與3163驗證，不是全市場排名","errors":errors,"sources":{},"rows":[]}
for market in results:
 exchange=market["市場"]
 days={r["官方行情日期"] for r in market["rows"]}
 if len(days)!=1:
  out["errors"].append({"市場":exchange,"原因":"日期不同"}); continue
 day=next(iter(days)); info={"date":day}
 try:
  chips=fetch_institution(exchange,day); info["institution_rows"]=len(chips)
 except Exception as exc:
  chips={}; info["institution_error"]=str(exc)[:180]
 try:
  margins=fetch_margin(exchange,day); info["margin_rows"]=len(margins)
 except Exception as exc:
  margins={}; info["margin_error"]=str(exc)[:180]
 out["sources"][exchange]=info
 code="2308" if exchange=="上市" else "3163"
 item=next((r for r in market["rows"] if r["代號"]==code),None)
 if not item: continue
 try:
  frame=history_as_of(yf.Ticker(item["Yahoo代號"]).history(period="1y",interval="1d",auto_adjust=False,timeout=10),day)
  five=price_factors(frame,day)["5日前日期"]
  try:
   past=fetch_margin(exchange,five).get(code) if code in margins else None
  except Exception as exc:
   past=None; info["margin_5d_error"]=str(exc)[:180]
  out["rows"].append(combine_factors(item,frame,chips.get(code),margins.get(code),past))
 except Exception as exc:
  out["errors"].append({"代號":code,"原因":str(exc)[:180]})
if len({r["資料日期"] for r in out["rows"]})==1:
 out["sample_ranking"]=rank_rows(out["rows"])
Path("diagnostics").mkdir(exist_ok=True)
Path("diagnostics/composite_live.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False))
if len(out["rows"])!=2: raise SystemExit("Two-stock live acceptance incomplete")
