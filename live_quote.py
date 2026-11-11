"""Personal-use Fugle quote panel. Does not modify historical candles."""
import re
import hmac
import json
import math
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

TZ = ZoneInfo("Asia/Taipei")


def _render_quote_metrics(price, change, percent):
    """Give sidebar quotes full-width rows without changing other metric cards."""
    st.markdown("""
    <style>
    .st-key-live_quote_metrics [data-testid="stMetric"] {
        display:flex;flex-direction:row;align-items:center;
        justify-content:space-between;gap:.5rem;min-width:0;
        padding:.75rem .875rem;
    }
    .st-key-live_quote_metrics [data-testid="stMetricLabel"] {
        flex:0 0 auto;width:auto;margin:0;
    }
    .st-key-live_quote_metrics [data-testid="stMetricLabel"],
    .st-key-live_quote_metrics [data-testid="stMetricLabel"] * {
        white-space:nowrap!important;overflow:visible!important;
        text-overflow:clip!important;overflow-wrap:normal;
    }
    .st-key-live_quote_metrics [data-testid="stMetricValue"],
    .st-key-live_quote_metrics [data-testid="stMetricValue"] * {
        white-space:nowrap!important;overflow-wrap:normal;word-break:normal;
        font-size:1.25rem!important;line-height:1.3;
        font-variant-numeric:tabular-nums;text-align:right;
    }
    .st-key-live_quote_metrics [data-testid="stMetricValue"] {
        flex:0 0 auto;width:auto;
    }
    </style>
    """, unsafe_allow_html=True)
    with st.container(key="live_quote_metrics", gap="small"):
        st.metric("最新成交價", f"{price:,.2f}")
        st.metric("漲跌", f"{change:+,.2f}" if change is not None else "—")
        st.metric("漲跌幅", f"{percent:+.2f}%" if percent is not None else "—")


def _secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except (FileNotFoundError, KeyError):
        return ""


def _fetch_quote(symbol, api_key):
    url = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/" + symbol
    request = urllib.request.Request(
        url, headers={"X-API-KEY": api_key, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=7) as response:
        return json.load(response)


def _format_trade_time(microseconds):
    if not microseconds:
        return "尚無成交時間"
    try:
        return datetime.fromtimestamp(int(microseconds) / 1_000_000, TZ).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OverflowError):
        return "成交時間無法解析"


def _render_quote(symbol, api_key):
    try:
        quote = _fetch_quote(symbol, api_key)
        last_trade = quote.get("lastTrade") or {}
        price = last_trade.get("price")
        if price is None:
            price = quote.get("closePrice")
        if price is None:
            st.info("目前沒有實際成交資料（可能尚未開盤或無成交）。")
            return
        price = float(price)
        if not math.isfinite(price) or price <= 0:
            st.warning("行情回傳無效成交價，本次不顯示價格。")
            return
        previous = quote.get("previousClose")
        previous = float(previous) if previous is not None else None
        if previous is not None and (not math.isfinite(previous) or previous <= 0):
            previous = None
        change = float(price) - previous if previous else None
        percent = change / float(previous) * 100 if change is not None else None
        _render_quote_metrics(price, change, percent)
        trade_time = _format_trade_time(last_trade.get("time") or quote.get("closeTime"))
        st.caption(f"富果行情｜{symbol}｜成交時間（台灣）：{trade_time}｜每 10 秒查詢一次")
        if quote.get("isTrial"):
            st.warning("目前包含試撮資訊；上方只顯示實際成交價。")
        now = datetime.now(TZ)
        if trade_time != "尚無成交時間":
            try:
                dt = datetime.strptime(trade_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
                if (now - dt).total_seconds() > 90:
                    st.info("最新成交時間距現在超過 90 秒，可能已收盤、暫停交易或沒有新成交。")
            except ValueError:
                pass
    except urllib.error.HTTPError as exc:
        st.warning(f"即時行情暫時不可用（HTTP {exc.code}）。歷史 K 線不受影響。")
    except Exception:
        st.warning("即時行情連線失敗，請確認金鑰、網路與權限。歷史 K 線不受影響。")


@st.fragment(run_every="10s")
def _quote_fragment(symbol, api_key):
    _render_quote(symbol, api_key)


def show_personal_quote(market, symbol, production=False):
    if market != "台灣股票／ETF":
        return
    stock_id = str(symbol).split(".")[0]
    if not re.fullmatch(r"[0-9]{4,6}[A-Za-z]?", stock_id):
        return
    with st.expander("個人即時價格" if production else "個人即時價格（測試版）", expanded=False):
        st.caption("僅報價面板自動更新；原本歷史 K 線與亞當鏡像不會被改寫。")
        st.caption(f"目前報價股票：{stock_id}。選股使用歷史日K，這裡的報價不會改變篩選結果。")
        key = _secret("FUGLE_API_KEY")
        password = _secret("LIVE_QUOTE_PASSWORD")
        if not key or not password:
            st.info("請先在 Streamlit Cloud Secrets 設定 FUGLE_API_KEY 與 LIVE_QUOTE_PASSWORD，才可使用個人報價。")
            return
        entered = st.text_input("個人報價密碼", type="password", key="live_quote_password_input")
        if not entered or not hmac.compare_digest(entered, password):
            if entered:
                st.error("密碼不正確")
            return
        enabled = st.checkbox("啟用每 10 秒更新", value=False, key="live_quote_enabled")
        refresh = st.button("查詢一次最新成交價", key="live_quote_refresh")
        if enabled:
            _quote_fragment(stock_id, key)
        elif refresh:
            _render_quote(stock_id, key)
        else:
            st.caption("尚未查詢報價。可單次查詢，或啟用每10秒更新；休市時顯示的是最近成交。")
