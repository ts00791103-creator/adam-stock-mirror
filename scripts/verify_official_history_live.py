"""Bounded four-month source diagnostic, with exactly the candidate preview core."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from official_history import compare_month_sources, invalid_candles

folder = ROOT / "history-source-output"
folder.mkdir(exist_ok=True)
rows = []
for symbol, month in (("8358.TWO", "2018-06"), ("2924.TWO", "2021-12"),
                      ("3095.TWO", "2021-12"), ("2330.TW", "2026-11")):
    row = {"symbol": symbol, "month": month, "status": "unconfirmed"}
    try:
        official, original, repaired, ledger, evidence, payload = compare_month_sources(symbol, month)
        row.update(official_bars=len(official), source_bars=len(original),
                   before_invalid_dates=invalid_candles(original), after_invalid_dates=invalid_candles(repaired),
                   proposals=ledger, evidence=evidence,
                   source_missing_official_dates=[str(d.date()) for d in sorted(set(official.index)-set(original.index))],
                   source_extra_unverified_dates=[str(d.date()) for d in sorted(set(original.index)-set(official.index))])
        differences = []
        for stamp in sorted(set(official.index) & set(original.index)):
            ref = official.loc[stamp]
            for field in ("Open", "High", "Low", "Close"):
                if abs(float(original.loc[stamp, field])-float(ref[field])) > .005:
                    differences.append({"date": str(stamp.date()), "field": field,
                                        "official": float(ref[field]), "source": float(original.loc[stamp, field]),
                                        "preview": float(repaired.loc[stamp, field])})
        row["dated_differences"] = differences
        row["status"] = "compared; preview only, not whole-history repair"
        (folder/f"official_{symbol}_{month}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        original.to_csv(folder/f"original_{symbol}_{month}.csv")
        official.to_csv(folder/f"official_{symbol}_{month}.csv")
        repaired.to_csv(folder/f"preview_{symbol}_{month}.csv")
    except Exception as exc:
        row["error"] = type(exc).__name__ + ": " + str(exc)[:240]
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
(folder/"report.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
print("OFFICIAL_HISTORY_SUMMARY="+json.dumps([{k:r.get(k) for k in ("symbol","month","status","before_invalid_dates","after_invalid_dates","error")} for r in rows],ensure_ascii=False),flush=True)
if any(r["status"] == "unconfirmed" for r in rows):
    raise SystemExit("source verification incomplete; see saved report")
