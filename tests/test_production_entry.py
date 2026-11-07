"""Exercise the production entrypoint without network access or live credentials."""
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class ProductionEntryTests(unittest.TestCase):
    def make_app(self):
        return AppTest.from_file(str(ROOT / "production_app.py"), default_timeout=45)

    def test_core_controls_and_experimental_panels_are_separated(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline test")):
            app = self.make_app().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "亞當鏡像分析 V1.0")
        selectors = {item.label: item for item in app.selectbox}
        self.assertEqual(selectors["選擇市場"].options, ["台灣股票／ETF"])
        self.assertEqual(selectors["K線週期"].options, ["日K", "週K"])
        checkbox_labels = [item.label for item in app.checkbox]
        self.assertNotIn("啟用估價", checkbox_labels)
        self.assertFalse(any("測試" in label for label in checkbox_labels))
        panels = [item.label for item in app.expander]
        self.assertFalse(any("估價" in label for label in panels))
        self.assertIn("個人即時價格", panels)
        self.assertIn("自選名單選股", panels)
        self.assertIn("全台股選股（上市＋上櫃）", panels)
        self.assertIn("尋找股票", [item.value for item in app.subheader])
        self.assertIn("市場範圍", selectors)
        self.assertIn("顯示關鍵壓力與支撐點", checkbox_labels)
        self.assertIn("顯示成交量集中區（估算）", checkbox_labels)
        self.assertIn("成交量分布估算設定", panels)
        self.assertEqual(len(app.multiselect), 0)

    def test_production_analysis_uses_the_same_core_pipeline(self):
        close = 100 + np.sin(np.arange(700) / 12) * 15 + np.arange(700) * 0.01
        frame = pd.DataFrame({"Open": close - 1, "High": close + 2,
                              "Low": close - 2, "Close": close, "Volume": 1000000},
                             index=pd.bdate_range("2023-01-02", periods=700))
        with patch("urllib.request.urlopen", side_effect=OSError("offline test")), \
             patch("yfinance.download", return_value=frame):
            app = self.make_app().run()
            button = next(item for item in app.button if item.label == "開始亞當鏡像分析")
            app = button.click().run()
        self.assertEqual(len(app.exception), 0)
        headings = [item.value for item in app.subheader]
        self.assertIn("亞當鏡像｜歷史波段來源", headings)
        self.assertIn("自動箱型突破目標分析", headings)
        self.assertFalse(any("估價" in heading for heading in headings))
        panels = [item.label for item in app.expander]
        self.assertIn("關鍵壓力與支撐點", panels)
        self.assertIn("成交量集中區｜POC與價值區（估算版）", panels)

    def test_production_watchlist_can_screen_and_select_stock(self):
        frame = pd.DataFrame({"Open": 100., "High": 110., "Low": 100.,
                              "Close": 101., "Volume": 1000000},
                             index=pd.bdate_range("2026-01-02", periods=40))
        with patch("urllib.request.urlopen", side_effect=OSError("offline test")), \
             patch("screener_ui.screening_data", return_value=frame):
            app = self.make_app().run()
            app.text_area[0].set_value("2330,2308")
            next(b for b in app.button if b.key == "screen_run").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.session_state["screen_result"][1]), 2)
            next(b for b in app.button if b.key == "screen_use").click().run()
            self.assertEqual(next(i for i in app.text_input if i.key == "adam_stock_query").value, "2330")
            self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
