"""Official TWSE historical daily P/E ratios (BWIBBU); listed stocks only."""
import datetime as dt
import time
import requests
import pandas as pd

def official_twse_pe(symbol, years=3):
    code = str(symbol).split(".")[0]
    if not str(symbol).endswith(".TW") or not code.isdigit():
        return None, "證交所歷史 PE 僅支援上市股票（.TW）"
    today = pd.Timestamp.now(tz="Asia/Taipei").normalize().tz_localize(None)
    rows = []
    deadline = time.monotonic() + 14
    failures = 0
    completed = 0
    session = requests.Session()
    session.headers.update({"User-Agent":"Mozilla/5.0 (compatible; AdamStockResearch/1.0)"})
    for offset in range(years*12+1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, "歷史 PE 讀取超時，月份尚未讀取完整；不使用部分月份估價"
        month = today.to_period("M")-offset
        date = f"{month.year}{month.month:02d}01"
        try:
            response = session.get("https://www.twse.com.tw/exchangeReport/BWIBBU",
                                   params={"response":"json","date":date,"stockNo":code}, timeout=min(5, max(.1, remaining / 2)))
            response.raise_for_status()
            body = response.json()
            completed += 1
            failures = 0
            fields = body.get("fields",[])
            data = body.get("data",[])
            pe_index = next((i for i,f in enumerate(fields) if "本益比" in f),None)
            date_index = next((i for i,f in enumerate(fields) if "日期" in f),None)
            if pe_index is None or date_index is None: continue
            for row in data:
                raw_date = str(row[date_index]).strip()
                parts = raw_date.split("/")
                if len(parts)!=3: continue
                day = pd.Timestamp(int(parts[0])+1911,int(parts[1]),int(parts[2]))
                raw_pe = str(row[pe_index]).replace(",","").strip()
                try: pe = float(raw_pe)
                except ValueError: continue
                if 0<pe<=200 and day<=today:
                    rows.append((day,pe))
        except (requests.RequestException, ValueError, TypeError, KeyError):
            failures += 1
            if failures >= 2:
                return None, "證交所歷史 PE 連續讀取失敗；請稍後重試，不使用部分月份估價"
    if completed != years*12+1:
        return None, "歷史 PE 有月份連線失敗，不使用不完整資料估價"
    if not rows:
        return None, "證交所目前未回傳可用歷史 PE（可能是 API 暫時無法連線或非上市股票）"
    series = pd.Series({d:p for d,p in rows}).sort_index()
    series = series.loc[series.index>=today-pd.DateOffset(years=years)]
    if len(series)<30:
        return None, f"證交所有效 PE 僅 {len(series)} 日，未達 30 日"
    q=[float(series.quantile(p)) for p in (.2,.5,.8)]
    if not q[0]<q[1]<q[2]: return None,"官方 PE 分位數無法區分"
    coverage=(series.index[-1]-series.index[0]).days
    warnings=[]
    if coverage<years*365*.8: warnings.append("官方 PE 有效資料跨度不足")
    if len(series)<250: warnings.append("官方 PE 有效交易日不足 250 日")
    if (today-series.index[-1]).days>20: warnings.append("最新官方 PE 超過 20 天")
    spread=(q[2]-q[0])/q[1]
    if spread<.15 or spread>1: warnings.append("PE 分布過窄或過寬")
    return {"pes":q,"samples":len(series),"coverage_days":coverage,
            "warnings":warnings,"spread":spread,
            "start":str(series.index[0].date()),"end":str(series.index[-1].date()),
            "eps_quarters":0,"eps_first":"官方本益比未附季度 EPS","eps_last":"官方本益比未附季度 EPS",
            "method":"臺灣證券交易所 BWIBBU 官方歷史本益比（使用當日官方揭露值；未獨立重建 EPS 公告日）"},None
