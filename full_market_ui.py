"""Two-stage scanner with explicit coverage and user-triggered batches."""
import pandas as pd
import streamlit as st
from market_universe import fetch_universe, shortlist, history_as_of
from screener_ui import screening_data
from stock_screener import screen_frame
from stock_navigation import stock_result_table, queue_analysis


@st.cache_data(ttl=900, show_spinner=False)
def official_snapshot(exchanges):
    results, errors = fetch_universe(exchanges)
    return results, errors, pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def show_full_market(production=False):
    with st.expander("全台股選股（上市＋上櫃）" if production else "全台股選股（分批測試）"):
        st.caption("官方公司名單中的上市／上櫃四碼股票；不含ETF、權證、興櫃。先讀每日行情初選，再分批讀歷史日K。不是即時全市場掃描，也不依鏡像終點排名。")
        scope = st.selectbox("市場範圍", ["上市＋上櫃", "上市", "上櫃"], key="market_scope")
        a, b = st.columns(2)
        low = a.number_input("全市場最低股價", min_value=0., value=0., key="market_low")
        high = b.number_input("全市場最高股價", min_value=0., value=10000., key="market_high")
        daily = st.number_input("初選最低當日成交量（張）", min_value=0., value=1000., key="market_daily")
        lots = st.number_input("複選最低20日平均成交量（張）", min_value=0., value=1000., key="market_avg")
        mode = st.selectbox("全市場箱型條件", ["接近箱底", "箱內整理", "不限箱型"], key="market_box")
        near = st.slider("全市場距箱底上限（%）", 1, 20, 5, key="market_near")
        window = st.slider("全市場箱型觀察根數", 10, 60, 20, key="market_window")
        width = st.slider("全市場箱型最大振幅（%）", 3, 25, 20, key="market_width")
        st.caption("1張＝1000股。初選用官方當日量，複選用Yahoo 20日均量，兩者不同。複選截取至官方行情日期，不使用之後的K棒。資料快取最多15分鐘，官方行情可能尚未更新，請看日期。")
        config = (scope, low, high, daily, lots, mode, near, window, width)
        if st.button("取得全市場初選", key="market_start"):
            st.session_state.pop("market_scan", None)
            if low > high:
                st.error("最低股價不可大於最高股價。")
                return
            exchanges = ("上市", "上櫃") if scope == "上市＋上櫃" else (scope,)
            with st.spinner("讀取官方每日行情與公司名單…"):
                results, errors, timestamp = official_snapshot(exchanges)
            st.session_state["market_scan"] = {
                "config": config, "results": results, "errors": errors,
                "timestamp": timestamp, "candidates": shortlist(results, low, high, daily),
                "cursor": 0, "checked": [], "failed": []}
        state = st.session_state.get("market_scan")
        if state is None:
            return
        if state["config"] != config:
            st.info("條件已變更，請重新按「取得全市場初選」。舊結果暫不顯示。")
            return
        results, errors = state["results"], state["errors"]
        st.caption(f"官方資料抓取時間（台灣）：{state['timestamp']}")
        if errors:
            st.warning("資料範圍不完整：以下市場未納入，本次不能視為全台股結果。")
            st.dataframe(pd.DataFrame(errors), hide_index=True)
        issues = []
        for result in results:
            dates = sorted({r["官方行情日期"] for r in result["rows"]})
            st.caption(f"{result['市場']}：公司名單{result['公司數']}檔｜有效每日行情{len(result['rows'])}檔｜缺漏或無效{len(result['failures'])}檔｜行情日期：{', '.join(dates)}")
            if any(day != str(pd.Timestamp.now(tz="Asia/Taipei").date()) for day in dates):
                st.info(f"{result['市場']}官方行情不是今天，可能休市或尚未更新。複選將以各檔顯示的官方日期為準。")
            issues.extend(result["failures"])
        if issues:
            with st.expander("官方行情缺漏／無效項目"):
                st.dataframe(pd.DataFrame(issues), hide_index=True)
        candidates = state["candidates"]
        total, cursor = len(candidates), state["cursor"]
        st.write(f"初選 {total} 檔｜已檢查 {cursor} 檔｜待檢查 {total-cursor} 檔")
        if candidates:
            with st.expander("查看初選股票（尚未驗證20日均量與箱型）"):
                stock_result_table(pd.DataFrame(candidates),candidates,"market_first_results",production)
                st.download_button("下載初選CSV", pd.DataFrame(candidates).to_csv(index=False).encode("utf-8-sig"),
                                   file_name="adam_market_shortlist.csv", mime="text/csv", key="market_first_csv")
        else:
            st.info("沒有符合初選條件的有效行情；請同時查看上方市場失敗或行情缺漏提示。")
        if cursor < total and st.button("分析下一批（最多10檔）", key="market_next"):
            progress = st.progress(0., text="開始複選")
            batch = candidates[cursor:cursor+10]
            for index, item in enumerate(batch):
                try:
                    history = history_as_of(screening_data(item["Yahoo代號"]), item["官方行情日期"])
                    row = screen_frame(history, min_price=low, max_price=high,
                                       min_lots=lots, mode=mode, near_pct=near, window=window, width_pct=width)
                    if row["資料日期"] != item["官方行情日期"]:
                        raise ValueError(f"來源日期不同：官方{item['官方行情日期']}／日K{row['資料日期']}，本次不判定")
                    state["checked"].append({**item, **row})
                except Exception:
                    state["failed"].append({"代號": item["代號"], "名稱": item["名稱"],
                                             "原因": "歷史行情無法讀取、無效或日期與官方不一致；本次未判定，請稍後重新初選"})
                state["cursor"] += 1
                progress.progress((index+1)/len(batch), text=f"已檢查 {state['cursor']}/{total} 檔")
            progress.empty()
            st.rerun()
        matched = [r for r in state["checked"] if r["符合"]]
        if cursor < total:
            st.warning(f"尚未檢查全部初選股票。以下僅已檢查部分結果：符合{len(matched)}檔、無法判定{len(state['failed'])}檔。初選依當日成交量由高到低處理，不代表投資排序。")
        elif total:
            st.success(f"本次初選名單已處理完：有效複選{len(state['checked'])}檔、符合{len(matched)}檔、無法判定{len(state['failed'])}檔。")
        if matched:
            stock_result_table(pd.DataFrame(matched),matched,"market_results",production)
            symbols = [r["Yahoo代號"] for r in matched]
            selected = st.selectbox("全市場結果帶入個股", symbols,
                                    format_func=lambda symbol: next(f"{r['代號']} {r['名稱']}（{r['市場']}）" for r in matched if r["Yahoo代號"] == symbol), key="market_choice")
            st.caption("選股以官方行情日期及一年日K複選；下方個股分析會依你選擇的期間重新讀取最新行情，日期與箱型可能不同。請核對兩邊日期與箱型參數。")
            if st.button("帶入這檔股票查看鏡像", key="market_use"):
                st.session_state["adam_stock_query"] = selected.split(".")[0]
                if not production:
                    queue_analysis(st.session_state, next(r for r in matched if r["Yahoo代號"]==selected))
                    st.rerun()
                st.success("已帶入下方個股查詢，請按「開始亞當鏡像分析」。")
        elif cursor:
            st.info("目前已檢查的股票沒有符合者；待檢查或無法判定項目不算不符合。")
        if state["checked"]:
            with st.expander("查看已檢查的有效行情（含未符合）"):
                stock_result_table(pd.DataFrame(state["checked"]),state["checked"],"market_checked_results",production)
            st.download_button("下載已檢查結果CSV", pd.DataFrame(state["checked"]).to_csv(index=False).encode("utf-8-sig"),
                               file_name="adam_market_checked.csv", mime="text/csv", key="market_checked_csv")
        if state["failed"]:
            st.dataframe(pd.DataFrame(state["failed"]), hide_index=True)
        st.caption("名單與進度僅保留於本次瀏覽器工作階段；可下載CSV保存。若要重試失敗或更新資料，請重新取得初選。")
