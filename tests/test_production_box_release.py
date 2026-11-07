"""Exercise the exact V1.0.5 production composition before publishing."""
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from test_production_financial_release import ProductionFinancialReleaseTests

ROOT = Path(__file__).resolve().parents[1]


class ProductionBoxReleaseTests(ProductionFinancialReleaseTests):
    def make_app(self):
        return AppTest.from_file(str(ROOT/"production_box_preview.py"), default_timeout=45)

    def test_box_controls_default_to_current_only_and_keep_core_features(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            app = self.make_app().run()
        self.assertEqual(len(app.exception),0)
        self.assertFalse(app.checkbox(key="box_history").value)
        self.assertEqual(app.selectbox(key="large_box_window").value,60)
        self.assertTrue(any("V1.0.5" in item.value for item in app.caption))
        self.assertIn("個人即時價格",[e.label for e in app.expander])
        self.assertTrue(app.checkbox(key="auto_financial_alternative").value)

    def test_large_window_stays_larger_than_changed_small_window(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            app = self.make_app().run()
            app.slider(key="b3_box_window_default_10").set_value(60).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key="large_box_window").options,["120","250"])
        self.assertGreater(app.selectbox(key="large_box_window").value,60)

    def test_published_app_is_exact_staged_source(self):
        staged = (ROOT/"production_box_preview.py").read_text(encoding="utf-8")
        expected = ROOT/"release-preview"/"v1.0.5"/"app.py"
        self.assertEqual(staged,"PRODUCTION_MODE = True\n"+expected.read_text(encoding="utf-8"))

    def test_switching_stocks_retains_analysis_control_and_symbol_results(self):
        import numpy as np
        import pandas as pd
        close=100+np.sin(np.arange(700)/12)*15+np.arange(700)*.01
        frame=pd.DataFrame({"Open":close-1,"High":close+2,"Low":close-2,
                            "Close":close,"Volume":1000000},
                           index=pd.bdate_range("2023-01-02",periods=700))
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), \
             patch("yfinance.download",return_value=frame):
            app=self.make_app().run()
            for code in ("2330","2308","2330"):
                app.text_input(key="adam_stock_query").set_value(code).run()
                self.assertEqual(len(app.exception),0)
                buttons=[b for b in app.button if b.label=="開始亞當鏡像分析"]
                self.assertEqual(len(buttons),1)
                buttons[0].click().run()
                self.assertEqual(len(app.exception),0)
                self.assertTrue(any(code+".TW" in item.value for item in app.caption))
                self.assertEqual(sum(b.label=="開始亞當鏡像分析" for b in app.button),1)
