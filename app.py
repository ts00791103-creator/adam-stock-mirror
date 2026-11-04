"""TAIFEX TX latest published daily-session data adapter for Adam B3 Pro.

This endpoint is a latest-trading-date snapshot, NOT a historical backfill.
Persist its output using a scheduled GitHub Actions job; Streamlit local disk
is not durable. This module never silently substitutes ^TWII for TX.
"""
import re
import pandas as pd
import requests

URL = 'https://openapi.taifex.com.tw/v1/DailyMarketReportFut'
REQUIRED = {'Date', 'Contract', 'ContractMonth(Week)', 'Open', 'High', 'Low', 'Last', 'Volume', 'TradingSession'}


def normalize_latest(rows):
    """Return one row per trading date / contract month / session."""
    if not isinstance(rows, list):
        raise ValueError('期交所 API 回傳格式不是資料清單')
    if not rows:
        return pd.DataFrame(columns=['Date', 'Month', 'Session', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df = pd.DataFrame(rows)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError('期交所 API 欄位異動：' + ', '.join(sorted(missing)))
    df = df.loc[df['Contract'].astype(str).str.strip().eq('TX')].copy()
    df['Month'] = df['ContractMonth(Week)'].astype(str).str.strip()
    df = df.loc[df['Month'].str.fullmatch(r'20\d{4}')].copy()
    df['Session'] = df['TradingSession'].astype(str).str.strip()
    df = df.loc[df['Session'].isin(['一般', '盤後'])].copy()
    df['Date'] = pd.to_datetime(df['Date'].astype(str), format='%Y%m%d', errors='coerce')
    for src, dest in [('Open','Open'),('High','High'),('Low','Low'),('Last','Close'),('Volume','Volume')]:
        df[dest] = pd.to_numeric(df[src].astype(str).str.replace(',', '', regex=False), errors='coerce')
    df = df.dropna(subset=['Date','Open','High','Low','Close'])
    df = df.loc[(df['High'] >= df['Low']) & (df['Open'] > 0) & (df['Close'] > 0)].copy()
    return df[['Date','Month','Session','Open','High','Low','Close','Volume']].drop_duplicates(['Date','Month','Session'], keep='last').sort_values(['Date','Month','Session']).reset_index(drop=True)


def fetch_latest(timeout=20):
    response = requests.get(URL, timeout=timeout, headers={'Accept':'application/json', 'User-Agent':'AdamB3Pro/1.0'})
    response.raise_for_status()
    return normalize_latest(response.json())


def merge_history(history, latest):
    """Merge normalized snapshots; callers must persist the result."""
    cols = ['Date','Month','Session','Open','High','Low','Close','Volume']
    combined = pd.concat([history[cols], latest[cols]], ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Date'])
    return combined.drop_duplicates(['Date','Month','Session'], keep='last').sort_values(['Date','Month','Session']).reset_index(drop=True)
