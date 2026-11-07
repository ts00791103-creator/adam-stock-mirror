"""Interval-aware reference windows; no changes to pivot or mirror algorithms."""
import streamlit as st

SPANS = {"短波": 3, "中波": 7, "長波": 14}


def wave_windows(interval, values=None):
    defaults = (26, 78, 156) if interval == "1wk" else (100, 260, 650)
    windows = tuple(defaults if values is None else values)
    if len(windows) != 3 or any(type(n) is not int or n > 5000 for n in windows):
        raise ValueError("請為三個波段輸入不超過5000的整數根數")
    if any(n < 2 * span + 1 for n, span in zip(windows, SPANS.values())):
        raise ValueError("觀察根數不足以辨識反轉點：短波至少7、中波至少15、長波至少29根")
    if not windows[0] < windows[1] < windows[2]:
        raise ValueError("觀察根數需依序增加：短波 < 中波 < 長波")
    return {name: (span, size) for (name, span), size in zip(SPANS.items(), windows)}


def show_wave_settings(interval):
    result = wave_windows(interval)
    if interval not in ("1d", "1wk"):
        return result
    unit = "週" if interval == "1wk" else "日"
    with st.expander("波段觀察根數（進階）", expanded=False):
        st.caption(f"目前為{unit}K，短／中／長波參考：" + "／".join(str(v[1]) for v in result.values()) + "根。")
        st.caption("這是歷史搜尋範圍的參考值，並非回測最佳值或完整波段保證；調整後，歷史來源與鏡像可能改變。資料不足仍會提示。")
        custom = st.checkbox("自訂三個波段的觀察根數", key=f"wave_custom_{interval}")
        if custom:
            values = [int(st.number_input(f"{name}觀察根數（{unit}K）", min_value=2*span+1,
                        max_value=5000, value=size, step=1, key=f"wave_{interval}_{name}"))
                      for name, (span, size) in result.items()]
            try:
                result = wave_windows(interval, values)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()
    return result

