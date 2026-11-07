"""Production preliminary row -> correct chart -> original results, offline."""
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest
from initial_navigation import queue_initial, consume_initial, selected_row

ROOT=Path(__file__).resolve().parents[1]
ROWS=[{"代號":"2330","名稱":"台積電","市場":"上市","Yahoo代號":"2330.TW","官方行情日期":"2026-11-06","收盤價":100.,"成交量(張)":2000.},
      {"代號":"8358","名稱":"金居","市場":"上櫃","Yahoo代號":"8358.TWO","官方行情日期":"2026-11-06","收盤價":200.,"成交量(張)":2000.}]


def bars(symbol):
    close=(100. if symbol=="2330.TW" else 200.)+np.sin(np.arange(700)/12)*15
    return pd.DataFrame({"Open":close-1,"High":close+2,"Low":close-2,"Close":close,"Volume":2000000},
                        index=pd.bdate_range("2023-01-02",periods=700))


def seed():
    return {"config":("上市＋上櫃",0.,10000.,1000.,1000.,"接近箱底",5,20,20),
            "results":[],"errors":[],"timestamp":"fixture","candidates":[dict(r) for r in ROWS],
            "cursor":0,"checked":[],"failed":[]}


class InitialNavigationTests(unittest.TestCase):
    def test_selection_keeps_source_position_and_taiwan_suffix(self):
        for event in ({"selection":{"cells":[[1,"名稱"]]}},{"selection":{"rows":[1]}}):
            row=selected_row(event,ROWS)
            state={"market_scan":seed()}
            queue_initial(state,row)
            request=consume_initial(state)
            self.assertEqual(request["symbol"],"8358.TWO")
            self.assertEqual(state["adam_stock_query"],"8358")
            self.assertTrue(state["initial_chart_open"])
            self.assertEqual(len(state["market_scan"]["candidates"]),2)
            self.assertIsNone(consume_initial(state))
        for event in ({},{"selection":{"rows":[99]}},{"selection":{"rows":[0,1]}}):
            self.assertIsNone(selected_row(event,ROWS))
        for symbol in ("8358","AAPL","8358.TW;"):
            with self.assertRaises(ValueError):
                queue_initial({},{"Yahoo代號":symbol})

    def test_jump_nonce_changes_and_manual_stock_drops_stale_context(self):
        state={}
        queue_initial(state,ROWS[0]);consume_initial(state)
        one=state.pop("initial_chart_jump")
        queue_initial(state,ROWS[1]);consume_initial(state)
        self.assertGreater(state["initial_chart_jump"],one)
        state["adam_stock_query"]="2308"
        consume_initial(state)
        self.assertNotIn("initial_chart_context",state)

    def make_app(self):
        app=AppTest.from_file(str(ROOT/"production_initial_preview.py"),default_timeout=45)
        app.session_state["market_scan"]=seed()
        return app.run()

    def setUp(self):
        st.cache_data.clear()

    def test_open_back_second_stock_correct_chart_and_original_progress(self):
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), \
             patch("yfinance.download",side_effect=lambda symbol,**kw:bars(symbol)):
            app=self.make_app()
            self.assertEqual(len(app.exception),0)
            app.selectbox(key="initial_chart_choice").set_value(0).run()
            app.button(key="initial_chart_open_button").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn("個股線圖｜2330.TW",[x.value for x in app.subheader])
            self.assertTrue(any("商品：2330.TW" in x.value for x in app.caption))
            self.assertTrue(any("尚未驗證20日均量" in x.value for x in app.info))
            self.assertIn("亞當鏡像｜歷史波段來源",[x.value for x in app.subheader])
            app.button(key="initial_chart_back").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertFalse(app.session_state["initial_chart_open"])
            self.assertEqual(app.session_state["market_scan"]["cursor"],0)
            self.assertEqual(len(app.session_state["market_scan"]["candidates"]),2)
            app.selectbox(key="initial_chart_choice").set_value(1).run()
            app.button(key="initial_chart_open_button").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertIn("個股線圖｜8358.TWO",[x.value for x in app.subheader])
            self.assertTrue(any("商品：8358.TWO" in x.value for x in app.caption))
            self.assertNotIn("估價",str([x.value for x in app.subheader]))

    def test_bad_history_stops_chart_but_keeps_navigation(self):
        bad=bars("8358.TWO")
        bad.iloc[0,bad.columns.get_loc("Close")]=1.
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), \
             patch("yfinance.download",return_value=bad):
            app=self.make_app()
            app.selectbox(key="initial_chart_choice").set_value(1).run()
            app.button(key="initial_chart_open_button").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertTrue(any("行情資料品質異常" in x.value for x in app.error))
            self.assertEqual(len([x for x in app.button if x.key=="initial_chart_back"]),1)
            self.assertNotIn("自動箱型突破目標分析",[x.value for x in app.subheader])

    def test_exact_staged_production_app(self):
        staged=(ROOT/"production_initial_preview.py").read_text(encoding="utf-8")
        expected=(ROOT/"release-preview/v1.0.6/app.py").read_text(encoding="utf-8")
        self.assertEqual(staged,"PRODUCTION_MODE = True\n"+expected)
