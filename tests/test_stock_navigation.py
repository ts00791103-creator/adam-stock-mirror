"""Exercise stock switching and prices through the real candidate entrypoint."""
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest
from stock_navigation import queue_analysis, consume_request, reset_stock_pricing

ROOT=Path(__file__).resolve().parents[1]


def frame(symbol):
    base=100. if symbol=="2330.TW" else 200.
    close=base+np.sin(np.arange(700)/12)*5
    return pd.DataFrame({"Open":close-1,"High":close+2,"Low":close-2,
                         "Close":close,"Volume":2000000.},index=pd.bdate_range("2023-01-02",periods=700))


def valuation(key,loader,timeout_seconds=12):
    if key[0]=="eps":
        return (5. if key[1]=="2330.TW" else 10.),"fixture symbol "+key[1]
    return {"pes":(10.,15.,20.),"samples":300,"coverage_days":900,"warnings":[],
            "eps_quarters":12,"eps_first":"2023Q1","eps_last":"2026Q1",
            "start":"2023-01-02","end":"2026-01-02","spread":.5,"method":"fixture"},None


class NavigationStateTests(unittest.TestCase):
    def test_market_suffix_and_manual_inputs_are_isolated(self):
        state={"pricing_input_symbol":"2330.TW","b3_eps_manual_v2":99.,
               "b3_eps_source_v2":"手動輸入 EPS","b3_filing_eps_csv_v1":b"old stock",
               "b3_growth_on_v1":True,"screen_result":"preserved"}
        queue_analysis(state,{"Yahoo代號":"3163.TWO","名稱":"波若威","資料日期":"2026-11-06"})
        request=consume_request(state)
        self.assertEqual(request["symbol"],"3163.TWO")
        self.assertEqual(state["adam_stock_query"],"3163")
        self.assertEqual(state["adam_market"],"台灣股票／ETF")
        self.assertEqual(state["b3_eps_manual_v2"],0.)
        self.assertEqual(state["b3_eps_source_v2"],"自動抓取近四季 EPS")
        self.assertNotIn("b3_filing_eps_csv_v1",state)
        self.assertFalse(state["b3_growth_on_v1"])
        self.assertEqual(state["screen_result"],"preserved")
        self.assertIsNone(consume_request(state))

    def test_same_symbol_does_not_erase_deliberate_manual_scenario(self):
        state={"pricing_input_symbol":"2330.TW","b3_eps_manual_v2":99.}
        reset_stock_pricing(state,"2330.TW")
        self.assertEqual(state["b3_eps_manual_v2"],99.)
        for symbol in ("AAPL","2330","2330.TW;echo"):
            with self.assertRaises(ValueError): queue_analysis({},{"Yahoo代號":symbol})


class StockClickIntegrationTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def setup_patches(self):
        from contextlib import ExitStack
        stack=ExitStack()
        stack.enter_context(patch("urllib.request.urlopen",side_effect=OSError("offline")))
        stack.enter_context(patch("screener_ui.screening_data",side_effect=frame))
        stack.enter_context(patch("yfinance.download",side_effect=lambda symbol,**kwargs:frame(symbol)))
        stack.enter_context(patch("valuation_io.bounded_fetch",side_effect=valuation))
        return stack

    def screen(self):
        app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=45).run()
        app.text_area(key="screen_list").set_value("2330,2308").run()
        app.button(key="screen_run").click().run()
        self.assertEqual(len(app.exception),0)
        return app

    def test_click_open_back_and_second_stock_have_distinct_prices(self):
        with self.setup_patches():
            app=self.screen()
            app.button(key="screen_results_open_2330.TW").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn("個股分析｜2330.TW",[s.value for s in app.subheader])
            values={m.label:m.value for m in app.metric}
            self.assertEqual(values["🟡 合理價（參考）"],"75.00")
            self.assertIn("亞當鏡像｜歷史波段來源",[s.value for s in app.subheader])
            app.radio(key="b3_eps_source_v2").set_value("手動輸入 EPS").run()
            app.number_input(key="b3_eps_manual_v2").set_value(99.).run()
            app.button(key="analysis_back").click().run()
            self.assertEqual(app.text_area(key="screen_list").value,"2330,2308")
            self.assertEqual(len(app.session_state["screen_result"][1]),2)
            app.button(key="screen_results_open_2308.TW").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn("個股分析｜2308.TW",[s.value for s in app.subheader])
            self.assertEqual(app.radio(key="b3_eps_source_v2").value,"自動抓取近四季 EPS")
            values={m.label:m.value for m in app.metric}
            self.assertEqual(values["🟡 合理價（參考）"],"150.00")
            self.assertTrue(any("估價標的：2308.TW" in c.value for c in app.caption))

    def test_missing_pe_keeps_charts_and_displays_reason_without_fake_prices(self):
        def missing(key,loader,timeout_seconds=12):
            return (5.,"fixture") if key[0]=="eps" else (None,"fixture PE unavailable")
        with self.setup_patches(),patch("valuation_io.bounded_fetch",side_effect=missing):
            app=self.screen()
            app.button(key="screen_results_open_2330.TW").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn("亞當鏡像｜歷史波段來源",[s.value for s in app.subheader])
            self.assertFalse(any("合理價" in m.label for m in app.metric))
            self.assertTrue(any("歷史 PE 資料不足" in w.value for w in app.warning))


if __name__=="__main__": unittest.main()
