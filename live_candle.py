"""Opt-in experimental live last-candle preview, isolated from confirmed Adam data."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from live_quote import _fetch_quote, _secret
from mobile_chart import mobile_chart

TZ = ZoneInfo("Asia/Taipei")
MINUTES = {"1m":1,"5m":5,"10m":10,"15m":15,"30m":30,"60m":60}


def _preview(df, price, trade_time, interval):
    """Return a copy. Never mutate cached history or Adam pivot input."""
    result = df.copy(deep=True)
    dt = datetime.fromtimestamp(int(trade_time)/1_000_000, TZ)
    now = datetime.now(TZ)
    if dt.date() != now.date() or abs((now-dt).total_seconds()) > 90:
        raise ValueError("成交資料非最近 90 秒，暫不合成即時 K 棒")
    if not (9 <= dt.hour < 14) or (dt.hour == 13 and dt.minute > 30):
        raise ValueError("非台股日盤成交時段")
    if interval not in MINUTES:
        raise ValueError("目前僅支援 1／5／10／15／30／60 分 K")
    minutes = MINUTES[interval]
    stamp = pd.Timestamp(dt.replace(tzinfo=None))
    if minutes == 60:
        # Taiwan day-session 60m bars begin at 09:00.
        bucket = stamp.normalize() + pd.Timedelta(hours=9) + pd.Timedelta(
            minutes=((stamp.hour*60+stamp.minute-540)//60)*60)
    else:
        bucket = stamp.floor(f"{minutes}min")
    if result.empty:
        raise ValueError("沒有歷史 K 棒")
    last = pd.Timestamp(result.index[-1])
    if bucket < last:
        raise ValueError("行情早於目前歷史 K 棒，等待資料同步")
    price = float(price)
    if bucket == last:
        result.loc[last,"Close"] = price
        result.loc[last,"High"] = max(float(result.loc[last,"High"]), price)
        result.loc[last,"Low"] = min(float(result.loc[last,"Low"]), price)
    else:
        if bucket.date() != last.date():
            raise ValueError("跨交易日請先重新下載歷史 K 棒")
        # This is only an indicative candle: intrabar high/low/volume are incomplete.
        result.loc[bucket, ["Open","High","Low","Close","Volume"]] = [price,price,price,price,0]
    return result, dt


@st.fragment(run_every="10s")
def live_candle_fragment(symbol, interval, df, waves, zoom, show_bollinger, boll_period, boll_std, theme):
    key = _secret("FUGLE_API_KEY")
    if not key:
        st.warning("尚未設定行情金鑰")
        return
    try:
        quote = _fetch_quote(symbol.split(".")[0], key)
        last_trade = quote.get("lastTrade") or {}
        price = last_trade.get("price")
        stamp = last_trade.get("time")
        if price is None or not stamp:
            st.info("目前沒有最新實際成交，暫停更新 K 棒。")
            return
        preview, dt = _preview(df, price, stamp, interval)
        st.caption(f"試算 K 棒｜成交時間：{dt:%Y-%m-%d %H:%M:%S}（台灣）｜每 10 秒查詢")
        st.warning("試算中：僅依最新成交價更新收盤與可見高低，無完整逐筆成交量；亞當鏡像仍採原歷史資料，不重新計算。")
        mobile_chart(preview, waves, zoom, f"{symbol}｜即時 K 棒預覽（非正式 OHLC）",
                     show_bollinger, boll_period, boll_std, theme,
                     viewport_key=f"live-{symbol}-{interval}-{zoom}")
    except ValueError as exc:
        st.info(str(exc))
    except Exception:
        st.warning("即時 K 棒暫時無法更新，原始 K 線不受影響。")


def show_live_candle(market, symbol, interval, df, waves, zoom, show_bollinger, boll_period, boll_std, theme):
    if market != "台灣股票／ETF" or interval not in MINUTES:
        return
    with st.expander("即時 K 棒同步預覽（第二階段測試）", expanded=False):
        st.caption("獨立測試圖表，不修改原本 K 線、亞當轉折與鏡像結果。")
        if not _secret("LIVE_QUOTE_PASSWORD"):
            st.info("尚未設定個人報價密碼")
            return
        # The live quote panel authenticates separately; do not expose data without this gate.
        import hmac
        entered = st.text_input("個人報價密碼（同步預覽）", type="password", key="live_candle_password")
        if not entered or not hmac.compare_digest(entered, _secret("LIVE_QUOTE_PASSWORD")):
            if entered:
                st.error("密碼不正確")
            return
        if st.checkbox("開始每 10 秒更新試算 K 棒", value=False, key="live_candle_enabled"):
            live_candle_fragment(symbol, interval, df, waves, zoom,
                                 show_bollinger, boll_period, boll_std, theme)
