"""Execute the exact production release snapshot, including its real loader."""
import ast
from pathlib import Path
from unittest.mock import patch
import unittest
import streamlit as st
from streamlit.testing.v1 import AppTest
import test_initial_navigation as original
from test_verified_daily_history import source, month, actions

ROOT=Path(__file__).resolve().parents[1]

class ReleaseNavigationTests(original.InitialNavigationTests):
    def test_exact_staged_production_app(self):
        self.assertEqual((ROOT/"production_quality_preview.py").read_bytes(),b"PRODUCTION_MODE = True\n"+(ROOT/"release-preview/v1.0.8/app.py").read_bytes())
    def make_app(self):
        app=AppTest.from_file(str(ROOT/"production_quality_preview.py"),default_timeout=45)
        app.session_state["market_scan"]=original.seed()
        return app.run()

class ReleaseQualityTests(unittest.TestCase):
    def setUp(self): st.cache_data.clear()
    def test_exact_snapshot(self):
        app=(ROOT/"release-preview/v1.0.8/app.py").read_text(encoding="utf8")
        self.assertEqual((ROOT/"production_quality_preview.py").read_text(encoding="utf8"),"PRODUCTION_MODE = True\n"+app)
        loader=next(n for n in ast.parse(app).body if isinstance(n,ast.FunctionDef) and n.name=="get_analysis_data")
        self.assertNotIn("PRODUCTION_MODE",ast.unparse(loader))
        self.assertIn("repair=False",app)
        self.assertIn("2025-08-01",app)
    def open_stock(self,symbol):
        from initial_navigation import queue_initial
        app=AppTest.from_file(str(ROOT/"production_quality_preview.py"),default_timeout=45)
        app.session_state["market_scan"]=original.seed()
        queue_initial(app.session_state,{"Yahoo代號":symbol,"官方收盤":200.,"官方行情日期":"2026-11-06"})
        return app.run()
    def test_official_replay_downloads_and_original_are_visible(self):
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), patch("yfinance.download",side_effect=lambda *a,**k:source("8358.TWO")), patch("verified_daily_history.fetch_official_month",side_effect=month), patch("verified_daily_history.fetch_official_actions",side_effect=actions):
            app=self.open_stock("8358.TWO")
            self.assertEqual(len(app.exception),0)
            self.assertTrue(any("逐根核對更正" in x.value for x in app.info))
            self.assertFalse(any("行情資料品質異常" in x.value for x in app.error))
            self.assertTrue(any("Adj Close" in x.value for x in app.caption))
            self.assertIn("下載原始Yahoo完整日K CSV",[b.label for b in app.get("download_button")])
    def test_unproven_source_keeps_gate_and_original_period(self):
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), patch("yfinance.download",side_effect=lambda *a,**k:source("6182.TWO")), patch("verified_daily_history.fetch_official_month",side_effect=month), patch("verified_daily_history.fetch_official_actions",side_effect=actions):
            app=self.open_stock("6182.TWO")
            self.assertEqual(len(app.exception),0)
            self.assertTrue(any("行情資料品質異常" in x.value for x in app.error))
            self.assertFalse(any("亞當鏡像｜歷史波段來源"==x.value for x in app.subheader))
            self.assertTrue(any("未猜價" in x.value for x in app.info))
