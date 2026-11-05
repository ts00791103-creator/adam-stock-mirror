"""Read candidate financial-report announcements from TWSE's company page.

The page can be JavaScript-rendered or limited to recent filings. Missing data
must remain missing. Duplicate announcements require manual adjudication.
"""
import io
import re
import requests
import pandas as pd

BASE = "https://www.twse.com.tw/IIH2/zh/market/information.html"


def fetch_official_filing_candidates(stock_code, timeout=12):
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{4,5}", code):
        return [], "股票代號格式錯誤"
    url = BASE
    try:
        response = requests.get(BASE, timeout=timeout,
                                headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        frames = pd.read_html(io.StringIO(response.text))
    except requests.RequestException:
        return [], "證交所網站連線失敗，請稍後再試"
    except (ValueError, ImportError):
        return [], "證交所資訊揭露頁沒有可直接讀取的 HTML 表格；需確認動態資料來源"
    found = []
    report_tables = 0
    for frame in frames:
        if any("財務報告書" in str(value) for value in frame.astype(str).to_numpy().flat):
            report_tables += 1
        frame.columns = [" ".join(map(str, col)) if isinstance(col, tuple) else str(col)
                         for col in frame.columns]
        for _, row in frame.iterrows():
            cells = [str(v).strip() for v in row.tolist()]
            joined = " ".join(cells)
            if "財務報告書" not in joined or code not in cells:
                continue
            quarter_match = re.search(r"(\d{3})年第?([1-4])季財務報告書", joined)
            time_match = re.search(r"(\d{3})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})", joined)
            if not quarter_match or not time_match:
                continue
            year = int(quarter_match.group(1)) + 1911
            quarter = int(quarter_match.group(2))
            try:
                announced = pd.Timestamp(
                    year=int(time_match.group(1)) + 1911,
                    month=int(time_match.group(2)), day=int(time_match.group(3)),
                    hour=int(time_match.group(4)), minute=int(time_match.group(5)))
            except ValueError:
                continue
            found.append({"股票代號": code, "季度": f"{year}Q{quarter}",
                          "公告日期時間": announced.strftime("%Y-%m-%d %H:%M"),
                          "官方來源網址": url, "公告主旨": joined[:300]})
    unique = list({(r["季度"], r["公告日期時間"], r["公告主旨"]): r for r in found}.values())
    unique.sort(key=lambda r: (r["季度"], r["公告日期時間"]))
    if not unique:
        if report_tables == 0:
            return [], "HTML 表格未包含財務報告書資料；可能需要官方動態資料接口"
        return [], "有財報相關文字，但股票代號、季度或公告日期格式無法完整辨識；不得推算公告日"
    return unique, None


def review_candidate_coverage(candidates, periods):
    grouped = {}
    for row in candidates:
        grouped.setdefault(row["季度"], []).append(row)
    return [{"季度": period, "候選公告筆數": len(grouped.get(period, [])),
             "狀態": ("無公告紀錄" if period not in grouped else
                     "多筆公告，須辨識初次申報及更正" if len(grouped[period]) > 1 else
                     "單筆候選，仍須核對是否為初次財報申報")}
            for period in periods]


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
    url = "https://mops.twse.com.tw/mops/web/ajax_t163sb01"
    payload = {"encodeURIComponent": 1, "step": 1, "firstin": 1,
               "off": 1, "queryName": "co_id", "inpuType": "co_id",
               "TYPEK": "all", "isnew": "false", "co_id": code,
               "year": year - 1911, "season": f"{quarter:02d}"}
    try:
        response = requests.post(url, data=payload, timeout=timeout,
                                 headers={"User-Agent": "Mozilla/5.0",
                                          "Referer": "https://mops.twse.com.tw/"})
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
    if not body.strip():
        return {"status": "empty", "message": "官方接口回傳空白內容", **diagnostic}
    try:
        frames = pd.read_html(io.StringIO(body))
    except (ValueError, ImportError):
        return {"status": "unparsed", "message": "官方接口有回應，但不是可直接解析的 HTML 表格",
                "response_chars": len(body), **diagnostic}
    return {"status": "tables_unverified", "message": "取得 HTML 表格，但尚未驗證公告日期欄位",
            "table_count": len(frames),
            "table_headers": [list(map(str, frame.columns))[:12] for frame in frames[:3]],
            "response_chars": len(body), **diagnostic}
