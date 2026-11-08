"""Auditable OHLCV approximation. This is not tick or session volume profile."""
import numpy as np
import pandas as pd


def clean_bars(frame):
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if data.empty or any(c not in data for c in required):
        raise ValueError("缺少OHLCV或資料為空")
    if not isinstance(data.index, pd.DatetimeIndex) or data.index.hasnans or not data.index.is_unique or not data.index.is_monotonic_increasing:
        raise ValueError("日期缺漏、重複或未排序")
    data = data[required].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("價格或成交量缺漏")
    prices = data[required[:4]]
    if (prices <= 0).any().any() or (data.Volume < 0).any():
        raise ValueError("非正數價格或負成交量")
    if (data.High < prices.max(axis=1)).any() or (data.Low > prices.min(axis=1)).any():
        raise ValueError("OHLC價格矛盾")
    return data


def estimate_profile(frame, bins=40, area_pct=70.):
    if not isinstance(bins, int) or isinstance(bins, bool) or not 5 <= bins <= 100:
        raise ValueError("價位格需為5至100的整數")
    if not np.isfinite(area_pct) or not 50 <= area_pct <= 95:
        raise ValueError("價值區比例需為50至95")
    data = clean_bars(frame)
    total = float(data.Volume.sum())
    if not np.isfinite(total) or total <= 0:
        raise ValueError("無有效成交量，不能估算")
    low, high = float(data.Low.min()), float(data.High.max())
    if high == low:
        return {"poc": low, "val": low, "vah": high, "total": total, "area_volume": total,
                "area_actual_pct": 100., "prices": [low], "volumes": [total],
                "lower": [low], "upper": [high], "area_mask": [True]}
    edges = np.linspace(low, high, bins + 1)
    volume = np.zeros(bins, dtype=float)
    for row in data.itertuples():
        if row.Volume == 0:
            continue
        if row.High == row.Low:
            index = int(np.clip(np.searchsorted(edges, row.Close, side="right") - 1, 0, bins-1))
            volume[index] += row.Volume
        else:
            overlap = np.maximum(0., np.minimum(edges[1:], row.High) - np.maximum(edges[:-1], row.Low))
            volume += row.Volume * overlap / (row.High - row.Low)
    if not np.isclose(volume.sum(), total, rtol=1e-9, atol=1e-6):
        raise ValueError("成交量分配無法對帳")
    poc_index = int(np.flatnonzero(np.isclose(volume, volume.max(), rtol=1e-12, atol=0.))[0])  # Tie: lower bin.
    left = right = poc_index
    accumulated = float(volume[poc_index])
    target = total * area_pct / 100
    while accumulated < target and (left > 0 or right < bins-1):
        below = float(volume[left-1]) if left > 0 else -1.
        above = float(volume[right+1]) if right < bins-1 else -1.
        if above >= below:  # Equal neighbours: choose higher price.
            right += 1
            accumulated += float(volume[right])
        else:
            left -= 1
            accumulated += float(volume[left])
    centers = (edges[:-1] + edges[1:]) / 2
    return {"poc": float(centers[poc_index]), "val": float(edges[left]),
            "vah": float(edges[right+1]), "total": total, "area_volume": accumulated,
            "area_actual_pct": accumulated/total*100, "prices": centers.tolist(),
            "volumes": volume.tolist(), "lower": edges[:-1].tolist(), "upper": edges[1:].tolist(),
            "area_mask": [(left <= i <= right) for i in range(bins)]}


def evaluate_profile(frame, window=60, bins=40, area_pct=70., buffer_pct=.5, volume_multiple=1.5):
    if not isinstance(window, int) or isinstance(window, bool) or not 20 <= window <= 500:
        raise ValueError("觀察根數需為20至500")
    if not np.isfinite(buffer_pct) or not 0 <= buffer_pct <= 5:
        raise ValueError("確認幅度需為0至5%")
    if not np.isfinite(volume_multiple) or not 1 <= volume_multiple <= 5:
        raise ValueError("量比需為1至5")
    if len(frame) < window + 1:
        raise ValueError(f"至少需要{window+1}根；目前{len(frame)}根")
    data = clean_bars(frame.tail(window+1))
    prior, last = data.iloc[:-1], data.iloc[-1]
    profile = estimate_profile(prior, bins, area_pct)
    average = float(prior.Volume.tail(20).mean())
    if average <= 0:
        raise ValueError("前20根均量為零，不能確認量能")
    ratio = float(last.Volume) / average
    previous = float(prior.Close.iloc[-1])
    close = float(last.Close)
    signal = "未成立"
    if ratio >= volume_multiple:
        if previous <= profile["vah"] and close > profile["vah"]*(1+buffer_pct/100):
            signal = "放量突破估算價值區"
        elif previous >= profile["val"] and close < profile["val"]*(1-buffer_pct/100):
            signal = "放量跌破估算價值區"
    return {"profile": profile, "signal": signal, "close": close, "previous_close": previous,
            "volume_ratio": ratio, "average_volume": average, "reference_bars": window,
            "reference_start": str(prior.index[0]), "reference_end": str(prior.index[-1]),
            "signal_time": str(data.index[-1]), "buffer_pct": buffer_pct,
            "volume_multiple": volume_multiple}


def show_volume_profile(frame, symbol, interval, window=60, bins=40, area_pct=70., buffer_pct=.5, volume_multiple=1.5):
    import streamlit as st
    import plotly.graph_objects as go
    with st.expander("成交量集中區｜POC與價值區（估算版）", expanded=True):
        st.warning("K線成交量估算，不是逐筆成交價量，也未分日盤／夜盤。價位會隨週期、觀察根數及價位格改變。")
        try:
            result = evaluate_profile(frame, window, bins, area_pct, buffer_pct, volume_multiple)
        except (ValueError, KeyError, TypeError) as exc:
            st.info("未判定：" + str(exc))
            return
        profile = result["profile"]
        st.caption(f'{symbol}｜{interval}｜參考區間 {result["reference_start"]} → {result["reference_end"]}｜訊號K線 {result["signal_time"]}（未納入參考區）')
        columns = st.columns(3)
        for column, label, key in zip(columns, ["估算POC", "價值區下緣 VAL", "價值區上緣 VAH"], ["poc", "val", "vah"]):
            column.metric(label, f'{profile[key]:,.2f}')
        st.write(f'觀察結果：{result["signal"]}｜本根量／前20根均量 {result["volume_ratio"]:.2f} 倍')
        st.caption(f'設定價值區 {area_pct:.0f}%，實際涵蓋估算量 {profile["area_actual_pct"]:.2f}%（整格納入，可能超過設定）；總量 {profile["total"]:,.0f}，依行情來源原始單位。')
        bars = clean_bars(frame.tail(window+1))
        chart = go.Figure(go.Candlestick(x=bars.index, open=bars.Open, high=bars.High, low=bars.Low, close=bars.Close, name="歷史K線"))
        chart.add_hrect(y0=profile["val"], y1=profile["vah"], fillcolor="#d6ad62", opacity=.12, line_width=0)
        for key, label, color in [("poc", "估算POC", "#d6ad62"), ("val", "VAL", "#41b899"), ("vah", "VAH", "#d56c85")]:
            chart.add_hline(y=profile[key], line_color=color, line_dash="dot", annotation_text=f'{label} {profile[key]:,.2f}')
        chart.update_layout(height=440, xaxis_rangeslider_visible=False, dragmode="pan", margin=dict(l=10,r=10,t=20,b=20))
        st.plotly_chart(chart, use_container_width=True, config={"scrollZoom": True})
        histogram = go.Figure(go.Bar(x=profile["volumes"], y=profile["prices"], orientation="h",
                                   marker_color=["#d6ad62" if flag else "#536c79" for flag in profile["area_mask"]], name="估算分配量"))
        histogram.update_layout(height=300, dragmode="pan", xaxis_title="估算分配量（來源原始單位）", yaxis_title="價位格中心", margin=dict(l=10,r=10,t=10,b=30))
        st.plotly_chart(histogram, use_container_width=True, config={"scrollZoom": True})
        audit = pd.DataFrame({"價位下緣": profile["lower"], "價位上緣": profile["upper"], "中心價": profile["prices"], "估算分配量": profile["volumes"], "價值區內": profile["area_mask"]})
        st.download_button("下載成交量分布估算CSV", audit.to_csv(index=False).encode("utf-8-sig"),
                           file_name="adam_volume_profile_estimate.csv", mime="text/csv")
        st.caption(f'觀察規則：前收盤位於既有VAH以下、本根收盤高於VAH {buffer_pct:.2f}%且量比至少{volume_multiple:.2f}倍，列為突破；跌破反向判斷。門檻使用前一段資料。本根若尚未收完則僅為盤中暫定觀察，不發送推播、不代表勝率或買賣指示。')
        st.caption("估算方法：每根成交量在最低到最高價間按重疊長度均分；一價K線放入對應格。POC同量取較低格；價值區由POC向量較大的相鄰格擴展，同量優先上格，直到至少設定比例。這是本工具的明示算法，並非TradingView逐筆或細週期的相同計算。")
