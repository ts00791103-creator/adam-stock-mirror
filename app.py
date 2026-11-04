
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="亞當理論 B3 Pro",
    layout="wide"
)

st.title("亞當理論 B3 Pro｜股票・ETF・期貨")
st.caption("短中長波鏡像｜互動K線｜完整波段反轉")

MARKETS = {
    "台灣股票／ETF": None,
    "小那斯達克 MNQ（NQ參考）": "NQ=F",
    "微型黃金 MGC（GC參考）": "GC=F",
    "原油期貨 CL": "CL=F",
    "微型標普 MES（ES參考）": "ES=F",
    "比特幣 BTC": "BTC-USD",
    "台指期（自訂代碼）": "CUSTOM",
    "其他商品（自訂代碼）": "CUSTOM",
}

INTERVALS = {
    "5分K": "5m",
    "15分K": "15m",
    "60分K": "60m",
    "日K": "1d",
    "週K": "1wk",
    "月K": "1mo",
}

PERIODS = {
    "5m": ["5d", "1mo", "60d"],
    "15m": ["5d", "1mo", "60d"],
    "60m": ["5d", "1mo", "3mo", "6mo", "2y"],
    "1d": ["6mo", "1y", "2y", "5y", "10y"],
    "1wk": ["1y", "2y", "5y", "10y"],
    "1mo": ["2y", "5y", "10y", "max"],
}

COLORS = {
    "短波": "green",
    "中波": "orange",
    "長波": "red",
}

SETTINGS = {
    "短波": (3, 100),
    "中波": (7, 260),
    "長波": (14, 650),
}

@st.cache_data(ttl=900)
def get_data(symbol, period, interval):
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

    if df.empty:
        return df

    df = df.dropna(subset=["Close"]).copy()
    df.index = pd.to_datetime(df.index)

    return df

def find_pivots(values, span, min_change):
    x = np.asarray(values, dtype=float)
    candidates = []

    if len(x) < 2 * span + 3:
        return []

    for i in range(span, len(x) - span):
        area = x[i-span:i+span+1]

        if x[i] >= np.max(area):
            candidates.append((i, "高"))
        elif x[i] <= np.min(area):
            candidates.append((i, "低"))

    turns = []

    for i, kind in candidates:
        if not turns:
            turns.append((i, kind))
            continue

        j, previous = turns[-1]

        if kind == previous:
            if (
                (kind == "高" and x[i] >= x[j])
                or
                (kind == "低" and x[i] <= x[j])
            ):
                turns[-1] = (i, kind)

        elif (
            abs(x[i] - x[j])
            / max(abs(x[j]), 1e-9)
            >= min_change
        ):
            turns.append((i, kind))

    return turns

def future_dates(last_date, steps, interval):
    last_date = pd.Timestamp(last_date)

    if interval == "1d":
        return pd.bdate_range(
            last_date,
            periods=steps + 1
        )[1:]

    if interval == "1wk":
        return pd.date_range(
            last_date,
            periods=steps + 1,
            freq="7D"
        )[1:]

    if interval == "1mo":
        return pd.date_range(
            last_date,
            periods=steps + 1,
            freq="MS"
        )[1:]

    freq = {
        "5m": "5min",
        "15m": "15min",
        "60m": "h",
    }[interval]

    return pd.date_range(
        last_date,
        periods=steps + 1,
        freq=freq
    )[1:]

market = st.selectbox(
    "選擇市場",
    list(MARKETS.keys())
)

if MARKETS[market] is None:
    code = st.text_input(
        "輸入台股代號",
        "2308"
    ).strip()

    exchange = st.radio(
        "交易市場",
        ["上市", "上櫃"],
        horizontal=True
    )

    if code.isdigit():
        suffix = ".TW" if exchange == "上市" else ".TWO"
        symbol = code + suffix
    else:
        symbol = code

elif MARKETS[market] == "CUSTOM":
    symbol = st.text_input(
        "輸入 Yahoo Finance 商品代碼",
        ""
    ).strip()

else:
    symbol = MARKETS[market]

c1, c2 = st.columns(2)

with c1:
    interval_name = st.selectbox(
        "選擇K線週期",
        list(INTERVALS.keys()),
        index=3
    )

with c2:
    interval = INTERVALS[interval_name]

    period = st.selectbox(
        "歷史資料長度",
        PERIODS[interval],
        index=len(PERIODS[interval])-1
    )

display_mode = st.radio(
    "波段顯示方式",
    ["單一波段", "三波同時顯示"],
    horizontal=True
)

wave = st.radio(
    "選擇波段",
    ["短波", "中波", "長波"],
    horizontal=True,
    disabled=(display_mode == "三波同時顯示")
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

st.caption(
    "鏡像為歷史波段反向排列與價格平移，"
    "不是保證未來走勢。"
)

if st.button("開始亞當鏡像分析", type="primary"):

    if not symbol:
        st.error("請輸入商品代碼")
        st.stop()

    try:
        df = get_data(symbol, period, interval)
    except Exception as exc:
        st.error(f"資料下載失敗：{exc}")
        st.stop()

    if df.empty:
        st.error("查無資料，請檢查代碼或週期")
        st.stop()

    if display_mode == "三波同時顯示":
        selected_waves = ["短波", "中波", "長波"]
    else:
        selected_waves = [wave]

    fig = go.Figure()

    if chart_type == "K線":
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="歷史K線"
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Close"],
                mode="lines",
                name="歷史收盤線",
                line=dict(color="blue", width=2)
            )
        )

    results = []

    for current_wave in selected_waves:

        span, lookback = SETTINGS[current_wave]

        recent = df.tail(lookback).copy()
        close = recent["Close"].astype(float).to_numpy()

        points = find_pivots(
            close,
            span,
            threshold / 100
        )

        if len(points) < 2:
            st.warning(
                f"{current_wave}轉折點不足，"
                "請降低反轉幅度或增加資料長度"
            )
            continue

        start = points[-2][0]
        end = points[-1][0]

        segment = close[start:end+1]

        if len(segment) < 2:
            continue

        mirrored = segment[::-1]

        last = float(close[-1])

        projection = (
            last + mirrored - mirrored[0]
        )

        dates = future_dates(
            recent.index[-1],
            len(projection)-1,
            interval
        )

        future_x = [recent.index[-1]] + list(dates)

        color = COLORS[current_wave]

        fig.add_trace(
            go.Scatter(
                x=recent.index[start:end+1],
                y=segment,
                mode="lines",
                name=f"{current_wave}歷史參考波段",
                line=dict(
                    color=color,
                    width=3
                ),
                opacity=0.6
            )
        )

        fig.add_trace(
            go.Scatter(
                x=future_x,
                y=projection,
                mode="lines",
                name=f"{current_wave}亞當鏡像",
                line=dict(
                    color=color,
                    dash="dash",
                    width=3
                )
            )
        )

        results.append({
            "波段": current_wave,
            "最新收盤價": round(last, 2),
            "鏡像終點參考價": round(
                float(projection[-1]), 2
            ),
            "歷史波段K數": len(segment),
            "參考起日": str(
                recent.index[start].date()
            ),
            "參考迄日": str(
                recent.index[end].date()
            )
        })

    fig.update_layout(
        title=f"{symbol}｜亞當理論 B3 Pro",
        height=680,
        hovermode="x unified",
        dragmode="pan",
        xaxis_rangeslider_visible=True,
        legend=dict(
            orientation="h",
            y=1.05
        ),
        margin=dict(
            l=30,
            r=30,
            t=90,
            b=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False
        }
    )

    st.caption(
        "滑鼠拖曳可移動圖表；"
        "滾輪可放大縮小；"
        "下方滑桿可調整時間範圍。"
    )

    if results:
        st.subheader("短中長波參考數值")

        result_df = pd.DataFrame(results)

        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True
        )

        csv_data = result_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "下載分析結果 CSV",
            csv_data,
            file_name="adam_b3_pro.csv",
            mime="text/csv"
        )
    else:
        st.info("目前沒有可用的完整波段")

    st.warning(
        "本程式為歷史鏡像情境分析，"
        "不是買賣建議。"
        "期貨參考代碼不一定對應微型契約即時報價。"
    )
