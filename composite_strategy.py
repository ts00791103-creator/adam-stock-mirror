"""Auditable rebound/volume/institution ranking, never a win probability."""
import math
import pandas as pd
from volume_profile_estimate import clean_bars


def price_factors(frame, day, low_window=20, volume_window=20):
    if not 5 <= low_window <= 250 or not 5 <= volume_window <= 250:
        raise ValueError("觀察根數需介於5至250")
    if len(frame) < max(low_window, volume_window+1, 6):
        raise ValueError("歷史日K不足")
    data = clean_bars(frame.tail(max(low_window, volume_window+1, 6)))
    if str(data.index[-1].date()) != str(day):
        raise ValueError("歷史日K與指定收盤日期不同")
    average = float(data.Volume.iloc[-volume_window-1:-1].mean())
    volume = float(data.Volume.iloc[-1])
    if average <= 0 or volume <= 0:
        raise ValueError("無有效當日成交量或前期均量")
    low = float(data.Low.tail(low_window).min())
    close = float(data.Close.iloc[-1])
    return {"收盤": close, "近低反彈%": (close/low-1)*100,
            "區間最低價": low, "量比": volume/average,
            "當日成交股數": volume, "前期平均成交股數": average,
            "收盤漲跌%": (close/float(data.Close.iloc[-2])-1)*100,
            "5日前日期": str(data.index[-6].date())}


def combine_factors(item, frame, chip, margin=None, baseline=None, low_window=20, volume_window=20):
    day = item["官方行情日期"]
    factors = price_factors(frame, day, low_window, volume_window)
    official_volume = float(item["官方當日成交量（張）"])*1000
    if official_volume <= 0 or abs(factors["當日成交股數"]/official_volume-1) > .05:
        raise ValueError("官方與歷史來源成交股數差異超過5%，不混用計算")
    if abs(factors["收盤"]/float(item["官方收盤"])-1) > .001:
        raise ValueError("官方與歷史收盤價不一致")
    if not chip or chip.get("date") != day:
        raise ValueError("法人資料缺漏或日期不同")
    values = [chip.get(k) for k in ("foreign", "trust", "dealer", "net")]
    if any(v is None or not math.isfinite(float(v)) for v in values):
        raise ValueError("法人買賣超欄位缺漏")
    foreign, trust, dealer, net = map(float, values)
    if abs(foreign+trust+dealer-net) > 1:
        raise ValueError("法人分項與合計無法對帳")
    row = {**item, **factors, "資料日期": day,
           "法人占比%": net/official_volume*100, "法人合計（張）": net/1000,
           "外資（張）": foreign/1000, "投信（張）": trust/1000, "自營商（張）": dealer/1000,
           "法人來源": chip["source"], "融資日增減（張）": None,
           "融資5日增減（張）": None, "融資來源": "", "融資日期": None, "融資5日前日期": None}
    if margin and margin.get("date") == day:
        current = float(margin["balance"])
        previous = float(margin["previous"])
        if not all(math.isfinite(v) and v >= 0 for v in (current, previous)):
            raise ValueError("融資餘額無效")
        row.update({"融資日增減（張）": current-previous, "融資來源": margin["source"], "融資日期": day})
        if baseline and baseline.get("date") == factors["5日前日期"]:
            old = float(baseline["balance"])
            if math.isfinite(old) and old >= 0:
                row.update({"融資5日增減（張）": current-old, "融資5日前日期": baseline["date"]})
    return row


def rank_rows(rows, weights=(40, 50, 10)):
    if len(weights) != 3 or any(not math.isfinite(float(w)) or w < 0 for w in weights) or abs(sum(weights)-100) > 1e-8:
        raise ValueError("三項權重須為非負且加總100%")
    if not rows:
        return []
    table = pd.DataFrame(rows).copy()
    if table["Yahoo代號"].duplicated().any() or table["資料日期"].nunique() != 1:
        raise ValueError("排名母體含重複股票或不同資料日期")
    columns = ["近低反彈%", "量比", "法人占比%"]
    if table[columns].isna().any().any() or not all(math.isfinite(float(x)) for x in table[columns].to_numpy().flat):
        raise ValueError("排名資料不完整；缺值不能補零")
    count = len(table)
    for column in columns:
        table[column+"百分位"] = (table[column].rank(method="average")-1)/(count-1)*100 if count > 1 else 50.
    table["綜合分"] = sum(table[c+"百分位"]*float(w)/100 for c,w in zip(columns, weights))
    table = table.sort_values(["綜合分","Yahoo代號"], ascending=[False,True], kind="stable").reset_index(drop=True)
    table.insert(0,"名次",table.index+1)
    return table.to_dict("records")


def margin_decliners(rows, period=1):
    column = "融資日增減（張）" if period == 1 else "融資5日增減（張）" if period == 5 else None
    if column is None:
        raise ValueError("融資期間只支援1或5日")
    valid = [r for r in rows if r.get(column) is not None and math.isfinite(float(r[column])) and r[column] < 0]
    return sorted(valid, key=lambda r:(r[column], r["Yahoo代號"]))
