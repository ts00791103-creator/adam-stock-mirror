import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from streamlit.testing.v1 import AppTest

from fugle_intraday_check import CheckError, check_snapshot, run_intraday_check


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

    def test_auction_window_gap_does_not_hide_closed_session_or_make_a_fake_end(self):
        candles, quote = self.closed_five_minute_fixture()
        result = check_snapshot(candles, quote, "2308.TW", 5, START.replace(hour=22))
        self.assertEqual((result["code"], result["session_state"]), ("SESSION_CLOSED", "closed"))
        self.assertEqual(result["last_bar_kind"], "closing_auction")
        self.assertIsNone(result["expected_bar_end"])
        self.assertEqual(result["missing_bar_times"], [])
        self.assertEqual(result["auction_window_gap_times"], ["2026-11-16T13:25:00+08:00"])
        self.assertEqual(result["received_bar_times"], [row["date"] for row in candles["data"]])
        self.assertEqual(result["bar_count"], len(result["received_bar_times"]))
        self.assertEqual((result["candles_volume"], result["quote_volume"]), (43378, 43378))
        self.assertTrue(result["reported_totals_equal"])
        self.assertFalse(result["comparison_performed"])
        self.assertNotIn("difference", result)

    def test_verified_close_audits_missing_tail_but_unknown_close_does_not(self):
        candles, quote = self.closed_five_minute_fixture()
        candles["data"] = candles["data"][:52]
        now = START.replace(hour=22)
        result = check_snapshot(candles, quote, "2308.TW", 5, now)
        self.assertEqual(result["coverage_end_basis"], "reported_close")
        self.assertEqual(result["coverage_through"], "2026-11-16T13:25:00+08:00")
        self.assertEqual(result["missing_bar_times"], ["2026-11-16T13:20:00+08:00"])
        self.assertEqual(result["auction_window_gap_times"], ["2026-11-16T13:25:00+08:00"])
        self.assertEqual(result["received_bar_times"][-1], "2026-11-16T13:15:00+08:00")
        self.assertNotIn("difference", result)
        del quote["closeTime"]
        result = check_snapshot(candles, quote, "2308.TW", 5, now)
        self.assertEqual(result["coverage_end_basis"], "received_extent")
        self.assertEqual(result["coverage_through"], "2026-11-16T13:15:00+08:00")
        self.assertIsNone(result["reported_close_time"])
        self.assertEqual(result["missing_bars"], 0)

    def test_received_times_are_normalized_without_forwarding_provider_payload(self):
        candles, quote = fixture()
        candles["data"][0]["date"] = "2026-11-16T01:00:00Z"
        candles["data"][0].update(headers={"X-API-KEY": "private-value"}, password="private-password")
        quote["token"] = "private-token"
        result = self.run_snapshot(candles, quote)
        self.assertEqual(result["received_bar_times"],
                         ["2026-11-16T09:00:00+08:00", "2026-11-16T09:01:00+08:00"])
        self.assertEqual(len(result["received_bar_times"]), result["bar_count"])
        self.assertTrue(result["comparison_performed"])
        for field in ("private", "headers", "X-API-KEY", "password", "token", "'open'", "'high'"):
            self.assertNotIn(field, repr(result))

    def test_wrong_quote_statistics_day_preserves_only_valid_candle_coverage(self):
        candles, quote = self.closed_five_minute_fixture()
        candles["data"] = candles["data"][:52]
        quote["total"]["time"] -= 86_400_000_000
        with self.assertRaises(CheckError) as failed:
            check_snapshot(candles, quote, "2308.TW", 5, START.replace(hour=22))
        report = failed.exception.report
        self.assertEqual(report["code"], "STAT_DATE_MISMATCH")
        self.assertEqual(report["coverage_end_basis"], "received_extent")
        self.assertEqual(len(report["received_bar_times"]), 52)
        self.assertNotIn("quote_volume", report)

    def test_interior_gap_is_reported_even_when_session_is_closed(self):
        candles, quote = self.closed_five_minute_fixture()
        del candles["data"][3]
        result = check_snapshot(candles, quote, "2308.TW", 5, START.replace(hour=22))
        self.assertEqual(result["code"], "SESSION_CLOSED")
        self.assertEqual(result["gap_code"], "MISSING_BARS")
        self.assertEqual(result["missing_bar_times"], ["2026-11-16T09:15:00+08:00"])

    def test_delayed_auction_accepts_observed_1333_as_event_not_regular_bar(self):
        candles, quote = self.closed_five_minute_fixture()
        match = START.replace(hour=13, minute=33)
        candles["data"][-1]["date"] = match.isoformat()
        quote.update(isDelayedClose=True, closeTime=int(match.timestamp() * 1_000_000))
        quote["total"]["time"] = quote["closeTime"]
        result = check_snapshot(candles, quote, "2308.TW", 5, START.replace(hour=22))
        self.assertEqual(result["session_state"], "closed")
        self.assertEqual(result["reported_close_time"], match.isoformat())
        self.assertEqual(result["received_bar_times"][-1], match.isoformat())
        self.assertIsNone(result["expected_bar_end"])

    def test_pending_delayed_close_and_open_bar_are_not_reconciled(self):
        candles, quote = self.closed_five_minute_fixture()
        del candles["data"][-1]
        quote.update(isClose=False, isDelayedClose=True)
        result = check_snapshot(candles, quote, "2308.TW", 5, START.replace(hour=13, minute=31))
        self.assertEqual(result["session_state"], "delayed_close_pending")
        self.assertEqual(result["code"], "DELAYED_CLOSE_PENDING")
        self.assertNotIn("difference", result)
        candles, quote = fixture()
        result = self.run_snapshot(candles, quote, NOW - timedelta(seconds=15))
        self.assertEqual(result["code"], "BAR_NOT_CLOSED")
        self.assertEqual(result["received_bar_times"][-1], "2026-11-16T09:01:00+08:00")
        self.assertFalse(result["comparison_performed"])
        self.assertNotIn("difference", result)

    @staticmethod
    def closed_five_minute_fixture():
        candles, quote = fixture()
        candles["timeframe"] = "5"
        candles["data"] = [{**candles["data"][0], "date": (START + timedelta(minutes=i * 5)).isoformat()}
                           for i in [*range(53), 54]]
        candles["data"][-1]["volume"] = 38078
        close = START.replace(hour=13, minute=30)
        quote.update(isClose=True, closeTime=int(close.timestamp() * 1_000_000))
        quote["total"].update(time=quote["closeTime"], tradeVolume=43378)
        return candles, quote


ROOT = Path(__file__).resolve().parents[1]


class CloudRouteTest(unittest.TestCase):
    def test_candidate_route_requires_password_and_manual_action(self):
        candles, quote = FugleIntradayCheckTest.closed_five_minute_fixture()
        report = check_snapshot(candles, quote, "2308.TW", 5, START.replace(hour=22))
        with (
            patch("fugle_intraday_preview._secret", side_effect=lambda name: "test-key" if name == "FUGLE_API_KEY" else "密碼"),
            patch("fugle_intraday_preview.run_intraday_check", return_value=report) as probe,
        ):
            app = AppTest.from_file(str(ROOT / "app.py"))
            app.query_params["view"] = "fugle-intraday"
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("FUGLE-INTRADAY-20261117-4" in item.value for item in app.caption))
            self.assertFalse(app.json)
            probe.assert_not_called()
            app.text_input(key="fugle_intraday_preview_password").input("錯誤").run()
            probe.assert_not_called()
            app.text_input(key="fugle_intraday_preview_password").input("密碼").run()
            app.selectbox(key="fugle_intraday_preview_timeframe").set_value(5).run()
            probe.assert_not_called()
            app.button(key="fugle_intraday_preview_check").click().run()
            probe.assert_called_once_with("2330.TW", 5, "test-key")
            self.assertFalse(app.exception)
            self.assertIn("received_bar_times", app.json[0].value)
            self.assertNotIn("test-key", app.json[0].value)
            self.assertTrue(any("尚未完成同截點對帳" in item.value for item in app.caption))
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
