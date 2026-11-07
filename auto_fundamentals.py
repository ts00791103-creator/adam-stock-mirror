"""Official reported EPS growth and book value. No forecast or trading signal."""
from datetime import datetime, timezone
import math
import re
import pandas as pd
import requests

SECTORS = ("ci", "basi", "fh", "ins", "bd", "mim")


def stock_code(symbol):
    match = re.fullmatch(r"(\d{4,5})\.(TW|TWO)", str(symbol).upper())
    if not match:
        raise ValueError("僅支援上市／上櫃公司代碼（.TW／.TWO）；不支援其他市場")
    if match.group(1).startswith("00"):
        raise ValueError("ETF 不適用公司 EPS 與每股淨值計算")
    return match.group(1), match.group(2)


def number(value):
    try:
        result = float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def eps_growth(rows, as_of=None):
    """Require eight consecutive, independently checked quarters; no gap filling."""
    as_of = pd.Timestamp(as_of or datetime.now(timezone.utc).date())
    by_period = {}
    for row in rows:
        p = pd.Period(row["quarter"], freq="Q")
        if p.end_time.normalize() > as_of.normalize():
            continue
        if p in by_period:
            raise ValueError("季報期間重複，停止計算")
        by_period[p] = row
    if not by_period:
        return {"error": "沒有可核對的歷史季 EPS"}
    end = max(by_period)
    window = [by_period.get(end - n) for n in range(8)]
    result = {"quarter": str(end), "quarter_end": str(end.end_time.date()),
              "growth_pct": None, "recent_ttm": None, "prior_ttm": None,
              "source": sorted({r.get("source", "") for r in rows if r.get("source")}),
              "age_days": (as_of.normalize() - end.end_time.normalize()).days}
    valid = lambda r: r is not None and r.get("ytd_consistent") is True and number(r.get("quarter_eps")) is not None
    if all(valid(r) for r in window[:4]):
        result["recent_ttm"] = round(sum(float(r["quarter_eps"]) for r in window[:4]), 4)
    if not all(valid(r) for r in window):
        result["error"] = "缺少連續八季或累計 EPS 核對未通過；不補零、不跨缺季計算成長率"
        return result
    recent = result["recent_ttm"]
    prior = round(sum(float(r["quarter_eps"]) for r in window[4:]), 4)
    result["prior_ttm"] = prior
    if prior <= 0 or recent <= 0:
        result["error"] = "比較期或近四季 EPS 非正；保留 EPS，停用百分比成長率以避免虧損／轉盈誤讀"
        return result
    result["growth_pct"] = (recent / prior - 1) * 100
    return result


def parse_book_value(records, code, source, as_of=None):
    """Use official per-share field directly; never infer shares from par value."""
    as_of = pd.Timestamp(as_of or datetime.now(timezone.utc).date())
    candidates = []
    for row in records:
        if str(row.get("公司代號", "")).strip() != code:
            continue
        year, quarter = number(row.get("年度")), number(row.get("季別"))
        if year is None or quarter is None or int(quarter) != quarter or not 1 <= quarter <= 4 or int(year) != year:
            continue
        year = int(year) + (1911 if year < 1911 else 0)
        if not 1900 <= year <= as_of.year:
            continue
        p = pd.Period(f"{year}Q{int(quarter)}", freq="Q")
        if p.end_time.normalize() > as_of.normalize():
            continue
        field = next((k for k in ("每股參考淨值", "每股淨值") if k in row), None)
        value = number(row.get(field)) if field else None
        if value is None:
            continue
        candidates.append({"value": value, "quarter": str(p),
                           "quarter_end": str(p.end_time.date()), "field": field,
                           "name": row.get("公司名稱", ""), "source": source,
                           "published_snapshot": row.get("出表日期", ""),
                           "age_days": (as_of.normalize()-p.end_time.normalize()).days})
    if not candidates:
        return None
    latest = max(r["quarter"] for r in candidates)
    latest_rows = [r for r in candidates if r["quarter"] == latest]
    if len({r["value"] for r in latest_rows}) != 1:
        raise ValueError("官方同季每股淨值不一致，停止顯示")
    return latest_rows[0]


def fetch_book_value(symbol, getter=None, timeout=8):
    code, market = stock_code(symbol)
    getter = getter or requests.get
    for sector in SECTORS:
        url = (f"https://openapi.twse.com.tw/v1/opendata/t187ap07_L_{sector}" if market == "TW"
               else f"https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap07_O_{sector}")
        try:
            response = getter(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            records = response.json()
            if not isinstance(records, list):
                continue
            result = parse_book_value(records, code, url)
            if result is not None:
                return result, None
        except (requests.RequestException, ValueError, TypeError, KeyError):
            continue
    return None, "官方最新資產負債表未找到有效每股淨值，或來源暫時不可用；不以股本÷10猜測股數"


def fetch_fundamentals(symbol, history_fetcher=None, book_fetcher=None):
    stock_code(symbol)
    if history_fetcher is None:
        from mops_history import fetch_mops_eps_history
        history_fetcher = fetch_mops_eps_history
    book_fetcher = book_fetcher or fetch_book_value
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        book_job = pool.submit(book_fetcher, symbol)
        eps_job = pool.submit(history_fetcher, symbol, years=3)
        try:
            rows, failures = eps_job.result()
            growth = eps_growth(rows)
        except Exception:
            growth, failures = {"error": "官方歷史 EPS 暫時無法核對"}, []
        try:
            book, book_error = book_job.result()
        except Exception:
            book, book_error = None, "官方每股淨值暫時無法取得"
    result = {"symbol": symbol, "retrieved_at": datetime.now(timezone.utc).isoformat(),
              "growth": growth, "book": book, "book_error": book_error,
              "history_failures": failures}
    if growth.get("recent_ttm") is None and book is None:
        return None, growth.get("error", "無可用資料") + "；" + (book_error or "")
    return result, None


def render_auto_fundamentals(st, symbol, market):
    import streamlit as streamlit_state
    with st.expander("自動財報｜盈餘成長率・每股淨值", expanded=False):
        st.caption("上市／上櫃個股，使用目前已取得的官方財報；非即時行情、非歷史時點回測。ETF 不適用。")
        if market != "台灣股票／ETF" or not symbol:
            st.info("請先選擇台灣個股並輸入代碼。")
            return
        try:
            stock_code(symbol)
        except ValueError as exc:
            st.info(str(exc))
            return
        # Taiwan ETF/security identifiers can be numeric too; reject fund codes.
        if str(symbol).split(".")[0].startswith("00"):
            st.info("ETF 不適用公司 EPS 與每股淨值計算。")
            return
        st.write(f"查詢個股：{symbol}")
        st.caption("首次最多查詢 12 季。每次等候 12 秒，未完成可再按同一按鈕取得結果，不重複排入相同查詢。")
        if st.button("自動讀取／更新個股財報", key="auto_fundamentals_load"):
            from valuation_io import bounded_fetch
            with st.spinner("核對官方財報中…"):
                result, error = bounded_fetch(("official_fundamentals_v1", symbol),
                                              lambda: fetch_fundamentals(symbol), timeout_seconds=12)
            if result is not None:
                streamlit_state.session_state.setdefault("official_fundamentals_results", {})[symbol] = result
            elif error:
                st.warning(error)
        result = streamlit_state.session_state.get("official_fundamentals_results", {}).get(symbol)
        if result is None:
            return
        st.caption(f"取值時間（UTC）：{result['retrieved_at']}｜來源：MOPS／證交所／櫃買中心")
        g = result["growth"]
        if g.get("recent_ttm") is not None:
            st.metric("近四季 EPS（元）", f"{g['recent_ttm']:.2f}")
        if g.get("growth_pct") is not None:
            st.metric("實際 EPS 年增率（%）", f"{g['growth_pct']:.2f}")
            st.caption(f"近四季 EPS {g['recent_ttm']:.4f} ÷ 前四季 EPS {g['prior_ttm']:.4f} − 1")
        if g.get("error"):
            st.info(g["error"])
        if g.get("quarter"):
            st.caption(f"EPS 最新季度：{g['quarter']}｜期末：{g['quarter_end']}；不代表公告日")
        for source in g.get("source", []):
            st.caption(f"EPS 來源：{source}")
        book = result["book"]
        if book:
            st.metric("官方每股淨值（元）", f"{book['value']:.2f}")
            st.caption(f"淨值季度：{book['quarter']}｜官方欄位：{book['field']}｜出表日期（民國）：{book['published_snapshot']}")
            st.caption(f"官方已計算的每股值，未自行假設面額或流通股數。來源：{book['source']}")
        else:
            st.info(result["book_error"])
        if book and g.get("quarter") and book["quarter"] != g["quarter"]:
            st.warning("EPS 與每股淨值季度不同，請分別閱讀，不合併成同季財報。")
        if g.get("age_days", 0) > 180 or (book and book["age_days"] > 180):
            st.warning("部分財報期末距今超過 180 天，請留意資料可能過舊。")
        if result["history_failures"]:
            st.caption(f"歷史季度缺漏／核對問題：{len(result['history_failures'])} 筆")
        st.caption("這是實際 EPS 成長率；圖片的 ROE × 留存率屬另一種成長情境，五年配發率尚未自動取得。資料不會自動帶入估價或觸發交易。")
