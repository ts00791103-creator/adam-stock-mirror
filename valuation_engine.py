"""Historical PE valuation with conservative availability lag; test branch only."""
import pandas as pd
import yfinance as yf

def historical_pe_bands(symbol, years=3):
    """Use trailing four reported quarterly EPS, available only after 75-day lag.
    Proxy reporting lag is conservative but not actual filing date.
    """
    ticker = yf.Ticker(symbol)
    income = ticker.quarterly_income_stmt
    if income is None or income.empty:
        return None, "缺少季報損益資料"
    names = ["Diluted EPS", "Basic EPS"]
    row = next((n for n in names if n in income.index), None)
    if row is None:
        return None, "季報未提供每股盈餘"
    eps = pd.to_numeric(income.loc[row], errors="coerce")
    eps.index = pd.to_datetime(eps.index).tz_localize(None)
    eps = eps.sort_index().dropna()
    if len(eps) < 4:
        return None, "有效季度 EPS 少於四季"
    daily = ticker.history(period=f"{max(years+2,5)}y", interval="1d", auto_adjust=False)
    if daily is None or daily.empty:
        return None, "缺少歷史收盤價"
    prices = daily["Close"].dropna()
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    values = []
    for date, price in prices.items():
        available = eps.loc[eps.index + pd.Timedelta(days=75) <= date]
        if len(available) < 4:
            continue
        ttm = float(available.iloc[-4:].sum())
        if ttm <= 0:
            continue
        pe = float(price) / ttm
        if 0 < pe <= 200:
            values.append((date, pe))
    if len(values) < 30:
        return None, "可用歷史本益比樣本不足（至少30個交易日）"
    latest_date = prices.index[-1]
    recent = [pe for date, pe in values if date >= latest_date - pd.DateOffset(years=years)]
    if len(recent) < 30:
        return None, "近年本益比樣本不足"
    s = pd.Series(recent)
    q = [float(s.quantile(p)) for p in (0.2, 0.5, 0.8)]
    if not q[0] < q[1] < q[2]:
        return None, "歷史本益比分位數無法有效區分"
    coverage_days = (max(d for d,p in values if d >= latest_date - pd.DateOffset(years=years)) - min(d for d,p in values if d >= latest_date - pd.DateOffset(years=years))).days
    spread = (q[2] - q[0]) / q[1]
    warnings = []
    if len(eps) < 8:
        warnings.append("季 EPS 少於 8 季，歷史獲利涵蓋不足")
    if coverage_days < 365:
        warnings.append("有效 PE 樣本期間不足一年")
    if spread < 0.15:
        warnings.append("歷史 PE 分位區間過度集中")
    if spread > 1.0:
        warnings.append("歷史 PE 波動過大")
    return {"pes": q, "samples": len(recent), "coverage_days": coverage_days, "warnings": warnings, "spread": spread, "start": str(latest_date - pd.DateOffset(years=years))[:10],
            "end": str(latest_date)[:10], "eps_quarters": len(eps),
            "method": "季 EPS 累計四季；季末後75天視為可用（非實際公告日）"}, None

def eps_growth_reference(symbol):
    """YoY change in latest reported trailing-four-quarter EPS, not a forecast."""
    try:
        income = yf.Ticker(symbol).quarterly_income_stmt
        row = next((n for n in ("Diluted EPS", "Basic EPS") if n in income.index), None)
        if row is None:
            return None, "找不到季 EPS"
        eps = pd.to_numeric(income.loc[row], errors="coerce").dropna()
        eps.index = pd.to_datetime(eps.index)
        eps = eps.sort_index()
        if len(eps) < 8:
            return None, "不足八季 EPS，無法計算近四季年增率"
        recent = float(eps.iloc[-4:].sum())
        prior = float(eps.iloc[-8:-4].sum())
        if recent <= 0 or prior <= 0:
            return None, "歷史 EPS 非正值，成長率不適用"
        return {"growth_pct": (recent / prior - 1) * 100,
                "recent_ttm": recent, "prior_ttm": prior,
                "quarter_end": str(eps.index[-1].date()),
                "source": "Yahoo Finance quarterly_income_stmt；近四季與前四季比較"}, None
    except Exception:
        return None, "季 EPS 來源暫時不可用"


def valuation_quality(pe_result, current_pe, growth_result=None):
    """Explainable heuristic quality rating; not predictive accuracy."""
    reasons = []
    if pe_result is None:
        return "低", ["歷史本益比資料不可用"]
    score = 0
    if pe_result["samples"] >= 250:
        score += 1
    else:
        reasons.append("歷史樣本少於 250 個交易日")
    if pe_result["coverage_days"] >= 730:
        score += 1
    else:
        reasons.append("有效樣本跨度少於兩年")
    if pe_result["eps_quarters"] >= 12:
        score += 1
    else:
        reasons.append("季 EPS 少於 12 季")
    if 0.15 <= pe_result["spread"] <= 1.0:
        score += 1
    else:
        reasons.append("本益比分布過窄或過寬")
    low, _, high = pe_result["pes"]
    if low * 0.8 <= current_pe <= high * 1.2:
        score += 1
    else:
        reasons.append("目前 PE 明顯偏離歷史分布")
    if growth_result is None:
        reasons.append("缺少可核對的 EPS 年增率")
    return ("高" if score == 5 and growth_result else "中" if score >= 3 else "低"), reasons


def conservative_entry(eps, pe_result, margin_pct=25):
    """Conservative reference only: lower of historical 20th PE and median PE discounted."""
    if eps <= 0 or pe_result is None:
        return None
    low, median, _ = pe_result["pes"]
    return eps * min(low, median * (1 - margin_pct / 100))
