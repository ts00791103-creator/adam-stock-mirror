
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="亞當理論 B3 Pro｜左右鏡像",
    layout="wide"
)

st.title("亞當理論 B3 Pro｜左右鏡像分析")
st.caption("歷史波段左右翻轉｜短中長波｜轉折價位")

MARKETS = {
    "台灣股票／ETF": None,
    "那斯達克期貨 NQ": "NQ=F",
    "黃金期貨 GC": "GC=F",
    "原油期貨 CL": "CL=F",
    "標普期貨 ES": "ES=F",
    "比特幣 BTC": "BTC-USD",
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

WAVE_SETTINGS = {
    "短波": (3, 100),
    "中波": (7, 260),
    "長波": (14, 650),
}

WAVE_COLORS = {
    "短波": "#16a34a",
    "中波": "#ea580c",
    "長波": "#dc2626",
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

    df = df.dropna(subset=["Close"]).sort_index().copy()
    df.index = pd.to_datetime(df.index)

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    return df[~df.index.duplicated(keep="last")]

def find_pivots(values, span, min_change):
    x = np.asarray(values, dtype=float)
    candidates = []

    if len(x) < 2 * span + 3:
        return []

    for i in range(span, len(x) - span):
        window = x[i-span:i+span+1]

        if x[i] >= np.max(window):
            candidates.append((i, "高"))
        elif x[i] <= np.min(window):
            candidates.append((i, "低"))

    pivots = []

    for i, kind in candidates:
        if not pivots:
            pivots.append((i, kind))
            continue

        j, previous = pivots[-1]

        if kind == previous:
            if (
                (kind == "高" and x[i] >= x[j])
                or (kind == "低" and x[i] <= x[j])
            ):
                pivots[-1] = (i, kind)

        elif (
            abs(x[i] - x[j])
            / max(abs(x[j]), 1e-9)
            >= min_change
        ):
            pivots.append((i, kind))

    return pivots

def extend_dates(last_date, steps, interval):
    last_date = pd.Timestamp(last_date)

    if steps <= 0:
        return pd.DatetimeIndex([])

    if interval == "1d":
        return pd.bdate_range(
            last_date + pd.offsets.BDay(1),
            periods=steps
        )

    if interval == "1wk":
        return pd.date_range(
            last_date + pd.Timedelta(days=7),
            periods=steps,
            freq="7D"
        )

    if interval == "1mo":
        return pd.date_range(
            last_date + pd.offsets.MonthBegin(1),
            periods=steps,
            freq="MS"
        )

    delta = {
        "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15),
        "60m": pd.Timedelta(hours=1),
    }[interval]

    return pd.DatetimeIndex([
        last_date + delta * i
        for i in range(1, steps + 1)
    ])

market = st.selectbox(
    "選擇市場",
    list(MARKETS)
)

if MARKETS[market] is None:
    code = st.text_input(
        "台股代號", value="2308"
    ).strip().upper()

    exchange = st.radio(
        "交易市場",
        ["上市", "上櫃"],
        horizontal=True
    )

    if code.isdigit():
        symbol = code + (
            ".TW" if exchange == "上市" else ".TWO"
        )
    else:
        symbol = code

elif MARKETS[market] == "CUSTOM":
    symbol = st.text_input(
        "Yahoo Finance 商品代碼",
        value=""
    ).strip().upper()
else:
    symbol = MARKETS[market]

c1, c2 = st.columns(2)

with c1:
    interval_name = st.selectbox(
        "K線週期",
        list(INTERVALS),
        index=3
    )

with c2:
    interval = INTERVALS[interval_name]
    periods = PERIODS[interval]

    period = st.selectbox(
        "歷史資料長度",
        periods,
        index=len(periods)-1
    )

mode = st.radio(
    "波段顯示方式",
    ["三波同時顯示", "單一波段"],
    horizontal=True
)

wave = st.radio(
    "選擇波段",
    list(WAVE_SETTINGS),
    horizontal=True,
    disabled=(mode == "三波同時顯示")
)

chart_type = st.radio(
    "圖表模式",
    ["K線", "線圖"],
    horizontal=True
)

threshold = st.slider(
    "最小反轉幅度（%）",
    1, 20, 3
)

zoom = st.selectbox(
    "預設圖表放大範圍",
    [
        "最近30根",
        "最近60根",
        "最近120根",
        "最近250根",
        "全部歷史"
    ],
    index=2
)

st.caption(
    "A模式：最後兩個已確認轉折點之間的"
    "歷史完整波段，左右翻轉後銜接最新收盤價。"
)

if st.button("開始亞當鏡像分析", type="primary"):

    if not symbol:
        st.error("請輸入商品代碼")
        st.stop()

    try:
        df = get_data(symbol, period, interval)
    except Exception as exc:
        st.error(f"資料取得失敗：{exc}")
        st.stop()

    if df.empty:
        st.error("沒有取得資料，請檢查商品代碼")
        st.stop()

    selected_waves = (
        list(WAVE_SETTINGS)
        if mode == "三波同時顯示"
        else [wave]
    )

    fig = go.Figure()

    if chart_type == "K線":
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="歷史K線"
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="歷史收盤價",
            line=dict(color="#64748b", width=2)
        ))

    results = []
    projected_dates = []

    last_date = df.index[-1]
    latest = float(df["Close"].iloc[-1])

    for current_wave in selected_waves:

        span, lookback = WAVE_SETTINGS[current_wave]

        recent = df.tail(lookback)
        close = recent["Close"].to_numpy(dtype=float)

        points = find_pivots(
            close,
            span,
            threshold / 100
        )

        if len(points) < 2:
            st.warning(
                f"{current_wave}轉折點不足，"
                "請增加資料或降低反轉幅度"
            )
            continue

        start = points[-2][0]
        end = points[-1][0]

        segment = close[start:end+1]

        if len(segment) < 2:
            continue

        # A模式：歷史價格順序左右反轉
        reversed_segment = segment[::-1]

        # 將鏡像起點平移至最新收盤價
        projection = (
            latest
            + reversed_segment
            - reversed_segment[0]
        )

        future_dates = extend_dates(
            last_date,
            len(projection)-1,
            interval
        )

        future_x = pd.DatetimeIndex(
            [last_date]
        ).append(future_dates)

        projected_dates.extend(list(future_dates))

        color = WAVE_COLORS[current_wave]

        fig.add_trace(go.Scatter(
            x=recent.index[start:end+1],
            y=segment,
            mode="lines",
            name=f"{current_wave}歷史完整波段",
            line=dict(color=color, width=2),
            opacity=0.65
        ))

        fig.add_trace(go.Scatter(
            x=future_x,
            y=projection,
            mode="lines",
            name=f"{current_wave}左右鏡像",
            line=dict(
                color=color,
                width=3,
                dash="dash"
            )
        ))

        high_i = int(np.argmax(projection))
        low_i = int(np.argmin(projection))

        for idx, label in [
            (high_i, "高"),
            (low_i, "低")
        ]:
            fig.add_trace(go.Scatter(
                x=[future_x[idx]],
                y=[projection[idx]],
                mode="markers+text",
                text=[
                    f"{current_wave}{label} "
                    f"{projection[idx]:,.2f}"
                ],
                textposition=(
                    "top center"
                    if label == "高"
                    else "bottom center"
                ),
                marker=dict(
                    color=color,
                    size=9
                ),
                showlegend=False
            ))

        results.append({
            "波段": current_wave,
            "最新收盤": round(latest, 2),
            "鏡像最高價": round(
                float(projection[high_i]), 2
            ),
            "最高價參考日": str(future_x[high_i]),
            "鏡像最低價": round(
                float(projection[low_i]), 2
            ),
            "最低價參考日": str(future_x[low_i]),
            "鏡像終點價": round(
                float(projection[-1]), 2
            ),
            "終點參考日": str(future_x[-1]),
            "歷史波段起點": str(recent.index[start]),
            "歷史波段終點": str(recent.index[end]),
            "歷史波段根數": len(segment)
        })

    fig.update_layout(
        title=f"{symbol}｜A模式左右鏡像｜{interval_name}",
        height=760,
        hovermode="x unified",
        dragmode="pan",
        xaxis_rangeslider_visible=True,
        legend=dict(
            orientation="h",
            y=1.13
        ),
        margin=dict(
            l=35, r=35, t=110, b=40
        ),
        xaxis_title="日期／時間",
        yaxis_title="價格",
        yaxis=dict(
            autorange=True,
            fixedrange=False
        )
    )

    if zoom != "全部歷史":

        n = int(
            zoom.replace("最近", "").replace("根", "")
        )

        left = df.index[max(0, len(df)-n)]

        right = (
            max(projected_dates)
            if projected_dates
            else last_date
        )

        if left < right:
            fig.update_xaxes(range=[left, right])

        visible = df.loc[df.index >= left]

        if not visible.empty:

            values = [
                float(visible["Low"].min()),
                float(visible["High"].max())
            ]

            for trace in fig.data:
                if (
                    isinstance(trace, go.Scatter)
                    and trace.y is not None
                ):
                    for x_val, y_val in zip(
                        trace.x, trace.y
                    ):
                        if (
                            pd.Timestamp(x_val) >= left
                            and pd.notna(y_val)
                        ):
                            values.append(float(y_val))

            if values:
                low = min(values)
                high = max(values)

                pad = max(
                    (high-low)*0.08,
                    abs(high)*0.005,
                    0.01
                )

                fig.update_yaxes(
                    range=[low-pad, high+pad]
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
        "滑鼠滾輪可放大縮小；"
        "拖曳可平移；"
        "下方滑桿可調整時間範圍。"
    )

    if results:

        st.subheader("短、中、長波鏡像轉折價位")

        table = pd.DataFrame(results)

        st.dataframe(
            table,
            hide_index=True,
            use_container_width=True
        )

        csv_data = table.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "下載轉折價位 CSV",
            csv_data,
            file_name="adam_b3_pro_A.csv",
            mime="text/csv"
        )

    else:
        st.info(
            "目前無法計算完整波段，"
            "請調整反轉幅度或歷史資料。"
        )

    st.warning(
        "鏡像為歷史走勢情境分析，"
        "不是保證未來會到達的價位。"
        "未來日期為估算，未完整排除交易所休市日。"
    )
