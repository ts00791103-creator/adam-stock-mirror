import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest
from quote_quality import invalid_price_rows


class QuoteQualityDetailsTests(unittest.TestCase):
    def setUp(self):
        # Other AppTests exercise the same download cache with synthetic valid bars.
        st.cache_data.clear()

    def tearDown(self):
        st.cache_data.clear()

    def test_exact_6148_anomalies_explained_without_mutating_source(self):
        frame = pd.DataFrame({"Open": [10.05, 10.5, 13.45], "High": [10.05, 10.5, 13.55],
                              "Low": [9.94, 10.1, 13.3], "Close": [10.2, 10.6, 13.7]},
                             index=pd.to_datetime(["2020-05-19", "2020-08-21", "2022-06-10"]))
        original = frame.copy(deep=True)
        rows = invalid_price_rows(frame)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["最高"], 10.05)
        self.assertEqual(rows[0]["收盤"], 10.2)
        self.assertTrue(all("最高價" in r["問題"] for r in rows))
        pd.testing.assert_frame_equal(frame, original)
        self.assertEqual(len(invalid_price_rows(frame, limit=2)), 2)

    def test_invalid_finite_and_low_prices_and_missing_columns(self):
        frame = pd.DataFrame({"Open": [1., 1.], "High": [2., 2.],
                              "Low": [1.5, -1.], "Close": [1., np.inf]})
        rows = invalid_price_rows(frame)
        self.assertEqual(len(rows), 2)
        self.assertIn("最低價", rows[0]["問題"])
        self.assertIn("非正數", rows[1]["問題"])
        self.assertEqual(invalid_price_rows(frame.drop(columns="Close")), [])

    def test_real_app_displays_dates_and_stops_before_mirror(self):
        close = np.full(700, 100.)
        frame = pd.DataFrame({"Open": close, "High": close+1, "Low": close-1,
                              "Close": close, "Volume": 1000000},
                             index=pd.bdate_range("2023-01-02", periods=700))
        frame.iloc[5, frame.columns.get_loc("Close")] = 105
        with patch("urllib.request.urlopen", side_effect=OSError("offline test")), \
             patch("yfinance.download", return_value=frame):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"production_app.py"), default_timeout=45).run()
            next(b for b in app.button if b.label == "開始亞當鏡像分析").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("已停止鏡像分析" in e.value for e in app.error))
        self.assertTrue(any("縮短" in i.value for i in app.info))
        self.assertFalse(any("歷史波段來源" in h.value for h in app.subheader))
        details = next(d.value for d in app.dataframe if "日期／時間" in d.value.columns)
        self.assertEqual(len(details), 1)
        self.assertEqual(details.iloc[0]["收盤"], 105)
