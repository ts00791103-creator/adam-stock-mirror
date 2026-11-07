"""Development-only monthly source comparison; never a production fallback."""
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from official_history import compare_month_sources, invalid_candles

CASES = {"8358 金居｜2018年6月": ("8358.TWO", "2018-06"),
         "2924 宏太-KY｜2021年12月": ("2924.TWO", "2021-12"),
         "3095 及成｜2021年12月": ("3095.TWO", "2021-12"),
         "2330 台積電｜2026年11月（對照）": ("2330.TW", "2026-11")}


@st.cache_data(ttl=86400, show_spinner=False)
def compare_month(symbol, month):
    return compare_month_sources(symbol, month)


def show_official_history_preview():
    with st.expander("官方歷史日K來源驗證（開發預覽）", expanded=False):
        st.caption("只核對所選月份；此區不更新正式站、不接入選股或推播，也不把官方原始價直接混入整段不同調整基準的資料。")
        with st.form("hsrc_query_form"):
            selected = st.selectbox("選擇歷史異常驗證案例", list(CASES), key="hsrc_case")
            submitted = st.form_submit_button("核對官方月份與修正預覽")
        if submitted:
            symbol, month = CASES[selected]
            try:
                with st.spinner("讀取官方月表與原始來源…"):
                    st.session_state["hsrc_result"] = (symbol, month, compare_month(symbol, month))
                st.session_state.pop("hsrc_error", None)
            except Exception as exc:
                st.session_state.pop("hsrc_result", None)
                st.session_state["hsrc_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        if st.session_state.get("hsrc_error"):
            st.error("本次來源驗證失敗，未套用修正：" + st.session_state["hsrc_error"])
        if "hsrc_result" not in st.session_state:
            return
        symbol, month, result = st.session_state["hsrc_result"]
        official, original, repaired, ledger, evidence, payload = result
        st.markdown(f"**{symbol}｜{month}｜官方原始日K／收盤修正預覽**")
        before, after = invalid_candles(original), invalid_candles(repaired)
        st.write(f"原始來源異常：{len(before)}根｜修正預覽：{len(ledger)}根｜預覽仍異常：{len(after)}根")
        missing_days = sorted(set(official.index) - set(original.index))
        extra_days = sorted(set(original.index) - set(official.index))
        st.caption(f"官方{len(official)}根；官方未提供一般交易OHLC：{len(evidence['unavailable_rows'])}天；原始來源缺少官方日期：{len(missing_days)}天、多出未核對日期：{len(extra_days)}天。這些日期未造價補齊或刪除。")
        st.warning("只處理原收盤超出高低範圍、且同日官方開高低均吻合的情況。原本看似正常但與官方不同的價格不自動改寫；此月份通過不代表整段歷史已修復。")
        if ledger:
            st.dataframe(pd.DataFrame(ledger), hide_index=True, width="stretch")
        st.caption("官方價格基準：未復權原始價。" + evidence["volume_precision"] + "；此預覽不計算量比或交易訊號。")
        view = st.radio("驗證圖表", ["官方原始日K", "收盤修正預覽"], horizontal=True, key="hsrc_chart_view")
        frame = official if view == "官方原始日K" else repaired
        if invalid_candles(frame):
            st.error("預覽仍有異常，停止畫圖。")
        else:
            figure = go.Figure(go.Candlestick(x=frame.index, open=frame.Open, high=frame.High,
                                               low=frame.Low, close=frame.Close, name=view))
            figure.update_layout(height=430, xaxis_rangeslider_visible=False, yaxis_title="元", title=symbol + "｜" + view)
            st.plotly_chart(figure, use_container_width=True, key="hsrc_chart")
        with st.expander("官方來源證據與未提供OHLC的日期"):
            st.json(evidence)
            st.dataframe(official, width="stretch")
        download = {"symbol": symbol, "month": month, "evidence": evidence, "repair_ledger": ledger,
                    "source_invalid_dates": before, "preview_invalid_dates": after,
                    "source_missing_official_dates": [str(d.date()) for d in missing_days],
                    "source_extra_unverified_dates": [str(d.date()) for d in extra_days],
                    "official_payload": payload}
        st.download_button("下載本月來源證據與修正紀錄", json.dumps(download, ensure_ascii=False, indent=2),
                           file_name=f"official_history_{symbol}_{month}.json", mime="application/json", key="hsrc_download")
