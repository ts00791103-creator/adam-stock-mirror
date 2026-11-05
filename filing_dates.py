"""Conservative validation of candidate financial filing dates.

A syntactically valid date and URL are NOT proof of official publication.
No output from this module authorizes historical point-in-time PE.
"""
from datetime import date, datetime
from calendar import monthrange
from urllib.parse import urlparse
import re


def inspect_filing_date(stock_code, quarter, announced_at, source_url, expected_stock_code):
    code = str(stock_code).strip()
    period = str(quarter).strip().upper()
    value = str(announced_at).strip()
    source = str(source_url).strip()
    if code != str(expected_stock_code).strip() or not re.fullmatch(r"\d{4}Q[1-4]", period):
        return "股票代號或季度不符"
    year, q = int(period[:4]), int(period[-1])
    if not value:
        return "缺少公告日期"
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            moment = datetime.strptime(value, "%Y/%m/%d")
        except ValueError:
            return "公告日期格式錯誤"
    month = q * 3
    quarter_end = date(year, month, monthrange(year, month)[1])
    if moment.date() <= quarter_end:
        return "公告日不得早於或等於季度結束日"
    if moment.date() > date.today():
        return "公告日期在未來"
    parsed = urlparse(source)
    if parsed.scheme != "https" or not parsed.hostname or not (
        parsed.hostname == "twse.com.tw" or parsed.hostname.endswith(".twse.com.tw")
        or parsed.hostname == "mops.twse.com.tw" or parsed.hostname.endswith(".mops.twse.com.tw")
        or parsed.hostname == "mopsov.twse.com.tw"
    ):
        return "缺少可核對的官方來源網址"
    return "格式通過，官方來源內容仍待核實（不可用於歷史 PE）"
