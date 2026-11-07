from unittest.mock import patch
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest


class CompositeUITests(unittest.TestCase):
    def fixtures(self):
        frame=pd.DataFrame({"Open":100.,"High":120.,"Low":100.,"Close":110.,"Volume":1000000.},
                           index=pd.bdate_range("2026-09-01",periods=30))
        day=str(frame.index[-1].date())
        item={"代號":"2330","名稱":"台積電","市場":"上市","Yahoo代號":"2330.TW",
              "官方行情日期":day,"官方收盤":110.,"官方當日成交量（張）":1000.}
        results=[{"市場":"上市","公司數":1,"rows":[item],"failures":[]}]
        chip={"2330":{"date":day,"foreign":100000.,"trust":0.,"dealer":0.,"net":100000.,"source":"fixture"}}
        return frame,results,chip

    def test_initialization_batch_rank_and_select_without_unrequested_network(self):
        frame,results,chip=self.fixtures()
        with patch("composite_strategy_ui.official_snapshot",return_value=(results,[],"fixture")), \
             patch("composite_strategy_ui.chips_for",return_value=chip), \
             patch("composite_strategy_ui.margin_for",return_value={}), \
             patch("composite_strategy_ui.rank_history",return_value=frame):
            app=AppTest.from_string("from composite_strategy_ui import show_composite_strategy\nshow_composite_strategy()",default_timeout=45).run()
            self.assertEqual(len(app.exception),0)
            app.button(key="rank_start").click().run()
            app.button(key="rank_next").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.session_state["composite_scan"]["rows"]),1)
            self.assertEqual(app.session_state["composite_scan"]["cursor"],1)
            app.button(key="rank_use").click().run()
            self.assertEqual(app.session_state["adam_stock_query"],"2330")

    def test_source_failure_is_unconfirmed_not_zero_score(self):
        frame,results,chip=self.fixtures()
        with patch("composite_strategy_ui.official_snapshot",return_value=(results,[],"fixture")), \
             patch("composite_strategy_ui.chips_for",side_effect=ValueError("offline")), \
             patch("composite_strategy_ui.margin_for",return_value={}), \
             patch("composite_strategy_ui.rank_history",return_value=frame):
            app=AppTest.from_string("from composite_strategy_ui import show_composite_strategy\nshow_composite_strategy()",default_timeout=45).run()
            app.button(key="rank_start").click().run()
            app.button(key="rank_next").click().run()
            self.assertEqual(len(app.exception),0)
            state=app.session_state["composite_scan"]
            self.assertEqual(len(state["rows"]),0)
            self.assertEqual(len(state["failed"]),1)


if __name__=="__main__": unittest.main()
