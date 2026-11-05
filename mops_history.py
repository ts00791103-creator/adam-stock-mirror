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
    table_headers = {}
    for table_number, table in enumerate(tables, start=1):
        table_headers[table_number] = {"columns": [str(c)[:120] for c in table.columns], "top_rows": [[str(v)[:90] for v in row.tolist()] for _, row in table.head(7).iterrows()]}
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
    # Map EPS cells only when the source header explicitly identifies the
    # requested current-quarter and year-to-date periods. Never use positions
    # alone: MOPS can add/reorder columns between statement formats.
    verified = []
    roc = year - 1911
    for candidate in candidates:
        header = table_headers[candidate["table"]]["columns"]
        mapping = {}
        for cell in candidate["values"]:
            index = cell["column"] - 1
            if index >= len(header):
                continue
            label = header[index]
            current_year = f"{roc}年"
            prior_year = f"{roc-1}年"
            current_quarter = f"{roc}年第{quarter}季"
            ytd_start = f"{roc}年01月01日"
            ytd_end = f"{roc}年{quarter*3:02d}月"
            if current_quarter in label and ("金額" in label):
                mapping["quarter_eps"] = cell["value"]
            elif ytd_start in label and ytd_end in label and "金額" in label:
                mapping["cumulative_eps"] = cell["value"]
        if "quarter_eps" in mapping and "cumulative_eps" in mapping:
            verified.append(mapping)
    verified_eps = verified[0] if len(verified) == 1 else None
    if not candidates:
        return None, "找不到可辨識的基本 EPS 數值，請確認 MOPS 是否回傳完整損益表"
    # Do not guess which column represents current-year cumulative EPS.
    return {"symbol": code,
            "quarter_end": str(pd.Period(f"{year}Q{quarter}").end_time.date()),
            "eps_rows": candidates[:15], "eps_row_count": len(candidates),
            "headers": {str(x["table"]): table_headers[x["table"]] for x in candidates[:15]},
            "source": URL, "filing_date_verified": False,
            "column_verified": verified_eps is not None,
            "verified_eps": verified_eps}, None

def probe_mops_history(symbol, years=3):
    now = pd.Timestamp.now()
    periods = pd.period_range(end=now.to_period("Q")-1,periods=years*4,freq="Q")
    rows, failures = [], []
    for period in periods:
        result, err = fetch_mops_quarter(symbol,period.year,period.quarter)
        if result: rows.append(result)
        else: failures.append(f"{period}: {err}")
    return rows, failures
