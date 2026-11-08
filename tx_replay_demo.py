"""Candidate-only demonstration of the provisional TX replay."""
from tx_provisional import replay


def show_demo(st):
    with st.expander("台指期｜60 分 K 暫行規則試跑"):
        st.caption("使用固定模擬資料驗算觸發與失效。規則為研究假設，作者原始取點與失效條件仍待核對。")
        direction = st.radio("模擬方向", ("空方", "多方"), horizontal=True)
        if st.button("執行台指期規則試跑"):
            sign = 1 if direction == "多方" else -1
            prices = [20000 + sign * n for n in (0, -10, -50, -20, 0, 20, 0, -10, 40, 40, 30)]
            bars = [dict(high=x + 10, low=x - 10, close=x) for x in prices]
            setup, = replay(bars)
            st.dataframe([{
                "方向": direction,
                "來源起始 K 棒": setup["source_start"] + 1,
                "觸發 K 棒": setup["trigger_at"] + 1,
                "失效價": setup["level"],
                "目標價": setup["target"],
                "失效 K 棒": setup["invalidated_at"] + 1,
            }], hide_index=True)
