"""Research-only, single-official-source daily series. Never patches Yahoo rows.

Complete monthly retrieval is not a certified trading calendar, company-action
adjustment chain, listing history, or permission to publish a trading strategy.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen
import re
import pandas as pd
from official_history import (OfficialHistoryError, fetch_official_month,
                              parse_official_month, request_spec, invalid_candles)

COLS = ["Open", "High", "Low", "Close", "Volume", "Turnover"]
STANDARD_LOT_RESEARCH_SYMBOLS={code+".TWO" for code in ("3105","3211","5274","8086","4123","6223","6146","6121","3552","3260","6182")}
LOT_RULE_SOURCE="https://www.tpex.org.tw/zh-tw/mainboard/trading/rules/system.html"


def parse_series_month(payload,symbol,month):
    """An explicit research adapter; production's strict parser stays unchanged."""
    tables=payload.get("tables",[]) if isinstance(payload,dict) else []
    fields=[re.sub(r"\s+","",str(v)) for v in tables[0].get("fields",[])] if len(tables)==1 else []
    if symbol.endswith(".TWO") and "成交張數" in fields:
        if symbol not in STANDARD_LOT_RESEARCH_SYMBOLS or "成交仟股" in fields:
            raise OfficialHistoryError("成交張數換算只限本輪明確列名的一千股普通股；拒絕未知交易單位")
        adapted=copy.deepcopy(payload)
        position=fields.index("成交張數")
        adapted["tables"][0]["fields"][position]="成交仟股"
        frame,evidence=parse_official_month(adapted,symbol,month)
        evidence.update(payload_sha256=payload_hash(payload),raw_volume_field="成交張數",parser_variant="tpex_lots_research_v1",
                        units_per_lot=1000,unit_rule_source=LOT_RULE_SOURCE,
                        volume_precision="官方成交張數×1000（本輪指定普通股每張1000股）；保留張數發布精度，不宣稱單股精度")
        frame.attrs["official_evidence"]=evidence
        return frame,evidence
    return parse_official_month(payload,symbol,month)


def fetch_series_month(symbol,month):
    method,endpoint,params=request_spec(symbol,month)
    body=urlencode(params).encode() if method=="POST" else None
    url=endpoint+("?"+urlencode(params) if method=="GET" else "")
    request=Request(url,data=body,method=method,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urlopen(request,timeout=20) as response:payload=json.load(response)
    frame,evidence=parse_series_month(payload,symbol,month)
    evidence["retrieved_at_utc"]=datetime.now(timezone.utc).isoformat()
    return frame,evidence,payload


def series_fingerprint(frame):
    rows=[[str(t.date())]+[float(row[c]) for c in COLS] for t,row in frame.iterrows()]
    return hashlib.sha256(json.dumps(rows,allow_nan=False).encode()).hexdigest()


def month_range(start, end):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start.tz is not None or end.tz is not None or start != start.normalize() or end != end.normalize() or end < start:
        raise OfficialHistoryError("必須提供遞增、無時區的日K日期")
    return [str(m) for m in pd.period_range(start, end, freq="M")]


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class OfficialArchive:
    """Serial, persistent monthly cache. 403/429 stops that host for this run."""
    def __init__(self, folder, delay=3.0, fetcher=fetch_series_month):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.delay = max(3.0, float(delay))  # Engineering throttle, not an official quota.
        self.fetcher = fetcher
        self.last_request = {}
        self.blocked_hosts = {}
        self.transport_events = []

    def get(self, symbol, month):
        _, endpoint, _ = request_spec(symbol, month)
        path = self.folder / f"{symbol}_{month}.json"
        if path.exists():
            bundle = json.loads(path.read_text(encoding="utf-8"))
            if bundle.get("symbol") != symbol or bundle.get("month") != month:
                raise OfficialHistoryError("快取股票／月份不符")
            parse_bundle(bundle)
            return bundle
        host = urlparse(endpoint).netloc
        if host in self.blocked_hosts:
            raise OfficialHistoryError("來源主機已因存取限制停止請求：" + self.blocked_hosts[host])
        wait = self.delay - (time.monotonic() - self.last_request.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self.last_request[host] = time.monotonic()
        for attempt in range(2):
            try:
                _, evidence, payload = self.fetcher(symbol, month)
                break
            except HTTPError as exc:
                self.transport_events.append({"symbol":symbol,"month":month,"host":host,"http_status":exc.code,
                                              "attempt":attempt+1,"at_utc":datetime.now(timezone.utc).isoformat()})
                (self.folder/"transport-events.json").write_text(json.dumps(self.transport_events,indent=2),encoding="utf8")
                if exc.code in (403, 429):
                    self.blocked_hosts[host] = str(exc.code)
                    raise
                # The edge confirmed a read-only request failed with 5xx. Keep
                # certificate validation and host unchanged; one bounded retry.
                if 500 <= exc.code < 600 and attempt == 0:
                    time.sleep(10)
                    self.last_request[host]=time.monotonic()
                    continue
                raise
        bundle = {"symbol": symbol, "month": month, "payload": payload,
                  "evidence": evidence,
                  "retrieved_at_utc": evidence.get("retrieved_at_utc", datetime.now(timezone.utc).isoformat())}
        parse_bundle(bundle)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        return bundle


def parse_bundle(bundle):
    frame, calculated = parse_series_month(bundle["payload"], bundle["symbol"], bundle["month"])
    saved = bundle.get("evidence", {})
    for key in ("symbol", "month", "method", "endpoint", "request", "payload_sha256", "parsed_frame_sha256", "price_basis", "volume_precision", "raw_volume_field", "parser_variant", "units_per_lot", "unit_rule_source"):
        if saved.get(key) != calculated.get(key):
            raise OfficialHistoryError("月表證據已變更或不相符：" + key)
    return frame, calculated


def assemble_official_series(symbol, start, end, bundles, *, route_evidence=None):
    """One explicitly named exchange, all requested months, no provider fallback.

    A market transfer requires a separately reviewed segment; a current suffix
    alone is never certified as a complete historical listing route.
    """
    months = month_range(start, end)
    request_spec(symbol, months[0])
    if symbol.endswith(".TW") and pd.Timestamp(start) < pd.Timestamp("2010-01-04"):
        raise OfficialHistoryError("證交所公開月表起點為2010-01-04；不得宣稱更早已涵蓋")
    if symbol.endswith(".TWO") and pd.Timestamp(start) < pd.Timestamp("1994-01-01"):
        raise OfficialHistoryError("櫃買公開月表起點為1994-01；個股另受上櫃日期限制")
    by_month = {}
    for bundle in bundles:
        if bundle.get("symbol") != symbol or bundle.get("month") not in months or bundle["month"] in by_month:
            raise OfficialHistoryError("禁止混合股票、市場、重複或非請求月份")
        by_month[bundle["month"]] = bundle
    missing = sorted(set(months) - set(by_month))
    if missing:
        raise OfficialHistoryError("官方月份未完整取得：" + ",".join(missing))
    pieces, evidence, unavailable = [], [], []
    for month in months:
        frame, item = parse_bundle(by_month[month])
        piece = frame.copy(deep=True)
        piece.attrs = {}
        pieces.append(piece)
        evidence.append({**item, "retrieved_at_utc": by_month[month].get("retrieved_at_utc")})
        unavailable.extend(item["unavailable_rows"])
    result = pd.concat(pieces).sort_index().loc[pd.Timestamp(start):pd.Timestamp(end)].copy()
    if result.empty or result.index.has_duplicates or invalid_candles(result):
        raise OfficialHistoryError("官方序列為空、重複或OHLC異常")
    unresolved = [r for r in unavailable if str(start)[:10] <= r["date"] <= str(end)[:10]]
    manifest = {"symbol": symbol, "requested_start": str(pd.Timestamp(start).date()),
                "requested_end": str(pd.Timestamp(end).date()), "requested_months": months,
                "retrieved_months": len(months), "bars": len(result),
                "first": str(result.index[0].date()), "last": str(result.index[-1].date()),
                "source": "TWSE" if symbol.endswith(".TW") else "TPEx",
                "price_basis": "official_raw_unadjusted", "volume_unit": "shares",
                "volume_precision": sorted({e["volume_precision"] for e in evidence}),
                "unavailable_ohlc_rows": unresolved, "monthly_evidence": evidence,
                "month_coverage_complete": True,
                "trading_calendar_independently_certified": False,
                "listing_route_evidence": copy.deepcopy(route_evidence),
                "listing_transitions_independently_certified": False,
                "corporate_action_adjustments": "not applied or certified",
                "production_ready": False, "series_sha256": series_fingerprint(result),
                "policy": "Whole official snapshot only; no Yahoo rows, guessed candles, ffill, deleted exceptions or adjusted-close substitution."}
    result.attrs = {"official_series": manifest, "price_basis": "official_raw_unadjusted"}
    return result, manifest


def aggregate_official_weeks(frame):
    manifest = frame.attrs.get("official_series", {})
    if not manifest.get("month_coverage_complete") or manifest.get("unavailable_ohlc_rows"):
        raise OfficialHistoryError("月份不完整或官方缺OHLC日尚未釐清，不能當成完整週K")
    if series_fingerprint(frame) != manifest.get("series_sha256"):
        raise OfficialHistoryError("官方序列在核對後曾被改動，停止週K聚合")
    if invalid_candles(frame) or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise OfficialHistoryError("日K品質未通過，停止週K聚合")
    # Monday through Sunday: historical Saturday makeup sessions are retained.
    groups = frame.index.to_period("W-SUN").start_time
    weekly = frame.groupby(groups).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum", "Turnover": "sum"})
    weekly.index.name = "Date"
    weekly.attrs = {"official_series": copy.deepcopy(manifest), "price_basis": "official_raw_unadjusted",
                    "week_rule": "Monday-Sunday, includes published Saturday sessions; no invented empty weeks",
                    "boundary_weeks": "Request boundaries may truncate a week; not certified by an independent trading calendar."}
    return weekly


def compare_provider(frame, official):
    """Diagnose only; this function cannot write or insert provider rows."""
    common = frame.index.intersection(official.index)
    prices, volumes = [], []
    for stamp in common:
        for column in ("Open", "High", "Low", "Close"):
            a, b = float(frame.loc[stamp, column]), float(official.loc[stamp, column])
            if not pd.notna(a) or abs(a-b) > .005:
                prices.append({"date": str(stamp.date()), "field": column, "provider": a if pd.notna(a) else None, "official": b})
        if "Volume" in frame and float(frame.loc[stamp, "Volume"]) != float(official.loc[stamp, "Volume"]):
            volumes.append({"date": str(stamp.date()), "provider": float(frame.loc[stamp, "Volume"]), "official": float(official.loc[stamp, "Volume"])})
    return {"provider_missing_official_dates": [str(t.date()) for t in official.index.difference(frame.index)],
            "provider_extra_dates": [str(t.date()) for t in frame.index.difference(official.index)],
            "price_differences": prices, "volume_differences": volumes,
            "local_patch_applied": False,
            "local_patch_status": "not authorized by comparison alone: shared economic adjustment basis, exact volume definition/precision and complete calendar are not proven"}
