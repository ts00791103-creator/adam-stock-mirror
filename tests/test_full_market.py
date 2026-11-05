import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from market_universe import normalize_market, trading_date, shortlist, fetch_universe


class OfficialMarketTests(unittest.TestCase):
    def test_dates_and_share_units_and_excluded_securities(self):
        companies = [{"公司代號": "2330", "公司名稱": "台積電"},
                     {"公司代號": "00878", "公司名稱": "ETF"},
                     {"公司代號": "2308", "公司名稱": "台達電"}]
        result = normalize_market(companies, [{"Code": "2330", "Date": "1151105",
                                              "ClosingPrice": "2,240", "TradeVolume": "1,234,000"}], "上市")
        self.assertEqual(result["公司數"], 2)
        self.assertEqual(result["rows"][0]["官方當日成交量（張）"], 1234)
        self.assertEqual(result["rows"][0]["官方行情日期"], "2026-11-05")
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(trading_date("2026/11/05"), "2026-11-05")
        with self.assertRaises(ValueError):
            trading_date("")

    def test_otc_fields_and_invalid_data(self):
        companies = [{"公司代號": "6488", "公司名稱": "環球晶"},
                     {"公司代號": "1001", "公司名稱": "測試"}]
        result = normalize_market(companies, [
            {"SecuritiesCompanyCode": "6488", "Date": "115/11/05", "Close": "450", "TradingShares": "2500000"},
            {"SecuritiesCompanyCode": "1001", "Date": "1151105", "Close": "--", "TradingShares": "nan"}], "上櫃")
        self.assertEqual(result["rows"][0]["Yahoo代號"], "6488.TWO")
        self.assertEqual(result["rows"][0]["官方當日成交量（張）"], 2500)
        self.assertEqual(len(result["failures"]), 1)

    def test_no_fallback_universe_on_source_failure(self):
        with patch("market_universe.fetch_market", side_effect=OSError("offline")):
            results, failures = fetch_universe(("上市", "上櫃"))
        self.assertEqual(results, [])
        self.assertEqual(len(failures), 2)
        with self.assertRaises(ValueError):
            normalize_market([], [], "上市")

    def test_shortlist_price_volume_boundaries_and_sort(self):
        rows = [{"Yahoo代號": "A", "官方收盤": 100, "官方當日成交量（張）": 1000},
                {"Yahoo代號": "B", "官方收盤": 200, "官方當日成交量（張）": 2000}]
        self.assertEqual([r["Yahoo代號"] for r in shortlist([{"rows": rows}], 100, 200, 1000)], ["B", "A"])
        self.assertEqual(shortlist([{"rows": rows}], 0, 99, 0), [])


class FullMarketUITests(unittest.TestCase):
    def test_batches_do_not_repeat_and_partial_results_and_selection(self):
        frame = pd.DataFrame({"Open": 100., "High": 110., "Low": 100., "Close": 101., "Volume": 1000000},
                             index=pd.bdate_range("2026-01-01", periods=40))
        day = str(frame.index[-1].date())
        rows = [{"代號": str(2000+i), "名稱": "測試"+str(i), "市場": "上市", "Yahoo代號": str(2000+i)+".TW",
                 "官方行情日期": day, "官方收盤": 101., "官方當日成交量（張）": 1000.} for i in range(12)]
        snapshot = ([{"市場": "上市", "公司數": 12, "rows": rows, "failures": []}], [], "2026-11-05 12:00:00")
        source = "from full_market_ui import show_full_market\nimport streamlit as st\nshow_full_market()\nst.text_input('個股',key='adam_stock_query')"
        with patch("full_market_ui.official_snapshot", return_value=snapshot), \
             patch("full_market_ui.screening_data", return_value=frame) as fetch:
            app = AppTest.from_string(source).run()
            next(b for b in app.button if b.key == "market_start").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(fetch.call_count, 0)
            next(b for b in app.button if b.key == "market_next").click().run()
            self.assertEqual(app.session_state["market_scan"]["cursor"], 10)
            self.assertEqual(fetch.call_count, 10)
            self.assertTrue(any("尚未檢查全部" in w.value for w in app.warning))
            next(b for b in app.button if b.key == "market_next").click().run()
            self.assertEqual(fetch.call_count, 12)
            self.assertEqual(len(app.session_state["market_scan"]["checked"]), 12)
            next(b for b in app.button if b.key == "market_use").click().run()
            self.assertEqual(app.text_input[0].value, "2000")
            app.number_input[0].set_value(200).run()
            self.assertTrue(any("條件已變更" in i.value for i in app.info))
            self.assertEqual(len(app.exception), 0)

    def test_date_mismatch_is_not_a_failed_filter(self):
        frame = pd.DataFrame({"Open": 100., "High": 110., "Low": 100., "Close": 101., "Volume": 1000000},
                             index=pd.bdate_range("2026-01-01", periods=40))
        row = {"代號": "2330", "名稱": "台積電", "市場": "上市", "Yahoo代號": "2330.TW",
               "官方行情日期": "2026-11-05", "官方收盤": 101., "官方當日成交量（張）": 1000.}
        with patch("full_market_ui.official_snapshot", return_value=([{"市場": "上市", "公司數": 1, "rows": [row], "failures": []}], [], "now")), \
             patch("full_market_ui.screening_data", return_value=frame):
            app = AppTest.from_string("from full_market_ui import show_full_market\nshow_full_market()").run()
            next(b for b in app.button if b.key == "market_start").click().run()
            next(b for b in app.button if b.key == "market_next").click().run()
            state = app.session_state["market_scan"]
            self.assertEqual(len(state["checked"]), 0)
            self.assertEqual(len(state["failed"]), 1)
            self.assertEqual(len(app.exception), 0)
