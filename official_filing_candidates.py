"""Read candidate financial-report announcements from TWSE's company page.

The page can be JavaScript-rendered or limited to recent filings. Missing data
must remain missing. Duplicate announcements require manual adjudication.
"""
import io
import re
import requests
import pandas as pd

BASE = "https://www.twse.com.tw/IIH2/zh/company/information.html"


def fetch_official_filing_candidates(stock_code, timeout=12):
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{4,5}", code):
        return [], "股票代號格式錯誤"
    url = f"{BASE}?code={code}"
    try:
        response = requests.get(BASE, params={"code": code}, timeout=timeout,
                                headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        frames = pd.read_html(io.StringIO(response.text))
    except requests.RequestException:
        return [], "證交所網站連線失敗，請稍後再試"
    except (ValueError, ImportError):
        return [], "官方頁面沒有可直接讀取的 HTML 表格；可能由 JavaScript 動態載入"
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
