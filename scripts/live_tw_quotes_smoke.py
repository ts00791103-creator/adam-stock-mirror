"""Opt-in LIVE Yahoo Finance smoke check; never used in offline CI.

Run: python scripts/live_tw_quotes_smoke.py
Exits nonzero on download/network failure or invalid OHLC. Does not alter data.
"""
import datetime as dt
import sys
import pandas as pd
import numpy as np
import yfinance as yf


SYMBOLS = ("2330.TW", "2308.TW")


def validate(symbol, frame):
    if frame.empty:
        raise ValueError("Yahoo 回傳空資料")
    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.copy()
        frame.columns = frame.columns.get_level_values(0)
    required = ("Open", "High", "Low", "Close")
    if any(c not in frame.columns for c in required):
        raise ValueError("缺少 OHLC 欄位")
    if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        raise ValueError("日期排序或重複異常")
    values = frame.loc[:, list(required)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("價格包含 NaN 或 Inf")
    if (values <= 0).any().any():
        raise ValueError("價格包含非正數")
    if (values["High"] < values[["Open", "Low", "Close"]].max(axis=1)).any():
        raise ValueError("最高價低於其他價格")
    if (values["Low"] > values[["Open", "High", "Close"]].min(axis=1)).any():
        raise ValueError("最低價高於其他價格")
    if len(frame) < 100:
        raise ValueError(f"日K不足100根：{len(frame)}")
    last = pd.Timestamp(frame.index[-1]).date()
    print(f"PASS {symbol}: {len(frame)} 根日K，最後日期 {last}，收盤 {values['Close'].iloc[-1]:.2f}")


def main():
    print(f"即時資料抽查 UTC {dt.datetime.now(dt.timezone.utc).isoformat()}")
    failed = False
    for symbol in SYMBOLS:
        try:
            frame = yf.download(symbol, period="2y", interval="1d",
                                auto_adjust=False, progress=False, threads=False)
            validate(symbol, frame)
        except Exception as exc:
            failed = True
            print(f"FAIL {symbol}: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
