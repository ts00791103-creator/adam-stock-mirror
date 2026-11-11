"""Candidate-only expanded test. Fixed 20 historical + 2 roster requests, no cache."""
from datetime import date, datetime, timezone
import hashlib
import json
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

import fugle_history_validation as v

ENDPOINT = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/tickers"
DOC_URL = "https://developer.fugle.tw/docs/data/http-api/intraday/tickers/"
BASELINE = v.BASELINE.parent / "tpex-fugle-expanded-20261111"
REQUEST_CAP = 22
FLAGS = ("isNormal", "isAttention", "isDisposition", "isHalted")


def parameters(kind):
    if kind not in ("all", "halted"):
        raise v.ValidationError("名單查詢條件不在固定允許清單。")
    params = {"type": "EQUITY", "exchange": "TPEx", "market": "OTC"}
    if kind == "halted":
        params["isHalted"] = "true"
    return params


def parse_universe(payload, kind):
    parameters(kind)
    if not isinstance(payload, dict) or any(payload.get(k) != val for k, val in
                                          (("type", "EQUITY"), ("exchange", "TPEx"), ("market", "OTC"))):
        raise v.ValidationError("富果名單市場或類型不符。")
    for flag in FLAGS:
        if flag in payload and (flag != "isHalted" or kind != "halted" or payload[flag] is not True):
            raise v.ValidationError("富果名單篩選條件不符，不能改變母體。")
    if kind == "halted" and payload.get("isHalted") is not True:
        raise v.ValidationError("富果暫停交易查詢未確認篩選條件。")
    day = payload.get("date")
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise v.ValidationError("富果名單缺少可驗證日期。")
    try:
        date.fromisoformat(day)
    except ValueError:
        raise v.ValidationError("富果名單日期無效。") from None
    data = payload.get("data")
    if not isinstance(data, list) or len(data) > 20000 or (kind == "all" and not data):
        raise v.ValidationError("富果名單格式或筆數無效。")
    rows, seen = [], set()
    for item in data:
        if not isinstance(item, dict):
            raise v.ValidationError("富果名單資料列無效。")
        symbol = item.get("symbol")
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9]{4,10}", symbol) or symbol in seen:
            raise v.ValidationError("富果名單代碼無效或重複。")
        seen.add(symbol)
        # Never echo arbitrary response strings, names, headers, or error bodies.
        industry = item.get("industry")
        rows.append({"symbol": symbol, "industry": industry if isinstance(industry, str) and
                     re.fullmatch(r"\d{2}", industry) else None})
    return {"date": day, "rows": rows}


def fetch_universe(kind, api_key):
    params = parameters(kind)
    req = Request(ENDPOINT + "?" + urlencode(params),
                  headers={"X-API-KEY": api_key, "Accept": "application/json"})
    started = time.monotonic()
    with build_opener(v.NoRedirect()).open(req, timeout=20) as response:
        raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise v.ValidationError("富果名單回應超出大小限制。")
        status = response.status
    parsed = parse_universe(json.loads(raw), kind)
    return parsed, {"endpoint": ENDPOINT, "parameters": params, "http_status": status,
                    "rows": len(parsed["rows"]), "response_date": parsed["date"],
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "response_sha256": hashlib.sha256(raw).hexdigest()}


def load_universe():
    manifest = json.loads((BASELINE / "manifest.json").read_text())
    if manifest.get("status") != "complete" or manifest.get("as_of") != v.END:
        raise v.ValidationError("官方基準未完整凍結或日期不符。")
    raw = (BASELINE / "universe.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["universe_sha256"]:
        raise v.ValidationError("官方名單校驗失敗。")
    official = json.loads(raw)
    rows = official.get("rows")
    if official.get("as_of") != v.END or not isinstance(rows, list) or not rows:
        raise v.ValidationError("官方名單日期或母體無效。")
    symbols = [r.get("code") for r in rows]
    if any(not isinstance(s, str) or not re.fullmatch(r"[1-9]\d{3}", s) for s in symbols) or len(set(symbols)) != len(symbols):
        raise v.ValidationError("官方普通股名單有重複或非普通股代碼。")
    if manifest["denominator"]["count"] != len(rows) or len(rows) != 897:
        raise v.ValidationError("官方名單母體筆數不符。")
    if not set(v.EXPANDED_SYMBOLS).issubset(symbols):
        raise v.ValidationError("擴大樣本不在官方母體。")
    for row in rows:
        if row.get("reference_date") != v.END or row.get("classification") != "ordinary_equity_candidate_by_official_issuer_code":
            raise v.ValidationError("官方名單日期或分類不符。")
        listing = row.get("listing_date")
        if listing is not None:
            if not isinstance(listing, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", listing):
                raise v.ValidationError("官方掛牌日期無效。")
            date.fromisoformat(listing)
            if listing > v.END:
                raise v.ValidationError("官方掛牌日期晚於基準日。")
        status = row.get("status_evidence")
        if status is not None and (not isinstance(status, dict) or status.get("Date") != "1151111" or
                                   status.get("SecuritiesCompanyCode") != row["code"]):
            raise v.ValidationError("官方交易狀態的日期或代碼不符。")
    return official, manifest


def compare_universes(official, all_result, halted_result, manifest):
    if all_result["date"] != halted_result["date"]:
        raise v.ValidationError("兩次富果名單日期不同，停止合併。")
    o = {r["code"]: r for r in official["rows"]}
    all_symbols = {r["symbol"] for r in all_result["rows"]}
    halted = {r["symbol"] for r in halted_result["rows"]}
    observed = all_symbols | halted
    same_date = all_result["date"] == official["as_of"]
    extras = sorted(observed - set(o))
    industry = {r["symbol"]: r["industry"] for r in all_result["rows"] + halted_result["rows"]}
    classes = []
    for symbol, row in o.items():
        listing = row.get("listing_date")
        classes.append({"symbol": symbol, "in_fugle": symbol in observed,
                        "listing_date": listing,
                        "new_listing_in_window": bool(listing and v.START < listing <= v.END),
                        "official_quote_status": row.get("quote_status", "unknown"),
                        "official_no_trade": row.get("volume_shares") == 0,
                        "official_status_evidence": row.get("status_evidence"),
                        "official_suspended": (row.get("status_evidence") or {}).get("SuspensionOfTrading") == "Ｙ",
                        "fugle_halted": symbol in halted,
                        "suspension_classification": "Fugle isHalted=true" if symbol in halted else "unconfirmed; absence/no-trade is not proof of suspension"})
    return {"official_as_of": official["as_of"], "fugle_response_date": all_result["date"],
            "date_matches": same_date, "dated_universe_mismatch": not same_date,
            "comparison_status": "same_response_date_observation" if same_date else "different_dates_not_point_in_time_coverage",
            "historical_roster_query_supported": False,
            "point_in_time_roster_equivalence_proven": False,
            "official_denominator": len(o), "denominator_evidence": manifest["denominator"],
            "denominator_scope": "TPEx official issuer-code roster; exact membership only; not exhaustive of every share class/instrument; instrument-level classification not independently verified",
            "fugle_raw_all_count": len(all_result["rows"]), "fugle_raw_halted_count": len(halted_result["rows"]),
            "fugle_union_count": len(observed), "observed_official_intersection_count": len(set(o) & observed),
            "same_date_observed_listing_coverage_percent": round(100 * len(set(o) & observed) / len(o), 4) if same_date else None,
            "official_symbols": sorted(o), "fugle_all_symbols": sorted(all_symbols), "fugle_halted_symbols": sorted(halted),
            "official_missing_from_fugle": sorted(set(o) - observed), "fugle_extra_symbols": extras,
            "extra_nonordinary_or_unclassified": [{"symbol": s, "industry": industry.get(s),
                "classification": "industry_00_instrument_unclassified" if industry.get(s) == "00" else "unclassified_not_in_official_issuer_denominator"} for s in extras],
            "official_symbol_classes": classes,
            "limitation": "Listing presence is not historical OHLC completeness. Intraday endpoint has no date parameter. No-trade, missing quotes and suspension are different states; do not infer suspension from absence."}


def run_expanded_validation(api_key, history_fetcher=v.fetch_segment, universe_fetcher=fetch_universe, sleeper=time.sleep):
    report = {"version": v.VERSION, "mode": "expanded10_and_universe", "range": {"from": v.START, "to": v.END},
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "status": "running", "requests": [],
              "actual_http_attempts": 0, "samples": [], "errors": [], "universe": None,
              "documentation": [v.DOC_URL, DOC_URL], "limitations": [v.VOLUME_NOTE,
                  "Ten volume-stratified established traded stocks are not random and exclude new listings/no-trade from the historical sample, not from the official listing denominator.",
                  "Intraday roster cannot request a historical date; a matching response date is an observation, not proof of point-in-time roster equivalence."],
              "methodology": {"request_cap": REQUEST_CAP, "historical_request_cap": 20, "universe_request_cap": 2,
                  "fixed_symbols": list(v.EXPANDED_SYMBOLS), "price_basis": "unadjusted", "ohlc_absolute_tolerance_twd": v.PRICE_TOLERANCE,
                  "date_basis": "Taiwan trading date; no filling", "universe_filters": [parameters("all"), parameters("halted")]}}
    if not api_key:
        report.update(status="blocked", errors=[{"reason": "尚未設定富果金鑰。"}])
        return report

    def call(kind, fn, *args):
        if report["actual_http_attempts"] >= REQUEST_CAP:
            raise v.ValidationError("已達查詢上限。")
        if report["requests"]:
            sleeper(1.1)
        attempt = {"kind": kind, "status": "started"}
        if kind == "historical":
            attempt.update(symbol=args[0], **{"from": args[1], "to": args[2]})
        else:
            attempt.update(endpoint=ENDPOINT, parameters=parameters(args[0]))
        report["requests"].append(attempt)
        report["actual_http_attempts"] += 1
        result, evidence = fn(*args)
        attempt.update(evidence, status="completed")
        return result

    try:
        # Validate every frozen source before spending any paid quota.
        official, manifest = load_universe()
        baselines = {s: v.load_baseline(s) for s in v.EXPANDED_SYMBOLS}
        report["sampling_evidence"] = manifest["sampling"]
        report["official_universe_evidence"] = {
            "as_of": official["as_of"], "sha256": manifest.get("universe_sha256"),
            "retrieved_utc": manifest.get("retrieved_utc"),
            "sources": [s for s in manifest.get("sources", []) if s.get("label") in
                        ("companies", "quotes", "openapi_schema", "tpex_cmode", "tpex_spendi_today", "tpex_spendi_history")],
            "limitations": manifest.get("limitations", [])}
        all_result = call("universe_all", universe_fetcher, "all", api_key)
        halted_result = call("universe_halted", universe_fetcher, "halted", api_key)
        report["universe"] = compare_universes(official, all_result, halted_result, manifest)
        for symbol in v.EXPANDED_SYMBOLS:
            rows = []
            for start, end in v.chunks():
                rows.extend(call("historical", history_fetcher, symbol, start, end, api_key))
            baseline, reference = baselines[symbol]
            report["samples"].append(v.compare_rows(symbol, rows, baseline, reference))
        report["status"] = "completed"
    except Exception as exc:
        # Never expose exception strings, even ValidationError from an injected transport.
        error = {"reason": "名單、歷史資料或官方基準檢核失敗；已停止，未自動重試。"}
        if isinstance(exc, HTTPError):
            error["http_status"] = exc.code
        report["errors"].append(error)
        if report["requests"] and report["requests"][-1]["status"] == "started":
            report["requests"][-1]["status"] = "failed"
        report["status"] = "stopped"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report
