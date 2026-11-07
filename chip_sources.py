"""Dated official institutional and margin records; shares vs lots stay explicit."""
import re
import requests
from market_universe import number, trading_date


def read(url, params=None):
    response=requests.get(url,params=params,timeout=8,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    response.raise_for_status()
    return response.json()


def parse_institution(body, exchange, day, source):
    if exchange=="上市":
        if trading_date(body.get("date","")) != day or body.get("stat")!="OK":
            raise ValueError("上市法人日期不同或資料尚未公布")
        fields=body.get("fields",[])
        records=[dict(zip(fields,row)) for row in body.get("data",[]) if len(row)==len(fields)]
        names=("證券代號","外陸資買賣超股數(不含外資自營商)","投信買賣超股數","自營商買賣超股數","三大法人買賣超股數")
    else:
        if not isinstance(body,list):
            raise ValueError("上櫃法人格式無法辨識")
        records=body
        names=("SecuritiesCompanyCode","Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference",
               "SecuritiesInvestmentTrustCompanies-Difference","Dealers-Difference","TotalDifference")
    found={}
    for row in records:
        code=str(row.get(names[0],"")).strip()
        if not re.fullmatch(r"[1-9][0-9]{3}",code):
            continue
        try:
            row_day=day if exchange=="上市" else trading_date(row.get("Date",""))
            if row_day!=day: continue
            vals=[number(row[k]) for k in names[1:]]
            if abs(sum(vals[:3])-vals[3])>1: continue
            if code in found: raise ValueError("法人代號重複")
            found[code]=dict(zip(("foreign","trust","dealer","net"),vals),date=row_day,source=source)
        except (KeyError,TypeError,ValueError):
            continue
    if not found: raise ValueError("沒有可核對日期與合計的法人明細")
    return found


def fetch_institution(exchange, day):
    if exchange=="上市":
        url="https://www.twse.com.tw/rwd/zh/fund/T86"
        body=read(url,{"response":"json","date":day.replace("-",""),"selectType":"ALLBUT0999"})
    else:
        url="https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"
        body=read(url)
    return parse_institution(body,exchange,day,url)


def parse_margin(body, exchange, day, source):
    # An undated latest OpenAPI response is not sufficient for a dated join.
    if not isinstance(body,dict) or trading_date(body.get("date",""))!=day:
        raise ValueError("融資資料缺少可核對的日期")
    tables=body.get("tables",[])
    if "fields" in body and "data" in body:
        tables=tables+[body]
    found={}
    for table in tables:
        fields=table.get("fields",[])
        if exchange=="上櫃":
            keys=("代號","前資餘額(張)","資餘額")
        elif "融資前日餘額" in fields and "融資今日餘額" in fields:
            keys=("股票代號","融資前日餘額","融資今日餘額")
        elif "股票代號" in fields and fields.count("前日餘額")==2 and fields.count("今日餘額")==2:
            # TWSE MI_MARGN publishes financing first, short balances second.
            groups=table.get("groups",[])
            if not any("融資" in str(g.get("title","")) for g in groups): continue
            keys=("股票代號","前日餘額","今日餘額")
        else:
            continue
        if not all(k in fields for k in keys): continue
        indices=[fields.index(k) for k in keys]
        for row in table.get("data",[]):
            try:
                code=str(row[indices[0]]).strip()
                if not re.fullmatch(r"[1-9][0-9]{3}",code): continue
                previous,current=number(row[indices[1]]),number(row[indices[2]])
                if min(previous,current)<0: continue
                if code in found: raise ValueError("融資代號重複")
                found[code]={"date":day,"previous":previous,"balance":current,"source":source}
            except (IndexError,ValueError,TypeError):
                continue
    if not found: raise ValueError("沒有可辨識的融資張數，未使用未確認欄位")
    return found


def fetch_margin(exchange, day):
    if exchange=="上櫃":
        url="https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php"
        y,m,d=map(int,day.split("-"))
        body=read(url,{"l":"zh-tw","d":f"{y-1911}/{m:02d}/{d:02d}","o":"json"})
    else:
        url="https://www.twse.com.tw/exchangeReport/MI_MARGN"
        body=read(url,{"date":day.replace("-",""),"selectType":"ALL","response":"json"})
    return parse_margin(body,exchange,day,url)
