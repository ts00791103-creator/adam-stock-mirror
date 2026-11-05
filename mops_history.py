"""Experimental historical MOPS cumulative EPS fetcher.
Do not infer filing dates from statement periods; fail closed until verified.
"""
import io
import re
import requests
import pandas as pd

URL = "https://mopsov.twse.com.tw/mops/web/ajax_t164sb04"

def fetch_mops_quarter(symbol, year, quarter, timeout=12):
    """Return an extracted cumulative EPS candidate, not a validated filing."""
    code = str(symbol).split(".")[0]
    if not (code.isdigit() and len(code) in (4,5)):
        return None, "股票代號格式錯誤"
    payload = {"encodeURIComponent":1,"step":1,"firstin":1,"off":1,
               "queryName":"co_id","inpuType":"co_id","TYPEK":"all",
               "isnew":"false","co_id":code,"year":year-1911,
               "season":f"{quarter:02d}"}
    try:
        response = requests.post(URL,data=payload,timeout=timeout,
                                 headers={"User-Agent":"Mozilla/5.0",
                                          "Referer":"https://mopsov.twse.com.tw/mops/web/index"})
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text))
    except Exception:
        return None, "MOPS 歷史財報服務無法讀取或格式已變更"
    # MOPS statements commonly contain current/prior and quarter/YTD columns.
    # Preserve each distinct EPS row and its original column positions.
    candidates = []
    for table_number, table in enumerate(tables, start=1):
        for row_number, (_, row) in enumerate(table.iterrows(), start=1):
            cells = [str(x).strip() for x in row.tolist()]
            labels = [x for x in cells if ("基本每股盈餘" in x or "基本每股收益" in x)]
            if not labels:
                continue
            values = []
            for column_number, cell in enumerate(cells, start=1):
                cleaned = cell.replace(",", "").replace("(", "-").replace(")", "").strip()
                if re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
                    values.append({"column": column_number, "value": float(cleaned)})
            if values:
                candidates.append({"table": table_number, "row": row_number,
                                   "label": labels[0][:100], "values": values})
    if not candidates:
        return None, "找不到可辨識的基本 EPS 數值，請確認 MOPS 是否回傳完整損益表"
    # Do not guess which column represents current-year cumulative EPS.
    return {"symbol": code,
            "quarter_end": str(pd.Period(f"{year}Q{quarter}").end_time.date()),
            "eps_rows": candidates[:15], "eps_row_count": len(candidates),
            "source": URL, "filing_date_verified": False,
            "column_verified": False}, None

def probe_mops_history(symbol, years=3):
    now = pd.Timestamp.now()
    periods = pd.period_range(end=now.to_period("Q")-1,periods=years*4,freq="Q")
    rows, failures = [], []
    for period in periods:
        result, err = fetch_mops_quarter(symbol,period.year,period.quarter)
        if result: rows.append(result)
        else: failures.append(f"{period}: {err}")
    return rows, failures
