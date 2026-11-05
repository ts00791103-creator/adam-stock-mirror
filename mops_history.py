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
    candidates = []
    for table in tables:
        for _, row in table.iterrows():
            cells = [str(x).strip() for x in row.tolist()]
            labels = [x for x in cells if "基本每股盈餘" in x or "基本每股收益" in x]
            if not labels:
                continue
            numeric = []
            for cell in cells:
                cleaned = cell.replace(",","").replace("(","-").replace(")","")
                if re.fullmatch(r"-?\d+(?:\\.\d+)?",cleaned):
                    numeric.append(float(cleaned))
            if len(numeric)==1:
                candidates.append(numeric[0])
    if len(candidates)!=1:
        return None, "EPS 欄位不唯一或無法辨識，為避免誤判已停止"
    return {"symbol":code,"quarter_end":str(pd.Period(f"{year}Q{quarter}").end_time.date()),
            "cumulative_eps_candidate":candidates[0],"source":URL,
            "filing_date_verified":False},None

def probe_mops_history(symbol, years=3):
    now = pd.Timestamp.now()
    periods = pd.period_range(end=now.to_period("Q")-1,periods=years*4,freq="Q")
    rows, failures = [], []
    for period in periods:
        result, err = fetch_mops_quarter(symbol,period.year,period.quarter)
        if result: rows.append(result)
        else: failures.append(f"{period}: {err}")
    return rows, failures
