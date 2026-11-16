"""Single-request-pair diagnostics for Fugle regular-lot intraday data."""

import json
import re
from math import isfinite
from datetime import date, datetime, time, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from fugle_history_validation import NoRedirect, ValidationError

TAIPEI = timezone(timedelta(hours=8))
BASE = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/"
UNVERIFIED = "延遲及收棒狀態未核實，當沖不可判定。"


class CheckError(ValueError):
    """Transportable diagnostic fields are assigned by this module, never by Fugle."""

    def __init__(self, endpoint, code, field=None, **details):
        super().__init__(code)
        self.report = {"endpoint": endpoint, "code": code, **details}
        if field:
            self.report["field"] = field


def _required(payload, key, endpoint, field=None):
    name = field or key
    if not isinstance(payload, dict):
        raise CheckError(endpoint, "INVALID_OBJECT", name)
    if key not in payload or payload[key] is None:
        raise CheckError(endpoint, "MISSING_FIELD", name)
    return payload[key]


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


def _regular_quantity(value, endpoint, field):
    # JSON number can be written as 200 or 200.0; neither permits fractional lots.
    if type(value) not in (int, float) or not isfinite(value) or value < 0 or value != int(value):
        raise CheckError(endpoint, "INVALID_LOTS", field)
    return int(value)


def _validate_header(payload, endpoint, code, market, trade_day):
    value = _required(payload, "date", endpoint)
    try:
        source_day = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise CheckError(endpoint, "INVALID_DATE", "date") from None
    if source_day != trade_day:
        raise CheckError(endpoint, "DATE_MISMATCH", "date", data_date=source_day.isoformat(),
                         requested_date=trade_day.isoformat())
    if _required(payload, "symbol", endpoint) != code:
        raise CheckError(endpoint, "SYMBOL_MISMATCH", "symbol")
    if _required(payload, "exchange", endpoint) != market[0]:
        raise CheckError(endpoint, "EXCHANGE_MISMATCH", "exchange")
    market_value = payload.get("market")
    if market_value != market[1] and (endpoint == "quote" or market_value is not None):
        raise CheckError(endpoint, "MISSING_FIELD" if market_value is None else "MARKET_MISMATCH", "market")


def _quote_stats(quote):
    total = _required(quote, "total", "quote")
    volume = _required(total, "tradeVolume", "quote", "total.tradeVolume")
    lots = _regular_quantity(volume, "quote", "total.tradeVolume")
    microseconds = _required(total, "time", "quote", "total.time")
    if type(microseconds) is not int or microseconds <= 0:
        raise CheckError("quote", "INVALID_STAT_TIME", "total.time")
    try:
        return lots, datetime.fromtimestamp(microseconds / 1_000_000, TAIPEI)
    except (ValueError, OverflowError, OSError):
        raise CheckError("quote", "INVALID_STAT_TIME", "total.time") from None


def _reported_close(quote, scheduled_close, last_possible_close, now):
    value = quote.get("closeTime")
    if quote.get("isClose") is not True or type(value) is not int or value <= 0:
        return None
    try:
        stamp = datetime.fromtimestamp(value / 1_000_000, TAIPEI)
    except (ValueError, OverflowError, OSError):
        return None
    if scheduled_close <= stamp <= min(last_possible_close, now):
        return stamp.isoformat()
    return None


def check_snapshot(candles, quote, symbol, timeframe, now):
    code, market = _identity(symbol, timeframe)
    if now.utcoffset() is None:
        raise ValueError("查核時間缺時區。")
    now = now.astimezone(TAIPEI)
    trade_day = now.date()
    _validate_header(candles, "candles", code, market, trade_day)
    if str(_required(candles, "timeframe", "candles")) != str(timeframe):
        raise CheckError("candles", "TIMEFRAME_MISMATCH", "timeframe")
    items = _required(candles, "data", "candles")
    if not isinstance(items, list) or not items:
        raise CheckError("candles", "INVALID_OR_EMPTY_BARS", "data")

    interval = timedelta(minutes=timeframe)
    opening = datetime.combine(trade_day, time(9), TAIPEI)
    auction = datetime.combine(trade_day, time(13, 25), TAIPEI)
    closing = datetime.combine(trade_day, time(13, 30), TAIPEI)
    latest_close = closing + timedelta(minutes=3)
    bars = []
    for item in items:
        value = _required(item, "date", "candles", "data[].date")
        try:
            stamp = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            raise CheckError("candles", "INVALID_BAR_TIME", "data[].date") from None
        if stamp.utcoffset() is None:
            raise CheckError("candles", "BAR_TIMEZONE_MISSING", "data[].date")
        stamp = stamp.astimezone(TAIPEI)
        if (not opening <= stamp <= min(latest_close, now)
                or (stamp < closing and (stamp - opening) % interval)):
            raise CheckError("candles", "BAR_TIME_OFF_GRID", "data[].date")
        if bars and stamp <= bars[-1][0]:
            raise CheckError("candles", "BAR_TIME_ORDER", "data[].date", bar_count=len(items))
        prices = tuple(_required(item, field, "candles", f"data[].{field}")
                       for field in ("open", "high", "low", "close"))
        if not all(type(value) in (int, float) and isfinite(value) for value in prices):
            raise CheckError("candles", "INVALID_OHLC", "data[].OHLC")
        first, high, low, last = prices
        if not 0 < low <= min(first, last) <= max(first, last) <= high:
            raise CheckError("candles", "INVALID_OHLC", "data[].OHLC")
        volume = _required(item, "volume", "candles", "data[].volume")
        bars.append((stamp, _regular_quantity(volume, "candles", "data[].volume")))

    first_start, last_start = bars[0][0], bars[-1][0]
    present = {stamp for stamp, _ in bars}
    last_regular = min(last_start, closing - interval)
    expected = [opening + i * interval for i in range((last_regular - opening) // interval + 1)]
    missing = [stamp for stamp in expected if stamp not in present]
    regular_gaps = [stamp.isoformat() for stamp in missing if stamp < auction]
    auction_gaps = [stamp.isoformat() for stamp in missing if stamp >= auction]
    coverage = dict(data_date=trade_day.isoformat(), first_bar=first_start.isoformat(),
                    last_bar_start=last_start.isoformat(), bar_count=len(bars), missing_bars=len(missing),
                    missing_bar_times=regular_gaps, auction_window_gap_times=auction_gaps)
    try:
        _validate_header(quote, "quote", code, market, trade_day)
        quote_volume, quote_time = _quote_stats(quote)
    except CheckError as exc:
        exc.report.update({k: v for k, v in coverage.items() if k not in exc.report})
        raise
    end = last_start + interval if last_start < closing else None
    kind = "closing_auction" if end is None else "closing_auction_window" if last_start >= auction else "regular"
    state = "regular_session"
    if quote.get("isClose") is True:
        state = "closed"
    elif quote.get("isDelayedClose") is True:
        state = "delayed_close_pending" if now <= latest_close else "delayed_close_unconfirmed"
    elif now > closing:
        state = "after_scheduled_close"
    elif now >= auction:
        state = "closing_auction_window"
    result = dict(symbol=symbol, timeframe=timeframe, unit="張",
                  expected_bar_end=end.isoformat() if end else None, last_bar_kind=kind, session_state=state,
                  scheduled_regular_close=closing.isoformat(),
                  reported_close_time=_reported_close(quote, closing, latest_close, now),
                  stage="reconcile",
                  obtained_at=now.isoformat(), quote_time=quote_time.isoformat(),
                  quote_age_seconds=(now - quote_time).total_seconds(), quote_volume=quote_volume,
                  candles_volume=sum(volume for _, volume in bars), eligibility=UNVERIFIED, **coverage)

    if regular_gaps:
        result["gap_code"] = "MISSING_BARS"
    elif auction_gaps:
        result["gap_code"] = "AUCTION_WINDOW_GAPS"

    if state in ("delayed_close_pending", "delayed_close_unconfirmed"):
        result.update(status="待核：延後收盤尚未確認", code="DELAYED_CLOSE_PENDING", endpoint="quote")
    elif state in ("closed", "after_scheduled_close"):
        result.update(status="盤後資料，僅供回看", code="SESSION_CLOSED", endpoint="quote")
    elif missing:
        result.update(status="待核：分 K 時間格有缺口", code=result["gap_code"], endpoint="candles")
    elif end is None or not last_start <= quote_time < end or quote_time > now:
        result.update(status="待核：分 K 與統計截點不同", code="CUTOFF_MISMATCH")
    elif end > now:
        result.update(status="待核：最新分 K 時間尚未結束", code="BAR_NOT_CLOSED", endpoint="candles")
    elif state == "closing_auction_window":
        result.update(status="待核：收盤集合競價時段", code="CLOSING_AUCTION", endpoint="quote")
    elif now - quote_time > interval:
        result.update(status="待核：統計時間已過期", code="STALE_QUOTE", endpoint="quote")
    else:
        result["difference"] = result["candles_volume"] - quote_volume
        result["status"] = "同時段量一致" if result["difference"] == 0 else "待核：同時段量不符"
    return result


def run_intraday_check(symbol, timeframe, api_key):
    if not api_key:
        return {"status": "本機沒有可用的富果授權設定"}
    try:
        code, _ = _identity(symbol, timeframe)
    except ValueError:
        return {"status": "不支援此商品或週期", "stage": "request", "code": "INVALID_REQUEST"}
    payloads = []
    for endpoint, path in (("candles", f"candles/{code}?timeframe={timeframe}&sort=asc"),
                           ("quote", f"quote/{code}")):
        try:
            payloads.append(_request(path, api_key))
        except HTTPError as exc:
            return {"status": f"富果查詢未通過（HTTP {exc.code}）", "endpoint": endpoint,
                    "stage": "fetch", "code": "HTTP_ERROR", "http_status": exc.code}
        except (OSError, URLError):
            return {"status": "富果連線未完成", "endpoint": endpoint, "stage": "fetch", "code": "NETWORK"}
        except ValidationError:
            return {"status": "富果重新導向已停止", "endpoint": endpoint, "stage": "fetch", "code": "REDIRECT"}
        except (UnicodeError, json.JSONDecodeError):
            return {"status": "富果回傳格式無法讀取", "endpoint": endpoint, "stage": "decode", "code": "INVALID_JSON"}
    try:
        return check_snapshot(*payloads, symbol, timeframe, datetime.now(TAIPEI))
    except CheckError as exc:
        return {"status": "富果資料欄位未通過驗證", "stage": "validate", **exc.report}
    except (ArithmeticError, TypeError, ValueError):
        return {"status": "富果回應無法驗證", "stage": "validate", "code": "INVALID_RESPONSE"}
