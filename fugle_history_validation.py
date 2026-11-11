"""Read-only, bounded Fugle daily-history validation against a frozen TPEx sample.

No API credentials, raw HTTP errors, or paid responses are logged/persisted.
This module is not imported by any trading, notification or production loader.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

import pandas as pd

SYMBOLS = {"5474": "聰泰", "6708": "天擎", "9962": "有益"}
START, END = "2025-11-11", "2026-11-11"
FIELDS = ("Open", "High", "Low", "Close")
ENDPOINT = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/"
DOC_URL = "https://developer.fugle.tw/docs/data/http-api/historical/candles/"
BASELINE = Path(__file__).parent / "docs/evidence/tpex-fugle-baseline-20261111"
VERSION = "FUGLE-HISTORY-20261111-1"
PRICE_TOLERANCE = 0.005
VOLUME_NOTE = ("富果日K以股計、含鉅額交易；TPEx月表以張計且不含鉅額。"
               "張數乘1000僅對齊單位，不能還原逐股精度。未取得逐日鉅額明細，"
               "量差只列觀察，不能直接判錯或全部歸因鉅額。")


class ValidationError(ValueError):
    """Only fixed, secret-free messages may be supplied."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward X-API-KEY to a different URL, including same-host redirects.
        raise ValidationError("API重新導向，已停止；未轉送金鑰。")


def chunks(start=START, end=END):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValidationError("日期範圍錯誤。")
    result = []
    while first <= last:
        stop = min(first + timedelta(days=182), last)
        result.append((first.isoformat(), stop.isoformat()))
        first = stop + timedelta(days=1)
    return result


def request_parameters(symbol, start, end):
    if symbol not in SYMBOLS or (start, end) not in chunks():
        raise ValidationError("僅允許本次三檔及固定一年區間。")
    return {"from": start, "to": end, "timeframe": "D", "adjusted": "false",
            "fields": "open,high,low,close,volume", "sort": "asc"}


def _number(value, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("富果數字格式無效。")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValidationError("富果數字不是有限非負值。")
    return value


def parse_payload(payload, symbol, start, end):
    request_parameters(symbol, start, end)
    if not isinstance(payload, dict) or payload.get("symbol") != symbol:
        raise ValidationError("富果回傳股票不符。")
    if payload.get("timeframe") != "D" or payload.get("exchange") != "TPEx":
        raise ValidationError("富果週期或交易所不符。")
    if payload.get("market", "OTC") != "OTC" or payload.get("type", "EQUITY") != "EQUITY":
        raise ValidationError("富果市場或證券類型不符。")
    if "adjusted" in payload and payload["adjusted"] is not False:
        raise ValidationError("富果回傳還原價，不可與官方原始價混比。")
    if payload.get("sort") != "asc":
        raise ValidationError("富果排序方向不符。")
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValidationError("富果未提供資料，不能宣稱通過。")
    seen, rows = set(), []
    for item in data:
        if not isinstance(item, dict):
            raise ValidationError("富果資料列格式無效。")
        day = item.get("date")
        if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            raise ValidationError("日K必須回傳交易日期，不接受盤中時間戳。")
        try:
            date.fromisoformat(day)
        except ValueError:
            raise ValidationError("富果交易日期無效。") from None
        if not start <= day <= end or day in seen:
            raise ValidationError("富果日期超出分段範圍或重複。")
        seen.add(day)
        if any(field.lower() not in item for field in FIELDS):
            raise ValidationError("富果缺少OHLC欄位。")
        row = {"Date": day, **{field: _number(item[field.lower()], True) for field in FIELDS},
               "Volume": _number(item.get("volume"))}
        if not row["Volume"].is_integer():
            raise ValidationError("富果日K成交股數非整數。")
        row["Volume"] = int(row["Volume"])
        row["valid_ohlc"] = valid_ohlc(row)
        rows.append(row)
    if [r["Date"] for r in rows] != sorted(seen):
        raise ValidationError("富果資料未依宣告日期升冪排列。")
    return rows


def valid_ohlc(row):
    vals = [row.get(field) for field in FIELDS]
    if any(v is None or not math.isfinite(float(v)) or v <= 0 for v in vals):
        return False
    op, hi, lo, cl = vals
    return hi >= max(op, lo, cl) and lo <= min(op, hi, cl)


def load_baseline(symbol):
    if symbol not in SYMBOLS:
        raise ValidationError("不支援的驗證股票。")
    manifest = json.loads((BASELINE / "manifest.json").read_text())
    info = manifest["baseline_files"][symbol]
    raw = (BASELINE / info["name"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != info["sha256"]:
        raise ValidationError("官方基準檔案校驗失敗。")
    frame = pd.read_csv(io.BytesIO(raw))
    rows = json.loads(frame.to_json(orient="records"))
    if len(rows) != info["rows"] or len({r["Date"] for r in rows}) != len(rows):
        raise ValidationError("官方基準筆數或日期不符。")
    if any(not START <= r["Date"] <= END for r in rows):
        raise ValidationError("官方基準日期超出本次範圍。")
    return rows, {"sha256": info["sha256"], "source": manifest["source"],
                  "retrieved_utc": manifest["retrieved_utc"],
                  "known_no_ohlc_dates": manifest["known_no_ohlc_dates"][symbol],
                  "known_nontrading_date": manifest["known_nontrading_date"]}


def fetch_segment(symbol, start, end, api_key):
    params = request_parameters(symbol, start, end)
    req = Request(ENDPOINT + symbol + "?" + urlencode(params),
                  headers={"X-API-KEY": api_key, "Accept": "application/json"})
    started = time.monotonic()
    with build_opener(NoRedirect()).open(req, timeout=20) as response:
        # Bounded read. Never put headers, request objects or raw bodies in evidence.
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValidationError("富果回應超出大小限制。")
        status = response.status
    payload = json.loads(raw)
    rows = parse_payload(payload, symbol, start, end)
    evidence = {"symbol": symbol, "endpoint": ENDPOINT + symbol, "parameters": params,
                "http_status": status, "rows": len(rows),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "adjusted_response": payload.get("adjusted", "omitted"),
                "price_basis": "adjusted=false explicitly requested"}
    return rows, evidence


def compare_rows(symbol, fugle, official, evidence):
    if len({r["Date"] for r in fugle}) != len(fugle):
        raise ValidationError("分段合併出現重複日期，停止比對。")
    f = {r["Date"]: r for r in fugle}
    o = {r["Date"]: r for r in official}
    valid_f, valid_o = {d for d, r in f.items() if valid_ohlc(r)}, {d for d, r in o.items() if valid_ohlc(r)}
    same = sorted(valid_f & valid_o)
    mismatches, volumes, day_rows = [], [], []
    for day in sorted(set(f) | set(o) | {evidence["known_nontrading_date"]}):
        fr, ore = f.get(day), o.get(day)
        item = {"Date": day, "Fugle_row": fr is not None, "TPEx_row": ore is not None,
                "Fugle_valid_OHLC": day in valid_f, "TPEx_valid_OHLC": day in valid_o}
        if day == evidence["known_nontrading_date"]:
            item["observation"] = "2026-10-23休市檢查；若有K線須另查，不自動刪除或補值"
        elif ore and day not in valid_o:
            item["observation"] = "官方無OHLC；保留缺值，不以富果價格自動填補"
        elif day not in o:
            item["observation"] = "富果多出官方未列日期；原因待核對"
        elif day not in f:
            item["observation"] = "富果缺少官方日期"
        elif day not in valid_f:
            item["observation"] = "富果OHLC缺值或矛盾，未納入價格一致統計"
        else:
            item["observation"] = "同日比較"
        for field in FIELDS:
            item["Fugle_" + field] = fr.get(field) if fr else None
            item["TPEx_" + field] = ore.get(field) if ore else None
            if day in same and abs(fr[field] - ore[field]) > PRICE_TOLERANCE:
                mismatches.append({"Date": day, "field": field,
                                   "Fugle": fr[field], "TPEx": ore[field]})
        item["Fugle_volume_shares"] = fr["Volume"] if fr else None
        item["TPEx_volume_lots"] = ore["Volume_lots"] if ore else None
        item["TPEx_scaled_shares"] = ore["Volume_shares_scaled"] if ore else None
        if fr and ore:
            diff = fr["Volume"] - ore["Volume_shares_scaled"]
            item["volume_difference_shares"] = diff
            volumes.append({"Date": day, "Fugle_shares": fr["Volume"],
                            "TPEx_lots": ore["Volume_lots"], "TPEx_scaled_shares": ore["Volume_shares_scaled"],
                            "difference_shares": diff})
        day_rows.append(item)
    summary = {"symbol": symbol, "name": SYMBOLS[symbol], "fugle_rows": len(f),
               "fugle_valid_ohlc": len(valid_f), "official_rows": len(o),
               "official_valid_ohlc": len(valid_o), "shared_valid_dates": len(same),
               "price_fields_compared": len(same) * 4, "price_mismatch_fields": len(mismatches),
               "price_mismatch_dates": len({r['Date'] for r in mismatches}),
               "fugle_missing_official_dates": sorted(set(o) - set(f)),
               "fugle_extra_dates": sorted(set(f) - set(o)),
               "fugle_invalid_or_missing_ohlc_dates": sorted(set(f) - valid_f),
               "official_no_ohlc_dates": sorted(set(o) - valid_o),
               "official_valid_dates_without_fugle_valid_ohlc": sorted(valid_o - valid_f),
               "volume_dates_compared": len(volumes),
               "volume_differing_dates": sum(v["difference_shares"] != 0 for v in volumes),
               "volume_difference_min": min((v['difference_shares'] for v in volumes), default=None),
               "volume_difference_max": max((v['difference_shares'] for v in volumes), default=None),
               "latest_fugle_date": max(f, default=None),
               "latest_fugle": f[max(f)] if f else None,
               "closure_2026_10_23_fugle_present": "2026-10-23" in f,
               "volume_note": VOLUME_NOTE}
    return {"summary": summary, "baseline_evidence": evidence,
            "price_differences": mismatches, "daily_comparison": day_rows}


def run_validation(api_key, fetcher=fetch_segment, sleeper=time.sleep):
    """At most six serial read requests; first failure stops the entire batch."""
    report = {"version": VERSION, "range": {"from": START, "to": END},
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "running", "requests": [], "samples": [], "errors": [],
              "limitations": [VOLUME_NOTE, "本次固定三個非隨機樣本，不能外推全市場或長期穩定性。",
                              "不改寫歷史、選股、提醒或交易。當日鉅額通常18:00後併入，延後公布可能更晚。"],
              "documentation": DOC_URL,
              "methodology": {"price_basis": "unadjusted; adjusted=false explicitly requested",
                              "ohlc_absolute_tolerance_twd": PRICE_TOLERANCE,
                              "request_cap": "6 per explicit run; serial within one run",
                              "date_basis": "Taiwan trading date YYYY-MM-DD; no timezone shift or filling"}}
    if not api_key:
        report.update(status="blocked", errors=[{"reason": "尚未設定富果金鑰。"}])
        return report
    for symbol in SYMBOLS:
        try:
            official, reference = load_baseline(symbol)
            rows = []
            for start, end in chunks():
                if report["requests"]:
                    sleeper(1.1)
                attempted = {"symbol": symbol, "from": start, "to": end, "status": "started"}
                report["requests"].append(attempted)
                data, evidence = fetcher(symbol, start, end, api_key)
                attempted.update(evidence, status="completed")
                rows.extend(data)
            report["samples"].append(compare_rows(symbol, rows, official, reference))
        except Exception as exc:
            # No exception repr, URL, response body or header may escape this boundary.
            if isinstance(exc, HTTPError):
                reason = {401: "富果未授權；請在平台安全檢查既有金鑰。",
                          403: "富果拒絕存取；目前帳號可能無歷史日K權限。",
                          429: "富果速率限制；已停止，未自動重試。",
                          404: "富果此分段查無資料；不當作成功。"}.get(exc.code, "富果HTTP請求失敗。")
                error = {"symbol": symbol, "http_status": exc.code, "reason": reason}
            elif isinstance(exc, ValidationError):
                error = {"symbol": symbol, "reason": str(exc)}
            else:
                error = {"symbol": symbol, "reason": "連線、JSON或基準讀取失敗；已停止，未自動重試。"}
            report["errors"].append(error)
            if report["requests"] and report["requests"][-1]["status"] == "started":
                report["requests"][-1]["status"] = "failed"
            report["status"] = "stopped"
            break
    else:
        report["status"] = "completed"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report
