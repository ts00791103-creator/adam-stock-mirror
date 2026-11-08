"""Candidate-only daily Close corrections backed by two independent TPEx tables.
Never converts adjusted units, deletes rows, changes O/H/L/volume or relaxes audit.
"""
import calendar
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import pandas as pd
from official_history import fetch_official_month, invalid_candles, preview_close_repairs, OfficialHistoryError

ACTION_URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ"


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def action_params(month):
    year, number = map(int, month.split("-"))
    return {"startDate": f"{year}/{number:02}/01",
            "endDate": f"{year}/{number:02}/{calendar.monthrange(year, number)[1]}", "response": "json"}


def action_evidence(payload, month):
    return {"method": "POST", "endpoint": ACTION_URL, "month": month, "request": action_params(month),
            "payload_sha256": payload_hash(payload), "payload": payload,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}


def fetch_official_actions(month):
    request = Request(ACTION_URL, data=urlencode(action_params(month)).encode(),
                      headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return action_evidence(payload, month)


def number(value):
    result = float(str(value).strip().replace(",", ""))
    if not math.isfinite(result):
        raise OfficialHistoryError("除權息數值非有限值")
    return result


def action_anchor(bundle, symbol, ex_date, official_close):
    month = ex_date.strftime("%Y-%m")
    if (bundle.get("method") != "POST" or bundle.get("endpoint") != ACTION_URL
            or bundle.get("month") != month or bundle.get("request") != action_params(month)
            or bundle.get("payload_sha256") != payload_hash(bundle.get("payload"))):
        raise OfficialHistoryError("除權息請求或內容證據不符")
    payload = bundle["payload"]
    if str(payload.get("stat", "")).lower() != "ok":
        raise OfficialHistoryError("官方除權息查詢未成功")
    expected = f"{ex_date.year-1911:03}/{ex_date.month:02}/{ex_date.day:02}"
    matches = []
    required = {"除權息日期", "代號", "除權息前收盤價", "除權息參考價", "權值", "現金股利", "權/息"}
    for table in payload.get("tables", []):
        fields = table.get("fields", [])
        if not required.issubset(fields):
            continue
        for values in table.get("data", []):
            row = dict(zip(fields, values))
            if str(row["代號"]).strip() == symbol.split(".")[0] and str(row["除權息日期"]).strip() == expected:
                matches.append(row)
    if len(matches) != 1:
        raise OfficialHistoryError("下一交易日沒有唯一可核對的官方除息紀錄")
    event = matches[0]
    if (str(event["權/息"]).strip() != "除息" or abs(number(event["權值"])) > .005
            or number(event["現金股利"]) <= 0):
        raise OfficialHistoryError("涉及除權或非單純現金除息，未建立相同價格基準")
    if abs(number(event["除權息前收盤價"]) - official_close) > .005:
        raise OfficialHistoryError("官方月表與除息前收盤價不一致")
    return {"ex_date": str(ex_date.date()), "official_previous_close": number(event["除權息前收盤價"]),
            "official_reference_price": number(event["除權息參考價"]), "cash_dividend": number(event["現金股利"]),
            "action_endpoint": ACTION_URL, "action_payload_sha256": bundle["payload_sha256"]}


def original_frame(frame):
    original = frame.copy(deep=True)
    for item in frame.attrs.get("official_close_verification", {}).get("ledger", []):
        original.loc[pd.Timestamp(item["date"]), "Close"] = item["original_close"]
    original.attrs.pop("official_close_verification", None)
    original.attrs["price_basis"] = "yahoo_auto_adjust_false"
    return original


def verify_daily_closes(symbol, frame, fetch_month=None, fetch_actions=None):
    """Preserve unresolved data. Every changed Close is exactly an official price."""
    if frame.empty or not all(c in frame for c in ("Open", "High", "Low", "Close")):
        return frame
    bad = invalid_candles(frame)
    if not bad:
        return frame
    report = {"symbol": symbol, "interval": "1d", "raw_invalid_dates": bad, "ledger": [], "months": [],
              "source_request": frame.attrs.get("source_request", {}),
              "scope": "Only reported invalid Close rows; not full-history price verification.",
              "adjusted_close": "Yahoo Adj Close retained, not recomputed or used by this correction."}
    original = frame.copy(deep=True)
    result = frame.copy(deep=True)
    request = frame.attrs.get("source_request", {})
    eligible = (re.fullmatch(r"[1-9][0-9]{3}\.TWO", symbol) and request.get("symbol") == symbol
                and request.get("interval") == "1d" and request.get("auto_adjust") is False
                and request.get("repair") is False and frame.attrs.get("price_basis") == "yahoo_auto_adjust_false"
                and not frame.attrs.get("raw_quote_notes"))
    if not eligible:
        report["unresolved_reason"] = "來源或原始價格基準無法確認，或不是上櫃日K；未改價"
    elif len(set(day[:7] for day in bad)) > 8:
        report["unresolved_reason"] = "異常月份超過本次逐根核對上限；未改價，保留品質阻擋"
    else:
        fetch_month = fetch_month or fetch_official_month
        fetch_actions = fetch_actions or fetch_official_actions
        action_cache = {}
        for month in sorted(set(day[:7] for day in bad)):
            attempt = {"month": month, "status": "unresolved"}
            try:
                source = original.loc[original.index.strftime("%Y-%m") == month].copy()
                source.attrs.update(symbol=symbol, price_basis="yahoo_auto_adjust_false")
                official, evidence, payload = fetch_month(symbol, month)
                attempt["official_evidence"] = evidence
                attempt["source_missing_official_dates"] = [str(t.date()) for t in official.index.difference(source.index)]
                attempt["source_extra_dates"] = [str(t.date()) for t in source.index.difference(official.index)]
                if not source.index.equals(official.index):
                    raise OfficialHistoryError("本月原始與官方日K日期不完全相同，未混補")
                proposed, ledger = preview_close_repairs(source, official, evidence)
                if not ledger:
                    raise OfficialHistoryError("同日開高低不吻合或並非可證實的收盤越界，未改價")
                if any(abs(float(proposed.loc[t, col]) - float(official.loc[t, col])) > .005
                       for t in source.index for col in ("Open", "High", "Low", "Close")):
                    raise OfficialHistoryError("月份仍有其他價格差異，無法確認相同基準")
                staged = []
                for entry in ledger:
                    if entry["applied_close"] != entry["official_close"]:
                        raise OfficialHistoryError("官方收盤不在來源原始上下界內；不作浮點夾限改價")
                    stamp = pd.Timestamp(entry["date"])
                    position = original.index.get_loc(stamp)
                    if position+1 >= len(original):
                        raise OfficialHistoryError("缺少下一交易日，不能核對除息前收盤")
                    next_day = original.index[position+1]
                    if (next_day-stamp).days > 10:
                        raise OfficialHistoryError("交易日期相隔過久，未推測下一交易日")
                    action_month = next_day.strftime("%Y-%m")
                    if action_month not in action_cache:
                        action_cache[action_month] = fetch_actions(action_month)
                    anchor = action_anchor(action_cache[action_month], symbol, next_day, entry["official_close"])
                    staged.append({**entry, **anchor,
                                   "original_ohlc": {c: float(original.loc[stamp, c]) for c in ("Open", "High", "Low", "Close")},
                                   "source_reference_difference": entry["original_close"] - anchor["official_reference_price"]})
                # Commit a month only after all its rows and action anchors agree.
                for entry in staged:
                    result.loc[pd.Timestamp(entry["date"]), "Close"] = entry["official_close"]
                report["ledger"].extend(staged)
                attempt.update(status="verified", count=len(staged))
            except Exception as exc:
                attempt["reason"] = type(exc).__name__ + ": " + str(exc)[:220]
            report["months"].append(attempt)
    # Structural and non-Close fields must remain byte-for-byte equivalent in pandas.
    if (not result.index.equals(original.index) or not result.columns.equals(original.columns)
            or not result.drop(columns="Close").equals(original.drop(columns="Close"))):
        raise RuntimeError("逐根核對不得改動其他欄位、日期或根數")
    report["remaining_invalid_dates"] = invalid_candles(result)
    report["original_price_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(original[["Open","High","Low","Close"]], index=True).values.tobytes()).hexdigest()
    report["analysis_price_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(result[["Open","High","Low","Close"]], index=True).values.tobytes()).hexdigest()
    result.attrs["official_close_verification"] = report
    if report["ledger"]:
        result.attrs["price_basis"] = "yahoo_with_verified_official_closes"
    return result


def show_verification(st, frame):
    report = frame.attrs.get("official_close_verification")
    if not report:
        return
    count = len(report["ledger"])
    if count:
        st.info(f"已依官方月表與除息前收盤價，逐根核對更正 {count} 根歷史收盤；原始資料保留。")
    else:
        st.warning("官方逐根核對尚未取得可安全改價的完整證據；保留原始行情與品質阻擋。")
    st.caption("僅核對列出的異常收盤，不代表十年每根均經官方驗證。Adj Close 保留Yahoo原值，未重算、不供本次分析使用。")
    with st.expander("歷史收盤核對紀錄與原始資料", expanded=False):
        if report["ledger"]:
            st.dataframe(pd.DataFrame([{"日期": x["date"], "原始收盤": x["original_close"], "官方收盤": x["official_close"],
                                        "除息日": x["ex_date"]} for x in report["ledger"]]), hide_index=True)
        st.json(report)
        st.download_button("下載原始Yahoo完整日K CSV", original_frame(frame).to_csv().encode("utf-8-sig"),
                           file_name=f"{report['symbol']}_original_daily.csv", mime="text/csv", key="verified_original_csv")
        st.download_button("下載分析用完整日K CSV", frame.to_csv().encode("utf-8-sig"),
                           file_name=f"{report['symbol']}_analysis_daily.csv", mime="text/csv", key="verified_analysis_csv")
        st.download_button("下載官方逐根核對證據JSON", json.dumps(report, ensure_ascii=False, indent=2),
                           file_name=f"{report['symbol']}_official_close_evidence.json", mime="application/json", key="verified_evidence_json")
