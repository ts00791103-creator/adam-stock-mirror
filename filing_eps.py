"""Validate a user-provided quarterly EPS history with actual publication dates.
Expected CSV columns: quarter_end, announced_on, eps, symbol.
eps must be SINGLE-quarter EPS, not cumulative YTD EPS.
"""
import io
import pandas as pd

def parse_quarterly_eps_csv(upload, expected_symbol):
    try:
        data = pd.read_csv(io.BytesIO(upload), encoding="utf-8-sig")
        required = {"quarter_end", "announced_on", "eps", "symbol"}
        if not required.issubset(data.columns):
            return None, "缺少欄位：quarter_end, announced_on, eps, symbol"
        stock_id = str(expected_symbol).split(".")[0]
        if len(data) < 8 or len(data) > 120:
            return None, "需要 8～120 季的季度 EPS"
        if not data["symbol"].astype(str).str.strip().eq(stock_id).all():
            return None, "CSV 股票代號與目前查詢股票不同"
        data["quarter_end"] = pd.to_datetime(data["quarter_end"], errors="coerce")
        data["announced_on"] = pd.to_datetime(data["announced_on"], errors="coerce")
        data["eps"] = pd.to_numeric(data["eps"], errors="coerce")
        if data[["quarter_end", "announced_on", "eps"]].isna().any().any():
            return None, "日期或 EPS 欄位有無效值"
        if (data["announced_on"] < data["quarter_end"]).any():
            return None, "公告日期不可早於季末"
        if (data["announced_on"] > pd.Timestamp.now()).any():
            return None, "公告日期不可在未來"
        data = data.sort_values("quarter_end")
        if data["quarter_end"].dt.to_period("Q").duplicated().any():
            return None, "同一季度重複"
        periods = data["quarter_end"].dt.to_period("Q").tolist()
        if any(b.ordinal-a.ordinal != 1 for a,b in zip(periods[:-1],periods[1:])):
            return None, "季度資料不連續，禁止計算 TTM"
        if not data["quarter_end"].dt.is_quarter_end.all():
            return None, "quarter_end 必須是實際季度末日"
        return data, None
    except Exception:
        return None, "CSV 讀取失敗；請確認 UTF-8 格式及欄位"

def historical_pe_from_filings(symbol, data, years=3):
    import yfinance as yf
    prices = yf.Ticker(symbol).history(period=f"{max(5,years+2)}y", interval="1d", auto_adjust=False)["Close"].dropna()
    if prices.empty:
        return None, "無法取得歷史股價"
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    values = []
    for date, price in prices.items():
        available = data.loc[data["announced_on"] <= date]
        if len(available) < 4:
            continue
        ttm = float(available.tail(4)["eps"].sum())
        if ttm <= 0:
            continue
        pe = float(price)/ttm
        if 0 < pe <= 200:
            values.append((date,pe))
    if not values:
        return None, "沒有可用的公告後四季 EPS 樣本"
    last_date = prices.index[-1]
    recent = [(d,p) for d,p in values if d >= last_date-pd.DateOffset(years=years)]
    if len(recent) < 30:
        return None, "有效樣本少於 30 個交易日"
    ps = pd.Series([p for d,p in recent])
    q = [float(ps.quantile(x)) for x in (.2,.5,.8)]
    if not q[0]<q[1]<q[2]:
        return None, "PE 分位數無法區分"
    coverage = (recent[-1][0]-recent[0][0]).days
    spread = (q[2]-q[0])/q[1]
    warnings = []
    if len(data)<12: warnings.append("季 EPS 少於12季")
    if coverage<730: warnings.append("有效樣本不足兩年")
    if spread<.15 or spread>1: warnings.append("PE 分布過窄或過寬")
    if (last_date-data["announced_on"].max()).days>180: warnings.append("財報公告距最新股價超過180天")
    return {"pes":q,"samples":len(recent),"coverage_days":coverage,
            "warnings":warnings,"spread":spread,"start":str(recent[0][0].date()),
            "end":str(recent[-1][0].date()),"eps_quarters":len(data),
            "eps_first":str(data["quarter_end"].iloc[0].date()),
            "eps_last":str(data["quarter_end"].iloc[-1].date()),
            "method":"使用 CSV 實際公告日（資料由使用者提供，未經官方驗證）"},None

def parse_cumulative_eps_csv(upload, expected_symbol):
    """Convert officially reported year-to-date EPS into standalone quarters.
    Columns: symbol,quarter_end,announced_on,cumulative_eps.
    All four quarters must be present for each converted full year; missing
    preceding quarter is rejected rather than silently treating YTD as Q EPS.
    """
    try:
        frame = pd.read_csv(io.BytesIO(upload), encoding="utf-8-sig")
        needed = {"symbol", "quarter_end", "announced_on", "cumulative_eps"}
        if not needed.issubset(frame.columns):
            return None, "累計 EPS CSV 需包含 symbol,quarter_end,announced_on,cumulative_eps"
        if not frame["symbol"].astype(str).str.strip().eq(str(expected_symbol).split(".")[0]).all():
            return None, "股票代號不符"
        frame["quarter_end"] = pd.to_datetime(frame["quarter_end"], errors="coerce")
        frame["announced_on"] = pd.to_datetime(frame["announced_on"], errors="coerce")
        frame["cumulative_eps"] = pd.to_numeric(frame["cumulative_eps"], errors="coerce")
        if frame[["quarter_end","announced_on","cumulative_eps"]].isna().any().any():
            return None, "日期或累計 EPS 有無效值"
        if len(frame)<8 or len(frame)>120:
            return None, "至少需 8 季、最多 120 季"
        frame = frame.sort_values("quarter_end").reset_index(drop=True)
        if not frame["quarter_end"].dt.is_quarter_end.all():
            return None, "季度末日不正確"
        if frame["quarter_end"].dt.to_period("Q").duplicated().any():
            return None, "有重複季度"
        if (frame["announced_on"] < frame["quarter_end"]).any() or (frame["announced_on"] > pd.Timestamp.now()).any():
            return None, "公告日期早於季末或晚於今天"
        periods = frame["quarter_end"].dt.to_period("Q").tolist()
        if any(b.ordinal-a.ordinal!=1 for a,b in zip(periods[:-1],periods[1:])):
            return None, "季度不連續，無法可靠換算單季 EPS"
        quarters = []
        for _, row in frame.iterrows():
            quarter = int(row["quarter_end"].quarter)
            if quarter==1:
                quarters.append(float(row["cumulative_eps"]))
            else:
                prev = frame.loc[frame["quarter_end"] == row["quarter_end"] - pd.offsets.QuarterEnd(1)]
                if len(prev)!=1:
                    return None, "缺少同年度前一季累計 EPS"
                quarters.append(float(row["cumulative_eps"])-float(prev.iloc[0]["cumulative_eps"]))
        out = frame[["symbol","quarter_end","announced_on"]].copy()
        out["eps"] = quarters
        return parse_quarterly_eps_csv(out.to_csv(index=False).encode("utf-8-sig"), expected_symbol)
    except Exception:
        return None, "累計 EPS 換算失敗，請核對 CSV 格式"
