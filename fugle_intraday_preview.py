"""Candidate-only, password-protected one-shot Fugle diagnostics."""

import hmac

import streamlit as st

from fugle_intraday_check import run_intraday_check
from live_quote import _secret


VERSION = "FUGLE-INTRADAY-20261116-2"
SYMBOL = "2330.TW"
PASSWORD_KEY = "fugle_intraday_preview_password"


def _lock():
    st.session_state.pop(PASSWORD_KEY, None)


def show_fugle_intraday_preview():
    st.subheader("富果分 K 單次驗收（候選版）")
    st.caption(f"{VERSION}｜{SYMBOL}｜盤中整股")
    if st.button("返回候選站首頁", key="fugle_intraday_back"):
        _lock()
        st.query_params.pop("view", None)
        st.rerun()

    api_key, password = _secret("FUGLE_API_KEY"), _secret("LIVE_QUOTE_PASSWORD")
    if not api_key or not password:
        _lock()
        st.warning("候選站缺少既有富果授權設定。尚未發送 API 請求。")
        return

    entered = st.text_input("個人報價密碼（分 K 驗收）", type="password", key=PASSWORD_KEY)
    if not entered or not hmac.compare_digest(entered.encode(), password.encode()):
        if entered:
            st.error("密碼不正確。尚未發送 API 請求。")
        return

    timeframe = st.selectbox("分 K 週期", (1, 5), format_func=lambda n: f"{n} 分 K",
                             key="fugle_intraday_preview_timeframe")
    st.caption("每次按鈕最多各查一次分 K 和日內報價。資料僅用於驗收。")
    if st.button("查核富果整股分 K 與日內報價一次", key="fugle_intraday_preview_check"):
        report = run_intraday_check(SYMBOL, timeframe, api_key)
        st.info(report["status"])
        if "quote_time" in report:
            st.caption("統計時間的資料年齡與服務延遲需分開核實。")
        if "quote_time" in report or "code" in report:
            st.json(report)
    st.warning("當沖不可判定。交易行情延遲及收棒狀態尚待實測。")
