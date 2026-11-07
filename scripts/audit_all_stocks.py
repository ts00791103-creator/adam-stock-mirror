"""Read-only production-data audit. This is NOT a browser UI acceptance test."""
import argparse
import ast
from collections import Counter
import csv
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "production-source"
sys.path.insert(0, str(PROD))
import numpy as np
import pandas as pd
import yfinance as yf
from market_universe import SOURCES, read_json, number, trading_date, normalize_market
from quote_quality import invalid_price_rows
from initial_navigation import queue_initial, consume_initial

OUT = ROOT / "audit-output"
OUT.mkdir(exist_ok=True)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def snapshot():
    report = {"retrieved_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
              "production_sha": "6ef07921465a9b4f50a2dce8c4c71935ef10b6be",
              "ui_status": "not tested by this diagnostic", "markets": [], "rows": []}
    for exchange in ("上市", "上櫃"):
        companies = read_json(SOURCES[exchange][0])
        quotes = read_json(SOURCES[exchange][1])
        normalized = normalize_market(companies, quotes, exchange)
        code_key, name_key = (("公司代號", "公司簡稱") if exchange == "上市"
                              else ("SecuritiesCompanyCode", "CompanyAbbreviation"))
        quote_key = "Code" if exchange == "上市" else "SecuritiesCompanyCode"
        raw_quotes = {str(r.get(quote_key, "")).strip(): r for r in quotes}
        valid = {r["代號"]: r for r in normalized["rows"]}
        failures = {r["代號"]: r["原因"] for r in normalized["failures"]}
        import re
        directory = {str(r.get(code_key, "")).strip(): r for r in companies
                     if re.fullmatch(r"[1-9][0-9]{3}", str(r.get(code_key, "")).strip())}
        for code, company in sorted(directory.items()):
            row = dict(valid.get(code, {"代號": code, "名稱": str(company.get(name_key, "")),
                       "市場": exchange, "Yahoo代號": code + (".TW" if exchange == "上市" else ".TWO")}))
            row["official_raw"] = raw_quotes.get(code)
            row["official_issue"] = failures.get(code, "")
            report["rows"].append(row)
        report["markets"].append({"exchange": exchange, "companies": len(directory),
                                  "valid_quotes": len(valid), "failures": normalized["failures"],
                                  "sources": list(SOURCES[exchange])})
    symbols = [r["Yahoo代號"] for r in report["rows"]]
    assert len(symbols) == len(set(symbols)), "duplicate universe symbols"
    write_json(OUT / "universe.json", report)
    print(json.dumps({"companies": len(symbols), "markets": report["markets"]}, ensure_ascii=False), flush=True)


def audit_shard(shard, count):
    universe = json.loads((OUT / "universe.json").read_text(encoding="utf-8"))
    tree = ast.parse((PROD / "app.py").read_text(encoding="utf-8"))
    definition = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "audit_ohlc_data")
    namespace = {"pd": pd, "np": np}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), "<production-quality>", "exec"), namespace)
    audit = namespace["audit_ohlc_data"]
    rows = universe["rows"][shard::count]
    path = OUT / f"shard-{shard}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for i, source in enumerate(rows):
            row = {k: v for k, v in source.items() if k != "official_raw"}
            row["ui_status"] = "not browser-tested"
            try:
                state = {}
                queue_initial(state, source)
                context = consume_initial(state)
                row["navigation_logic_match"] = bool(context["symbol"] == source["Yahoo代號"]
                    and state["adam_stock_query"] == source["代號"]
                    and state["initial_chart_context"]["symbol"] == source["Yahoo代號"])
                if source["official_issue"]:
                    row["status"] = "official unavailable"
                else:
                    keys = ({"Open": "OpeningPrice", "High": "HighestPrice", "Low": "LowestPrice", "Close": "ClosingPrice"}
                            if source["市場"] == "上市" else {k: k for k in ("Open", "High", "Low", "Close")})
                    raw = source["official_raw"]
                    day = trading_date(raw.get("Date", ""))
                    row["official_ohlc"] = {field: number(raw.get(key)) for field, key in keys.items()}
                    df = pd.DataFrame()
                    for attempt in range(2):
                        df = yf.download(source["Yahoo代號"], period="10y", interval="1d",
                                         auto_adjust=False, progress=False, threads=False, timeout=15)
                        if not df.empty:
                            break
                        time.sleep(2)
                    if df.empty:
                        raise ValueError("no historical candles after two attempts")
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    row["raw_duplicate_times"] = int(df.index.duplicated().sum())
                    df = df.dropna(subset=["Close"]).sort_index().copy()
                    df.index = pd.to_datetime(df.index)
                    if df.index.tz is not None:
                        df.index = df.index.tz_localize(None)
                    df = df[~df.index.duplicated(keep="last")]
                    row["history_10y_bars"] = len(df)
                    row["history_10y_issues"] = audit(df)
                    row["history_10y_invalid_rows"] = invalid_price_rows(df, limit=20)
                    cutoff = pd.Timestamp.now(tz="Asia/Taipei").tz_localize(None) - pd.DateOffset(years=5)
                    five = df.loc[df.index >= cutoff.normalize()]
                    row["history_5y_bars"] = len(five)
                    row["history_5y_issues"] = audit(five)
                    row["history_5y_invalid_rows"] = invalid_price_rows(five, limit=20)
                    row["yahoo_latest_date"] = str(df.index[-1].date())
                    dated = df.loc[df.index.normalize() == pd.Timestamp(day)]
                    if len(dated) != 1:
                        raise ValueError("official date has no unique historical candle")
                    row["yahoo_dated_ohlc"] = {field: float(dated.iloc[0][field]) for field in keys}
                    row["dated_ohlc_match"] = all(abs(row["yahoo_dated_ohlc"][k] - row["official_ohlc"][k]) <= .005 for k in keys)
                    row["close_match"] = abs(row["yahoo_dated_ohlc"]["Close"] - row["official_ohlc"]["Close"]) <= .005
                    row["status"] = "dated OHLC matched" if row["dated_ohlc_match"] else "dated OHLC mismatch"
            except Exception as exc:
                row["status"] = "unconfirmed"
                row["error"] = type(exc).__name__ + ": " + str(exc)[:240]
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"shard={shard} {i+1}/{len(rows)} {row['Yahoo代號']} {row['status']}", flush=True)
            time.sleep(.5)


def aggregate():
    universe = json.loads((OUT / "universe.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for path in sorted(OUT.glob("shard-*.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = {r["Yahoo代號"] for r in universe["rows"]}
    actual = [r["Yahoo代號"] for r in rows]
    missing = sorted(expected - set(actual))
    assert len(actual) == len(set(actual)), "duplicate results"
    summary = {"expected": len(expected), "recorded": len(rows), "missing": missing,
               "status_counts": dict(Counter(r["status"] for r in rows)),
               "navigation_logic_pass": sum(r.get("navigation_logic_match") is True for r in rows),
               "ten_year_quality_blocked": sum(bool(r.get("history_10y_issues")) for r in rows),
               "five_year_quality_blocked": sum(bool(r.get("history_5y_issues")) for r in rows),
               "browser_ui_tested_by_this_run": 0}
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "all_stocks.json", {"snapshot": {k: v for k, v in universe.items() if k != "rows"},
                                        "summary": summary, "rows": rows})
    fields = ["代號", "名稱", "市場", "Yahoo代號", "官方行情日期", "官方收盤", "status", "close_match",
              "dated_ohlc_match", "navigation_logic_match", "history_10y_bars", "history_10y_issues",
              "history_5y_bars", "history_5y_issues", "official_issue", "error", "ui_status"]
    with (OUT / "all_stocks.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["市場"], r["代號"])):
            writer.writerow({k: row.get(k, "") for k in fields})
    print("ALL_MARKET_SUMMARY=" + json.dumps(summary, ensure_ascii=False), flush=True)
    assert not missing, "incomplete audit; do not label full coverage"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["snapshot", "audit", "aggregate"])
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    {"snapshot": snapshot, "audit": lambda: audit_shard(args.shard, args.count), "aggregate": aggregate}[args.mode]()
