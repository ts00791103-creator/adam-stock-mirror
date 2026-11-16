import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from streamlit.testing.v1 import AppTest

from fugle_intraday_check import check_snapshot, run_intraday_check


TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 16, 9, tzinfo=TZ)
NOW = START + timedelta(minutes=2, seconds=10)


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz)


def fixture():
    header = {"symbol": "2308", "date": "2026-11-16", "exchange": "TWSE", "market": "TSE", "type": "EQUITY"}
    bars = [dict(date=(START + timedelta(minutes=i)).isoformat(), open=100, high=103, low=99,
                 close=102, volume=100, average=200) for i in range(2)]
    quote = {**header, "total": {"time": int((NOW - timedelta(seconds=15)).timestamp() * 1_000_000),
                                "tradeVolume": 200}}
    return {**header, "timeframe": "1", "data": bars}, quote


class FugleIntradayCheckTest(unittest.TestCase):
    def run_snapshot(self, candles, quote, now=NOW):
        return check_snapshot(candles, quote, "2308.TW", 1, now)

    def test_same_window_validates_volume_in_lots_without_creating_live_feed(self):
        result = self.run_snapshot(*fixture())
        self.assertEqual(result["status"], "同時段量一致")
        self.assertEqual((result["candles_volume"], result["quote_volume"], result["unit"]), (200, 200, "張"))
        self.assertIn("延遲及收棒狀態未核實", result["eligibility"])

    def test_volume_gap_or_duplicate_or_naive_time_fails(self):
        for field, value in (("volume", None), ("date", START.isoformat()),
                             ("date", "2026-11-16T09:01:00")):
            candles, quote = fixture()
            candles["data"][-1][field] = value
            self.assertRaises(ValueError, self.run_snapshot, candles, quote)

    def test_older_than_one_interval_or_unclosed_does_not_compare(self):
        candles, quote = fixture()
        self.assertEqual(self.run_snapshot(candles, quote, NOW + timedelta(minutes=2))["status"], "待核：統計時間已過期")
        self.assertEqual(self.run_snapshot(candles, quote, NOW - timedelta(seconds=15))["status"], "待核：最新分 K 時間尚未結束")

    def test_mismatched_total_is_visible(self):
        candles, quote = fixture()
        quote["total"]["tradeVolume"] = 210
        result = self.run_snapshot(candles, quote)
        self.assertEqual((result["status"], result["difference"]), ("待核：同時段量不符", -10))

    def test_quote_in_next_interval_or_close_auction_is_not_compared(self):
        candles, quote = fixture()
        for timestamp in (NOW, START + timedelta(hours=4, minutes=30)):
            other = deepcopy(quote)
            other["total"]["time"] = int(timestamp.timestamp() * 1_000_000)
            self.assertEqual(self.run_snapshot(candles, other, timestamp)["status"], "待核：分 K 與統計截點不同")

    def test_market_and_http_permissions(self):
        candles, quote = fixture()
        quote["exchange"] = "TPEx"
        self.assertRaises(ValueError, self.run_snapshot, candles, quote)
        with patch("fugle_intraday_check._request", side_effect=HTTPError("", 403, "", {}, None)) as get:
            self.assertEqual(run_intraday_check("2308.TW", 1, "test-key")["status"], "富果查詢未通過（HTTP 403）")
            self.assertEqual(get.call_count, 1)

    def test_market_optional_and_integral_json_numbers_supported(self):
        candles, quote = fixture()
        del candles["market"]
        candles["data"][0]["volume"] = 100.0
        quote["total"]["tradeVolume"] = 200.0
        self.assertEqual(self.run_snapshot(candles, quote)["difference"], 0)

    def test_missing_bars_report_observed_range_without_volume_comparison(self):
        candles, quote = fixture()
        candles["data"][-1]["date"] = (START + timedelta(minutes=3)).isoformat()
        result = self.run_snapshot(candles, quote, START + timedelta(minutes=4))
        self.assertEqual(result["code"], "MISSING_BARS")
        self.assertEqual(result["missing_bars"], 2)
        self.assertEqual(result["first_bar"], START.isoformat())
        self.assertTrue(result["last_bar_start"].endswith("09:03:00+08:00"))
        self.assertNotIn("difference", result)

    def test_validations_report_missing_field_without_exposing_payload(self):
        candles, quote = fixture()
        del quote["total"]["tradeVolume"]
        quote["unknown"] = "private payload"
        with (patch("fugle_intraday_check._request", side_effect=[candles, quote]) as fetch,
              patch("fugle_intraday_check.datetime", FixedDateTime)):
            result = run_intraday_check("2308.TW", 1, "private key")
        self.assertEqual((result["stage"], result["endpoint"], result["code"], result["field"]),
                         ("validate", "quote", "MISSING_FIELD", "total.tradeVolume"))
        self.assertNotIn("private", repr(result))
        self.assertEqual(result["bar_count"], 2)
        self.assertEqual(fetch.call_count, 2)

    def test_distinguishes_transport_endpoint_and_suppresses_raw_exception(self):
        candles, _ = fixture()
        with patch("fugle_intraday_check._request", side_effect=[candles, URLError("private detail")]):
            result = run_intraday_check("2308.TW", 1, "test-key")
        self.assertEqual((result["stage"], result["endpoint"], result["code"]), ("fetch", "quote", "NETWORK"))
        self.assertNotIn("private", repr(result))

    def test_closed_quote_never_claims_same_window_live_comparison(self):
        candles, quote = fixture()
        quote["isClose"] = True
        result = self.run_snapshot(candles, quote)
        self.assertEqual(result["code"], "SESSION_CLOSED")
        self.assertNotIn("difference", result)


ROOT = Path(__file__).resolve().parents[1]


class CloudRouteTest(unittest.TestCase):
    def test_candidate_route_requires_password_and_manual_action(self):
        with (
            patch("fugle_intraday_preview._secret", side_effect=lambda name: "test-key" if name == "FUGLE_API_KEY" else "密碼"),
            patch("fugle_intraday_preview.run_intraday_check", return_value={"status": "測試狀態"}) as probe,
        ):
            app = AppTest.from_file(str(ROOT / "app.py"))
            app.query_params["view"] = "fugle-intraday"
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("FUGLE-INTRADAY-20261116-2" in item.value for item in app.caption))
            probe.assert_not_called()
            app.text_input(key="fugle_intraday_preview_password").input("錯誤").run()
            probe.assert_not_called()
            app.text_input(key="fugle_intraday_preview_password").input("密碼").run()
            app.selectbox(key="fugle_intraday_preview_timeframe").set_value(5).run()
            probe.assert_not_called()
            app.button(key="fugle_intraday_preview_check").click().run()
            probe.assert_called_once_with("2330.TW", 5, "test-key")
            self.assertFalse(app.exception)
            self.assertTrue(any("當沖不可判定" in item.value for item in app.warning))

    def test_production_ignores_direct_candidate_query(self):
        with (
            patch("urllib.request.urlopen", side_effect=OSError("offline test")),
            patch("fugle_intraday_preview.show_fugle_intraday_preview") as preview,
        ):
            app = AppTest.from_file(str(ROOT / "production_app.py"))
            app.query_params["view"] = "fugle-intraday"
            app.run()
        self.assertFalse(app.exception)
        preview.assert_not_called()
        self.assertFalse(any("富果分 K" in item.label for item in app.button))
