"""Candidate-only demonstration of the provisional TX replay."""
import plotly.graph_objects as go
from tx_provisional import replay, rotate_ohlc


def show_demo(st):
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
