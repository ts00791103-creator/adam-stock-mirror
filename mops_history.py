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
    # Pandas read_html produces a MultiIndex for the MOPS two-level header.
    # Inspect tuple levels directly; a stringified tuple must not be matched
    # as one flat string (it can mix current and prior period labels).
    verified = []
    roc = year - 1911
    for candidate in candidates:
        table = tables[candidate["table"] - 1]
        matches = {"quarter_eps": [], "cumulative_eps": []}
        for cell in candidate["values"]:
            index = cell["column"] - 1
            if index >= len(table.columns):
                continue
            raw = table.columns[index]
            levels = raw if isinstance(raw, tuple) else (raw,)
            levels = [re.sub(r"\\s+", "", str(x)) for x in levels]
            if not any("金額" in level for level in levels):
                continue
            if any("%" in level or "％" in level for level in levels):
                continue
            period_levels = [level for level in levels if "年" in level and ("季" in level or "月" in level)]
            if len(period_levels) != 1:
                continue
            period = period_levels[0]
            years = rf"(?:{roc}|{year})"
            quarter_re = rf"(?<!\\d){years}年第0?{quarter}季"
            cumulative_re = (
                rf"(?<!\\d){years}年0?1月0?1日至"
                rf"{years}年0?{quarter*3}月(?:30|31)日"
            )
            if re.search(cumulative_re, period):
                matches["cumulative_eps"].append(cell["value"])
            elif re.search(quarter_re, period):
                matches["quarter_eps"].append(cell["value"])
        if all(len(matches[k]) == 1 for k in matches):
            verified.append({k: matches[k][0] for k in matches})
    # Diagnostic: show the exact unflattened header levels attached to each
    # EPS value, plus classification, without treating candidates as verified.
    eps_header_diagnostics = []
    for candidate in candidates[:15]:
        table = tables[candidate["table"] - 1]
        for cell in candidate["values"]:
            idx = cell["column"] - 1
            if idx >= len(table.columns):
                continue
            raw = table.columns[idx]
            levels = [str(x) for x in (raw if isinstance(raw, tuple) else (raw,))]
            eps_header_diagnostics.append({
                "table": candidate["table"], "column": cell["column"],
                "value": cell["value"], "header_levels": levels,
                "contains_amount": any("金額" in x for x in levels),
                "contains_percent": any("%" in x or "％" in x for x in levels),
                "period_text": " | ".join(x for x in levels if "年" in x),
            })
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
            "verified_eps": verified_eps,
            "eps_header_diagnostics": eps_header_diagnostics}, None

def probe_mops_history(symbol, years=3):
    now = pd.Timestamp.now()
    periods = pd.period_range(end=now.to_period("Q")-1,periods=years*4,freq="Q")
    rows, failures = [], []
    for period in periods:
        result, err = fetch_mops_quarter(symbol,period.year,period.quarter)
        if result: rows.append(result)
        else: failures.append(f"{period}: {err}")
    return rows, failures
