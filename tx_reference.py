"""Manual TX research references. No quotes, signal generation, or stock scoring."""
import copy
import csv
import io
import math
from urllib.parse import urlparse

TX_MARKET = "台指期 TX（官方 CSV）"
SOURCE = "https://www.youtube.com/watch?v=iCbMHLc3oUM&t=3235s"
EXAMPLES = (
    {"id": "video-day", "period": "日K", "direction": "空方", "target": 41216,
     "invalidation": 45624},
    {"id": "video-hour-1", "period": "60分K", "direction": "空方", "target": 42839,
     "invalidation": 44107},
    {"id": "video-hour-2", "period": "60分K", "direction": "空方", "target": 40719,
     "invalidation": 44107},
)


def enabled(market, production=False):
    return not production and market == TX_MARKET


def validate_reference(item):
    result = copy.deepcopy(item)
    if result.get("period") not in ("日K", "60分K"):
        raise ValueError("僅支援日K或60分K參考")
    if result.get("direction") not in ("多方", "空方"):
        raise ValueError("請選擇多方或空方")
    for key in ("target", "invalidation"):
        try:
            value = float(result[key])
        except (KeyError, TypeError, ValueError):
            raise ValueError("目標與失效價須為正數") from None
        if not math.isfinite(value) or value <= 0:
            raise ValueError("目標與失效價須為有限正數")
        result[key] = value
    if ((result["direction"] == "空方" and result["target"] >= result["invalidation"])
            or (result["direction"] == "多方" and result["target"] <= result["invalidation"])):
        raise ValueError("目標與失效價的方向關係不一致")
    source = str(result.get("source", "")).strip()
    parsed = urlparse(source)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError("請填寫可核對的來源網址")
    result["source"] = source
    # Manual entry never grants verification or current validity.
    result["status"] = "待核對（不判定現行有效）"
    return result


def example_references():
    return [validate_reference({**item, "source": SOURCE,
        "context": "歷史案例；原訊息日期、契約月份、日夜盤、換月還原口徑未核對",
        "note": ("60分K兩點後共列同一失效價，是否各自另有條件待確認"
                 if item["period"] == "60分K" else "失效須何種收盤及幾根確認，尚未核對")})
        for item in EXAMPLES]


def reference_rows(items):
    return [{"週期": x["period"], "方向": x["direction"], "目標參考": x["target"],
        "失效參考": x["invalidation"], "核對狀態": x["status"],
        "資料口徑": x.get("context", "未核對"), "備註": x.get("note", ""),
        "來源": x["source"]} for x in map(validate_reference, items)]


def export_csv(items):
    rows = reference_rows(items)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["核對狀態"])
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + output.getvalue()


def show_tx_reference(st, market, production=False):
    if not enabled(market, production):
        return
    with st.expander("台指期｜亞當點位參考（人工來源）", expanded=True):
        st.caption("僅供台指期研究；不套用個股、加權指數或選股評分。與自動鏡像分開。")
        st.warning("以下為影片展示的歷史案例，不是目前有效訊號。未核對原訊息日期、契約與日夜盤、換月還原，暫不自動判定達標或失效，也不疊入目前K線。")
        st.markdown("[查看影片 53:55 的點位來源](" + SOURCE + ")")
        st.caption("影片無逐字稿；目前依可見畫面記錄。日K與60分K須各自核對；本站官方TX日K不能替代60分K收盤判斷。")
        custom = st.session_state.setdefault("tx_manual_references_v1", [])
        items = example_references() + list(custom)
        st.dataframe(reference_rows(items), hide_index=True, use_container_width=True)
        st.download_button("下載台指期參考點位CSV", export_csv(items),
                           "adam_tx_manual_references.csv", "text/csv")
        with st.expander("新增自己的台指期參考點"):
            st.caption("新增後仍標為待核對。僅保存在本次瀏覽器工作階段，請下載CSV備份；不發送推播。")
            with st.form("tx_manual_reference_form", clear_on_submit=False):
                period = st.selectbox("參考點週期", ["日K", "60分K"])
                direction = st.selectbox("參考點方向", ["空方", "多方"])
                target = st.number_input("目標參考價", min_value=1.0, value=40000.0, step=1.0)
                invalidation = st.number_input("失效參考價", min_value=1.0, value=44000.0, step=1.0)
                source = st.text_input("來源網址")
                context = st.text_input("原訊息日期、契約、時段及價格口徑（未知請填未核對）", value="未核對")
                submitted = st.form_submit_button("加入台指期參考")
            if submitted:
                try:
                    record = validate_reference({"period": period, "direction": direction,
                        "target": target, "invalidation": invalidation, "source": source,
                        "context": context, "note": "使用者手動參考；非程式計算"})
                    if len(custom) >= 30:
                        raise ValueError("本次最多保存30筆自訂參考，請先下載備份")
                    custom.append(record)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
