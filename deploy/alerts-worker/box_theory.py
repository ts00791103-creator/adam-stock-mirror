"""Causal consolidation-box detection for the B3 Pro test branch."""
import pandas as pd

def detect_boxes(df, window=20, max_width_pct=12.0, max_boxes=5):
    if df is None or len(df) < window:
        return []
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    boxes = []
    i = window - 1
    while i < len(df):
        top = float(high.iloc[i-window+1:i+1].max())
        bottom = float(low.iloc[i-window+1:i+1].min())
        if pd.isna(top) or pd.isna(bottom) or bottom <= 0 or (top-bottom)/bottom*100 > max_width_pct:
            i += 1
            continue
        start, end = i-window+1, i
        while end+1 < len(df) and bottom <= float(close.iloc[end+1]) <= top:
            end += 1
        status = "整理中"
        if end+1 < len(df):
            status = "上破" if float(close.iloc[end+1]) > top else "下破"
        boxes.append({"start":start,"end":end,"top":top,"bottom":bottom,"mid":(top+bottom)/2,"status":status})
        i = end+1
    return boxes[-max_boxes:]
