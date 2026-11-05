import unittest
from unittest.mock import patch
from pathlib import Path
import pandas as pd
from stock_screener import resolve_watchlist, screen_frame
from streamlit.testing.v1 import AppTest


def bars(close=101, volume=1000000):
    return pd.DataFrame({"Open": 100., "High": 110., "Low": 100., "Close": close,
                         "Volume": volume}, index=pd.bdate_range("2026-01-01", periods=40))


class ScreenerTests(unittest.TestCase):
    def test_names_suffixes_duplicates_unknown_and_market_resolution(self):
        items, failures = resolve_watchlist("2330,台積電\n6488.TWO，2330.TW,不存在",
                                           [("2330", "台積電", "上市")])
        self.assertEqual([i[0] for i in items], ["2330.TW", "6488.TWO"])
        self.assertEqual(len(failures), 1)
        self.assertEqual(resolve_watchlist("", [])[0], [])

    def test_over_limit_is_rejected_not_silently_truncated(self):
        with self.assertRaises(ValueError):
            resolve_watchlist(",".join(f"{1000+i}.TW" for i in range(31)), [])

    def test_box_and_volume_filters_at_boundaries(self):
        row = screen_frame(bars(), mode="接近箱底", near_pct=1.01, min_lots=1000,
                           min_price=101, max_price=101)
        self.assertTrue(row["符合"])
        self.assertEqual(row["箱底"], 100)
        self.assertEqual(row["20日均量（張）"], 1000)
        self.assertFalse(screen_frame(bars(), min_lots=1001)["符合"])
        self.assertFalse(screen_frame(bars(), mode="接近箱底", near_pct=.5)["符合"])

    def test_broken_box_never_used_as_current_support(self):
        frame = bars()
        frame.iloc[-1, frame.columns.get_loc("Close")] = 120
        frame.iloc[-1, frame.columns.get_loc("High")] = 121
        self.assertFalse(screen_frame(frame, mode="接近箱底")["符合"])
        self.assertIsNone(screen_frame(frame)["箱底"])

    def test_invalid_and_insufficient_data_are_failures(self):
        for frame in [bars().iloc[:10], bars().drop(columns="Volume"),
                      bars(volume=-1), bars(close=float("nan")), bars(close=120)]:
            with self.subTest(length=len(frame)), self.assertRaises(ValueError):
                screen_frame(frame)

    def test_zero_volume_ratio_is_unknown(self):
        row = screen_frame(bars(volume=0))
        self.assertIsNone(row["當日量／前20日均量"])

    def test_ui_screening_survives_rerun_and_uses_selected_stock(self):
        source = "from screener_ui import show_screener\nimport streamlit as st\nshow_screener([('2330','台積電','上市'),('2308','台達電','上市')])\nst.text_input('個股', key='adam_stock_query')"
        with patch("screener_ui.screening_data", return_value=bars()):
            app = AppTest.from_string(source).run()
            app.text_area[0].set_value("2330,2308,錯字")
            next(b for b in app.button if b.key == "screen_run").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.session_state["screen_result"][1]), 2)
            self.assertEqual(len(app.session_state["screen_result"][2]), 1)
            next(b for b in app.button if b.key == "screen_use").click().run()
            self.assertEqual(app.text_input[0].value, "2330")
            app.number_input[0].set_value(200).run()
            self.assertTrue(any("條件或名單已變更" in i.value for i in app.info))
            self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
