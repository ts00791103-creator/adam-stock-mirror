import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="亞當理論 B3 Pro",
    layout="wide"
)

st.title("亞當理論 B3 Pro｜股票＋期貨")
st.caption("完整波段鏡像｜互動K線｜短中長波切換")

MARKETS = {
    "台灣股票／ETF": None,
    "小那斯達克 MNQ（NQ參考）": "NQ=F",
    "微型黃金 MGC（GC參考）": "GC=F",
    "原油期貨 CL": "CL=F",
    "微型標普 MES（ES參考）": "ES=F",
    "比特幣 BTC（現貨）": "BTC-USD"
}

INTERVALS = {
    "5分K": "5m",
    "15分K": "15m",
    "60分K": "60m",
    "日K": "1d",
    "週K": "1wk",
    "月K": "1mo"
}

@st.cache_data(ttl=900)
def get_data(symbol, interval):
    if interval in ["5m", "15m"]:
        period = "30d"
    elif interval == "60m":
        period = "60d"
    else:
        period = "5y"

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df.dropna(subset=["Close"])

def find_pivots(values, span, threshold):
    x = np.asarray(values, dtype=float)
    points = []

    for i in range(span, len(x) - span):
        area = x[i-span:i+span+1]

        if x[i] >= np.max(area):
            kind = "高"
        elif x[i] <= np.min(area):
            kind = "低"
        else:
            continue

        if not points:
            points.append((i, kind))
            continue

        j, old_kind = points[-1]

        if kind == old_kind:
            if (
                (kind == "高" and x[i] > x[j])
                or (kind == "低" and x[i] < x[j])
            ):
                points[-1] = (i, kind)

        elif abs(x[i] / x[j] - 1) >= threshold:
            points.append((i, kind))

    return points

market = st.selectbox("選擇市場", list(MARKETS.keys()))

if market == "台灣股票／ETF":
    code = st.text_input("輸入股票代號", "2308")
    exchange = st.selectbox("交易市場", ["上市", "上櫃"])
    suffix = ".TW" if exchange == "上市" else ".TWO"
    symbol = code.strip() + suffix
else:
    symbol = MARKETS[market]

interval_name = st.selectbox(
    "選擇K線週期",
    list(INTERVALS.keys()),
    index=3
)

wave = st.radio(
    "選擇波段",
    ["短波", "中波", "長波"],
    horizontal=True
)

chart_type = st.radio(
    "圖表模式",
    ["K線", "線圖"],
    horizontal=True
)

threshold = st.slider(
    "最小反轉幅度（%）",
    1, 20, 5
)

settings = {
    "短波": (3, 100),
    "中波": (7, 260),
    "長波": (14, 650)
}

if st.button("開始亞當鏡像分析", type="primary"):

    if market == "台灣股票／ETF" and not code.strip().isdigit():
        st.error("請輸入正確的台股代號。")
        st.stop()

    try:
        df = get_data(symbol, INTERVALS[interval_name])

        if df.empty:
            st.error("查無資料，請更換商品或週期。")
            st.stop()

        span, lookback = settings[wave]
        recent = df.tail(lookback).copy()
        close = recent["Close"].astype(float).to_numpy()

        points = find_pivots(
            close,
            span,
            threshold / 100
        )

        if len(points) < 2:
            st.warning("轉折點不足，請降低反轉幅度。")
            st.stop()

        start = points[-2][0]
        end = points[-1][0]

        segment = close[start:end+1]
        mirrored = segment[::-1]

        last = float(close[-1])
        projection = last + mirrored - mirrored[0]

        n = len(segment) - 1
        interval = INTERVALS[interval_name]

        if interval == "1d":
            freq = "B"
        elif interval == "1wk":
            freq = "W"
        elif interval == "1mo":
            freq = "MS"
        elif interval == "60m":
            freq = "h"
        elif interval == "15m":
            freq = "15min"
        else:
            freq = "5min"

        future = pd.date_range(
            recent.index[-1],
            periods=n+1,
            freq=freq
        )

        fig = go.Figure()

        if chart_type == "K線":
            fig.add_trace(go.Candlestick(
                x=recent.index,
                open=recent["Open"],
                high=recent["High"],
                low=recent["Low"],
                close=recent["Close"],
                name="歷史K線"
            ))
        else:
            fig.add_trace(go.Scatter(
                x=recent.index,
                y=recent["Close"],
                mode="lines",
                name="歷史線圖"
            ))

        fig.add_trace(go.Scatter(
            x=recent.index[start:end+1],
            y=segment,
            mode="lines",
            name="完整歷史波段",
            line=dict(color="orange", width=3)
        ))

        fig.add_trace(go.Scatter(
            x=future,
            y=projection,
            mode="lines",
            name="亞當鏡像",
            line=dict(color="red", dash="dash", width=3)
        ))

        fig.update_layout(
            title=f"{market}｜{wave}鏡像分析",
            xaxis_rangeslider_visible=True,
            hovermode="x unified",
            dragmode="pan",
            height=650
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displayModeBar": True
            }
        )

        st.write(
            "資料日期：",
            str(recent.index[-1])
        )

        st.metric(
            "最新可取得收盤價",
            f"{last:,.2f}"
        )

        st.metric(
            "鏡像最高參考價",
            f"{np.max(projection):,.2f}"
        )

        st.metric(
            "鏡像最低參考價",
            f"{np.min(projection):,.2f}"
        )

        st.warning(
            "本系統為歷史波段鏡像研究工具，"
            "不代表未來價格預測。"
            "期貨連續合約與實際交易合約可能不同。"
            "推演日期未完整考慮各市場休市時間。"
        )

    except Exception as e:
        st.error(f"分析失敗：{e}")
