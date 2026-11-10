"""Candidate-only watchlist interface. No changes to production entrypoint."""
import pandas as pd
import streamlit as st
import yfinance as yf
from stock_screener import resolve_watchlist, screen_frame
from stock_navigation import stock_result_table, queue_analysis


@st.cache_data(ttl=900, show_spinner=False)
def screening_data(symbol):
    return yf.download(symbol, period="1y", interval="1d", auto_adjust=False,
                       progress=False, threads=False, timeout=12)


def show_screener(stock_list, production=False):
    with st.expander("自選名單選股" if production else "自選名單選股（測試版）", expanded=False):
        st.caption("最多30檔，依歷史日K篩選。條件符合不代表未來上漲；合理價格與鏡像請於個股分析查看。")
        text = st.text_area("股票名單（代號或完整中文名稱，以逗號或換行分隔）",
                            "2330, 2308, 2317, 2454", key="screen_list")
        c1, c2 = st.columns(2)
        low = c1.number_input("最低股價", min_value=0.0, value=0.0, key="screen_low")
        high = c2.number_input("最高股價", min_value=0.0, value=10000.0, key="screen_high")
        lots = st.number_input("最低20日平均成交量（張）", min_value=0.0, value=1000.0, key="screen_lots")
        mode = st.selectbox("箱型條件", ["不限箱型", "箱內整理", "接近箱底"], key="screen_mode")
        near = st.slider("接近箱底的最大距離（%）", 1, 20, 5, key="screen_near")
        if production:
            window = st.slider("選股箱型觀察根數", 10, 60, 20, key="screen_window")
            width = st.slider("選股箱型最大振幅（%）", 3, 25, 20, key="screen_width")
            st.caption("箱型使用與個股相同的演算法；比較時請將個股箱型參數設為相同值。成交量1張＝1000股，20日均量含最新一根。盤中日K尚未收盤，數值可能變動。資料快取最多15分鐘。")
        else:
            window, width = 20, 20
            st.caption("固定選股基準：日K、20根箱型、最大振幅20%。20日均量含最新一根，盤中數值可能變動。")
        config = (text, low, high, lots, mode, near, window, width)
        if st.button("開始篩選自選名單", key="screen_run"):
            st.session_state.pop("screen_result", None)
            if low > high:
                st.error("最低股價不可大於最高股價。")
                return
            try:
                items, failures = resolve_watchlist(text, stock_list)
            except ValueError as exc:
                st.error(str(exc))
                return
            if not items:
                st.warning("沒有可辨識的股票，請輸入名單。")
            rows = []
            progress = st.progress(0.0, text="準備讀取日K")
            for n, (symbol, code, name, exchange) in enumerate(items):
                try:
                    result = screen_frame(screening_data(symbol), min_price=low, max_price=high,
                                          min_lots=lots, mode=mode, near_pct=near,
                                          window=window, width_pct=width)
                    rows.append({"代號": code, "名稱": name, "市場": exchange,
                                 "Yahoo代號": symbol, **result})
                except Exception as exc:
                    failures.append({"輸入": symbol, "原因": f"行情無法篩選：{str(exc)[:160]}"})
                progress.progress((n+1)/len(items), text=f"已處理 {n+1}/{len(items)} 檔")
            progress.empty()
            st.session_state["screen_result"] = (config, rows, failures, pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S"))
        saved = st.session_state.get("screen_result")
        if saved is None:
            return
        old_config, rows, failures, timestamp = saved
        if old_config != config:
            st.info("條件或名單已變更，請重新按「開始篩選自選名單」。")
            return
        matched = [r for r in rows if r["符合"]]
        st.caption(f"執行時間（台灣）：{timestamp}｜有效行情 {len(rows)} 檔｜符合 {len(matched)} 檔｜無法處理 {len(failures)} 筆。請查看各檔資料日期，舊日期可能來自休市、停牌或資料延遲。")
        if matched:
            stock_result_table(pd.DataFrame(matched),matched,"screen_results",production)
            choice = st.selectbox("帶入個股分析", [r["代號"] for r in matched],
                                  format_func=lambda code: next(f"{r['代號']} {r['名稱']}" for r in matched if r["代號"] == code), key="screen_choice")
            if st.button("使用這檔股票", key="screen_use"):
                st.session_state["adam_stock_query"] = choice
                if not production:
                    queue_analysis(st.session_state, next(r for r in matched if r["代號"]==choice))
                    st.rerun()
                st.success("已帶入下方股票查詢；請選擇日K／週K後按「開始亞當鏡像分析」。")
        else:
            st.info("本次沒有符合條件的股票；無法取得行情的股票不計為不符合。")
        if rows:
            with st.expander("查看所有有效行情（含未符合）"):
                stock_result_table(pd.DataFrame(rows),rows,"screen_all_results",production)
            st.download_button("下載本次完整篩選CSV", pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
                               file_name="adam_watchlist_screen.csv", mime="text/csv", key="screen_csv")
        if failures:
            st.warning("以下項目沒有完成篩選，請修正代號或稍後重試。")
            st.dataframe(pd.DataFrame(failures), hide_index=True)
