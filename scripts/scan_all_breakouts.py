"""Read-only all-company scan. No credentials, messages, orders or state commits."""
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yfinance as yf
from market_universe import SOURCES, read_json
from entry_alerts import AlertSettings, evaluate_entry_alerts


def directory(exchange):
    import re
    rows = read_json(SOURCES[exchange][0])
    code_key, name_key = (("公司代號", "公司簡稱") if exchange == "上市"
                          else ("SecuritiesCompanyCode", "CompanyAbbreviation"))
    names = {}
    for row in rows:
        code = str(row.get(code_key, "")).strip()
        if re.fullmatch(r"[1-9][0-9]{3}", code):
            names[code] = str(row.get(name_key) or row.get("公司名稱") or row.get("CompanyName") or code)
    if not names:
        raise ValueError("Official company directory unavailable")
    return [{"代號": code, "名稱": name, "市場": exchange,
             "股票": code + (".TW" if exchange == "上市" else ".TWO")}
            for code, name in sorted(names.items())]


def inspect(row, day, settings):
    result = dict(row, 核對日期=day, 狀態="未判定", 行情日期="", 收盤="", 原因="")
    events = []
    try:
        frame = yf.Ticker(row["股票"]).history(period="1y", interval="1d", auto_adjust=False,
                                               actions=False, timeout=15, raise_errors=True)
        if frame.empty:
            result["原因"] = "無歷史行情"
            return result, events
        result["行情日期"] = str(frame.index[-1].date())
        if result["行情日期"] != day:
            result["原因"] = "最新行情非核對日期"
            return result, events
        events = evaluate_entry_alerts(frame, row["股票"], day, settings, rules=("箱頂突破",))
        result.update(狀態="突破成立" if events else "未符合", 收盤=round(float(frame.Close.iloc[-1]), 4))
        for event in events:
            event.update(名稱=row["名稱"], 市場=row["市場"])
    except Exception:
        # No arbitrary exception content, credentials or provider request URLs in reports.
        result["原因"] = "歷史不足、價格品質異常或來源讀取失敗"
    return result, events


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    now = datetime.now(ZoneInfo("Asia/Taipei"))
    day = now.date().isoformat()
    if now.weekday() >= 5 or now.hour < 14:
        raise SystemExit("Only weekday after-close scans; no scan performed")
    settings = AlertSettings()
    universe, directory_failures = [], []
    for exchange in ("上市", "上櫃"):
        try:
            universe.extend(directory(exchange))
        except Exception:
            directory_failures.append(exchange)
    if not universe:
        raise SystemExit("Both company directories unavailable")
    print("SCAN_START " + json.dumps({"as_of": day, "companies": len(universe),
                                      "directory_failures": directory_failures,
                                      "settings": asdict(settings)}, ensure_ascii=False), flush=True)
    results, events = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(inspect, row, day, settings) for row in universe]
        for job in as_completed(jobs):
            result, found = job.result()
            results.append(result)
            events.extend(found)
            print("SCAN_ROW " + json.dumps(result, ensure_ascii=False), flush=True)
            for event in found:
                print("SCAN_EVENT " + json.dumps(event, ensure_ascii=False), flush=True)
            if len(results) % 100 == 0:
                print("SCAN_PROGRESS " + str(len(results)), flush=True)
    results.sort(key=lambda row: row["股票"])
    events.sort(key=lambda event: event["股票"])
    summary = {"as_of": day, "companies": len(universe), "processed": len(results),
               "unconfirmed": sum(r["狀態"] == "未判定" for r in results),
               "triggered": len(events), "directory_failures": directory_failures,
               "settings": asdict(settings), "completed_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat()}
    output = Path("reports/all-breakouts")
    output.mkdir(parents=True, exist_ok=True)
    fields = ["代號", "名稱", "市場", "股票", "核對日期", "狀態", "行情日期", "收盤", "原因"]
    write_csv(output / "all_checked.csv", results, fields)
    write_csv(output / "unconfirmed.csv", [r for r in results if r["狀態"] == "未判定"], fields)
    write_csv(output / "breakouts.csv", events, ["股票", "名稱", "市場", "行情日期", "觀察價", "既有箱底", "既有箱頂", "相對成交量", "前20日均量（張）", "觸發原因", "提醒編號"])
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SCAN_SUMMARY " + json.dumps(summary, ensure_ascii=False), flush=True)
    if directory_failures or len(results) != len(universe):
        raise SystemExit("Incomplete directory coverage; review report")


if __name__ == "__main__":
    main()
