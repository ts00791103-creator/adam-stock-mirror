"""Candidate view of observations computed from official fixed-contract historical data."""
from datetime import datetime

from tx_four_lines import read_replay_bars, replay


REACTIONS = {
    "wick_return": "外界影線收回",
    "touch": "觸及價帶",
    "close_outside": "收盤越過外界",
    "outer_missing": "缺外側轉折",
    "missing_bar": "缺棒",
    "no_confirmed_box": "未確認箱型",
    "no_touch": "未觸帶",
}


def show_four_lines(st):
    st.subheader("台指 TX 202611 四線價帶觀察")
    st.caption("期交所逐筆成交｜台灣時間｜固定 11 月合約｜到期日 2026/11/18 13:30")
    bars = read_replay_bars()
    rows = replay(bars)
    observations = []
    for row in rows:
        for side, sign, direction in (("upper", 1, "上側"), ("lower", -1, "下側")):
            reaction = row[f"{side}_event"]
            inner = row.get(f"{side}_inner")
            extreme = row["high"] if sign == 1 else row["low"]
            inner_recovered = inner is not None and sign * (extreme - inner) > 0 and sign * (row["close"] - inner) <= 0
            if reaction in ("no_touch", "no_confirmed_box") and not inner_recovered:
                continue
            observations.append({
                "收棒時間": datetime.fromisoformat(row["time"]).strftime("%Y-%m-%d %H:%M"),
                "棒長（分）": row["minutes"],
                "側別": direction,
                "內界": inner,
                "外界": row.get(f"{side}_outer"),
                "極值": extreme,
                "收盤": row["close"],
                "反應": REACTIONS[reaction],
                "內界收回": inner_recovered,
                "單根確認": row.get(f"{side}_one", False),
                "兩根確認": row.get(f"{side}_two", False),
            })
    wick_count = sum(r["反應"] == "外界影線收回" for r in observations)
    st.write(f"已回放 {len(bars)} 根｜外界影線收回 {wick_count} 次")
    st.caption("以 20 根確認箱型，最大振幅 20%。外側轉折須左右各兩根已收棒。影線收回屬歷史觀察，收盤越界另外顯示單根與連續兩根確認。")
    mode = st.selectbox("觀察項目", ["外界影線收回", "收盤越界確認", "全部觀察"])
    if mode == "外界影線收回":
        observations = [r for r in observations if r["反應"] == mode]
    elif mode == "收盤越界確認":
        observations = [r for r in observations if r["單根確認"] or r["兩根確認"]]
    st.dataframe(observations, hide_index=True, width="stretch")
    st.markdown("[期交所官方逐筆成交資料](https://www.taifex.com.tw/cht/3/dlFutPrevious30DaysSalesData)")
