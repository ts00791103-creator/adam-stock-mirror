"""Valuation must never fetch network data merely because a checkbox changed."""
from pathlib import Path
from threading import Event
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
import valuation_io
import twse_pe

ROOT = Path(__file__).resolve().parents[1]


class ValuationQueryTests(unittest.TestCase):
    def frame(self):
        close = 100 + np.sin(np.arange(700) / 12) * 15 + np.arange(700) * .01
        return pd.DataFrame({"Open": close-1, "High": close+2, "Low": close-2,
                             "Close": close, "Volume": 1000000},
                            index=pd.bdate_range("2023-01-02", periods=700))

    def test_enable_and_analyze_do_not_fetch_optional_valuation(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")), \
             patch("yfinance.Ticker", side_effect=AssertionError("unexpected valuation I/O")) as ticker, \
             patch("yfinance.download", return_value=self.frame()), \
             patch("twse_pe.official_twse_pe", side_effect=AssertionError("unexpected PE I/O")) as pe:
            app = AppTest.from_file(str(ROOT/"app.py"), default_timeout=45).run()
            app.checkbox(key="b3_valuation_enabled_v1").check().run()
            self.assertEqual(len(app.exception), 0)
            next(b for b in app.button if b.label == "開始亞當鏡像分析").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertIn("亞當鏡像｜歷史波段來源", [s.value for s in app.subheader])
            self.assertTrue(any("目前沒有有效 EPS" in s.value for s in app.info))
            ticker.assert_not_called()
            pe.assert_not_called()

    def test_manual_valuation_does_not_require_live_valuation_sources(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")), \
             patch("yfinance.Ticker", side_effect=AssertionError("unexpected valuation I/O")), \
             patch("yfinance.download", return_value=self.frame()):
            app = AppTest.from_file(str(ROOT/"app.py"), default_timeout=45).run()
            app.checkbox(key="b3_valuation_enabled_v1").check().run()
            app.radio(key="b3_eps_source_v2").set_value("手動輸入 EPS").run()
            app.number_input(key="b3_eps_manual_v2").set_value(10.).run()
            app.checkbox(key="b3_auto_pe_v3").uncheck().run()
            next(b for b in app.button if b.label == "開始亞當鏡像分析").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any(m.value == "160.00" for m in app.metric))
            ticker.assert_not_called()

    def test_timeout_reuses_pending_work_and_does_not_repeat_requests(self):
        release = Event()
        calls = []
        def slow():
            calls.append(1)
            release.wait(2)
            return 12., "ok"
        try:
            result, message = valuation_io.bounded_fetch(("test-timeout",), slow, .01)
            self.assertIsNone(result)
            self.assertIn("超時", message)
            result, message = valuation_io.bounded_fetch(("test-timeout",), slow, .01)
            self.assertIsNone(result)
            self.assertEqual(len(calls), 1)
        finally:
            release.set()
        result, message = valuation_io.bounded_fetch(("test-timeout",), slow, 1)
        self.assertEqual(result, 12.)
        self.assertEqual(len(calls), 1)

    def test_twse_repeated_failure_stops_without_partial_valuation(self):
        import requests
        with patch("twse_pe.requests.Session") as session:
            session.return_value.get.side_effect = requests.Timeout()
            result, error = twse_pe.official_twse_pe("2330.TW")
            self.assertIsNone(result)
            self.assertIn("連續", error)
            self.assertEqual(session.return_value.get.call_count, 2)

    def test_twse_budget_does_not_return_partial_months(self):
        with patch("twse_pe.time.monotonic", side_effect=[0, 15]), \
             patch("twse_pe.requests.Session") as session:
            result, error = twse_pe.official_twse_pe("2330.TW")
            self.assertIsNone(result)
            self.assertIn("超時", error)
            session.return_value.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
