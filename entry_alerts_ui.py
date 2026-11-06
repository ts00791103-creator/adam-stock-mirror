"""Guided preview only: browser UI never sends Telegram messages."""
from dataclasses import asdict
import json
import pandas as pd
import streamlit as st
from entry_alerts import AlertSettings, EntryDataError, evaluate_entry_alerts, telegram_text
from stock_screener import resolve_watchlist
from screener_ui import screening_data


def show_entry_alerts(stock_list):
    with st.expander("進場觀察提醒｜三步試跑", expanded=False):
        st.info("這裡只做提醒條件預覽，不會發送訊息，也不會變更背景服務的追蹤名單與條件。Telegram自動通知由獨立背景服務執行；本頁不會讀取其啟用狀態。")
        text = st.text_area("① 選擇追蹤股票（最多30檔，逗號或換行分隔）", "2330,2308,2317,2454", key="entry_watchlist")
        rules = st.multiselect("② 選擇提醒條件", ["箱底反彈", "箱頂突破"], default=["箱底反彈", "箱頂突破"], key="entry_rules")
        st.caption("箱底反彈：前收盤靠近既有箱底，本日上漲且收高於開盤，並仍在箱內。箱頂突破：收盤超過既有箱頂且放量，超出過多則不提醒。箱型與均量只使用訊號日前資料。")
        with st.expander("進階條件（可先用預設值）"):
            st.caption("以下是初始測試參數，不代表適合所有股票的進場門檻。")
            window = st.slider("提醒箱型觀察根數", 10, 60, 20, key="entry_window")
            width = st.slider("提醒箱型最大振幅（%）", 3, 25, 20, key="entry_width")
            near = st.slider("前收盤距箱底上限（%）", 1, 20, 3, key="entry_near")
            rebound = st.number_input("反彈最低漲幅（%）", min_value=.1, max_value=20., value=.5, key="entry_rebound")
            buffer = st.number_input("突破最低幅度（%）", min_value=0., max_value=19., value=.5, key="entry_buffer")
            maximum = st.number_input("突破最大追蹤幅度（%）", min_value=.1, max_value=20., value=5., key="entry_max")
            ratio = st.number_input("突破量／前20日均量最低倍數", min_value=.1, value=1.5, key="entry_ratio")
            lots = st.number_input("提醒最低前20日均量（張）", min_value=0., value=1000., key="entry_lots")
        settings = AlertSettings(window, width, near, rebound, buffer, maximum, ratio, lots)
        signature = (text, tuple(sorted(rules)), json.dumps(asdict(settings), sort_keys=True))
        if st.button("③ 試跑並產生提醒紀錄", key="entry_preview"):
            st.session_state.pop("entry_preview_result", None)
            try:
                settings.validate()
                if not rules:
                    raise ValueError("請至少選擇一種提醒條件")
                items, failures = resolve_watchlist(text, stock_list)
                if not items:
                    raise ValueError("請輸入可辨識的股票名單")
            except ValueError as exc:
                st.error(str(exc))
                return
            now = pd.Timestamp.now(tz="Asia/Taipei")
            events, checked = [], []
            progress = st.progress(0., text="開始試跑")
            for n, (symbol, code, name, exchange) in enumerate(items):
                stage = "取得行情"
                try:
                    data = screening_data(symbol).copy()
                    stage = "整理已完成日K"
                    index = pd.to_datetime(data.index)
                    if index.tz is not None:
                        index = index.tz_convert("Asia/Taipei").tz_localize(None)
                    data.index = index
                    # Never preview today's unfinished candle before 14:00 Taiwan time.
                    if now.hour < 14:
                        data = data.loc[data.index.normalize() < now.tz_localize(None).normalize()]
                    if data.empty:
                        raise ValueError("沒有已完成的日K")
                    day = str(data.index[-1].date())
                    stage = "檢查行情與提醒條件"
                    found = evaluate_entry_alerts(data, symbol, day, settings, rules)
                    events.extend({**event, "名稱": name} for event in found)
                    checked.append({"股票": symbol, "名稱": name, "檢查日期": day, "符合提醒": len(found)})
                except EntryDataError as exc:
                    dates = "、".join(dict.fromkeys(r["日期／時間"][:10] for r in exc.records))
                    fields = []
                    for field in ("開盤", "最高", "最低", "收盤"):
                        if any(pd.isna(r[field]) for r in exc.records):
                            fields.append(field + "價缺漏")
                    reason = "、".join(fields) or "價格高低不一致或含無效數值"
                    failures.append({"輸入": symbol, "階段": stage, "異常日期（最多20根）": dates,
                                     "原因": reason + "，本次未判定；不補值、不使用前一日替代"})
                except Exception as exc:
                    # Never expose raw exception text, URLs, credentials or traceback.
                    known = {"ValueError": "資料格式或品質未通過", "TypeError": "資料型態不相容",
                             "KeyError": "缺少必要欄位", "IndexError": "資料筆數不足",
                             "TimeoutError": "行情連線逾時", "ConnectionError": "行情連線失敗"}
                    reason = known.get(type(exc).__name__, "處理失敗")
                    failures.append({"輸入": symbol, "階段": stage, "原因": reason + "，本次未判定"})
                progress.progress((n+1)/len(items), text=f"已檢查{n+1}/{len(items)}檔")
            progress.empty()
            st.session_state["entry_preview_result"] = (signature, events, checked, failures)
        saved = st.session_state.get("entry_preview_result")
        if saved is None:
            return
        if saved[0] != signature:
            st.info("條件已變更，請重新試跑。")
            return
        _, events, checked, failures = saved
        st.write(f"已檢查{len(checked)}檔｜符合提醒{len(events)}筆｜未判定{len(failures)}筆")
        st.caption("這是最近已完成日K的歷史試跑，不會發送通知，也不是保證上漲或自動下單。紀錄僅保留本次瀏覽器工作階段，可下載CSV保存。")
        if events:
            st.dataframe(pd.DataFrame(events), hide_index=True)
            with st.expander("看看手機會收到什麼"):
                st.text(telegram_text(events[0]))
            st.download_button("下載本次提醒CSV", pd.DataFrame(events).to_csv(index=False).encode("utf-8-sig"),
                               file_name="adam_entry_alert_preview.csv", mime="text/csv", key="entry_csv")
        elif checked:
            st.info("本次沒有條件成立，不產生進場觀察提醒。")
        else:
            st.info("本次沒有股票完成判定，尚無法確認提醒條件是否成立。")
        with st.expander("逐檔檢查紀錄"):
            st.dataframe(pd.DataFrame(checked), hide_index=True)
        if failures:
            st.warning("以下股票沒有完成判定，不算成不符合。")
            st.dataframe(pd.DataFrame(failures), hide_index=True)

