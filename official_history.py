"""Traceable official monthly candles and conservative, opt-in close proposals.

No implicit provider fallback, corporate-action conversion or in-place mutation.
"""
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

TWSE_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
TPEX_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"
PRICE_COLUMNS = ["Open", "High", "Low", "Close"]


class OfficialHistoryError(ValueError):
    pass


def request_spec(symbol, month):
    match = re.fullmatch(r"([1-9][0-9]{3})\.(TW|TWO)", str(symbol))
    if not match:
        raise OfficialHistoryError("僅接受明確市場的四碼普通股代碼")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", str(month)):
        raise OfficialHistoryError("年月須為 YYYY-MM")
    try:
        first = date.fromisoformat(month + "-01")
    except ValueError as exc:
        raise OfficialHistoryError("年月無效") from exc
    code, market = match.groups()
    if market == "TW":
        params = {"stockNo": code, "date": first.strftime("%Y%m%d"), "response": "json"}
        return "GET", TWSE_URL, params
    params = {"code": code, "date": first.strftime("%Y/%m/%d"), "response": "json"}
    return "POST", TPEX_URL, params


def _number(value):
    try:
        result = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise OfficialHistoryError("官方數字缺漏或格式無法辨識") from exc
    if not math.isfinite(result):
        raise OfficialHistoryError("官方數字不是有限值")
    return result


def _day(value):
    parts = str(value).strip().split("/")
    if len(parts) != 3:
        raise OfficialHistoryError("官方日期格式不明")
    year, month, day = map(int, parts)
    return pd.Timestamp(date(year + 1911 if year < 1911 else year, month, day))


def invalid_candles(frame):
    if not all(c in frame for c in PRICE_COLUMNS):
        raise OfficialHistoryError("缺少 OHLC 欄位")
    bad = []
    for stamp, row in frame.iterrows():
        try:
            op, hi, lo, cl = [float(row[c]) for c in PRICE_COLUMNS]
            valid = all(math.isfinite(v) and v > 0 for v in (op, hi, lo, cl))
            valid = valid and hi >= max(op, lo, cl) and lo <= min(op, hi, cl)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            bad.append(str(pd.Timestamp(stamp).date()))
    return bad


def _frame_hash(frame):
    values = [[str(stamp.date())] + [float(row[c]) for c in PRICE_COLUMNS + ["Volume", "Turnover"]]
              for stamp, row in frame.iterrows()]
    return hashlib.sha256(json.dumps(values, allow_nan=False).encode()).hexdigest()


def parse_official_month(payload, symbol, month):
    method, endpoint, params = request_spec(symbol, month)
    code, market = symbol.split(".")
    if not isinstance(payload, dict) or str(payload.get("stat", "")).lower() != "ok":
        raise OfficialHistoryError("官方查詢未成功或該月無資料；未改用其他股票")
    expected_date = month.replace("-", "") + "01"
    if str(payload.get("date", "")) != expected_date:
        raise OfficialHistoryError("官方回應月份不符")
    if market == "TW":
        if not re.search(r"(?<![0-9])" + code + r"(?![0-9])", str(payload.get("title", ""))):
            raise OfficialHistoryError("官方回應股票代碼不符")
        table = payload
        field_map = {"日期": "Date", "成交股數": "Volume", "成交金額": "Turnover",
                     "開盤價": "Open", "最高價": "High", "最低價": "Low", "收盤價": "Close"}
        volume_scale, turnover_scale = 1, 1
        precision = "官方股數原值"
    else:
        if str(payload.get("code", "")) != code:
            raise OfficialHistoryError("官方回應股票代碼不符")
        tables = payload.get("tables", [])
        if len(tables) != 1 or str(tables[0].get("date", "")) != expected_date:
            raise OfficialHistoryError("官方月表不完整或月份不符")
        table = tables[0]
        field_map = {"日期": "Date", "成交仟股": "Volume", "成交仟元": "Turnover",
                     "開盤": "Open", "最高": "High", "最低": "Low", "收盤": "Close"}
        volume_scale, turnover_scale = 1000, 1000
        precision = "官方月表仟股／仟元乘1000；不宣稱精確到單股／單元"
    fields = [re.sub(r"\s+", "", str(v)) for v in table.get("fields", [])]
    if len(fields) != len(set(fields)) or not set(field_map).issubset(fields):
        raise OfficialHistoryError("官方欄位已變更或重複，停止解析")
    data = table.get("data", [])
    if not data:
        raise OfficialHistoryError("官方該月沒有資料列")
    parsed, unavailable, seen = [], [], set()
    for values in data:
        if len(values) != len(fields):
            raise OfficialHistoryError("官方資料列長度不符")
        raw = {field_map[k]: values[fields.index(k)] for k in field_map}
        stamp = _day(raw["Date"])
        if stamp.strftime("%Y-%m") != month or stamp in seen:
            raise OfficialHistoryError("官方含跨月或重複日期")
        seen.add(stamp)
        prices = [str(raw[c]).strip() for c in PRICE_COLUMNS]
        missing = [p in ("", "--", "---", "----") for p in prices]
        if all(missing):
            unavailable.append({"date": str(stamp.date()), "raw": raw,
                                "reason": "官方當日未提供一般交易 OHLC；未造出K線"})
            continue
        if any(missing):
            raise OfficialHistoryError("官方 OHLC 部分缺漏")
        row = {c: _number(raw[c]) for c in PRICE_COLUMNS}
        row.update(Date=stamp, Volume=_number(raw["Volume"]) * volume_scale,
                   Turnover=_number(raw["Turnover"]) * turnover_scale)
        if row["Volume"] < 0 or row["Turnover"] < 0:
            raise OfficialHistoryError("官方成交量或金額為負數")
        parsed.append(row)
    if not parsed:
        raise OfficialHistoryError("官方該月沒有可畫出的日K")
    frame = pd.DataFrame(parsed).set_index("Date").sort_index()
    if invalid_candles(frame):
        raise OfficialHistoryError("官方 OHLC 本身有矛盾，停止使用")
    raw_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    evidence = {"symbol": symbol, "month": month, "method": method, "endpoint": endpoint,
                "request": params, "payload_sha256": raw_hash,
                "parsed_frame_sha256": _frame_hash(frame),
                "price_basis": "official_raw_unadjusted", "volume_precision": precision,
                "unavailable_rows": unavailable, "bars": len(frame)}
    frame.attrs["official_evidence"] = evidence
    return frame, evidence


def fetch_official_month(symbol, month):
    method, endpoint, params = request_spec(symbol, month)
    body = urlencode(params).encode() if method == "POST" else None
    url = endpoint + ("?" + urlencode(params) if method == "GET" else "")
    request = Request(url, data=body, method=method,
                      headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    frame, evidence = parse_official_month(payload, symbol, month)
    evidence["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    return frame, evidence, payload


def compare_month_sources(symbol, month):
    import yfinance as yf
    official, evidence, payload = fetch_official_month(symbol, month)
    start = pd.Timestamp(month + "-01")
    end = start + pd.DateOffset(months=1)
    source = yf.download(symbol, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                         interval="1d", auto_adjust=False, progress=False, threads=False)
    if isinstance(source.columns, pd.MultiIndex):
        source.columns = source.columns.get_level_values(0)
    if source.empty:
        raise OfficialHistoryError("Yahoo該月無資料，不能宣稱修正通過")
    source.index = pd.to_datetime(source.index)
    if source.index.tz is not None:
        source.index = source.index.tz_localize(None)
    source.attrs = {"symbol": symbol, "price_basis": "yahoo_auto_adjust_false"}
    repaired, ledger = preview_close_repairs(source, official, evidence)
    return official, source, repaired, ledger, evidence, payload


def month_differences(source, official):
    differences = []
    for stamp in sorted(set(source.index) & set(official.index)):
        for field in PRICE_COLUMNS:
            left, right = float(source.loc[stamp, field]), float(official.loc[stamp, field])
            if not math.isfinite(left) or abs(left - right) > .005:
                differences.append({"date": str(stamp.date()), "field": field,
                                    "source": left if math.isfinite(left) else None, "official": right})
    return differences


def preview_close_repairs(source, official, evidence):
    """Only invalid Close with matching O/H/L anchors; never convert price basis.

    Same-date O/H/L agreement is the conservative anchor, not a claim that
    every historical corporate action has been verified. Original is preserved.
    """
    symbol, month = evidence.get("symbol"), evidence.get("month")
    method, endpoint, params = request_spec(symbol, month)
    if evidence.get("method") != method or evidence.get("endpoint") != endpoint or evidence.get("request") != params:
        raise OfficialHistoryError("官方請求證據不符")
    if source.attrs.get("symbol") != symbol or source.attrs.get("price_basis") != "yahoo_auto_adjust_false":
        raise OfficialHistoryError("來源股票或價格基準不明，不能混補")
    if evidence.get("price_basis") != "official_raw_unadjusted" or not re.fullmatch(r"[0-9a-f]{64}", evidence.get("payload_sha256", "")):
        raise OfficialHistoryError("缺少官方來源與價格基準證據")
    if official.attrs.get("official_evidence") != evidence:
        raise OfficialHistoryError("官方資料與來源證據不相符")
    for frame in (source, official):
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is not None or frame.index.has_duplicates:
            raise OfficialHistoryError("來源時間索引不明、含時區或重複")
        if not frame.index.equals(frame.index.normalize()) or not frame.index.is_monotonic_increasing:
            raise OfficialHistoryError("僅接受排序後的日K日期，不接受盤中時間")
        if not all(c in frame for c in PRICE_COLUMNS):
            raise OfficialHistoryError("來源缺少 OHLC")
        if any(stamp.strftime("%Y-%m") != month for stamp in frame.index):
            raise OfficialHistoryError("修正預覽僅接受指定月份，不跨月混補")
    if not all(c in official for c in ("Volume", "Turnover")) or _frame_hash(official) != evidence.get("parsed_frame_sha256"):
        raise OfficialHistoryError("官方資料解析後曾被改動")
    if invalid_candles(official):
        raise OfficialHistoryError("官方資料本身異常")
    result = source.copy(deep=True)
    ledger = []
    for stamp, row in source.iterrows():
        if stamp not in official.index:
            continue
        values = [float(row[c]) for c in PRICE_COLUMNS]
        op, hi, lo, close = values
        # Missing/negative OHL cannot establish a shared unit of price.
        if not all(math.isfinite(v) and v > 0 for v in values) or hi < max(op, lo) or lo > min(op, hi):
            continue
        if math.isfinite(close) and lo <= close <= hi and close > 0:
            continue
        reference = official.loc[stamp]
        if not all(abs(float(row[c]) - float(reference[c])) <= .005 for c in ("Open", "High", "Low")):
            continue
        # Replacement must also fit the original candle bounds exactly.
        official_close = float(reference["Close"])
        corrected = min(max(official_close, lo), hi)
        if abs(corrected - official_close) > .00001:
            continue
        result.loc[stamp, "Close"] = corrected
        ledger.append({"symbol": symbol, "date": str(stamp.date()),
                       "original_close": close if math.isfinite(close) else None,
                       "official_close": official_close, "applied_close": corrected,
                       "float_alignment_delta": corrected - official_close,
                       "anchor": "same-date O/H/L within 0.005; boundary float alignment at most 0.00001",
                       "endpoint": evidence["endpoint"], "payload_sha256": evidence["payload_sha256"]})
    if ledger:
        result.attrs["price_basis"] = "yahoo_with_official_close_preview"
        result.attrs["repair_ledger"] = ledger
    return result, ledger
