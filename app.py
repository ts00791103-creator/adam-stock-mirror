
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="亞當理論 B3 Pro", layout="wide")
st.title("亞當理論 B3 Pro｜A 模式左右鏡像")
st.caption("完整鏡像 K 棒｜三波同圖／各波獨立放大｜轉折價位表")

MARKETS = {
    "台灣股票／ETF": None,
    "那斯達克期貨 NQ（MNQ 參考）": "NQ=F",
    "黃金期貨 GC（MGC 參考）": "GC=F",
    "原油期貨 CL": "CL=F",
    "標普期貨 ES（MES 參考）": "ES=F",
    "比特幣 BTC": "BTC-USD",
    "其他商品／台指期（自訂 Yahoo 代碼）": "CUSTOM",
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

        j, prev_kind = pivots[-1]

        if kind == prev_kind:
            if (
                (kind == "高" and x[i] >= x[j])
                or
                (kind == "低" and x[i] <= x[j])
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

    segment = close[start:end + 1]

    if len(segment) < 2:
        return None

    # A模式：歷史價格順序左右翻轉
    reversed_segment = segment[::-1]

    # 銜接最新收盤價
    latest = float(df["Close"].iloc[-1])

    projection = (
        latest
        + reversed_segment
        - reversed_segment[0]
    )

    future = future_index(
        df.index[-1],
        len(projection) - 1,
        interval
    )

    times = pd.DatetimeIndex(
        [df.index[-1]]
    ).append(future)

    high_i = int(np.argmax(projection))
    low_i = int(np.argmin(projection))

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
        "last": latest,
    }

def fmt_time(t, interval):
    if interval in ("5m", "15m", "60m"):
        return pd.Timestamp(t).strftime("%Y-%m-%d %H:%M")

    return pd.Timestamp(t).strftime("%Y-%m-%d")

def make_figure(df, waves, chart_type, zoom, interval, title):
    fig = go.Figure()

    if chart_type == "K線":
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="歷史 K 線"
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="歷史收盤線",
            line=dict(color="#64748b", width=2)
        ))

    for w in waves:
        color = w["color"]
        name = w["name"]

        r = w["recent"]
        s = w["start"]
        e = w["end"]

        fig.add_trace(go.Scatter(
            x=r.index[s:e + 1],
            y=w["segment"],
            mode="lines",
            name=f"{name}歷史波段",
            line=dict(color=color, width=3),
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

        for i, label, position in (
            (w["high_i"], "高", "top center"),
            (w["low_i"], "低", "bottom center")
        ):
            fig.add_trace(go.Scatter(
                x=[w["times"][i]],
                y=[float(w["projection"][i])],
                mode="markers+text",
                text=[
                    f"{name}{label} "
                    f"{w['projection'][i]:,.2f}"
                ],
                textposition=position,
                marker=dict(
                    color=color,
                    size=8
                ),
                showlegend=False,
                hovertemplate="%{text}<extra></extra>"
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
        ),
        yaxis=dict(
            autorange=True,
            fixedrange=False
        )
    )

    # 放大只影響初始顯示，不截斷鏡像資料
    if zoom != "全部歷史":
        n = int(
            zoom.replace("最近", "").replace("根", "")
        )

        left = df.index[max(0, len(df) - n)]

        right = max(
            [df.index[-1]]
            + [w["times"][-1] for w in waves]
        )

        fig.update_xaxes(range=[left, right])

        visible = df.loc[df.index >= left]
        values = []

        if not visible.empty:
            values.extend([
                float(visible["Low"].min()),
                float(visible["High"].max())
            ])

        for w in waves:
            for t, price in zip(
                w["times"], w["projection"]
            ):
                if (
                    t >= left
                    and t <= right
                    and np.isfinite(price)
                ):
                    values.append(float(price))

            r = w["recent"]
            s = w["start"]
            e = w["end"]

            for t, price in zip(
                r.index[s:e + 1],
                w["segment"]
            ):
                if (
                    t >= left
                    and t <= right
                    and np.isfinite(price)
                ):
                    values.append(float(price))

        if values:
            lo = min(values)
            hi = max(values)

            pad = max(
                (hi - lo) * 0.07,
                abs(hi) * 0.005,
                0.01
            )

            fig.update_yaxes(
                range=[lo - pad, hi + pad]
            )

    return fig

# ===== 操作介面 =====

market = st.selectbox(
    "選擇市場",
    list(MARKETS)
)

if MARKETS[market] is None:
    code = st.text_input(
        "台股代號", "2308"
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
        "Yahoo Finance 商品代碼", ""
    ).strip().upper()
else:
    symbol = MARKETS[market]

c1, c2 = st.columns(2)

with c1:
    interval_name = st.selectbox(
        "K 線週期",
        list(INTERVALS),
        index=3
    )

with c2:
    interval = INTERVALS[interval_name]
    options = PERIODS[interval]

    period = st.selectbox(
        "歷史資料長度",
        options,
        index=len(options) - 1
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
    "三波同圖／單波預設放大範圍",
    zoom_choices,
    index=2
)

if mode == "三波各自獨立放大":
    st.markdown(
        "**每一波可選不同的初始放大範圍**"
    )

    z1, z2, z3 = st.columns(3)

    with z1:
        short_zoom = st.selectbox(
            "短波放大",
            zoom_choices,
            index=0
        )

    with z2:
        mid_zoom = st.selectbox(
            "中波放大",
            zoom_choices,
            index=1
        )

    with z3:
        long_zoom = st.selectbox(
            "長波放大",
            zoom_choices,
            index=3
        )

    individual_zoom = {
        "短波": short_zoom,
        "中波": mid_zoom,
        "長波": long_zoom
    }

st.info(
    "未來鏡像長度：全部 K 棒（不截斷）。"
    "圖表縮放只影響觀看範圍。"
)

st.caption(
    "A 模式：最後兩個已確認轉折點之間的"
    "歷史波段，左右翻轉並平移銜接最新收盤價。"
)

# ===== 執行分析 =====

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
        st.error(f"下載資料失敗：{exc}")
        st.stop()

    if df.empty:
        st.error(
            "查無資料，請檢查代碼、"
            "歷史長度及週期。"
        )
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
                f"{name}找不到足夠的完整轉折波段，"
                "可增加歷史資料或降低反轉幅度。"
            )
        else:
            waves.append(result)

    if not waves:
        st.stop()

    latest = float(df["Close"].iloc[-1])

    st.caption(
        f"商品：{symbol}｜"
        f"最新資料日期：{fmt_time(df.index[-1], interval)}｜"
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
                interval,
                f"{symbol}｜{w['name']}完整左右鏡像"
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
            interval,
            f"{symbol}｜{mode}｜完整左右鏡像"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config=config,
            key="chart_combined"
        )

    st.caption(
        "滑鼠滾輪放大縮小；拖曳平移；"
        "下方時間滑桿調整範圍。"
        "各波完整鏡像資料均保留。"
    )

    # ===== 轉折價位表 =====

    rows = []

    for w in waves:
        p = w["projection"]
        t = w["times"]

        hi = w["high_i"]
        lo = w["low_i"]
        r = w["recent"]

        rows.append({
            "波段": w["name"],
            "最新收盤": round(w["last"], 2),
            "鏡像最高價": round(float(p[hi]), 2),
            "高點參考日期": fmt_time(t[hi], interval),
            "鏡像最低價": round(float(p[lo]), 2),
            "低點參考日期": fmt_time(t[lo], interval),
            "鏡像終點價": round(float(p[-1]), 2),
            "終點參考日期": fmt_time(t[-1], interval),
            "鏡像K棒數": len(p),
            "歷史波段起日": fmt_time(
                r.index[w["start"]], interval
            ),
            "歷史波段迄日": fmt_time(
                r.index[w["end"]], interval
            )
        })

    st.subheader(
        "短、中、長波轉折價位表"
    )

    table = pd.DataFrame(rows)

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "下載轉折價位 CSV",
        table.to_csv(index=False).encode("utf-8-sig"),
        file_name="adam_b3_pro_turning_points.csv",
        mime="text/csv"
    )

    st.warning(
        "鏡像為歷史波段的情境推演，"
        "非價格保證或投資建議。"
        "未來日期為估算；分 K 與期貨未完整排除休市時段。"
        "Yahoo 期貨連續合約可能不等於微型契約報價。"
    )
