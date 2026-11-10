"""Official Taiwan daily snapshots followed by bounded historical screening."""
import json
import math
import re
from datetime import date
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor


SOURCES = {
    "上市": ("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
           "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"),
    "上櫃": ("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
           "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"),
}


def read_json(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(request, timeout=12) as response:
        rows = json.load(response)
    if not isinstance(rows, list) or not rows:
        raise ValueError("官方來源未提供有效清單")
    return rows


def trading_date(value):
    digits = re.sub(r"[^0-9]", "", str(value))
    if len(digits) == 7:
        year, month, day = int(digits[:3])+1911, int(digits[3:5]), int(digits[5:])
    elif len(digits) == 8:
        year, month, day = int(digits[:4]), int(digits[4:6]), int(digits[6:])
    else:
        raise ValueError("行情日期缺失或格式不明")
    return date(year, month, day).isoformat()


def number(value):
    result = float(str(value).replace(",", "").strip())
    if not math.isfinite(result):
        raise ValueError("無效數字")
    return result


def normalize_market(companies, quotes, exchange):
    # Use the company directory, not all securities: exclude ETFs, warrants and emerging stocks.
    company_code, company_name, abbreviation = (("公司代號", "公司名稱", "公司簡稱") if exchange == "上市"
                                                else ("SecuritiesCompanyCode", "CompanyName", "CompanyAbbreviation"))
    names = {str(r.get(company_code, "")).strip(): str(r.get(abbreviation) or r.get(company_name, "")).strip()
             for r in companies if re.fullmatch(r"[1-9][0-9]{3}", str(r.get(company_code, "")).strip())}
    if not names:
        raise ValueError("公司名單無法辨識，未使用少數備援股票冒充全市場")
    code_key, close_key, volume_key = (("Code", "ClosingPrice", "TradeVolume") if exchange == "上市"
                                       else ("SecuritiesCompanyCode", "Close", "TradingShares"))
    found, failures = {}, []
    for quote in quotes:
        code = str(quote.get(code_key, "")).strip()
        if code not in names:
            continue
        try:
            close, volume = number(quote.get(close_key)), number(quote.get(volume_key))
            if close <= 0 or volume < 0:
                raise ValueError("無有效收盤價或成交量")
            day = trading_date(quote.get("Date", ""))
            found[code] = {"代號": code, "名稱": names[code], "市場": exchange,
                           "Yahoo代號": code + (".TW" if exchange == "上市" else ".TWO"),
                           "官方行情日期": day, "官方收盤": close,
                           "官方當日成交量（張）": round(volume/1000, 3)}
        except (TypeError, ValueError, OverflowError):
            failures.append({"市場": exchange, "代號": code, "原因": "官方價格、成交量或日期無法辨識"})
    failed_codes = {r["代號"] for r in failures}
    for code in names.keys() - found.keys() - failed_codes:
        failures.append({"市場": exchange, "代號": code, "原因": "公司名單有此股票，但本次無每日行情（可能停牌或資料缺漏）"})
    if not found:
        raise ValueError("沒有可辨識的官方每日行情，請稍後重試")
    return {"市場": exchange, "公司數": len(names), "rows": list(found.values()), "failures": failures}


def fetch_market(exchange):
    company_url, quote_url = SOURCES[exchange]
    return normalize_market(read_json(company_url), read_json(quote_url), exchange)


def fetch_universe(exchanges):
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {exchange: pool.submit(fetch_market, exchange) for exchange in exchanges}
        for exchange, future in jobs.items():
            try:
                results.append(future.result())
            except Exception:
                errors.append({"市場": exchange, "原因": "官方公司名單或每日行情暫時無法讀取，該市場未納入"})
    return results, errors


def shortlist(results, minimum, maximum, min_daily_lots):
    rows = [r for result in results for r in result["rows"]
            if minimum <= r["官方收盤"] <= maximum and r["官方當日成交量（張）"] >= min_daily_lots]
    return sorted(rows, key=lambda r: (-r["官方當日成交量（張）"], r["Yahoo代號"]))


def history_as_of(frame, day):
    """Never mix a snapshot from one day with later historical candles."""
    import pandas as pd
    data = frame.copy()
    index = pd.to_datetime(data.index)
    if index.tz is not None:
        index = index.tz_convert("Asia/Taipei").tz_localize(None)
    data.index = index
    target = pd.Timestamp(day)
    data = data.loc[data.index.normalize() <= target].sort_index()
    if data.empty or data.index[-1].normalize() != target:
        raise ValueError("歷史日K缺少官方行情日期，本次不判定")
    return data


def fetch_dated_market(exchange, day):
    """Load the requested completed session from an exchange's dated report."""
    listed = exchange == "上市"
    digits = day.strftime("%Y%m%d")
    if listed:
        url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?date={digits}&response=json&type=ALLBUT0999"
        fields = ("證券代號", "收盤價", "成交股數")
        keys = ("Code", "ClosingPrice", "TradeVolume")
    else:
        formatted = day.strftime("%Y/%m/%d")
        url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={formatted}&response=json"
        fields = ("代號", "收盤", "成交股數")
        keys = ("SecuritiesCompanyCode", "Close", "TradingShares")
    try:
        companies = read_json(SOURCES[exchange][0])
    except (ValueError, OSError) as exc:
        raise ValueError("官方公司名單讀取失敗") from exc
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urlopen(request, timeout=12) as response:
            payload = json.load(response)
    except (ValueError, OSError) as exc:
        raise ValueError("指定日期收盤報表讀取失敗") from exc
    if str(payload.get("stat", "")).lower() != "ok" or payload.get("date") != digits:
        raise ValueError("指定日期尚無收盤報表或來源日期不符")
    table = next((t for t in payload.get("tables", [])
                  if t.get("data") and set(fields).issubset(t.get("fields", []))), None)
    if table is None:
        raise ValueError("指定日期收盤報表缺少必要欄位或行情")
    indices = [table["fields"].index(field) for field in fields]
    quotes = [dict(zip(keys, (row[i] for i in indices)), Date=digits)
              for row in table["data"]]
    return normalize_market(companies, quotes, exchange)


def fetch_dated_universe(exchanges, day):
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {exchange: pool.submit(fetch_dated_market, exchange, day) for exchange in exchanges}
        for exchange, future in jobs.items():
            try:
                results.append(future.result())
            except ValueError as exc:
                errors.append({"市場": exchange, "原因": f"{day}｜{exc}"})
            except Exception as exc:
                errors.append({"市場": exchange, "原因": f"{day}｜官方報表解析失敗（{type(exc).__name__}）"})
    return results, errors
