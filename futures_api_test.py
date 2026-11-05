"""Read-only Fugle futures API permission diagnostic; no order submission."""
import hmac
import json
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

def show_futures_api_test():
    with st.expander("台指期｜富果 API 權限測試", expanded=False):
        st.caption("只查詢 TXF1! 最近月台指期報價，不下單、不修改歷史 K 線。")
        try:
            key = str(st.secrets.get("FUGLE_API_KEY", "")).strip()
            password = str(st.secrets.get("LIVE_QUOTE_PASSWORD", "")).strip()
        except Exception:
            key, password = "", ""
        if not key or not password:
            st.info("請先設定 FUGLE_API_KEY 和 LIVE_QUOTE_PASSWORD。")
            return
        entered = st.text_input("個人報價密碼（台指期測試）", type="password", key="futures_api_test_password")
        if not entered or not hmac.compare_digest(entered, password):
            if entered:
                st.error("密碼不正確")
            return
        if not st.button("測試 TXF1! 即時行情權限", key="futures_api_test_button"):
            return
        url = "https://api.fugle.tw/marketdata/v1.0/futopt/intraday/quote/TXF1!"
        request = urllib.request.Request(url, headers={"X-API-KEY": key, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.load(response)
            trade = data.get("lastTrade") or {}
            price = trade.get("price")
            if price is None:
                price = data.get("closePrice")
            timestamp = trade.get("time") or data.get("closeTime")
            when = "無成交時間"
            if timestamp:
                when = datetime.fromtimestamp(int(timestamp)/1_000_000, ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
            st.success("富果台指期行情 API 權限測試成功")
            st.metric("最近一筆成交價（可能非目前即時）", f"{float(price):,.0f}" if price is not None else "無成交")
            st.caption(f"商品：{data.get('symbol','TXF1!')}｜成交時間（台灣）：{when}")
            st.caption("測試成功只代表 API 可查詢；夜盤、更新延遲及正式 K 棒仍需後續驗證。")
        except urllib.error.HTTPError as exc:
            code = exc.code
            if code in (401,403):
                st.warning(f"HTTP {code}：金鑰未通過驗證或目前方案無期權行情權限。免費基本方案不支援期權日內 API。")
            elif code == 429:
                st.warning("HTTP 429：已達 API 呼叫限制，請稍後再試。")
            else:
                st.warning(f"期貨 API 回應 HTTP {code}；請確認商品代碼與服務狀態。")
        except Exception:
            st.warning("測試連線失敗，請稍後再試；原本圖表不受影響。")
