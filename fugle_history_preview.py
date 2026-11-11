"""Candidate-only protected page. No shared data cache, secrets or background fetch."""
import hmac
import json
import time

import pandas as pd
import streamlit as st

from fugle_history_validation import DOC_URL, END, START, VERSION, VOLUME_NOTE, run_validation
from fugle_universe_validation import run_expanded_validation
from live_quote import _secret

RESULT_KEY = "fugle_history_validation_result"
PASSWORD_KEY = "fugle_history_validation_password"
COOLDOWN_KEY = "fugle_history_validation_last_attempt"


def _lock():
    st.session_state.pop(RESULT_KEY, None)
    st.session_state.pop(PASSWORD_KEY, None)


def show_fugle_history_preview():
    st.subheader("富果歷史日K驗證（受保護測試頁）")
    st.caption(f"{VERSION}｜原三檔／新增十檔與上櫃名單｜{START} 至 {END}")
    if st.button("返回候選站首頁", key="fugle_history_back"):
        _lock()
        st.query_params.pop("view", None)
        st.rerun()
    st.info("使用候選站既有個人報價密碼。金鑰留在伺服器；此頁不提供金鑰輸入、顯示或搬運。")
    api_key, password = _secret("FUGLE_API_KEY"), _secret("LIVE_QUOTE_PASSWORD")
    if not api_key or not password:
        _lock()
        st.warning("候選站缺少既有富果金鑰或個人報價密碼。請由擁有者在平台安全設定，勿貼到聊天或GitHub。尚未發送API請求。")
        return
    entered = st.text_input("個人報價密碼（歷史驗證）", type="password", key=PASSWORD_KEY)
    if not entered or not hmac.compare_digest(entered.encode(), password.encode()):
        st.session_state.pop(RESULT_KEY, None)
        if entered:
            st.error("密碼不正確。尚未發送歷史API請求。")
        else:
            st.caption("尚未解鎖；未查詢歷史資料。請直接在此頁輸入既有密碼，不要傳到聊天。")
        return
    st.button("鎖定並清除本次結果", on_click=_lock, key="fugle_history_lock")
    st.caption("原三檔最多6次；擴大十檔最多22次（20次日K＋2次名單）。每段最多183天，依序間隔至少1秒；遇錯即停、不重試。兩種測試共用60秒冷卻。請勿多開頁籤同時執行。")
    st.warning(VOLUME_NOTE)
    st.caption("價格使用未還原日K，OHLC逐欄以0.005元為絕對容差。只與已保存的官方TPEx基準比對，不重新抓TPEx、不串入選股或推播。")
    st.caption("2026-10-23休市與6708官方7天沒有OHLC均保留缺值，絕不補造平盤K。富果當日鉅額約18:00後併入，仍可能延後。")
    st.link_button("富果歷史日K文件與成交量口徑", DOC_URL)
    original_run = st.button("執行三檔一年驗證（最多6次查詢）", key="fugle_history_run")
    st.caption("原三檔：5474 聰泰、6708 天擎、9962 有益。擴大樣本：5276、4153、1240、4121、8927、6419、8436、3303、3236、1815。依官方當日量分層選取，非隨機；新掛牌及無一般交易收盤價另列，不從名單母體刪除。")
    st.warning("名單母體是官方發行公司代碼的普通股候選集合，證券種類未獨立逐檔驗證。富果日內名單不接受歷史日期；回傳日期不同時只列觀察交集，不宣稱當日涵蓋率。名單存在不代表一年日K完整。")
    expanded_run = st.button("執行擴大十檔＋上櫃名單驗證（最多22次查詢）", key="fugle_history_expanded_run")
    if original_run or expanded_run:
        last = st.session_state.get(COOLDOWN_KEY)
        if last is not None and time.monotonic() - last < 60:
            st.warning("距前次查詢未滿60秒，未發送新的API請求。")
        else:
            st.session_state.pop(RESULT_KEY, None)
            st.session_state[COOLDOWN_KEY] = time.monotonic()
            with st.spinner("依序讀取富果資料並比對固定官方基準…"):
                st.session_state[RESULT_KEY] = (run_expanded_validation(api_key) if expanded_run else run_validation(api_key))
    report = st.session_state.get(RESULT_KEY)
    if report is None:
        st.caption("已解鎖，尚未執行。按上方按鈕才會使用既有富果額度。")
        return
    if report["status"] == "completed":
        st.success("本次請求與比對已完成；下方仍須逐項查看差異，不代表來源可直接替換。")
    else:
        st.error("本次驗證中途停止；未完成部分不算通過。")
    st.caption("查詢時間（UTC）：" + report["started_at_utc"])
    st.caption(f"本次實際HTTP嘗試數：{report.get('actual_http_attempts', len(report['requests']))}")
    if report.get("universe"):
        universe = report["universe"]
        st.write(f"官方母體 {universe['official_denominator']}；富果聯集 {universe['fugle_union_count']}；觀察交集 {universe['observed_official_intersection_count']}")
        if universe["dated_universe_mismatch"]:
            st.warning("富果名單日期與2026-11-11不同。這不是同日期名單涵蓋率。")
        with st.expander("名單日期、母體、缺漏、多出及掛牌／停牌／無一般交易收盤價分類"):
            st.json(universe)
    with st.expander("請求紀錄、方法與限制（不含憑證）"):
        st.json({k: report[k] for k in ("requests", "methodology", "limitations")})
    for error in report["errors"]:
        st.warning(error["reason"] + (f"（HTTP {error['http_status']}）" if "http_status" in error else ""))
    summaries = [s["summary"] for s in report["samples"]]
    if summaries:
        display = [{"股票": s["symbol"], "富果列數": s["fugle_rows"], "官方有效日K": s["official_valid_ohlc"],
                    "同日有效日K": s["shared_valid_dates"], "價差欄位": s["price_mismatch_fields"],
                    "缺少官方有效日K": len(s["official_valid_dates_without_fugle_valid_ohlc"]),
                    "多出官方未列日期": len(s["fugle_extra_dates"]), "量差日期（非錯誤判定）": s["volume_differing_dates"]}
                   for s in summaries]
        st.dataframe(pd.DataFrame(display), hide_index=True, width="stretch")
    for sample in report["samples"]:
        s = sample["summary"]
        with st.expander(s["symbol"] + " " + s["name"] + "｜日期、價量與缺值明細"):
            st.json(s)
            st.dataframe(pd.DataFrame(sample["daily_comparison"]), hide_index=True, width="stretch")
            if sample["price_differences"]:
                st.dataframe(pd.DataFrame(sample["price_differences"]), hide_index=True, width="stretch")
    st.download_button("下載驗證報告 JSON（不含金鑰或密碼）",
                       json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
                       file_name=("fugle_expanded_validation_20261111.json" if report.get("mode") == "expanded10_and_universe"
                                  else "fugle_history_validation_20261111.json"), mime="application/json",
                       key="fugle_history_download")
    st.caption("結果只保留在本次瀏覽工作階段，不寫入GitHub或共用快取。需要後續判讀時可將下載的報告提供給助理。")
