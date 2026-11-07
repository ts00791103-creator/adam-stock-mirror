"""Price zones inferred from OHLCV; not the screenshot author's strategy."""
import numpy as np
import pandas as pd
from box_theory import detect_boxes


def estimate_poc(df, bins=40):
    """Allocate each bar's volume to HLC3 bins, not actual traded-price volume."""
    if "Volume" not in df or df.empty:
        return None
    price = df[["High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    volume = pd.to_numeric(df["Volume"], errors="coerce")
    valid = np.isfinite(price) & np.isfinite(volume) & (volume > 0)
    if not valid.any():
        return None
    price, volume = price[valid], volume[valid]
    if price.min() == price.max():
        return float(price.iloc[0])
    totals, edges = np.histogram(price, bins=bins, weights=volume)
    i = int(totals.argmax())
    return float((edges[i] + edges[i+1]) / 2)


def zone_status(df, box):
    """Latest bar relative to a frozen box; retest requires a prior outside close."""
    top, bottom = box["top"], box["bottom"]
    latest = df.iloc[-1]
    close = float(latest["Close"])
    if len(df) > 1:
        previous = float(df["Close"].iloc[-2])
        if previous > top and float(latest["Low"]) <= top and close > top:
            return "上破後回測守住"
        if previous < bottom and float(latest["High"]) >= bottom and close < bottom:
            return "下破後反彈受阻"
    return "箱頂上方" if close > top else "箱底下方" if close < bottom else "箱內／回到箱內"


def add_price_zones(fig, df, window=20, width=3.0, show_poc=True, lookback=120):
    boxes = detect_boxes(df, window=window, max_width_pct=width)
    for box in boxes:
        fig.add_shape(type="rect", x0=pd.to_datetime(box["start"], unit="s"),
                      x1=pd.to_datetime(box["end"], unit="s"), y0=box["bottom"],
                      y1=box["top"], line=dict(color="#e6a0c4", width=1),
                      fillcolor="rgba(230,160,196,0.06)", layer="below")
    if boxes:
        for value, label in [(boxes[-1]["top"], "最近箱頂"), (boxes[-1]["bottom"], "最近箱底")]:
            fig.add_hline(y=value, line_dash="dot", line_color="#e6a0c4", annotation_text=label)
    poc = estimate_poc(df.tail(lookback)) if show_poc else None
    if poc is not None:
        fig.add_hline(y=poc, line_color="#e5a830", annotation_text=f"近 {min(len(df), lookback)} 根估算 POC {poc:,.2f}")
    return boxes, poc
