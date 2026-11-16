"""Single-request-pair diagnostics for Fugle regular-lot intraday data."""

import json
import re
from math import isfinite
from datetime import datetime, time, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from fugle_history_validation import NoRedirect



TAIPEI = timezone(timedelta(hours=8))
BASE = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/"


def _request(path, api_key):
    request = Request(BASE + path, headers={"X-API-KEY": api_key, "Accept": "application/json"})
    with build_opener(NoRedirect()).open(request, timeout=7) as response:
        return json.load(response)


def _identity(symbol, timeframe):
    match = re.fullmatch(r"([0-9]{4,6}[A-Za-z]?)\.(TW|TWO)", symbol)
    if not match or timeframe not in (1, 5):
        raise ValueError("僅支援已選上市櫃商品及 1／5 分 K。")
    code, market = match.groups()
    return code, ("TWSE", "TSE") if market == "TW" else ("TPEx", "OTC")


def _regular_quantity(value):
    # Both endpoints count only on-session whole-lot trades in this request.
    if type(value) is not int or value < 0:
        raise ValueError("整股成交量缺漏或不是非負整數。")
    return value


def check_snapshot(candles, quote, symbol, timeframe, now):
    code, market = _identity(symbol, timeframe)
    if now.utcoffset() is None:
        raise ValueError("查核時間缺時區。")
    now = now.astimezone(TAIPEI)
    trade_day = now.date()
    for payload in (candles, quote):
        if (not isinstance(payload, dict) or payload.get("symbol") != code
                or (payload.get("exchange"), payload.get("market")) != market
                or payload.get("date") != trade_day.isoformat()):
            raise ValueError("富果商品、交易所、盤別或交易日不符。")
    if str(candles.get("timeframe")) != str(timeframe) or not candles.get("data"):
        raise ValueError("富果週期或分 K 資料不符。")

    interval = timedelta(minutes=timeframe)
    opening = datetime.combine(trade_day, time(9), TAIPEI)
    closing = datetime.combine(trade_day, time(13, 30), TAIPEI)
    bars = []
    for i, item in enumerate(candles["data"]):
        stamp = datetime.fromisoformat(item["date"])
        if stamp.utcoffset() is None or stamp != opening + i * interval:
            raise ValueError("分 K 開棒時間缺時區、缺棒、重複或未依序。")
        prices = tuple(item[field] for field in ("open", "high", "low", "close"))
        if not all(type(value) in (int, float) and isfinite(value) for value in prices):
            raise ValueError("分 K OHLC 無效。")
        first, high, low, last = prices
        if not 0 < low <= min(first, last) <= max(first, last) <= high:
            raise ValueError("分 K OHLC 無效。")
        bars.append((stamp, _regular_quantity(item["volume"])))
    total = quote["total"]
    quote_volume = _regular_quantity(total["tradeVolume"])
    seconds = total["time"]
    if type(seconds) is not int or seconds <= 0:
        raise ValueError("日內報價缺少有效統計時間。")
    quote_time = datetime.fromtimestamp(seconds / 1_000_000, TAIPEI)
    end = bars[-1][0] + interval
    result = dict(symbol=symbol, timeframe=timeframe, unit="張", first_bar=bars[0][0].isoformat(),
                  last_bar_start=bars[-1][0].isoformat(), expected_bar_end=end.isoformat(),
                  obtained_at=now.isoformat(), quote_time=quote_time.isoformat(),
                  quote_age_seconds=(now - quote_time).total_seconds(), quote_volume=quote_volume,
                  bar_count=len(bars), candles_volume=sum(volume for _, volume in bars),
                  eligibility="延遲及收棒狀態未核實，當沖不可判定。")

    if bars[-1][0] >= closing or not bars[-1][0] <= quote_time < end or quote_time > now:
        result["status"] = "待核：分 K 與統計截點不同"
    elif end > now:
        result["status"] = "待核：最新分 K 時間尚未結束"
    elif now - quote_time > interval:
        result["status"] = "待核：統計時間已過期"
    else:
        result["difference"] = result["candles_volume"] - quote_volume
        result["status"] = "同時段量一致" if result["difference"] == 0 else "待核：同時段量不符"
    return result


def run_intraday_check(symbol, timeframe, api_key):
    if not api_key:
        return {"status": "本機沒有可用的富果授權設定"}
    try:
        code, _ = _identity(symbol, timeframe)
        candles = _request(f"candles/{code}?timeframe={timeframe}&sort=asc", api_key)
        quote = _request(f"quote/{code}", api_key)
        return check_snapshot(candles, quote, symbol, timeframe, datetime.now(TAIPEI))
    except HTTPError as exc:
        return {"status": f"富果查詢未通過（HTTP {exc.code}）"}
    except (OSError, URLError, TypeError, ValueError, KeyError, OverflowError):
        return {"status": "富果回應、盤別或資料品質驗證未通過"}
