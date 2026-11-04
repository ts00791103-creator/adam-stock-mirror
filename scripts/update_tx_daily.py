"""Collect TAIFEX free daily TX report. Daily snapshots only; no historical backfill."""
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://openapi.taifex.com.tw/v1/DailyMarketReportFut"
OUTPUT = Path("data/tx_daily_official.csv")
FIELDS = ["Date", "Session", "ContractMonth", "Open", "High", "Low", "Close", "Volume", "FetchedUTC"]

def pick(row, *keys):
    for key in keys:
        if key in row and str(row[key]).strip() not in ("", "-", "None"):
            return str(row[key]).strip()
    return ""

def parse_date(value):
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) == 8:
        return datetime.strptime(digits, "%Y%m%d").strftime("%Y-%m-%d")
    return ""

def parse_num(value):
    try:
        return float(value.replace(",", ""))
    except (ValueError, AttributeError):
        return None

def normalize(row):
    contract = pick(row, "Contract", "契約", "契約代號", "ContractCode")
    if contract != "TX":
        return None
    month = pick(row, "ContractMonth(Week)", "ContractMonth", "到期月份(週別)", "到期月份")
    if not (len(month) == 6 and month.isdigit() and month.startswith("20")):
        return None
    day = parse_date(pick(row, "Date", "交易日期", "日期"))
    session_raw = pick(row, "TradingSession", "交易時段", "Session")
    session = "一般" if session_raw in ("一般", "Regular", "0", "1") else ("盤後" if session_raw in ("盤後", "AfterHours", "2") else "")
    if not day or not session:
        return None
    vals = [parse_num(pick(row, *keys)) for keys in (
        ("Open", "開盤價"), ("High", "最高價"), ("Low", "最低價"),
        ("Last", "Close", "收盤價", "最後成交價"), ("Volume", "成交量", "合計成交量"))]
    if any(v is None for v in vals):
        return None
    return dict(zip(FIELDS, [day, session, month, *vals, datetime.now(timezone.utc).isoformat(timespec="seconds")]))

def main():
    req = Request(URL, headers={"User-Agent": "B3Pro-OfficialData/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("TAIFEX API did not return a JSON list")
    rows = [r for raw in payload if isinstance(raw, dict) if (r := normalize(raw))]
    if not rows:
        print("API sample keys:", list(payload[0]) if payload and isinstance(payload[0], dict) else "empty")
        raise ValueError("No TX monthly-contract daily rows; check official API schema")
    stored = {}
    if OUTPUT.exists():
        with OUTPUT.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if all(row.get(k) for k in ("Date", "Session", "ContractMonth")):
                    stored[(row["Date"], row["Session"], row["ContractMonth"])] = row
    for row in rows:
        stored[(row["Date"], row["Session"], row["ContractMonth"])] = row
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(stored[k] for k in sorted(stored))
    new_content = buffer.getvalue()
    previous = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
    if new_content != previous:
        OUTPUT.write_text(new_content, encoding="utf-8")
    print(f"Official TX records: {len(rows)}; stored: {len(stored)}; latest: {max(r['Date'] for r in rows)}")

if __name__ == "__main__":
    main()
