"""Candidate-only availability, distinct from initial and one-year screening."""
import hashlib
import pandas as pd
from quote_quality import invalid_price_rows


def availability_key(symbol, period, interval):
    return f"{symbol}|{period}|{interval}"


def inspect_history(symbol, period, interval, frame, auditor):
    result = {"symbol": symbol, "period": period, "interval": interval,
              "checked_at": pd.Timestamp.now(tz="Asia/Taipei").isoformat(),
              "source": "Yahoo auto_adjust=False；歷史價格可能含供應商回溯調整",
              "status": "unconfirmed", "issues": [], "invalid_rows": [], "bars": 0}
    if frame.empty:
        result.update(status="empty", issues=["完整請求未取得資料"])
        return result
    result.update(bars=len(frame), first=str(frame.index[0]), last=str(frame.index[-1]))
    result["issues"] = list(auditor(frame))
    result["invalid_rows"] = invalid_price_rows(frame, limit=20)
    result["status"] = "blocked" if result["issues"] else "available"
    verification = frame.attrs.get("official_close_verification")
    if verification:
        result["official_verified_closes"] = len(verification["ledger"])
        result["original_invalid_dates"] = verification["raw_invalid_dates"]
        result["source"] += "；列出的異常收盤另經官方月表與除息前收盤價核對，原始資料保留"
    columns = [c for c in ("Open", "High", "Low", "Close") if c in frame]
    result["price_frame_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(frame[columns], index=True).values.tobytes()).hexdigest()
    return result


def save_availability(state, result):
    cache = dict(state.get("analysis_availability", {}))
    cache[availability_key(result["symbol"], result["period"], result["interval"])] = dict(result)
    state["analysis_availability"] = cache


def failed_history(symbol, period, interval, exc):
    return {"symbol": symbol, "period": period, "interval": interval, "status": "download_failed",
            "issues": [f"{type(exc).__name__}: {str(exc)[:180]}"], "bars": 0,
            "checked_at": pd.Timestamp.now(tz="Asia/Taipei").isoformat(), "invalid_rows": []}


def availability_label(state, symbol, period, interval):
    report = state.get("analysis_availability", {}).get(availability_key(symbol, period, interval))
    suffix = f"{interval}／{period}"
    if report is None:
        return f"尚未核對（{suffix}）"
    if report["status"] == "available":
        return f"上次核對價格品質通過（{suffix}）"
    reason = "；".join(report.get("issues", []))
    return f"上次未通過／未判定（{suffix}）：{reason}"


def show_availability(st, report, navigation=False):
    if navigation:
        st.success(f"個股導航成功：{report['symbol']}；初選成功與資料可分析是不同狀態。")
    request = f"{report['symbol']}｜{report['interval']}／{report['period']}"
    if report["status"] == "available":
        st.info("所選期間資料可分析：價格品質檢查通過｜" + request)
    else:
        st.error("所選期間資料可分析：未通過／未判定｜" + request)
        st.caption("原因：" + "；".join(report.get("issues", [])))
    if report.get("bars"):
        st.caption(f"完整請求回傳 {report['bars']} 根｜實際範圍：{report['first']} ～ {report['last']}。未縮短期間或刪除異常K線。")
    st.caption("核對時間："+report.get("checked_at","")+"；價格品質通過不代表所有指標均有足量資料，實際開啟仍重新檢查。")
    if report["status"] == "blocked":
        st.warning("目前尚無可確認價格基準一致的完整行情，鏡像分析保持停止。請返回選股結果查看其他股票；一年複選成功不代表十年資料可分析。")
