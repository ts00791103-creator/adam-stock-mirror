"""Candidate integration for an explicit, auditable cross-sectional ranking."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import streamlit as st
import yfinance as yf
from full_market_ui import official_snapshot
from market_universe import history_as_of
from composite_strategy import combine_factors, rank_rows, margin_decliners, price_factors
from chip_sources import fetch_institution, fetch_margin


@st.cache_data(ttl=900,show_spinner=False)
def chips_for(exchange,day):
    return fetch_institution(exchange,day)


@st.cache_data(ttl=900,show_spinner=False)
def margin_for(exchange,day):
    return fetch_margin(exchange,day)


@st.cache_data(ttl=900,show_spinner=False)
def rank_history(symbol):
    return yf.Ticker(symbol).history(period="1y",interval="1d",auto_adjust=False,timeout=10)


def inspect_item(item,state,low_window,volume_window,min_lots):
    frame=history_as_of(rank_history(item["Yahoo代號"]),item["官方行情日期"])
    factors=price_factors(frame,item["官方行情日期"],low_window,volume_window)
    if factors["前期平均成交股數"]/1000<min_lots:
        return "excluded",{**item,"原因":"前期平均成交量未達設定"}
    exchange=item["市場"]; code=item["代號"]
    margin=state["margin"].get(exchange,{}).get(code)
    baseline=None; warning=""
    if margin:
        try:
            baseline=margin_for(exchange,factors["5日前日期"]).get(code)
        except Exception:
            warning="5日前融資來源無法核對"
    row=combine_factors(item,frame,state["chips"].get(exchange,{}).get(code),
                        margin,baseline,low_window,volume_window)
    row["融資備註"]=warning if warning else "" if margin else "當日融資缺漏或日期未確認"
    return "rows",row


def show_composite_strategy():
    with st.expander("綜合選股策略｜反彈・量比・法人（測試版）"):
        st.caption("圖片策略的可驗算版本。預設全體上市櫃四碼個股，與圖片的先挑50檔母體不同，因此分數不能直接對照。分數是當次母體相對排名，不是勝率。")
        scope=st.selectbox("綜合排名市場",["上市＋上櫃","上市","上櫃"],key="rank_scope")
        a,b=st.columns(2)
        low_window=a.selectbox("反彈低點觀察日數",[10,20,60],index=1,key="rank_low")
        volume_window=b.selectbox("量比均量日數（不含當日）",[5,20,60],index=1,key="rank_vol")
        min_lots=st.number_input("母體最低前期平均成交量（張）",min_value=0.,value=1000.,key="rank_liquidity")
        preset=st.selectbox("綜合分權重",["量能優先：40／50／10","法人較重：40／30／30","自訂"],key="rank_preset")
        weights=(40,50,10) if preset.startswith("量能") else (40,30,30)
        if preset=="自訂":
            cols=st.columns(3)
            weights=tuple(col.number_input(label,min_value=0,max_value=100,value=default,key=key)
                          for col,label,default,key in zip(cols,["反彈權重%","量比權重%","法人權重%"],[40,50,10],["rank_w1","rank_w2","rank_w3"]))
        positive=st.checkbox("結果只顯示法人買超",key="rank_positive")
        margin_filter=st.selectbox("結果融資條件",["不限（缺融資仍可排名）","融資1日減少","融資5日減少"],key="rank_margin")
        st.caption("反彈＝(收盤÷近N日最低價−1)×100%；量比＝當日量÷前N日均量；法人占比＝法人淨買賣超股數÷官方當日成交股數。三項先轉成相同母體百分位再加權。同分取平均；單檔或全相同為50分。")
        st.caption("融資增減＝當日餘額減前日／5根日K前對應日期的餘額，單位為張；負值表示減少。融資條件只篩選結果，不改變原母體百分位。融資減少不代表後續必漲。")
        config=(scope,low_window,volume_window,min_lots)
        if st.button("建立綜合排名母體",key="rank_start"):
            st.session_state.pop("composite_scan",None)
            if sum(weights)!=100:
                st.error("權重加總需為100%。")
                return
            exchanges=("上市","上櫃") if scope=="上市＋上櫃" else (scope,)
            with st.spinner("核對官方公司名單、日期與法人資料…"):
                results,errors,timestamp=official_snapshot(exchanges)
                candidates=[r for result in results for r in result["rows"]]
                days={r["官方行情日期"] for r in candidates}
                if len(days)!=1:
                    st.warning("行情日期未一致或無行情；請稍後重試或改選單一市場，不混用不同日期排名。")
                    return
                day=next(iter(days)); chips={}; margin={}; source_errors=[]
                with ThreadPoolExecutor(max_workers=4) as pool:
                    jobs={pool.submit(loader,ex,day):(kind,ex) for ex in exchanges
                          for kind,loader in (("chips",chips_for),("margin",margin_for))}
                    for future in as_completed(jobs):
                        kind,ex=jobs[future]
                        try:
                            (chips if kind=="chips" else margin)[ex]=future.result()
                        except Exception:
                            source_errors.append({"市場":ex,"來源":"法人" if kind=="chips" else "融資","原因":"官方資料缺漏、日期不同或來源暫時不可用；不填零"})
            st.session_state["composite_scan"]={"config":config,"results":results,"errors":errors,
                "timestamp":timestamp,"day":day,"candidates":sorted(candidates,key=lambda r:r["Yahoo代號"]),
                "chips":chips,"margin":margin,"source_errors":source_errors,"cursor":0,"rows":[],"failed":[],"excluded":[]}
        state=st.session_state.get("composite_scan")
        if not state: return
        if state["config"]!=config:
            st.info("母體或觀察期間已變更，請重新建立母體。")
            return
        st.write(f"行情日期：{state['day']}｜公司名單 {sum(r['公司數'] for r in state['results'])} 檔｜有效官方行情 {len(state['candidates'])} 檔")
        st.caption(f"抓取時間（台灣）：{state['timestamp']}；遇休市可為最近交易日，不能視為今天盤中訊號。")
        if state["errors"] or state["source_errors"]:
            st.warning("來源有未完成項目；排名只包含資料完整者。")
            st.dataframe(pd.DataFrame(state["errors"]+state["source_errors"]),hide_index=True)
        missing=[r for market in state["results"] for r in market["failures"]]
        if missing:
            with st.expander("官方行情未判定清單"):
                st.dataframe(pd.DataFrame(missing),hide_index=True)
        total=len(state["candidates"]); cursor=state["cursor"]
        if cursor<total and st.button("計算下一批綜合因子（最多10檔）",key="rank_next"):
            batch=state["candidates"][cursor:cursor+10]
            with st.spinner("讀取本批日K與核對融資日期…"):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    jobs={pool.submit(inspect_item,item,state,low_window,volume_window,min_lots):item for item in batch}
                    for future in as_completed(jobs):
                        item=jobs[future]
                        try:
                            category,row=future.result()
                            state[category].append(row)
                        except Exception as exc:
                            state["failed"].append({**item,"原因":str(exc)[:180]})
                        state["cursor"]+=1
            st.rerun()
        cursor=state["cursor"]
        st.write(f"已檢查 {cursor}/{total}｜可排名 {len(state['rows'])}｜流動性排除 {len(state['excluded'])}｜未判定 {len(state['failed'])}")
        if cursor<total:
            st.warning("尚未檢查全部股票，以下僅為已檢查母體的暫排名；後續批次會改變百分位與分數。")
        else:
            st.info("本次有效官方行情已處理；缺資料未判定股票未納入分數，不代表不符合或零買超。")
        try:
            ranked=rank_rows(state["rows"],weights)
        except ValueError as exc:
            st.warning(str(exc)); return
        display=ranked
        if positive: display=[r for r in display if r["法人占比%"]>0]
        if margin_filter!="不限（缺融資仍可排名）":
            allowed={r["Yahoo代號"] for r in margin_decliners(display,1 if "1日" in margin_filter else 5)}
            display=[r for r in display if r["Yahoo代號"] in allowed]
        if display:
            columns=["名次","代號","名稱","市場","綜合分","近低反彈%","量比","法人占比%","法人合計（張）","外資（張）","投信（張）","自營商（張）","融資日增減（張）","融資5日增減（張）","收盤","收盤漲跌%","資料日期"]
            st.dataframe(pd.DataFrame(display[:20])[columns].round(2),hide_index=True)
            choice=st.selectbox("綜合排名帶入個股",[r["Yahoo代號"] for r in display[:20]],key="rank_choice")
            if st.button("查看這檔的亞當鏡像",key="rank_use"):
                st.session_state["adam_stock_query"]=choice.split(".")[0]
                st.success("已帶入側欄，請按「開始亞當鏡像分析」。")
        elif cursor: st.info("目前結果沒有資料完整且符合顯示條件的股票，請查看未判定項目。")
        if ranked:
            audit=pd.DataFrame(ranked)
            audit["母體可排名數"]=len(ranked); audit["已檢查數"]=cursor; audit["待檢查數"]=total-cursor
            audit["權重"]=str(weights); audit["反彈日數"]=low_window; audit["量比日數"]=volume_window
            st.download_button("下載綜合排名完整CSV",audit.to_csv(index=False).encode("utf-8-sig"),file_name=f"adam_composite_{state['day']}.csv",mime="text/csv",key="rank_csv")
        if state["failed"]:
            with st.expander("綜合策略未判定項目"):
                st.dataframe(pd.DataFrame(state["failed"]),hide_index=True)
        for label,period in (("融資1日減少排行",1),("融資5日減少排行",5)):
            with st.expander(label):
                drops=margin_decliners(state["rows"],period)
                if drops: st.dataframe(pd.DataFrame(drops).head(50),hide_index=True)
                else: st.info("已檢查股票尚無可確認的減少項目；缺資料不當成零。")
        st.caption("本次進度只保留本瀏覽器工作階段，請下載CSV保存。綜合分只做觀察排序，需再核對箱型、支撐壓力與風險；不自動下單、不新增推播。")
