"""TWSE official current financial snapshot. NOT a historical EPS archive."""
import requests

ENDPOINTS = [
    "t187ap06_L_ci", "t187ap06_L_basi", "t187ap06_L_fh",
    "t187ap06_L_ins", "t187ap06_L_bd", "t187ap06_L_mim",
]
def fetch_twse_latest_eps(symbol, timeout=8):
    code = str(symbol).split(".")[0]
    if not code.isdigit() or not str(symbol).endswith(".TW"):
        return None, "目前僅支援上市股票（.TW）；上櫃或 ETF 尚未支援"
    errors = []
    for endpoint in ENDPOINTS:
        try:
            url = "https://openapi.twse.com.tw/v1/opendata/" + endpoint
            resp = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data,list):
                continue
            for record in data:
                if str(record.get("公司代號", "")).strip() != code:
                    continue
                keys = [k for k in record if "每股盈餘" in k or "基本每股" in k]
                if not keys:
                    return None, "官方資料存在，但沒有可辨識的 EPS 欄位"
                for key in keys:
                    try:
                        eps = float(str(record[key]).replace(",",""))
                    except (ValueError,TypeError):
                        continue
                    if eps <= 0:
                        return None, "官方累計 EPS 非正值，無法當作估價依據"
                    return {"eps":eps,"field":key,"source":url,
                            "period":{k:v for k,v in record.items() if any(x in k for x in ("年度","季別","季度","期間"))},
                            "note":"官方當期財報 EPS 可能為年初至今累計值，非近四季 TTM；禁止直接用作 TTM 歷史估價"},None
        except (requests.RequestException,ValueError) as exc:
            errors.append(type(exc).__name__)
    return None, "官方最新財報未找到可辨識 EPS（或服務暫時不可用）"
