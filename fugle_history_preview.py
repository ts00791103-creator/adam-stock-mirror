"""Candidate-only protected page. No shared data cache, secrets or background fetch."""
import hmac
import json
import time

import pandas as pd
import streamlit as st

from fugle_history_validation import DOC_URL, END, START, VERSION, VOLUME_NOTE, run_validation
from live_quote import _secret

RESULT_KEY = "fugle_history_validation_result"
PASSWORD_KEY = "fugle_history_validation_password"
COOLDOWN_KEY = "fugle_history_validation_last_attempt"


def _lock():
    st.session_state.pop(RESULT_KEY, None)
    st.session_state.pop(PASSWORD_KEY, None)


def show_fugle_history_preview():
    st.subheader("富果歷史日K驗證（受保護測試頁）")
    st.caption(f"{VERSION}｜5474 聰泰、6708 天擎、9962 有益｜{START} 至 {END}")
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
    st.caption("每次執行每檔分兩段、每段小於一年，最多6次唯讀請求。遇錯誤立即停止，不自動重試；同一工作階段重複按鈕至少間隔60秒。請勿多開頁籤同時執行。")
    st.warning(VOLUME_NOTE)
    st.caption("價格使用未還原日K，OHLC逐欄以0.005元為絕對容差。只與已保存的官方TPEx基準比對，不重新抓TPEx、不串入選股或推播。")
    st.caption("2026-10-23休市與6708官方7天沒有OHLC均保留缺值，絕不補造平盤K。富果當日鉅額約18:00後併入，仍可能延後。")
    st.link_button("富果歷史日K文件與成交量口徑", DOC_URL)
    if st.button("執行三檔一年驗證（最多6次查詢）", key="fugle_history_run"):
        last = st.session_state.get(COOLDOWN_KEY)
        if last is not None and time.monotonic() - last < 60:
            st.warning("距前次查詢未滿60秒，未發送新的API請求。")
        else:
            st.session_state.pop(RESULT_KEY, None)
            st.session_state[COOLDOWN_KEY] = time.monotonic()
            with st.spinner("依序讀取三檔富果日K並比對官方基準…"):
                st.session_state[RESULT_KEY] = run_validation(api_key)
    report = st.session_state.get(RESULT_KEY)
    if report is None:
        st.caption("已解鎖，尚未執行。按上方按鈕才會使用既有富果額度。")
        return
    if report["status"] == "completed":
        st.success("六次請求與三檔比對已完成；下方仍須逐項查看差異，不代表來源可直接替換。")
    else:
        st.error("本次驗證中途停止；未完成部分不算通過。")
    st.caption("查詢時間（UTC）：" + report["started_at_utc"])
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
                       file_name="fugle_history_validation_20261111.json", mime="application/json",
                       key="fugle_history_download")
    st.caption("結果只保留在本次瀏覽工作階段，不寫入GitHub或共用快取。需要後續判讀時可將下載的報告提供給助理。")
