"""Candidate-only demonstration of the provisional TX replay."""
import csv
from pathlib import Path

import plotly.graph_objects as go
from tx_provisional import replay, rotate_ohlc


def show_demo(st):
    with st.expander("台指期｜延遲行情查看"):
        st.caption("TradingView 的期交所免費方案標示延遲 15 分鐘。資料時間、合約與交易時段請以來源畫面為準。")
        st.markdown("[開啟 TradingView 台指期連續合約](https://tw.tradingview.com/symbols/TAIFEX-TXF1%21/)")
        st.markdown("[在 TradingView 開啟台指期圖表](https://www.tradingview.com/chart/?symbol=TAIFEX%3ATXF1%21)")
        st.caption("圖表連結帶入台指期連續合約。週期、交易時段及 Pine 指標請在 TradingView 設定。")
        st.info("本站行情串接尚未啟用。下方真實 60 分 K 為固定歷史樣本。")

    with st.expander("台指期｜60 分 K 暫行規則試跑"):
        st.caption("使用固定模擬資料驗算觸發與失效。規則為研究假設，作者原始取點與失效條件仍待核對。")
        direction = st.radio("模擬方向", ("空方", "多方"), horizontal=True)
        if st.button("執行台指期規則試跑"):
            sign = 1 if direction == "多方" else -1
            prices = [20000 + sign * n for n in (0, -10, -50, -20, 0, 20, 0, -10, 40, 40, 30)]
            bars = [dict(open=x, high=x + 10, low=x - 10, close=x) for x in prices]
            setup, = replay(bars)
            st.dataframe([{
                "方向": direction,
                "來源起始 K 棒": setup["source_start"] + 1,
                "觸發 K 棒": setup["trigger_at"] + 1,
                "失效價": setup["level"],
                "目標價": setup["target"],
                "失效 K 棒": setup["invalidated_at"] + 1,
            }], hide_index=True)
            source = bars[setup["source_start"]:setup["trigger_at"] + 1]
            rotated = rotate_ohlc(source, source[-1]["close"])
            fig = go.Figure()
            for name, segment, start in (
                ("模擬來源", source, 0), ("180° 旋轉情境", rotated, len(source) - 1)
            ):
                fig.add_trace(go.Candlestick(
                    name=name, x=list(range(start, start + len(segment))),
                    **{field: [bar[field] for bar in segment]
                       for field in ("open", "high", "low", "close")}
                ))
            fig.update_layout(xaxis_rangeslider_visible=False, yaxis_title="模擬點數")
            st.plotly_chart(fig)

        st.markdown("[期交所逐筆成交來源](https://www.taifex.com.tw/cht/3/futPrevious30DaysSalesData)")
        st.caption("真實樣本為 TX 202611 單一契約，2026/10/29 至 11/06 日盤 35 根已收盤 60 分 K，台北時間。")
        if st.button("回放真實台指期 60 分 K"):
            with Path(__file__).with_name("tx_202611_sample.csv").open(encoding="utf-8") as file:
                bars = [
                    {"time": row["time"], **{key: int(row[key]) for key in ("open", "high", "low", "close")}}
                    for row in csv.DictReader(file)
                ]
            rows = []
            for setup in replay(bars):
                trigger = bars[setup["trigger_at"]]
                invalidated_at = setup["invalidated_at"]
                rows.append({
                    "方向": "多方" if setup["sign"] == 1 else "空方",
                    "觸發時間": trigger["time"],
                    "觸發收盤": trigger["close"],
                    "失效價": setup["level"],
                    "目標價": setup["target"],
                    "收盤失效時間": bars[invalidated_at]["time"] if invalidated_at is not None else "樣本內未失效",
                })
            st.caption(f"回放 {len(bars)} 根 K 棒，觸發 {len(rows)} 筆。")
            if rows:
                st.table(rows)
            else:
                st.info("這段樣本沒有觸發訊號。")
