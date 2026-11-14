"""Manual valuation scenarios grounded in published dividend, PEG and stress examples."""
from math import isfinite


def dividend_prices(dividends):
    if (len(dividends) != 5 or any(not isfinite(x) or x < 0 for x in dividends)
            or not any(dividends)):
        raise ValueError("請輸入五個完整年度的非負現金股利，且至少一年有配息。")
    average = sum(dividends) / 5
    return {name: average / rate for name, rate in
            (("便宜價", 0.07), ("合理價", 0.05), ("昂貴價", 0.03))}


def peg_prices(eps, growth_pct):
    base = eps * growth_pct
    if not isfinite(base) or eps <= 0 or growth_pct <= 0:
        raise ValueError("請輸入有效且大於零的 EPS 與成長率。")
    return {name: base * factor for name, factor in (
        ("特價", 0.75), ("便宜價", 0.875), ("合理價", 1.0),
        ("昂貴價", 1.25), ("瘋狂價", 1.5),
    )}


def scenario_prices(eps, pe, eps_cut_pct, pe_cut_pct):
    if not all(isfinite(x) for x in (eps, pe, eps_cut_pct, pe_cut_pct)):
        raise ValueError("請輸入有限數值。")
    if eps <= 0 or pe <= 0 or not (0 <= eps_cut_pct <= 100 and 0 <= pe_cut_pct <= 100):
        raise ValueError("EPS 與本益比須大於零，下修幅度須介於 0% 與 100%。")
    base = eps * pe
    if not isfinite(base):
        raise ValueError("基準估值超出計算範圍。")
    return {"基準估值": base, "情境估值": base * (1 - eps_cut_pct / 100) * (1 - pe_cut_pct / 100)}


def show_sun_valuation(st, symbol=None):
    with st.expander("價值投資｜357、PEG 與情境估價"):
        st.caption("可自動讀取目前選定個股，或手動填入個股資料。")
        method = st.radio("試算方法", ("357 現金股利法", "PEG（日報 2021-10-06 版）", "EPS／本益比下修情境"))
        auto = symbol and st.radio("估價資料來源", ("自動線上", "手動輸入"), horizontal=True) == "自動線上"
        if auto:
            show_online_valuation(st, symbol, method)
            return
        if method.startswith("357"):
            st.markdown("[五年現金股利來源](https://www.sie.com.tw/Luckylong/article.do?id=A20240411954337J55)")
            values = st.text_input("最近五個完整年度每股現金股利（元，以逗號分隔）",
                                   placeholder="5, 5, 5, 5, 5.05")
        elif method.startswith("PEG"):
            st.markdown("[台積電案例與級距](https://smart.businessweekly.com.tw/Event/investorDaily/dist/paper/20211006.pdf#page=2)")
            st.caption("日報案例使用近四季 ROE 代理成長率。請確認輸入依據，29.85% 請輸入 29.85。")
            eps = st.number_input("PEG 使用的每股盈餘（元）", min_value=0.0, format="%.2f")
            growth = st.number_input("預估 EPS 成長率或代理 ROE（%）", min_value=0.0, format="%.2f")
        else:
            st.markdown("[孫慶龍的估價情境案例](https://www.sie.com.tw/Luckylong/article.do?id=A202404117064411GH)")
            st.caption("以手動輸入的基準 EPS 和本益比估價，兩項下修幅度預設為 0%。")
            eps = st.number_input("情境基準 EPS（元）", min_value=0.0, format="%.2f")
            pe = st.number_input("情境基準本益比（倍）", min_value=0.0, format="%.2f")
            eps_cut = st.number_input("EPS 下修（%）", min_value=0.0, max_value=100.0)
            pe_cut = st.number_input("本益比下修（%）", min_value=0.0, max_value=100.0)
        if st.button("計算價值投資試算"):
            try:
                if method.startswith("357"):
                    try:
                        dividends = [float(x) for x in values.replace("，", ",").split(",")]
                    except ValueError:
                        raise ValueError("請以逗號分隔五個年度的現金股利數字。") from None
                    prices = dividend_prices(dividends)
                elif method.startswith("PEG"):
                    prices = peg_prices(eps, growth)
                else:
                    prices = scenario_prices(eps, pe, eps_cut, pe_cut)
                st.table({name: [f"{price:,.2f} 元"] for name, price in prices.items()})
            except ValueError as exc:
                st.warning(str(exc))


def show_online_valuation(st, symbol, method):
    import pandas as pd
    from full_market_ui import VALUE_MODES, value_inputs

    mode = VALUE_MODES[0] if method.startswith("357") else VALUE_MODES[1] if method.startswith("PEG") else VALUE_MODES[2]
    day = pd.Timestamp.now(tz="Asia/Taipei").date().isoformat()
    st.caption(f"{symbol}｜Yahoo Finance 線上資料")
    scenario = ()
    if mode == VALUE_MODES[0]:
        st.caption("使用最近五個完整曆年的每股現金股利。")
    elif mode == VALUE_MODES[1]:
        st.caption("使用近四季 EPS 與 ROE，ROE 作為成長率代理。")
    else:
        automatic_pe = st.radio("基準本益比來源", ("自動取得目前本益比", "手動設定"), horizontal=True) == "自動取得目前本益比"
        if automatic_pe:
            st.caption("使用 Yahoo Finance 的目前本益比（TTM）。兩項下修是可調的情境假設。")
        scenario = (
            None if automatic_pe else st.number_input("基準本益比（倍）", min_value=0.1, value=15.0, key="single_value_pe"),
            st.number_input("EPS 下修（%）", min_value=0.0, max_value=100.0, key="single_value_eps_cut"),
            st.number_input("本益比下修（%）", min_value=0.0, max_value=100.0, key="single_value_pe_cut"),
        )
    key = (symbol, mode, day, scenario)
    if st.button("抓取線上資料並試算"):
        st.session_state.pop("single_value_result", None)
        try:
            with st.spinner("讀取線上股利或財報…"):
                data = value_inputs(symbol, mode, day)
            if mode == VALUE_MODES[0]:
                prices = dividend_prices(data["dividends"])
                detail = "各年度現金股利：" + "、".join(
                    f"{int(day[:4]) - 5 + index} 年 {value:g} 元"
                    for index, value in enumerate(data["dividends"])
                )
            else:
                if data.get("eps") is None:
                    raise ValueError("缺少近四季 EPS")
                eps = float(data["eps"])
                detail = f"近四季 EPS {eps:g} 元｜財報快照擷取 {data['financial_snapshot']}"
                if mode == VALUE_MODES[1]:
                    if data.get("roe") is None:
                        raise ValueError("缺少 ROE")
                    roe = float(data["roe"]) * 100
                    detail += f"｜ROE {roe:.2f}%"
                    prices = peg_prices(eps, roe)
                else:
                    pe, eps_cut, pe_cut = scenario
                    if pe is None:
                        if data.get("pe") is None:
                            raise ValueError("線上缺少有效本益比，可切換手動設定基準本益比。")
                        pe = float(data["pe"])
                    prices = scenario_prices(eps, pe, eps_cut, pe_cut)
                    detail += f"｜基準本益比 {pe:.2f} 倍"
            st.session_state["single_value_result"] = (key, detail, prices)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.warning("線上行情或財報暫時無法取得，可稍後重試或切換手動輸入。")
    saved = st.session_state.get("single_value_result")
    if saved and saved[0] == key:
        st.caption(saved[1])
        st.table({name: [f"{price:,.2f} 元"] for name, price in saved[2].items()})
