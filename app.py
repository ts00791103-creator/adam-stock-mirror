import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="亞當理論 B3 Pro",
    layout="wide"
)

st.title("亞當理論 B3 Pro｜A 模式左右鏡像")
st.caption("完整鏡像｜短中長波｜內部轉折點｜互動圖表")

MARKETS = {
    "台灣股票／ETF": None,
    "那斯達克期貨 NQ（MNQ參考）": "NQ=F",
    "黃金期貨 GC（MGC參考）": "GC=F",
    "原油期貨 CL": "CL=F",
    "標普期貨 ES（MES參考）": "ES=F",
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

WAVES = {
    "短波": (3, 100),
    "中波": (7, 260),
    "長波": (14, 650),
}

COLORS = {
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

    if len(x) < 2 * span + 3:
        return []

    candidates = []

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


def future_index(last_date, count, interval):
    t = pd.Timestamp(last_date)

    if count <= 0:
        return pd.DatetimeIndex([])

    if interval == "1d":
        return pd.bdate_range(
            t + pd.offsets.BDay(1),
            periods=count
        )

    if interval == "1wk":
        return pd.date_range(
            t + pd.Timedelta(days=7),
            periods=count,
            freq="7D"
        )

    if interval == "1mo":
        return pd.date_range(
            t + pd.offsets.MonthBegin(1),
            periods=count,
            freq="MS"
        )

    step = {
        "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15),
        "60m": pd.Timedelta(hours=1),
    }[interval]

    return pd.DatetimeIndex([
        t + step * i
        for i in range(1, count + 1)
    ])


def internal_turns(values, span=2, max_points=3):
    """
    找出鏡像內部局部高低點。
    不把第一根與最後一根當作內部轉折。
    依未來時間排序，最多取前3個。
    """
    x = np.asarray(values, dtype=float)
    turns = []

    if len(x) < 2 * span + 1:
        return turns

    for i in range(span, len(x) - span):
        window = x[i-span:i+span+1]

        if x[i] > np.max(np.delete(window, span)):
            turns.append((i, "高點"))

        elif x[i] < np.min(np.delete(window, span)):
            turns.append((i, "低點"))

    return turns[:max_points]


def mirror_wave(df, name, threshold, interval):
    span, lookback = WAVES[name]

    recent = df.tail(lookback)
    close = recent["Close"].to_numpy(dtype=float)

    pivots = find_pivots(
        close,
        span,
        threshold / 100.0
    )

    if len(pivots) < 2:
        return None

    start = pivots[-2][0]
    end = pivots[-1][0]

    segment = close[start:end+1]

    if len(segment) < 2:
        return None

    # A模式：左右翻轉歷史完整波段
    reversed_segment = segment[::-1]

    latest = float(df["Close"].iloc[-1])

    # 鏡像起點銜接最新收盤價
    projection = (
        latest
        + reversed_segment
        - reversed_segment[0]
    )

    future = future_index(
        df.index[-1],
        len(projection)-1,
        interval
    )

    times = pd.DatetimeIndex(
        [df.index[-1]]
    ).append(future)

    high_i = int(np.argmax(projection))
    low_i = int(np.argmin(projection))

    turns = internal_turns(
        projection,
        span=2,
        max_points=3
    )

    return {
        "name": name,
        "color": COLORS[name],
        "recent": recent,
        "start": start,
        "end": end,
        "segment": segment,
        "times": times,
        "projection": projection,
        "high_i": high_i,
        "low_i": low_i,
        "turns": turns,
        "last": latest,
    }


def fmt_time(t, interval):
    if interval in ("5m", "15m", "60m"):
        return pd.Timestamp(t).strftime(
            "%Y-%m-%d %H:%M"
        )

    return pd.Timestamp(t).strftime("%Y-%m-%d")


def make_figure(df, waves, chart_type, zoom, title):
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
            name="歷史收盤線",
            line=dict(
                color="#64748b",
                width=2
            )
        ))

    for w in waves:
        name = w["name"]
        color = w["color"]
        recent = w["recent"]
        start = w["start"]
        end = w["end"]

        fig.add_trace(go.Scatter(
            x=recent.index[start:end+1],
            y=w["segment"],
            mode="lines",
            name=f"{name}歷史波段",
            line=dict(
                color=color,
                width=3
            ),
            opacity=0.65
        ))

        fig.add_trace(go.Scatter(
            x=w["times"],
            y=w["projection"],
            mode="lines",
            name=f"{name}完整左右鏡像",
            line=dict(
                color=color,
                width=3,
                dash="dash"
            )
        ))

        for i, kind in w["turns"]:
            price = float(w["projection"][i])

            fig.add_trace(go.Scatter(
                x=[w["times"][i]],
                y=[price],
                mode="markers+text",
                text=[
                    f"{name}{kind} {price:,.2f}"
                ],
                textposition=(
                    "top center"
                    if kind == "高點"
                    else "bottom center"
                ),
                marker=dict(
                    color=color,
                    size=9
                ),
                showlegend=False
            ))

    fig.update_layout(
        title=title,
        height=680,
        hovermode="x unified",
        dragmode="pan",
        xaxis_rangeslider_visible=True,
        xaxis_title="日期／時間",
        yaxis_title="價格",
        legend=dict(
            orientation="h",
            y=1.16
        ),
        margin=dict(
            l=35,
            r=35,
            t=120,
            b=45
        )
    )

    # 修正縮放：只限制初始視窗，
    # 不截斷完整鏡像資料
    if zoom != "全部歷史":
        n = int(
            zoom.replace("最近", "").replace("根", "")
        )

        left = df.index[max(0, len(df)-n)]

        # 右側只顯示未來前n根
        right_candidates = [df.index[-1]]

        for w in waves:
            idx = min(
                n,
                len(w["times"])-1
            )
            right_candidates.append(
                w["times"][idx]
            )

        right = max(right_candidates)

        fig.update_xaxes(
            range=[left, right]
        )

        values = []

        visible = df.loc[df.index >= left]

        if not visible.empty:
            values.extend([
                float(visible["Low"].min()),
                float(visible["High"].max())
            ])

        for w in waves:
            for t, price in zip(
                w["times"],
                w["projection"]
            ):
                if left <= t <= right:
                    values.append(float(price))

        if values:
            lo = min(values)
            hi = max(values)

            pad = max(
                (hi-lo)*0.07,
                abs(hi)*0.005,
                0.01
            )

            fig.update_yaxes(
                range=[lo-pad, hi+pad]
            )

    return fig


# ===== 使用者操作介面 =====

market = st.selectbox(
    "選擇市場",
    list(MARKETS)
)

if MARKETS[market] is None:
    code = st.text_input(
        "台股代號",
        "2308"
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
        "Yahoo Finance商品代碼",
        ""
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
    options = PERIODS[interval]

    period = st.selectbox(
        "歷史資料長度",
        options,
        index=len(options)-1
    )

mode = st.radio(
    "顯示模式",
    [
        "三波同圖",
        "單一波段",
        "三波各自獨立放大"
    ],
    horizontal=True
)

selected = st.radio(
    "單一波段選擇",
    list(WAVES),
    horizontal=True,
    disabled=(mode != "單一波段")
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

zoom_choices = [
    "最近30根",
    "最近60根",
    "最近120根",
    "最近250根",
    "全部歷史"
]

zoom = st.selectbox(
    "三波同圖／單波放大範圍",
    zoom_choices,
    index=2
)

individual_zoom = {
    "短波": "最近30根",
    "中波": "最近60根",
    "長波": "最近250根"
}

if mode == "三波各自獨立放大":
    z1, z2, z3 = st.columns(3)

    with z1:
        individual_zoom["短波"] = st.selectbox(
            "短波放大",
            zoom_choices,
            index=0
        )

    with z2:
        individual_zoom["中波"] = st.selectbox(
            "中波放大",
            zoom_choices,
            index=1
        )

    with z3:
        individual_zoom["長波"] = st.selectbox(
            "長波放大",
            zoom_choices,
            index=3
        )

st.info(
    "未來鏡像保留全部K棒。"
    "圖表放大只改變初始顯示範圍。"
)

# ===== 開始分析 =====

if st.button(
    "開始亞當鏡像分析",
    type="primary"
):

    if not symbol:
        st.error("請輸入商品代碼")
        st.stop()

    try:
        df = get_data(
            symbol,
            period,
            interval
        )
    except Exception as exc:
        st.error(f"資料下載失敗：{exc}")
        st.stop()

    if df.empty:
        st.error("查無資料")
        st.stop()

    if mode == "單一波段":
        names = [selected]
    else:
        names = list(WAVES)

    waves = []

    for name in names:
        result = mirror_wave(
            df,
            name,
            threshold,
            interval
        )

        if result is None:
            st.warning(
                f"{name}轉折點不足，"
                "請調整資料長度或反轉幅度。"
            )
        else:
            waves.append(result)

    if not waves:
        st.stop()

    latest = float(df["Close"].iloc[-1])

    st.caption(
        f"商品：{symbol}｜"
        f"資料日期：{fmt_time(df.index[-1], interval)}｜"
        f"最新收盤：{latest:,.2f}"
    )

    config = {
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False
    }

    if mode == "三波各自獨立放大":
        for w in waves:
            st.subheader(
                f"{w['name']}｜獨立放大"
            )

            fig = make_figure(
                df,
                [w],
                chart_type,
                individual_zoom[w["name"]],
                f"{symbol}｜{w['name']}左右鏡像"
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config=config,
                key=f"chart_{w['name']}"
            )
    else:
        fig = make_figure(
            df,
            waves,
            chart_type,
            zoom,
            f"{symbol}｜{mode}｜左右鏡像"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config=config,
            key="chart_combined"
        )

    # ===== 最高最低價表 =====

    summary_rows = []
    turn_rows = []

    for w in waves:
        p = w["projection"]
        t = w["times"]

        hi = w["high_i"]
        lo = w["low_i"]

        summary_rows.append({
            "波段": w["name"],
            "最新收盤": round(w["last"], 2),
            "鏡像最高價": round(float(p[hi]), 2),
            "高點日期": fmt_time(t[hi], interval),
            "鏡像最低價": round(float(p[lo]), 2),
            "低點日期": fmt_time(t[lo], interval),
            "鏡像終點價": round(float(p[-1]), 2),
            "終點日期": fmt_time(t[-1], interval),
            "鏡像K棒數": len(p)
        })

        for order, (i, kind) in enumerate(
            w["turns"],
            start=1
        ):
            turn_rows.append({
                "波段": w["name"],
                "順序": order,
                "轉折類型": kind,
                "參考日期": fmt_time(t[i], interval),
                "參考價位": round(float(p[i]), 2)
            })

    st.subheader("短中長波｜最高最低價表")

    summary = pd.DataFrame(summary_rows)

    st.dataframe(
        summary,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "下載最高最低價CSV",
        summary.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="adam_summary.csv",
        mime="text/csv"
    )

    st.subheader("短中長波｜前3個內部轉折點")

    if turn_rows:
        turns_df = pd.DataFrame(turn_rows)

        st.dataframe(
            turns_df,
            hide_index=True,
            use_container_width=True
        )

        st.download_button(
            "下載內部轉折點CSV",
            turns_df.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="adam_turns.csv",
            mime="text/csv"
        )
    else:
        st.info(
            "目前鏡像波段內沒有符合條件的內部轉折點。"
        )

    st.warning(
        "本程式為歷史波段左右鏡像情境分析，"
        "不是價格保證或投資建議。"
        "未來日期為估算，未完整排除交易所休市日。"
    )
