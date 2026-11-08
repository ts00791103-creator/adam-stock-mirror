from contextlib import ExitStack
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest
from analysis_availability import inspect_history,save_availability,availability_label
from stock_navigation import queue_analysis,consume_request,return_to_results
from test_market_data_quality import audit
from test_stock_navigation import valuation

ROOT=Path(__file__).resolve().parents[1]


def bars(symbol="2330.TW",bad=False):
    index=pd.bdate_range(end="2026-11-06",periods=2600)
    close=100+np.sin(np.arange(len(index))/12)*3
    frame=pd.DataFrame({"Open":close-.5,"High":close+1,"Low":close-1,"Close":close,"Volume":2000000.},index=index)
    if bad:
        for day in ("2017-07-21","2018-07-26"):
            frame.loc[day,"Close"]=frame.loc[day,"Low"]-1
    return frame


def snapshot():
    samples=[("1815","富喬","上櫃"),("2330","台積電","上市"),("2887","台新新光金","上市")]+[(str(2000+i),"測試"+str(i),"上市") for i in range(9)]
    rows=[{"代號":c,"名稱":n,"市場":m,"Yahoo代號":c+(".TW" if m=="上市" else ".TWO"),
           "官方行情日期":"2026-11-06","官方收盤":100.,"官方當日成交量（張）":2000.} for c,n,m in samples]
    return ([{"市場":m,"公司數":len([r for r in rows if r["市場"]==m]),
              "rows":[r for r in rows if r["市場"]==m],"failures":[]} for m in ("上市","上櫃")],[],"fixture time")


class AvailabilityTests(unittest.TestCase):
    def test_complete_bad_history_is_preserved_and_remains_blocked(self):
        frame=bars(bad=True);before=frame.copy(deep=True)
        report=inspect_history("1815.TWO","10y","1d",frame,audit)
        self.assertEqual(report["status"],"blocked")
        self.assertEqual(report["bars"],len(frame))
        self.assertEqual([r["日期／時間"][:10] for r in report["invalid_rows"]],["2017-07-21","2018-07-26"])
        pd.testing.assert_frame_equal(frame,before)
        state={};save_availability(state,report)
        self.assertIn("未通過",availability_label(state,"1815.TWO","10y","1d"))
        self.assertIn("尚未核對",availability_label(state,"1815.TWO","1y","1d"))
        self.assertIn("尚未核對",availability_label(state,"2330.TW","10y","1d"))

    def test_good_price_quality_is_not_screening_recommendation(self):
        frame=bars();result=inspect_history("2330.TW","10y","1d",frame,audit)
        self.assertEqual(result["status"],"available")
        self.assertEqual(len(result["price_frame_sha256"]),64)
        self.assertNotIn("符合",result)

    def test_navigation_reference_cleared_on_manual_symbol_switch(self):
        state={"market_scan":{"cursor":10}}
        queue_analysis(state,{"Yahoo代號":"1815.TWO","官方收盤":117.5,"官方行情日期":"2026-11-06"})
        consume_request(state)
        self.assertEqual(state["analysis_context"]["official_close"],117.5)
        state["adam_stock_query"]="2330"
        consume_request(state)
        self.assertNotIn("analysis_context",state)
        self.assertEqual(state["market_scan"]["cursor"],10)

    def test_back_resets_table_selection_epoch_without_losing_results(self):
        state={"analysis_page_open":True,"market_scan":{"cursor":10,"candidates":[1,2]},"analysis_jump_sequence":3}
        with patch("stock_navigation.st.session_state",state):return_to_results()
        self.assertFalse(state["analysis_page_open"])
        self.assertEqual(state["stock_result_epoch"],1)
        self.assertEqual(state["analysis_jump_sequence"],4)
        self.assertEqual(state["market_scan"]["cursor"],10)


class AcquisitionRecoveryTests(unittest.TestCase):
    def setUp(self):st.cache_data.clear()

    def app(self):
        return AppTest.from_string("from full_market_ui import show_full_market\nshow_full_market()",default_timeout=30).run()

    def test_failure_then_retry_is_fresh_and_preserves_scan(self):
        with patch("full_market_ui.official_snapshot",side_effect=[snapshot(),OSError("temporary network"),snapshot()]) as fetch,patch("full_market_ui.screening_data",return_value=bars().tail(260)):
            app=self.app();app.button(key="market_start").click().run()
            app.button(key="market_next").click().run()
            self.assertEqual(app.session_state["market_scan"]["cursor"],10)
            app.button(key="market_start").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.session_state["market_scan"]["candidates"]),12)
            self.assertEqual(app.session_state["market_scan"]["cursor"],10)
            self.assertTrue(any("保留" in r.value for r in app.error))
            app.button(key="market_start").click().run()
            self.assertEqual(app.session_state["market_scan"]["cursor"],0)
            tokens=[r.kwargs["refresh_token"] for r in fetch.call_args_list]
            self.assertEqual(len(set(tokens)),3)

    def test_invalid_conditions_keep_old_list_and_restore_keeps_progress(self):
        with patch("full_market_ui.official_snapshot",return_value=snapshot()) as fetch,patch("full_market_ui.screening_data",return_value=bars().tail(260)):
            app=self.app();app.button(key="market_start").click().run();app.button(key="market_next").click().run()
            app.number_input(key="market_low").set_value(20000.).run()
            self.assertEqual(app.session_state["market_scan"]["cursor"],10)
            self.assertTrue(app.button(key="market_next").disabled)
            app.button(key="market_start").click().run()
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(app.session_state["market_scan"]["cursor"],10)
            app.button(key="market_restore").click().run()
            self.assertEqual(app.number_input(key="market_low").value,0.)
            self.assertEqual(app.session_state["market_scan"]["cursor"],10)
            self.assertFalse(app.button(key="market_next").disabled)

    def test_partial_retry_does_not_replace_complete_snapshot(self):
        good=snapshot();partial=([good[0][0]],[{"市場":"上櫃","原因":"temporary"}],"partial")
        with patch("full_market_ui.official_snapshot",side_effect=[good,partial]):
            app=self.app();app.button(key="market_start").click().run();app.button(key="market_start").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.session_state["market_scan"]["candidates"]),12)
            self.assertEqual(app.session_state["market_scan"]["timestamp"],"fixture time")
            self.assertTrue(any("部分失敗" in e.value for e in app.error))

    def test_empty_source_is_not_a_zero_matching_result(self):
        with patch("full_market_ui.official_snapshot",return_value=([],[{"市場":"上市","原因":"offline"}],"now")):
            app=self.app();app.button(key="market_start").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertNotIn("market_scan",app.session_state)
            self.assertTrue(any("未取得有效" in e.value for e in app.error))
        with patch("full_market_ui.official_snapshot",return_value=snapshot()):
            app=self.app();app.number_input(key="market_high").set_value(1.).run();app.button(key="market_start").click().run()
            self.assertEqual(app.session_state["market_scan"]["candidates"],[])
            self.assertEqual(len(app.error),0)


class CandidateNavigationIntegrationTests(unittest.TestCase):
    def setUp(self):st.cache_data.clear()

    def patches(self):
        stack=ExitStack()
        stack.enter_context(patch("urllib.request.urlopen",side_effect=OSError("offline")))
        stack.enter_context(patch("full_market_ui.official_snapshot",return_value=snapshot()))
        stack.enter_context(patch("full_market_ui.screening_data",return_value=bars().tail(260)))
        stack.enter_context(patch("yfinance.download",side_effect=lambda symbol,**kw:bars(symbol,bad=symbol=="1815.TWO")))
        stack.enter_context(patch("valuation_io.bounded_fetch",side_effect=valuation))
        return stack

    def test_preflight_1815_blocked_full_period_navigation_back_and_batch(self):
        with self.patches():
            app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
            app.button(key="market_start").click().run()
            app.selectbox(key="market_first_results_stock_choice").set_value("1815.TWO").run()
            app.button(key="market_first_results_preflight").click().run()
            self.assertEqual(len(app.exception),0)
            report=app.session_state["analysis_availability"]["1815.TWO|10y|1d"]
            self.assertEqual(report["status"],"blocked")
            self.assertEqual(report["bars"],2600)
            app.button(key="market_first_results_selected_open").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn("個股分析｜1815.TWO",[s.value for s in app.subheader])
            self.assertEqual(app.selectbox(key="analysis_period").value,"10y")
            self.assertTrue(any("導航成功" in v.value for v in app.success))
            self.assertTrue(any("行情資料品質異常" in v.value for v in app.error))
            self.assertFalse(any("亞當鏡像｜歷史波段來源"==s.value for s in app.subheader))
            app.button(key="analysis_back").click().run()
            self.assertEqual(len(app.session_state["market_scan"]["candidates"]),12)
            app.button(key="market_next").click().run()
            self.assertEqual(app.session_state["market_scan"]["cursor"],10)
            for symbol in ("2330.TW","2887.TW"):
                app.selectbox(key="market_first_results_stock_choice").set_value(symbol).run()
                app.button(key="market_first_results_selected_open").click().run()
                self.assertEqual(len(app.exception),0)
                self.assertIn("個股分析｜"+symbol,[s.value for s in app.subheader])
                self.assertIn("亞當鏡像｜歷史波段來源",[s.value for s in app.subheader])
                self.assertEqual(app.session_state["market_scan"]["cursor"],10)
                app.button(key="analysis_back").click().run()
                self.assertEqual(app.session_state["market_scan"]["cursor"],10)


if __name__=="__main__":unittest.main()
