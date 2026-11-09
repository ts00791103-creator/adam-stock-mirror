"""Manual valuation scenarios grounded in the published dividend and PEG examples."""
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


def show_sun_valuation(st):
    with st.expander("價值投資｜357 與 PEG 手動試算"):
        st.caption("請填入同一檔台股的資料。試算價位依輸入而變動。")
        method = st.radio("試算方法", ("357 現金股利法", "PEG（日報 2021-10-06 版）"))
        if method.startswith("357"):
            st.markdown("[五年現金股利來源](https://www.sie.com.tw/Luckylong/article.do?id=A20240411954337J55)")
            values = st.text_input("最近五個完整年度每股現金股利（元，以逗號分隔）",
                                   placeholder="5, 5, 5, 5, 5.05")
        else:
            st.markdown("[台積電案例與級距](https://smart.businessweekly.com.tw/Event/investorDaily/dist/paper/20211006.pdf#page=2)")
            st.caption("日報案例使用近四季 ROE 代理成長率。請確認輸入依據，29.85% 請輸入 29.85。")
            eps = st.number_input("PEG 使用的每股盈餘（元）", min_value=0.0, format="%.2f")
            growth = st.number_input("預估 EPS 成長率或代理 ROE（%）", min_value=0.0, format="%.2f")
        if st.button("計算價值投資試算"):
            try:
                if method.startswith("357"):
                    try:
                        dividends = [float(x) for x in values.replace("，", ",").split(",")]
                    except ValueError:
                        raise ValueError("請以逗號分隔五個年度的現金股利數字。") from None
                    prices = dividend_prices(dividends)
                else:
                    prices = peg_prices(eps, growth)
                st.table({name: [f"{price:,.2f} 元"] for name, price in prices.items()})
            except ValueError as exc:
                st.warning(str(exc))
