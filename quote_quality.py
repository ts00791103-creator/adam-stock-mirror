"""Explain invalid source prices without guessing or changing them."""
import numpy as np
import pandas as pd


def invalid_price_rows(frame, limit=20):
    columns = ["Open", "High", "Low", "Close"]
    if any(name not in frame for name in columns):
        return []
    prices = frame[columns].apply(pd.to_numeric, errors="coerce")
    records = []
    for stamp, row in prices.iterrows():
        reasons = []
        if not np.isfinite(row.to_numpy(dtype=float)).all():
            reasons.append("價格缺漏或非有限數值")
        if (row <= 0).any():
            reasons.append("非正數價格")
        if row.High < row[["Open", "Low", "Close"]].max():
            reasons.append("最高價低於開盤／最低／收盤")
        if row.Low > row[["Open", "High", "Close"]].min():
            reasons.append("最低價高於開盤／最高／收盤")
        if reasons:
            records.append({"日期／時間": str(stamp), "開盤": row.Open,
                            "最高": row.High, "最低": row.Low, "收盤": row.Close,
                            "問題": "；".join(reasons)})
            if len(records) >= limit:
                break
    return records
