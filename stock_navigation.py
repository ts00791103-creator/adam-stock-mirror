"""Single-stock navigation with symbol-scoped pricing and preserved scan state."""
import hashlib
import re
import math
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
    state["analysis_jump_top"]=True
    state["analysis_jump_sequence"]=state.get("analysis_jump_sequence",0)+1
    try:
        official_close=float(row.get("官方收盤"))
        if not math.isfinite(official_close) or official_close<=0:official_close=None
    except (TypeError,ValueError):official_close=None
    state["stock_analysis_request"]={"symbol":symbol,"name":str(row.get("名稱","")),
                                    "screen_date":str(row.get("資料日期") or row.get("官方行情日期") or ""),
                                    "official_date":str(row.get("官方行情日期") or ""),"official_close":official_close,
                                    "screen_stage":"一年日K複選" if "符合" in row else "官方每日行情初選（尚未複選）"}


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
    context=state.get("analysis_context",{})
    if context and str(state.get("adam_stock_query","")).strip()!=context["symbol"].split(".")[0]:
        state.pop("analysis_context",None)
    return request


def preserve_scanner_inputs(state):
    # Keep only normal input widgets, never assign button/file/dataframe state.
    for key in SCANNER_INPUTS:
        if key in state:
            state[key]=state[key]


def return_to_results():
    st.session_state["analysis_page_open"]=False
    st.session_state["results_jump_top"]=True
    st.session_state["analysis_jump_sequence"]=st.session_state.get("analysis_jump_sequence",0)+1
    st.session_state["stock_result_epoch"]=st.session_state.get("stock_result_epoch",0)+1


def stock_result_table(frame, rows, key, production=False, analysis_options=None):
    if production:
        st.dataframe(frame,hide_index=True,use_container_width=True)
        return
    snapshot=[dict(r) for r in rows]
    identity="|".join(str(r.get("Yahoo代號"))+str(r.get("資料日期",r.get("官方行情日期",""))) for r in snapshot)
    widget_key=key+"_"+hashlib.sha256(identity.encode()).hexdigest()[:12]+"_"+str(st.session_state.get("stock_result_epoch",0))
    def picked():
        event=st.session_state.get(widget_key,{})
        selection=event.get("selection",{})
        cells=selection.get("cells",[])
        selected=[cells[0][0]] if len(cells)==1 else selection.get("rows",[])
        if len(selected)==1 and 0 <= selected[0] < len(snapshot):
            queue_analysis(st.session_state,snapshot[selected[0]])
    options=analysis_options or {}
    period,interval=options.get("period","10y"),options.get("interval","1d")
    if analysis_options:
        from analysis_availability import availability_label
        frame=frame.copy()
        frame["個股分析資料可用性（所選期間）"]=[availability_label(st.session_state,r["Yahoo代號"],period,interval) for r in snapshot]
    st.caption("點選股票列可跳轉正確個股，再檢查所選期間資料。初選／一年複選成功，不代表十年資料可分析；可先核對再開啟。")
    st.dataframe(frame,hide_index=True,width="stretch",key=widget_key,
                 on_select=picked,selection_mode=["single-row","single-cell"])
    symbols=[r["Yahoo代號"] for r in snapshot]
    lookup={r["Yahoo代號"]:r for r in snapshot}
    choice_label="初選名單個股（全部可搜尋）" if key=="market_first_results" else "選擇個股（全部結果可搜尋）"
    chosen=st.selectbox(choice_label,symbols,
                        format_func=lambda s:f"{s.split('.')[0]} {lookup[s].get('名稱','')}（{s}）",
                        key=key+"_stock_choice")
    if analysis_options:
        from analysis_availability import (inspect_history,save_availability,failed_history,
                                           availability_label,availability_key,show_availability)
        st.caption("所選期間："+interval+"／"+period+"｜"+availability_label(st.session_state,chosen,period,interval))
        if options.get("loader") and st.button("先核對所選期間資料",key=key+"_preflight"):
            try:
                with st.spinner("核對完整所選期間，保留品質閘門…"):
                    report=inspect_history(chosen,period,interval,options["loader"](chosen,period,interval),options["auditor"])
            except Exception as exc:report=failed_history(chosen,period,interval,exc)
            save_availability(st.session_state,report)
            st.rerun()
        report=st.session_state.get("analysis_availability",{}).get(availability_key(chosen,period,interval))
        if report:
            show_availability(st,report)
            st.caption("以上為該次核對結果；實際開啟時仍重新執行品質檢查。")
    st.button("開啟所選個股分析",key=key+"_selected_open",on_click=queue_analysis,
              args=(st.session_state,lookup[chosen]),use_container_width=True)
    if len(snapshot)>30:
        return
    with st.expander("逐檔開啟分析（手機可用）"):
        for row in snapshot[:30]:
            symbol=str(row.get("Yahoo代號",""))
            label=f"{symbol.split('.')[0]} {row.get('名稱','')}｜開啟分析"
            st.button(label,key=key+"_open_"+symbol,on_click=queue_analysis,
                      args=(st.session_state,row),use_container_width=True)
        if len(snapshot)>30:
            st.caption("逐檔按鈕顯示前30檔，其餘股票可直接點選表格列。")

def scroll_main_to_top(nonce=0,target=""):
    import streamlit.components.v1 as components
    selector=".st-key-"+target if target in ("stock_results_panel","candidate_analysis_heading") else ""
    import json
    components.html("""<script>
    // navigation sequence """+str(int(nonce))+"""
    const main = window.parent.document.querySelector('[data-testid="stMain"]');
    const selector = """+json.dumps(selector)+""";
    if (main) {
        const move = () => {
          const anchor=selector?window.parent.document.querySelector(selector):null;
          const top=anchor?main.scrollTop+anchor.getBoundingClientRect().top-main.getBoundingClientRect().top-65:0;
          main.scrollTo({top:Math.max(0,top),behavior:"auto"});
        };
        requestAnimationFrame(move);
        setTimeout(move, 250);
    }
    </script>""",height=0,scrolling=False)
