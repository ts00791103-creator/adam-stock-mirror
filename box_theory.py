"""Causal consolidation-box detector for OHLC data."""
import pandas as pd

def detect_boxes(df, window=20, max_width_pct=12.0, max_boxes=6):
    """Confirm a box using only bars through its confirmation date."""
    if df is None or len(df) < window:
        return []
    highs = pd.to_numeric(df["High"], errors="coerce")
    lows = pd.to_numeric(df["Low"], errors="coerce")
    closes = pd.to_numeric(df["Close"], errors="coerce")
    boxes = []
    i = window - 1
    while i < len(df):
        h = float(highs.iloc[i-window+1:i+1].max())
        l = float(lows.iloc[i-window+1:i+1].min())
        if l <= 0 or (h-l)/l*100 > max_width_pct:
            i += 1
            continue
        start = i-window+1
        end = i
        # Only extend with subsequently observed bars; break on close outside the box.
        while end+1 < len(df):
            close = float(closes.iloc[end+1])
            if close > h or close < l:
                break
            end += 1
        boxes.append({
            "start": int(pd.Timestamp(df.index[start]).timestamp()),
            "end": int(pd.Timestamp(df.index[end]).timestamp()),
            "top": round(h, 4), "bottom": round(l, 4),
            "mid": round((h+l)/2, 4),
            "breakout": ("上破" if end+1<len(df) and float(closes.iloc[end+1])>h
                         else "下破" if end+1<len(df) and float(closes.iloc[end+1])<l
                         else "整理中")
        })
        i = end + 1 if end >= i else i + 1
    return boxes[-max_boxes:]
