"""Run production navigation and quality safeguards with full retained history."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
import test_initial_navigation as original

ROOT=Path(__file__).resolve().parents[1]


class ProductionHistoryNavigationTests(original.InitialNavigationTests):
    def make_app(self):
        app=AppTest.from_file(str(ROOT/"production_history_preview.py"),default_timeout=45)
        app.session_state["market_scan"]=original.seed()
        return app.run()

    def test_exact_staged_production_app(self):
        actual=(ROOT/"production_history_preview.py").read_text(encoding="utf-8")
        expected=(ROOT/"release-preview/v1.0.7/app.py").read_text(encoding="utf-8")
        self.assertEqual(actual,"PRODUCTION_MODE = True\n"+expected)

    def test_official_initial_price_is_visible_and_changes_with_stock(self):
        from unittest.mock import patch
        import copy
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), \
             patch("yfinance.download",side_effect=lambda symbol,**kw:original.bars(symbol)):
            app=AppTest.from_file(str(ROOT/"production_history_preview.py"),default_timeout=45)
            state=original.seed()
            state["candidates"][0]["官方收盤"]=100.
            state["candidates"][1]["官方收盤"]=200.
            app.session_state["market_scan"]=state
            app.run()
            app.button(key="initial_chart_open_button").click().run()
            self.assertTrue(any("初選官方收盤：100.00" in c.value for c in app.caption))
            app.button(key="initial_chart_back").click().run()
            app.selectbox(key="initial_chart_choice").set_value(1).run()
            app.button(key="initial_chart_open_button").click().run()
            self.assertTrue(any("初選官方收盤：200.00" in c.value for c in app.caption))
            self.assertFalse(any("初選官方收盤：100.00" in c.value for c in app.caption))
