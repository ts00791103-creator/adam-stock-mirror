"""Read candidate financial-report announcements from TWSE's company page.

The page can be JavaScript-rendered or limited to recent filings. Missing data
must remain missing. Duplicate announcements require manual adjudication.
"""
import io
import re
from datetime import datetime, timezone
import requests
import pandas as pd

BASE = "https://www.twse.com.tw/IIH2/zh/market/information.html"


def fetch_official_filing_candidates(stock_code, timeout=12):
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{4,5}", code):
        return [], "股票代號格式錯誤"
    urls = [
        f"https://www.twse.com.tw/IIH2/zh/company/information.html?code={code}",
        f"https://wwwc.twse.com.tw/IIH2/zh/company/information.html?code={code}",
    ]
    found = []
    diagnostics = []
    saw_report_table = False
    for url in urls:
        try:
            response = requests.get(url, timeout=timeout,
                                    headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            frames = pd.read_html(io.StringIO(response.text))
        except requests.RequestException:
            diagnostics.append("官方網站連線失敗")
            continue
        except (ValueError, ImportError):
            diagnostics.append("頁面沒有可直接讀取的 HTML 表格")
            continue
        source_found = []
        for frame in frames:
            if any("財務報告書" in str(value) for value in frame.astype(str).to_numpy().flat):
                saw_report_table = True
            frame.columns = [" ".join(map(str, col)) if isinstance(col, tuple) else str(col)
                             for col in frame.columns]
            for _, row in frame.iterrows():
                cells = [str(v).strip() for v in row.tolist()]
                joined = " ".join(cells)
                if "財務報告書" not in joined or not re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", joined):
                    continue
                quarter_match = re.search(r"(\d{3})\s*年\s*第?\s*([1-4])\s*季\s*財務報告書", joined)
                time_match = re.search(r"(?<!\d)(\d{3})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s+(\d{1,2}):(\d{2})(?!\d)", joined)
                if not quarter_match or not time_match:
                    continue
                year = int(quarter_match.group(1)) + 1911
                quarter = int(quarter_match.group(2))
                try:
                    announced = pd.Timestamp(
                        year=int(time_match.group(1)) + 1911,
                        month=int(time_match.group(2)), day=int(time_match.group(3)),
                        hour=int(time_match.group(4)), minute=int(time_match.group(5)))
                except (ValueError, OverflowError):
                    continue
                quarter_end = pd.Period(f"{year}Q{quarter}", freq="Q").end_time
                if announced <= quarter_end or announced > pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None)):
                    continue
                source_found.append({"股票代號": code, "季度": f"{year}Q{quarter}",
                                     "公告日期時間": announced.strftime("%Y-%m-%d %H:%M"),
                                     "官方來源網址": url, "公告主旨": joined[:300]})
        if source_found:
            found.extend(source_found)
            break
        diagnostics.append("頁面表格沒有符合股票代號、季度及公告時間的財報紀錄")
    unique = list({(r["季度"], r["公告日期時間"], r["公告主旨"]): r for r in found}.values())
    unique.sort(key=lambda r: (r["季度"], r["公告日期時間"]))
    if not unique:
        return [], "；".join(dict.fromkeys(diagnostics)) + ("；含財報相關表格但尚無可核實日期" if saw_report_table else "；尚無可核實公告日期")
    return unique, None


def review_candidate_coverage(candidates, periods):
    """Report visible candidates without certifying historical filing dates."""
    grouped = {}
    for row in candidates:
        grouped.setdefault(row['季度'], []).append(row)
    summary = []
    for period in periods:
        records = grouped.get(period, [])
        dates = sorted(str(r['公告日期時間']) for r in records if r.get('公告日期時間'))
        count = len(records)
        summary.append({
            '季度': period,
            '候選公告筆數': count,
            '頁面可見最早公告（未核實）': dates[0] if dates else None,
            '狀態': ('頁面未提供紀錄，不能推定未公告' if not count else
                     '多筆公告，須辨識首次申報與更正' if count > 1 else
                     '單筆候選，須核對是否首次申報'),
            '可用於歷史PE': False,
        })
    return summary


def probe_discovered_mops_form(stock_code, year, quarter, timeout=12):
    """Probe the observed legacy MOPS form action, without trusting its contents.

    The action was observed on the query page; it is not yet verified as a
    filing-announcement endpoint. Never return announcement dates from here.
    """
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{4,5}", code):
        return {"status": "invalid_stock"}
    if not (isinstance(year, int) and 2000 <= year <= 2100
            and isinstance(quarter, int) and 1 <= quarter <= 4):
        return {"status": "invalid_period"}
    endpoint = "https://mopsov.twse.com.tw/mops/web/ajax_t56sb31_q1"
    payload = {"step": "1", "firstin": "1", "co_id": code,
               "TYPEK": "all", "YEAR_SEASON": f"{year - 1911}{quarter:02d}"}
    try:
        response = requests.post(endpoint, data=payload, timeout=timeout,
                                 headers={"User-Agent": "Mozilla/5.0",
                                          "Referer": "https://mopsov.twse.com.tw/"})
        response.raise_for_status()
    except requests.RequestException:
        return {"status": "connection_error", "message": "新路徑連線失敗"}
    body = response.text or ""
    try:
        tables = pd.read_html(io.StringIO(body))
    except (ValueError, ImportError):
        tables = []
    # Diagnose non-tabular responses without returning raw HTML or user data.
    import hashlib
    from html.parser import HTMLParser
    class _SafeResponseParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.title = []
            self.in_title = False
            self.forms = []
        def handle_starttag(self, tag, attrs):
            if tag == "title":
                self.in_title = True
            if tag == "form":
                attrs = dict(attrs)
                self.forms.append(str(attrs.get("method", "GET")).upper()[:8])
        def handle_endtag(self, tag):
            if tag == "title":
                self.in_title = False
        def handle_data(self, data):
            if self.in_title:
                self.title.append(data[:100])
    parser = _SafeResponseParser()
    parser.feed(body)
    response_diagnostic = {
        "content_type": response.headers.get("Content-Type", "").split(";")[0],
        "html_title": " ".join(parser.title)[:100] or None,
        "looks_like_json": body.lstrip().startswith(("{", "[")),
        "looks_like_html": "<html" in body.lower(),
        "contains_table": "<table" in body.lower(),
        "contains_script": "<script" in body.lower(),
        "contains_captcha": any(x in body.lower() for x in ("captcha", "驗證碼")),
        "contains_no_data": any(x in body for x in ("查無資料", "無資料", "沒有符合")),
        "contains_parameter_error": any(x in body.lower() for x in ("參數錯誤", "參數有誤", "invalid parameter")),
        "form_methods": parser.forms[:10],
        "response_sha256_prefix": hashlib.sha256(body.encode("utf-8")).hexdigest()[:12],
    }
    profiles = []
    for idx, frame in enumerate(tables[:15]):
        sample = " ".join(map(str, frame.astype(str).to_numpy().flat))
        profiles.append({"表格": idx, "列數": len(frame), "欄數": len(frame.columns),
                         "含股票代號": bool(re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", sample)),
                         "含公告日期字樣": any(k in sample for k in ("公告日期", "申報日期", "公告時間", "申報時間")),
                         "含財報字樣": any(k in sample for k in ("財務報告", "財報"))})
    if not tables and response_diagnostic["looks_like_html"] and response_diagnostic["contains_script"]:
        return {"status": "javascript_shell", "endpoint": "/mops/web/ajax_t56sb31_q1",
                "http_status": response.status_code, "response_chars": len(body),
                "table_count": 0, "response_diagnostic": response_diagnostic,
                "message": "回傳公開資訊觀測站網頁外殼，不是公告結果；停止以此請求取得公告日"}
    return {"status": "diagnostic_only", "endpoint": "/mops/web/ajax_t56sb31_q1",
            "http_status": response.status_code, "response_chars": len(body),
            "table_count": len(tables), "table_profiles": profiles,
            "response_diagnostic": response_diagnostic,
            "message": "僅診斷回傳資料，不視為已核實公告日期"}


def classify_filing_response_html(html, stock_code, year, quarter):
    """Structural evidence only; never extracts or certifies a filing date."""
    from html.parser import HTMLParser
    class TableCollector(HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.tables = []
            self.parts = []
        def handle_starttag(self, tag, attrs):
            if tag == "table":
                if self.depth == 0:
                    self.parts = []
                self.depth += 1
        def handle_endtag(self, tag):
            if tag == "table" and self.depth:
                self.depth -= 1
                if not self.depth:
                    self.tables.append(" ".join(self.parts))
        def handle_data(self, data):
            if self.depth:
                self.parts.append(data.strip())
    parser = TableCollector()
    parser.feed(html or "")
    code = str(stock_code)
    roc = str(year - 1911)
    quarter_markers = [f"{year}Q{quarter}", f"{roc}年第{quarter}季",
                       f"{roc}年 第{quarter}季", f"{roc}/{quarter:02d}"]
    results = []
    for content in parser.tables[:30]:
        has_code = bool(re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", content))
        has_period = any(marker in content for marker in quarter_markers)
        has_filing = any(x in content for x in ("財務報告", "財報", "申報", "公告"))
        has_date = bool(re.search(r"(?:20\d{2}|1\d{2})[/-]\d{1,2}[/-]\d{1,2}", content))
        results.append({"has_stock_code": has_code, "has_period": has_period,
                        "has_filing_keyword": has_filing, "has_date_pattern": has_date})
    candidates = [x for x in results if all(x.values())]
    return {"table_count": len(parser.tables), "inspected_tables": len(results),
            "candidate_table_count": len(candidates),
            "table_signals": results,
            "classification": ("possible_filing_table_unverified" if candidates else
                               "no_matching_filing_table"),
            "verified_filing_date": None}


def probe_session_backed_filing_query(stock_code, year, quarter, timeout=12, session=None):
    """Compare the official t163sb01 query page and a same-session AJAX POST.

    Diagnostic only. No filing date is accepted from either response.
    """
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{4,5}", code):
        return {"status": "invalid_stock"}
    if not (isinstance(year, int) and 2000 <= year <= 2100
            and isinstance(quarter, int) and 1 <= quarter <= 4):
        return {"status": "invalid_period"}
    client = session if session is not None else requests.Session()
    base = "https://mopsov.twse.com.tw/mops/web/"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": base + "t163sb01"}
    payload = {"encodeURIComponent": "1", "step": "1", "firstin": "1",
               "off": "1", "queryName": "co_id", "inpuType": "co_id",
               "TYPEK": "all", "isnew": "false", "co_id": code,
               "year": str(year - 1911), "season": f"{quarter:02d}"}
    try:
        landing = client.get(base + "t163sb01", headers=headers, timeout=timeout)
        landing.raise_for_status()
        result = client.post(base + "ajax_t163sb01", data=payload,
                             headers=headers, timeout=timeout)
        result.raise_for_status()
    except requests.RequestException:
        return {"status": "connection_error", "message": "官方財報公告查詢連線失敗"}
    import hashlib
    def signature(response):
        body = response.text or ""
        return {"chars": len(body),
                "sha256_prefix": hashlib.sha256(body.encode("utf-8")).hexdigest()[:12],
                "has_table": "<table" in body.lower(),
                "has_script": "<script" in body.lower(),
                "has_stock_code": bool(re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", body))}
    a, b = signature(landing), signature(result)
    b["table_evidence"] = classify_filing_response_html(result.text, code, year, quarter)
    return {"status": "session_diagnostic_only",
            "query_page": a, "ajax_result": b,
            "same_response": a["sha256_prefix"] == b["sha256_prefix"],
            "message": "同一工作階段的官方查詢診斷；尚未核實財報首次申報日，不可解鎖歷史 PE"}


def compare_filing_quarters(stock_code, periods=((2026, 3), (2025, 4), (2024, 4)),
                            timeout=12, probe=None):
    """Compare recent and old quarters without treating diagnostics as filings.

    A successful HTTP response does not establish that a report was filed.
    Inject probe for offline tests; failures are isolated per quarter.
    """
    worker = probe if probe is not None else probe_session_backed_filing_query
    rows = []
    for year, quarter in periods:
        period = f"{year}Q{quarter}"
        try:
            result = worker(stock_code, year, quarter, timeout=timeout)
        except Exception:
            result = {"status": "probe_error"}
        ajax = result.get("ajax_result") or {}
        rows.append({"季度": period, "查詢狀態": result.get("status", "unknown"),
                     "回應字元數": ajax.get("chars"),
                     "包含表格": ajax.get("has_table"),
                     "包含股票代號": ajax.get("has_stock_code"),
                     "回應指紋": ajax.get("sha256_prefix"),
                     "符合條件候選表格數": (ajax.get("table_evidence") or {}).get("candidate_table_count"),
                     "表格判讀": (ajax.get("table_evidence") or {}).get("classification"),
                     "公告日期已核實": False})
    fingerprints = [row["回應指紋"] for row in rows if row["回應指紋"]]
    same = len(fingerprints) == len(rows) and len(set(fingerprints)) == 1
    return {"rows": rows, "all_ajax_responses_identical": same,
            "conclusion": ("三個季度回應完全相同，疑似取得通用查詢頁或未依季度查詢"
                           if same else "各季度回應不同或部分失敗；仍須驗證資料內容及首次申報時間"),
            "verified_filing_dates": 0}


def probe_mops_financial_announcement(stock_code, year, quarter, timeout=12):
    """Probe historical MOPS financial-report announcement transport only.

    This intentionally does not infer an announcement timestamp from the
    report year/quarter or from a response without a validated date field.
    """
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{4,5}", code):
        return {"status": "invalid_stock", "message": "股票代號格式錯誤"}
    if not (isinstance(year, int) and 2000 <= year <= 2100
            and isinstance(quarter, int) and 1 <= quarter <= 4):
        return {"status": "invalid_period", "message": "季度格式錯誤"}
    url = "https://mopsov.twse.com.tw/mops/web/ajax_t163sb01"
    payload = {"encodeURIComponent": 1, "step": 1, "firstin": 1,
               "off": 1, "queryName": "co_id", "inpuType": "co_id",
               "TYPEK": "all", "isnew": "false", "co_id": code,
               "year": year - 1911, "season": f"{quarter:02d}"}
    try:
        response = requests.post(url, data=payload, timeout=timeout,
                                 headers={"User-Agent": "Mozilla/5.0",
                                          "Referer": "https://mopsov.twse.com.tw/"})
        response.raise_for_status()
    except requests.RequestException:
        return {"status": "connection_error", "message": "MOPS 財報公告介接連線失敗"}
    body = response.text or ""
    # Diagnostic metadata only: do not expose raw response text, cookies, or tokens.
    import hashlib
    diagnostic = {
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type", "").split(";")[0],
        "final_host": __import__("urllib.parse", fromlist=["urlparse"]).urlparse(response.url).hostname,
        "response_sha256_prefix": hashlib.sha256(body.encode("utf-8")).hexdigest()[:12],
        "looks_like_html": "<html" in body.lower(),
        "looks_like_json": body.lstrip().startswith(("{", "[")),
        "contains_table": "<table" in body.lower(),
        "contains_captcha": any(x in body.lower() for x in ("captcha", "驗證碼")),
        "contains_redirect": any(x in body.lower() for x in ("location.href", "window.location")),
        "contains_error_marker": any(x in body.lower() for x in ("error", "查無資料", "系統忙碌")),
        "has_form": "<form" in body.lower(),
        "has_script": "<script" in body.lower(),
        "has_meta_refresh": "http-equiv" in body.lower() and "refresh" in body.lower(),
        "has_login_hint": any(x in body.lower() for x in ("login", "登入", "session")),
        "has_access_denied_hint": any(x in body.lower() for x in ("access denied", "forbidden", "存取被拒")),
        "has_mops_brand": any(x in body.lower() for x in ("公開資訊觀測站", "mops")),
        "html_title": __import__("html").unescape(
            re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S).group(1).strip()[:100]
        ) if re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S) else None,
    }
    if diagnostic["has_script"] and not diagnostic["contains_table"] and not diagnostic["looks_like_json"]:
        return {"status": "javascript_shell", "message": "官方端點回傳 JavaScript 網頁外殼，並非財報公告資料", "response_chars": len(body), **diagnostic}
    if diagnostic["contains_table"]:
        # The legacy endpoint can return its query form as 11 HTML tables.
        # Do not interpret those tables as announcement records.
        if not re.search(r"(?<!\d)" + re.escape(code) + r"(?!\d)", body):
            diagnostic["response_has_requested_stock"] = False
        else:
            diagnostic["response_has_requested_stock"] = True
    else:
        diagnostic["response_has_requested_stock"] = False
    if not body.strip():
        return {"status": "empty", "message": "官方接口回傳空白內容", **diagnostic}
    try:
        frames = pd.read_html(io.StringIO(body))
    except (ValueError, ImportError):
        return {"status": "unparsed", "message": "官方接口有回應，但不是可直接解析的 HTML 表格",
                "response_chars": len(body), **diagnostic}
    # Identify whether the response is a query UI, and surface safe input names
    # so the next request can be based on observed parameters rather than guesses.
    from html.parser import HTMLParser
    class _InputNames(HTMLParser):
        def __init__(self):
            super().__init__()
            self.names = set()
            self.forms = 0
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "form":
                self.forms += 1
            if tag in ("input", "select") and attrs.get("name"):
                name = attrs["name"]
                if re.fullmatch(r"[A-Za-z0-9_\\-]{1,60}", name):
                    self.names.add(name)
    parser = _InputNames()
    parser.feed(body)
    diagnostic["form_count"] = parser.forms
    diagnostic["input_field_names"] = sorted(parser.names)[:40]
    # Read only static form action/method and option field names; no field values
    # or raw HTML are exposed. This helps identify whether an actual submit route exists.
    class _Forms(HTMLParser):
        def __init__(self):
            super().__init__()
            self.forms = []
        def handle_starttag(self, tag, attrs):
            if tag != "form":
                return
            data = dict(attrs)
            action = data.get("action", "")
            # Do not expose full URLs or embedded query strings.
            from urllib.parse import urlparse
            parsed = urlparse(action)
            self.forms.append({
                "method": str(data.get("method", "get")).upper()[:8],
                "action_path": parsed.path[:120],
                "action_host": parsed.hostname,
            })
    form_parser = _Forms()
    form_parser.feed(body)
    diagnostic["form_targets"] = form_parser.forms[:10]
    # Expose only non-sensitive query defaults from the observed official form.
    # These are evidence for the request schema, NOT evidence of a filing date.
    class _QueryDefaults(HTMLParser):
        allowed = {"co_id", "YEAR_SEASON", "TYPEK", "step", "firstin",
                   "CID", "DTYPE", "RID", "SKEY", "kind"}
        def __init__(self):
            super().__init__()
            self.defaults = {}
        def handle_starttag(self, tag, attrs):
            if tag != "input":
                return
            attrs = dict(attrs)
            name = attrs.get("name")
            if name not in self.allowed:
                return
            value = str(attrs.get("value", ""))
            # SKEY/RID may be session-specific: never expose their values.
            if name in {"SKEY", "RID"}:
                self.defaults[name] = "[隱藏]"
            elif re.fullmatch(r"[A-Za-z0-9_\\-]{0,30}", value):
                self.defaults[name] = value
    defaults_parser = _QueryDefaults()
    defaults_parser.feed(body)
    diagnostic["safe_form_defaults"] = defaults_parser.defaults
    table_profiles = []
    for idx, frame in enumerate(frames[:25]):
        values = frame.astype(str)
        sample = " ".join(str(x) for x in values.to_numpy().flat)
        headers = " ".join(str(x) for x in frame.columns)
        text = headers + " " + sample
        table_profiles.append({
            "index": idx,
            "rows": len(frame),
            "columns": len(frame.columns),
            "has_stock_code": code in text,
            "has_filing_keyword": any(k in text for k in ("財務報告", "財報公告", "申報日期", "公告日期")),
            "has_date_keyword": any(k in text for k in ("日期", "時間", "公告", "申報")),
            "has_roc_date_pattern": bool(re.search(r"(?<!\d)1\d{2}[/.-]\d{1,2}[/.-]\d{1,2}", text)),
            "header_labels": [str(x)[:65] for x in frame.columns[:8]],
            "looks_like_result_table": (
                code in text
                and any(k in text for k in ("財務報告", "申報日期", "公告日期"))
                and any(k in text for k in ("日期", "時間"))
            ),
            "likely_ui_table": (
                code not in text
                and not bool(re.search(r"(?<!\d)1\d{2}[/.-]\d{1,2}[/.-]\d{1,2}", text))
            ),
        })
    # The legacy t163sb01 page is not an independently verified filing-date source.
    # Even a table containing dates must remain unverified until its semantics
    # and first-filing provenance are established.
    if not any(p["looks_like_result_table"] for p in table_profiles):
        return {"status": "query_form_only",
                "message": "取得的表格未同時包含指定股票與公告日期，可能只是查詢表單；不可作為公告紀錄",
                "table_count": len(frames), "table_profiles": table_profiles,
                "response_chars": len(body), **diagnostic}
    return {"status": "tables_unverified", "message": "取得 HTML 表格，但尚未驗證公告日期欄位",
            "table_count": len(frames),
            "table_profiles": table_profiles,
            "response_chars": len(body), **diagnostic}
