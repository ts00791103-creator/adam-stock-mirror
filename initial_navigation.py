"""Open an official preliminary result in the production single-stock chart."""
import hashlib
import re
import streamlit as st


def queue_initial(state, row):
    symbol=str(row.get("Yahoo代號","")).upper()
    if not re.fullmatch(r"[0-9]{4,6}\.(TW|TWO)",symbol):
        raise ValueError("無法確認個股代號與上市／上櫃市場")
    state["adam_stock_query"]=symbol.split(".")[0]
    state["initial_chart_request"]={"symbol":symbol,"name":str(row.get("名稱","")),
                                    "date":str(row.get("官方行情日期",""))}
    state["initial_chart_sequence"]=state.get("initial_chart_sequence",0)+1
    state["initial_chart_jump"]=state["initial_chart_sequence"]


def consume_initial(state):
    request=state.pop("initial_chart_request",None)
    if request:
        state["adam_stock_query"]=request["symbol"].split(".")[0]
        state["initial_chart_open"]=True
        state["initial_chart_context"]=request
    context=state.get("initial_chart_context",{})
    if context and str(state.get("adam_stock_query","")).strip()!=context["symbol"].split(".")[0]:
        state.pop("initial_chart_context",None)
    return request


def back_to_initial():
    st.session_state["initial_chart_open"]=False
    st.session_state["initial_chart_sequence"]=st.session_state.get("initial_chart_sequence",0)+1
    st.session_state["initial_chart_jump"]=st.session_state["initial_chart_sequence"]
    st.session_state["initial_chart_epoch"]=st.session_state.get("initial_chart_epoch",0)+1


def selected_row(event, snapshot):
    selection=event.get("selection",{})
    cells=selection.get("cells",[])
    rows=[cells[0][0]] if len(cells)==1 else selection.get("rows",[])
    if len(rows)==1 and isinstance(rows[0],int) and 0<=rows[0]<len(snapshot):
        return snapshot[rows[0]]
    return None


def initial_result_table(frame, rows):
    snapshot=[dict(row) for row in rows]
    identity="|".join(str(r.get("Yahoo代號"))+str(r.get("官方行情日期")) for r in snapshot)
    key="initial_click_"+hashlib.sha256(identity.encode()).hexdigest()[:12]+"_"+str(st.session_state.get("initial_chart_epoch",0))
    def picked():
        row=selected_row(st.session_state.get(key,{}),snapshot)
        if row is not None:
            queue_initial(st.session_state,row)
    st.caption("點選股票名稱或代號，即可開啟該股線圖；初選尚未驗證20日均量與箱型。")
    st.dataframe(frame,hide_index=True,width="stretch",key=key,on_select=picked,
                 selection_mode=["single-row","single-cell"])
    choice=st.selectbox("從初選名單選擇個股（手機也可用）",range(len(snapshot)),
                        format_func=lambda i:f'{snapshot[i]["Yahoo代號"].split(".")[0]} {snapshot[i].get("名稱","")}',
                        key="initial_chart_choice")
    st.button("開啟這檔股票線圖",key="initial_chart_open_button",
              on_click=queue_initial,args=(st.session_state,snapshot[choice]),use_container_width=True)


def scroll_chart_top(nonce):
    import streamlit.components.v1 as components
    components.html("""<script>
    // Navigation request: """+str(int(nonce))+"""
    const main=window.parent.document.querySelector('[data-testid="stMain"]');
    if(main){
      const move=()=>main.scrollTo({top:0,behavior:"auto"});
      requestAnimationFrame(move);setTimeout(move,250);
    }
    </script>""",height=0,scrolling=False)
