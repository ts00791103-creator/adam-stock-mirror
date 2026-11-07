"""Single-stock navigation with symbol-scoped pricing and preserved scan state."""
import hashlib
import re
import streamlit as st

SCANNER_INPUTS = (
 "screen_list","screen_low","screen_high","screen_lots","screen_mode","screen_near","screen_window","screen_width","screen_choice",
 "market_scope","market_low","market_high","market_daily","market_avg","market_box","market_near","market_window","market_width","market_choice",
 "rank_scope","rank_low","rank_vol","rank_liquidity","rank_preset","rank_positive","rank_margin","rank_w1","rank_w2","rank_w3","rank_choice"
)


def queue_analysis(state, row):
    symbol=str(row.get("Yahoo代號","")).upper()
    if not re.fullmatch(r"[0-9]{4,6}\.(TW|TWO)",symbol):
        raise ValueError("無法確認個股代號與上市／上櫃市場")
    state["adam_stock_query"]=symbol.split(".")[0]
    state["stock_analysis_request"]={"symbol":symbol,"name":str(row.get("名稱","")),
                                    "screen_date":str(row.get("資料日期") or row.get("官方行情日期") or "")}


def reset_stock_pricing(state, symbol):
    if state.get("pricing_input_symbol")==symbol:
        return
    state["pricing_input_symbol"]=symbol
    state["b3_eps_source_v2"]="自動抓取近四季 EPS"
    state["b3_eps_manual_v2"]=0.
    state["b3_eps_period_manual_v2"]=""
    state["b3_auto_pe_v3"]=True
    state["b3_growth_on_v1"]=False
    state.pop("b3_filing_eps_csv_v1",None)


def consume_request(state):
    request=state.pop("stock_analysis_request",None)
    if request:
        state["adam_stock_query"]=request["symbol"].split(".")[0]
        state["adam_market"]="台灣股票／ETF"
        state["analysis_page_open"]=True
        state["analysis_context"]=request
        reset_stock_pricing(state,request["symbol"])
        state["b3_valuation_enabled_v1"]=True
    return request


def preserve_scanner_inputs(state):
    # Keep only normal input widgets, never assign button/file/dataframe state.
    for key in SCANNER_INPUTS:
        if key in state:
            state[key]=state[key]


def return_to_results():
    st.session_state["analysis_page_open"]=False


def stock_result_table(frame, rows, key, production=False):
    if production:
        st.dataframe(frame,hide_index=True,use_container_width=True)
        return
    snapshot=[dict(r) for r in rows]
    identity="|".join(str(r.get("Yahoo代號"))+str(r.get("資料日期",r.get("官方行情日期",""))) for r in snapshot)
    widget_key=key+"_"+hashlib.sha256(identity.encode()).hexdigest()[:12]
    def picked():
        event=st.session_state.get(widget_key,{})
        selected=event.get("selection",{}).get("rows",[])
        if len(selected)==1 and 0 <= selected[0] < len(snapshot):
            queue_analysis(st.session_state,snapshot[selected[0]])
    st.caption("點選股票列即可開啟線型、箱型與價格分析；也可展開下方逐檔按鈕。")
    st.dataframe(frame,hide_index=True,width="stretch",key=widget_key,
                 on_select=picked,selection_mode="single-row")
    with st.expander("逐檔開啟分析（手機可用）"):
        for row in snapshot[:30]:
            symbol=str(row.get("Yahoo代號",""))
            label=f"{symbol.split('.')[0]} {row.get('名稱','')}｜開啟分析"
            st.button(label,key=key+"_open_"+symbol,on_click=queue_analysis,
                      args=(st.session_state,row),use_container_width=True)
        if len(snapshot)>30:
            st.caption("逐檔按鈕顯示前30檔，其餘股票可直接點選表格列。")
