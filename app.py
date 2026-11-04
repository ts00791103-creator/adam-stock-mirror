
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="亞當理論｜完整波段鏡像",
    layout="wide"
)

st.title("亞當理論｜完整波段鏡像分析 B 版")
st.caption("台股短、中、長波｜歷史完整波段左右翻轉")

@st.cache_data(ttl=1800)
def load_prices(symbol, period):
    df = yf.download(
        symbol,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return df["Close"].dropna().astype(float)

def find_turns(values, span, min_change):
    x = np.asarray(values, dtype=float)
    candidates = []

    for i in range(span, len(x) - span):
        area = x[i-span:i+span+1]
        if x[i] == max(area):
            candidates.append((i, "高"))
        elif x[i] == min(area):
            candidates.append((i, "低"))

    turns = []

    for i, kind in candidates:
        if not turns:
            turns.append((i, kind))
            continue

        j, previous = turns[-1]

        if kind == previous:
            better = (
                (kind == "高" and x[i] > x[j])
                or (kind == "低" and x[i] < x[j])
            )
            if better:
                turns[-1] = (i, kind)
        elif abs(x[i] / x[j] - 1) >= min_change:
            turns.append((i, kind))

    return turns

def analyze_wave(name, prices, span, lookback, threshold):
    recent = prices.tail(lookback)
    x = recent.to_numpy()
    turns = find_turns(x, span, threshold)

    st.subheader(name)

    if len(turns) < 2:
        st.info("目前沒有足夠的已確認完整波段。")
        return

    start = turns[-2][0]
    end = turns[-1][0]

    segment = x[start:end+1]
    n = len(segment) - 1

    if n < 2:
        st.info("波段太短，無法分析。")
        return

    last = float(prices.iloc[-1])

    # 將已完成波段依時間左右翻轉
    reversed_segment = segment[::-1]

    # 平移至目前股價，不改變歷史波段價差
    projection = last + reversed_segment - reversed_segment[0]

    future = pd.bdate_range(
        prices.index[-1] + pd.Timedelta(days=1),
        periods=n
    )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=recent.index,
        y=x,
        name="歷史股價",
        mode="lines",
        line=dict(color="#2563eb")
    ))

    fig.add_trace(go.Scatter(
        x=recent.index[start:end+1],
        y=segment,
        name="已完成波段",
        mode="lines",
        line=dict(color="#f59e0b", width=4)
    ))

    fig.add_trace(go.Scatter(
        x=[prices.index[-1], *future],
        y=projection,
        name="亞當鏡像參考",
        mode="lines",
        line=dict(color="#ef4444", dash="dash", width=3)
    ))

    for i, kind in turns:
        fig.add_trace(go.Scatter(
            x=[recent.index[i]],
            y=[x[i]],
            mode="markers",
            marker=dict(size=8),
            name=kind + "點",
            showlegend=False
        ))

    fig.update_layout(
        title=f"{name}｜完整波段 {n} 個交易日",
        xaxis_title="日期",
        yaxis_title="股價（元）",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    levels = np.array([x[i] for i, _ in turns])
    supports = levels[levels <= last]
    resistances = levels[levels >= last]

    support = float(max(supports)) if len(supports) else None
    resistance = float(min(resistances)) if len(resistances) else None

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "歷史支撐參考",
        f"{support:.2f}" if support is not None else "無"
    )
    c2.metric(
        "歷史壓力參考",
        f"{resistance:.2f}" if resistance is not None else "無"
    )
    c3.metric(
        "鏡像終點參考",
        f"{projection[-1]:.2f}"
    )

    rows = []
    for day in sorted(set([min(5, n), min(10, n), n])):
        rows.append({
            "鏡像交易日": day,
            "參考日期": str(future[day-1].date()),
            "參考價位": round(float(projection[day]), 2)
        })

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "歷史波段起點："
        + str(recent.index[start].date())
        + "｜終點："
        + str(recent.index[end].date())
    )

code = st.text_input("輸入台股代號", "2308").strip()
market = st.selectbox("股票市場", ["上市", "上櫃"])
period = st.selectbox(
    "歷史資料長度",
    ["5y", "10y", "2y", "1y"]
)

threshold = st.slider(
    "最小波段反轉幅度（%）",
    min_value=2,
    max_value=20,
    value=5
)

if st.button("開始完整波段分析", type="primary"):
    if not code.isdigit():
        st.error("請輸入正確的股票代號。")
    else:
        suffix = ".TW" if market == "上市" else ".TWO"
        symbol = code + suffix

        try:
            prices = load_prices(symbol, period)

            if prices.empty:
                st.error("查無資料，請檢查股票代號。")
            else:
                st.metric(
                    "最新可取得收盤價",
                    f"{prices.iloc[-1]:,.2f} 元"
                )
                st.write(
                    "資料日期：",
                    str(prices.index[-1].date())
                )

                settings = [
                    ("短波", 3, 100),
                    ("中波", 7, 260),
                    ("長波", 14, 650)
                ]

                for name, span, lookback in settings:
                    analyze_wave(
                        name,
                        prices,
                        span,
                        lookback,
                        threshold / 100
                    )

                st.warning(
                    "鏡像為歷史波段反轉後的參考情境，"
                    "並非未來價格預測。"
                    "支撐壓力來自歷史轉折點。"
                    "未來日期僅排除週末，"
                    "尚未排除台股休市日。"
                )

        except Exception as e:
            st.error(f"分析失敗：{e}")
