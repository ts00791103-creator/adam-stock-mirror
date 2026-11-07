"""User-supplied screenshot formulas. Inputs are scenarios, never live data."""
import math


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("輸入必須是有限數字")
    return value


def growth_valuation(eps, roe_pct, payouts, pes):
    eps, roe = finite(eps), finite(roe_pct)
    payouts = [finite(x) for x in payouts]
    pes = [finite(x) for x in pes]
    if eps <= 0 or len(payouts) != 5 or any(x < 0 or x > 100 for x in payouts):
        raise ValueError("需正 EPS 與五年 0～100% 配發率；超額配發不套用此模型")
    if len(pes) != 6 or any(x <= 0 for x in pes) or any(a >= b for a, b in zip(pes, pes[1:])):
        raise ValueError("六段本益比需為正值且由低至高排列")
    payout = sum(payouts) / 5 / 100
    growth = roe / 100 * (1 - payout)
    forecast = eps * (1 + growth)
    if forecast <= 0:
        raise ValueError("預估 EPS 非正，本益比估價不適用")
    return {"payout_pct": payout * 100, "growth_pct": growth * 100,
            "forecast_eps": forecast, "dividend": forecast * payout,
            "prices": [forecast * pe for pe in pes]}


def book_value(equity, shares):
    equity, shares = finite(equity), finite(shares)
    if shares <= 0:
        raise ValueError("普通股流通股數需大於零")
    return equity / shares


def margin_zone(ratio):
    ratio = finite(ratio)
    if ratio <= 0:
        raise ValueError("維持率需大於零")
    if ratio < 140:
        return "極低維持率觀察區（低於 140%；接近或低於 130% 時加強留意）"
    if ratio < 150:
        return "低維持率觀察區（140%～未滿 150%）"
    if ratio <= 160:
        return "融資壓力觀察區（150%～160%）"
    if ratio < 180:
        return "門檻間過渡區（高於 160%、低於 180%）"
    if ratio < 200:
        return "高維持率觀察區（180%～未滿 200%）"
    return "極高維持率觀察區（200% 以上）"


def render_reference_strategies(st):
    with st.expander("圖片策略試算｜融資維持率・成長估價・每股淨值", expanded=False):
        st.caption("手動輸入試算，未連接即時資料。圖片門檻未經回測，不作為自動買賣訊號。")
        source = st.text_input("數值來源／財報季度", key="ref_source")
        date = st.date_input("資料基準日", value=None, key="ref_date")
        kind = st.selectbox("試算項目", ["盈餘成長與六段估價", "大盤融資維持率", "每股淨值"], key="ref_kind")
        with st.form("reference_strategy_form"):
            if kind == "盈餘成長與六段估價":
                eps = st.number_input("近四季 EPS（元）", value=0.0, key="ref_eps")
                roe = st.number_input("近四季 ROE（%）", value=0.0, key="ref_roe")
                payouts = [st.number_input(f"近 {n} 年配發率（%）", min_value=0.0, max_value=100.0, value=0.0, key=f"ref_payout_{n}") for n in range(1, 6)]
                labels = ["特價", "便宜", "合理下緣", "合理上緣", "昂貴", "瘋狂"]
                pes = [st.number_input(f"{label}本益比（自行設定）", min_value=0.0, value=0.0, key=f"ref_pe_{i}") for i, label in enumerate(labels)]
                st.caption("六段名稱沿用圖片；倍數選取公式不明，需自行輸入。近五年配發率採簡單平均。這是成長情境，不是分析師預測；未納入增資、庫藏股或景氣變化。")
            elif kind == "大盤融資維持率":
                ratio = st.number_input("整體市場融資維持率（%）", min_value=0.0, value=0.0, key="ref_margin")
                st.caption("不可用個人帳戶維持率或融資餘額代替。圖片區間以 140／150／160／180／200% 分段，不代表已驗證的底部或高點。")
            else:
                equity = st.number_input("歸屬普通股股東權益（元；已扣除非控制權益與特別股權益）", value=0.0, key="ref_equity")
                shares = st.number_input("期末普通股流通股數（股）", min_value=0.0, value=0.0, key="ref_shares")
                st.caption("兩者須同一基準日；金額請換算成元。每股淨值不等同合理股價。")
            submitted = st.form_submit_button("計算圖片策略")
        if submitted:
            if not source.strip() or date is None:
                st.warning("請填數值來源／財報季度及資料基準日。")
                return
            try:
                if kind == "盈餘成長與六段估價":
                    result = growth_valuation(eps, roe, payouts, pes)
                    st.write(f"五年平均配發率：{result['payout_pct']:.2f}%｜情境盈餘成長率：{result['growth_pct']:.2f}%")
                    st.write(f"預估 EPS：{result['forecast_eps']:.2f} 元｜情境股利：{result['dividend']:.2f} 元")
                    st.table([{"區段": label, "本益比": pe, "情境價格（元）": round(price, 2)} for label, pe, price in zip(labels, pes, result["prices"])])
                    st.caption("公式：ROE ×（1－平均配發率）；預估 EPS＝近四季 EPS ×（1＋成長率）；情境價格＝預估 EPS × 本益比。")
                elif kind == "大盤融資維持率":
                    st.info(margin_zone(ratio))
                    st.caption("低維持率仍可能伴隨續跌；高維持率不能單獨判定過熱。未驗證圖片對歷史底部的敘述。")
                else:
                    st.metric("每股淨值（元）", f"{book_value(equity, shares):,.2f}")
                st.caption(f"來源：{source}｜基準日：{date}｜手動輸入，未自動核實")
            except ValueError as exc:
                st.error(str(exc))
