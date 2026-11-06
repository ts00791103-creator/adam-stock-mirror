"""Confirmed historical swing levels; no projected mirror prices are used."""
import numpy as np
import pandas as pd


def key_levels(frame, lookback=120, wing=3, tolerance_pct=0.8, limit=3):
    if not (7 <= lookback <= 500 and 1 <= wing <= 10 and
            0 < tolerance_pct <= 5 and 1 <= limit <= 5):
        raise ValueError("Invalid level settings")
    if not isinstance(frame.index, pd.DatetimeIndex) or not frame.index.is_monotonic_increasing or not frame.index.is_unique:
        raise ValueError("Dates must be sorted and unique")
    data = frame.tail(lookback).copy()
    values = data[["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
    if (not np.isfinite(values.to_numpy()).all() or (values <= 0).any().any()
            or (values.High < values.max(axis=1)).any()
            or (values.Low > values.min(axis=1)).any()):
        raise ValueError("Invalid OHLC")
    if len(data) < 2 * wing + 1:
        return []
    points = []
    for i in range(wing, len(data) - wing):
        for column, kind, compare in (("High", "高點", max), ("Low", "低點", min)):
            window = values[column].iloc[i-wing:i+wing+1]
            price = float(window.iloc[wing])
            if price == compare(window) and (window == price).sum() == 1:
                points.append((price, data.index[i], kind, data.index[i+wing]))
    groups = []
    for point in sorted(points):
        if not groups or (point[0] / groups[-1][0][0] - 1) * 100 > tolerance_pct:
            groups.append([])
        groups[-1].append(point)
    close = float(values.Close.iloc[-1])
    result = []
    for group in groups:
        prices = [p[0] for p in group]
        low, high = min(prices), max(prices)
        side = "支撐" if high < close else "壓力" if low > close else "附近價位"
        price = float(np.median(prices))
        result.append({"類型": side, "參考價": price, "區間下緣": low,
                       "區間上緣": high, "距收盤%": (price/close-1)*100,
                       "轉折來源數": len(group),
                       "最近來源日": max(p[1] for p in group).isoformat(),
                       "最近確認日": max(p[3] for p in group).isoformat()})
    chosen = []
    for side in ("支撐", "壓力", "附近價位"):
        chosen.extend(sorted((r for r in result if r["類型"] == side),
                             key=lambda r: abs(r["距收盤%"]))[:limit])
    return chosen


def show_key_levels(frame, symbol, interval):
    import streamlit as st
    import plotly.graph_objects as go
    with st.expander("關鍵壓力與支撐點（測試版）", expanded=True):
        st.caption("使用歷史高低轉折，需右側3根K線確認；每組價差最多0.8%。來源數是轉折數，不是觸價次數或勝率。")
        window = st.selectbox("支撐壓力觀察根數", [60, 120, 250], index=1, key="sr_lookback")
        if not st.checkbox("顯示關鍵價位", value=True, key="sr_show"):
            return
        try:
            levels = key_levels(frame, lookback=window)
        except (ValueError, KeyError):
            st.warning("歷史行情格式或價格異常，無法確認關鍵價位。")
            return
        if not levels:
            st.info("目前資料沒有足夠的已確認轉折，請增加歷史期間或觀察根數。")
            return
        latest = float(frame.Close.iloc[-1])
        st.write(f"{symbol}｜{interval}｜資料截至 {frame.index[-1]}｜收盤 {latest:,.2f}｜實際使用 {min(window,len(frame))} 根")
        table = pd.DataFrame(levels)
        st.dataframe(table.round({"參考價": 2, "區間下緣": 2, "區間上緣": 2, "距收盤%": 2}), hide_index=True)
        history = frame.tail(window)
        fig = go.Figure(go.Candlestick(x=history.index, open=history.Open, high=history.High,
                                     low=history.Low, close=history.Close, name="歷史K線"))
        for row in levels:
            color = {"支撐": "#168f5b", "壓力": "#d74747", "附近價位": "#997000"}[row["類型"]]
            fig.add_hline(y=row["參考價"], line_color=color, line_dash="dot",
                          annotation_text=f'{row["類型"]} {row["參考價"]:,.2f}')
        fig.update_layout(height=440, xaxis_rangeslider_visible=False, dragmode="pan",
                          margin=dict(l=15,r=15,t=20,b=20))
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
        st.caption("支撐為整組價位低於收盤，壓力為整組高於收盤；跨越收盤列為附近價位。圖線為區間中位數，非精確買賣點。未排除尚未收完的最後一根K線，盤中結果可能變動；已確認轉折也可能隨觀察範圍改變。")
