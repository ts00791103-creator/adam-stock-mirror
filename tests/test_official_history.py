import copy
import json
from pathlib import Path
import unittest

import pandas as pd
from official_history import (OfficialHistoryError, invalid_candles, parse_official_month,
                              preview_close_repairs, request_spec, month_differences)

FIXTURES = Path(__file__).parent / "fixtures" / "official-history"


class OfficialHistoryTests(unittest.TestCase):
    def payload(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))

    def gold(self):
        frame, evidence = parse_official_month(self.payload("tpex_8358_201806.json"), "8358.TWO", "2018-06")
        return frame, evidence

    def source(self, official, symbol="8358.TWO"):
        source = official.copy(deep=True)
        source.attrs = {"symbol": symbol, "price_basis": "yahoo_auto_adjust_false"}
        return source

    def test_real_gold_fixture_matches_official_observation(self):
        frame, evidence = self.gold()
        self.assertEqual(frame.loc["2018-06-28", ["Open", "High", "Low", "Close"]].tolist(), [40.35, 40.75, 40, 40])
        self.assertEqual(frame.loc["2018-06-28", "Volume"], 4356000)
        self.assertIn("仟股", evidence["volume_precision"])
        self.assertEqual(invalid_candles(frame), [])

    def test_real_twse_fields_are_mapped_not_guessed(self):
        frame, evidence = parse_official_month(self.payload("twse_2330_202611.json"), "2330.TW", "2026-11")
        self.assertEqual(frame.loc["2026-11-06", "Close"], 2135)
        self.assertEqual(frame.loc["2026-11-06", "Volume"], 110714587)
        self.assertEqual(evidence["price_basis"], "official_raw_unadjusted")

    def test_no_regular_ohlc_days_are_preserved_as_unavailable(self):
        frame, evidence = parse_official_month(self.payload("tpex_2924_202112.json"), "2924.TWO", "2021-12")
        self.assertNotIn(pd.Timestamp("2021-12-02"), frame.index)
        self.assertIn("2021-12-02", [r["date"] for r in evidence["unavailable_rows"]])
        self.assertEqual(frame.loc["2021-12-01", "Close"], 17.1)

    def test_close_repair_is_a_copy_with_audit_evidence(self):
        official, evidence = self.gold()
        source = self.source(official)
        source.loc["2018-06-28", "Close"] = 37
        original = source.copy(deep=True)
        fixed, ledger = preview_close_repairs(source, official, evidence)
        pd.testing.assert_frame_equal(source, original)
        self.assertEqual(fixed.loc["2018-06-28", "Close"], 40)
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["original_close"], 37)
        self.assertEqual(ledger[0]["payload_sha256"], evidence["payload_sha256"])
        pd.testing.assert_frame_equal(source.drop(columns="Close"), fixed.drop(columns="Close"))

    def test_split_or_adjusted_ohl_cannot_be_mixed(self):
        official, evidence = self.gold()
        source = self.source(official)
        source.loc[:, ["Open", "High", "Low"]] *= .5
        source.loc[:, "Close"] = 1
        fixed, ledger = preview_close_repairs(source, official, evidence)
        self.assertEqual(ledger, [])
        pd.testing.assert_frame_equal(source, fixed)

    def test_valid_but_different_close_is_not_silently_changed(self):
        official, evidence = self.gold()
        source = self.source(official)
        source.loc["2018-06-28", "Close"] = 40.5
        fixed, ledger = preview_close_repairs(source, official, evidence)
        self.assertEqual(fixed.loc["2018-06-28", "Close"], 40.5)
        self.assertEqual(ledger, [])

    def test_missing_or_nonpositive_values_remain_blocked(self):
        official, evidence = self.gold()
        for value in (float("nan"), 0, -1):
            source = self.source(official)
            source.loc["2018-06-28", "Close"] = value
            fixed, ledger = preview_close_repairs(source, official, evidence)
            self.assertEqual(ledger, [])
            self.assertIn("2018-06-28", invalid_candles(fixed))

    def test_float32_boundary_representation_is_logged_without_new_invalid_bar(self):
        official, evidence = self.gold()
        source = self.source(official)
        source.loc["2018-06-28", "Low"] = 40.0000004
        source.loc["2018-06-28", "Close"] = 37
        fixed, ledger = preview_close_repairs(source, official, evidence)
        self.assertEqual(invalid_candles(fixed), [])
        self.assertEqual(ledger[0]["official_close"], 40)
        self.assertLess(abs(ledger[0]["float_alignment_delta"]), .00001)

    def test_real_price_gap_at_boundary_is_not_clamped(self):
        official, evidence = self.gold()
        source = self.source(official)
        source.loc["2018-06-28", "Low"] = 40.004
        source.loc["2018-06-28", "Close"] = 37
        fixed, ledger = preview_close_repairs(source, official, evidence)
        self.assertEqual(ledger, [])
        self.assertIn("2018-06-28", invalid_candles(fixed))

    def test_valid_adjusted_candles_are_still_reported_as_official_differences(self):
        official, evidence = self.gold()
        source = self.source(official)
        source.loc[:, ["Open", "High", "Low", "Close"]] *= 2
        self.assertEqual(invalid_candles(source), [])
        fixed, ledger = preview_close_repairs(source, official, evidence)
        self.assertEqual(ledger, [])
        self.assertEqual(len(month_differences(fixed, official)), len(official) * 4)

    def test_wrong_stock_or_unknown_basis_rejected(self):
        official, evidence = self.gold()
        for symbol, basis in (("2924.TWO", "yahoo_auto_adjust_false"), ("8358.TWO", "adjusted")):
            source = self.source(official, symbol)
            source.attrs["price_basis"] = basis
            with self.assertRaises(OfficialHistoryError):
                preview_close_repairs(source, official, evidence)

    def test_modified_official_frame_rejected(self):
        official, evidence = self.gold()
        source = self.source(official)
        official.loc["2018-06-28", "Close"] = 40.5
        with self.assertRaises(OfficialHistoryError):
            preview_close_repairs(source, official, evidence)

    def test_partial_missing_ohlc_rejected(self):
        payload = self.payload("tpex_8358_201806.json")
        payload["tables"][0]["data"][0][3] = "--"
        with self.assertRaises(OfficialHistoryError):
            parse_official_month(payload, "8358.TWO", "2018-06")

    def test_wrong_response_identity_or_month_rejected(self):
        payload = self.payload("tpex_8358_201806.json")
        for field, value in (("code", "2924"), ("date", "20261101"), ("stat", "error")):
            bad = copy.deepcopy(payload)
            bad[field] = value
            with self.assertRaises(OfficialHistoryError):
                parse_official_month(bad, "8358.TWO", "2018-06")

    def test_duplicate_or_cross_month_rows_rejected(self):
        payload = self.payload("tpex_8358_201806.json")
        for day in ("107/06/01", "107/07/01"):
            bad = copy.deepcopy(payload)
            bad["tables"][0]["data"][1][0] = day
            with self.assertRaises(OfficialHistoryError):
                parse_official_month(bad, "8358.TWO", "2018-06")

    def test_duplicate_source_dates_rejected(self):
        official, evidence = self.gold()
        source = self.source(pd.concat([official, official.iloc[:1]]))
        with self.assertRaises(OfficialHistoryError):
            preview_close_repairs(source, official, evidence)

    def test_symbol_and_month_input_validation(self):
        for symbol, month in (("2330", "2026-11"), ("2330.TWO/../../", "2026-11"),
                              ("0050.TW", "2026-11"), ("2330.TW", "2026-13")):
            with self.assertRaises(OfficialHistoryError):
                request_spec(symbol, month)


if __name__ == "__main__":
    unittest.main()
