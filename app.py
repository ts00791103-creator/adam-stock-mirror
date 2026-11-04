
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="亞當理論鏡像分析",
    layout="wide"
)

st.title("亞當理論｜台股鏡像分析系統")
st.caption("歷史走勢左右翻轉，推演短、中、長波參考路徑")

code = st.text_input("輸入台股代號", "2308").strip()
market = st.selectbox("股票市場", ["上市", "上櫃"])
period = st.selectbox("歷史資料長度", ["5y", "10y", "2y", "1y"])

windows = {
    "短波": 20,
    "中波": 60,
    "長波": 120
}

@st.cache_data(ttl=1800)
def load_data(symbol, period):
    df = yf.download(
        symbol,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["Close"])

if st.button("開始分析", type="primary"):
    if not code.isdigit():
        st.error("請輸入正確的股票代號")
    else:
        suffix = ".TW" if market == "上市" else ".TWO"
        symbol = code + suffix

        try:
            df = load_data(symbol, period)

            if df.empty:
                st.error("查無資料，請檢查股票代號")
            else:
                close = df["Close"].astype(float)
                last = float(close.iloc[-1])

                st.metric(
                    "最新可取得收盤價（非即時）",
                    f"{last:,.2f} 元"
                )
                st.write(
                    "資料日期：",
                    str(df.index[-1].date())
                )

                results = []

                for name, n in windows.items():
                    if len(close) < n + 1:
                        continue

                    history = close.iloc[-(n + 1):].to_numpy()
                    mirrored = history[::-1]
                    projected = last + mirrored - mirrored[0]

                    future = pd.bdate_range(
                        df.index[-1] + pd.Timedelta(days=1),
                        periods=n
                    )

                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=df.index[-(n + 1):],
                        y=history,
                        mode="lines",
                        name="歷史走勢"
                    ))

                    fig.add_trace(go.Scatter(
                        x=[df.index[-1], *future],
                        y=projected,
                        mode="lines",
                        name="亞當鏡像",
                        line=dict(dash="dash")
                    ))

                    fig.update_layout(
                        title=f"{name}｜{n}個交易日",
                        xaxis_title="日期",
                        yaxis_title="股價（元）"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                    results.append({
                        "週期": name,
                        "目前價格": round(last, 2),
                        "鏡像第5日": round(float(projected[5]), 2),
                        "鏡像第10日": round(float(projected[10]), 2),
                        "鏡像終點": round(float(projected[-1]), 2)
                    })

                st.subheader("短中長波鏡像參考價位")
                st.dataframe(
                    pd.DataFrame(results),
                    hide_index=True,
                    use_container_width=True
                )

                st.warning(
                    "鏡像分析僅供研究參考，"
                    "不代表未來股價必然依此走勢發展。"
                )

        except Exception as e:
            st.error(f"資料取得失敗：{e}")
