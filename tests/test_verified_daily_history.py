import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal
from official_history import parse_official_month, invalid_candles
from verified_daily_history import verify_daily_closes, original_frame, action_evidence
FIXTURES=Path(__file__).parent/"fixtures"/"verified-daily"


def source(symbol):
    rows=json.loads((FIXTURES/(symbol+".source.json")).read_text(encoding="utf-8"))
    frame=pd.DataFrame(rows).set_index("Date");frame.index=pd.to_datetime(frame.index)
    frame.attrs={"symbol":symbol,"price_basis":"yahoo_auto_adjust_false","raw_quote_notes":[],
                 "source_request":{"symbol":symbol,"period":"10y","interval":"1d","auto_adjust":False,"repair":False}}
    return frame


def month(symbol, value):
    payload=json.loads((FIXTURES/("official_"+symbol+"_"+value+".json")).read_text(encoding="utf-8"))
    official,evidence=parse_official_month(payload,symbol,value)
    return official,evidence,payload


def actions(value):
    return action_evidence(json.loads((FIXTURES/("official_actions_"+value+".json")).read_text(encoding="utf-8")),value)


class VerifiedDailyTests(unittest.TestCase):
    def run_case(self, symbol, **kwargs):
        frame=source(symbol)
        return frame,verify_daily_closes(symbol,frame,fetch_month=kwargs.get("fetch_month",month),
                                         fetch_actions=kwargs.get("fetch_actions",actions))

    def test_real_monthly_replay_seven_complete_shared_basis_cases(self):
        for symbol in ("3105.TWO","8299.TWO","3227.TWO","6274.TWO","1565.TWO","3529.TWO","8358.TWO"):
            with self.subTest(symbol=symbol):
                before,after=self.run_case(symbol)
                self.assertTrue(invalid_candles(before))
                self.assertEqual(invalid_candles(after),[])
                self.assertEqual(len(before),len(after))
                assert_frame_equal(before.drop(columns="Close"),after.drop(columns="Close"))
                self.assertTrue(original_frame(after).equals(before))
                for entry in after.attrs["official_close_verification"]["ledger"]:
                    ref=month(symbol,entry["date"][:7])[0]
                    self.assertEqual(after.loc[pd.Timestamp(entry["date"]),"Close"],ref.loc[pd.Timestamp(entry["date"]),"Close"])
                    self.assertEqual(entry["official_close"],entry["official_previous_close"])

    def test_adjusted_ohl_four_remain_unchanged_and_blocked(self):
        for symbol in ("3260.TWO","5274.TWO","6182.TWO","4123.TWO"):
            with self.subTest(symbol=symbol):
                before,after=self.run_case(symbol)
                self.assertTrue(after.equals(before))
                self.assertEqual(after.attrs["official_close_verification"]["ledger"],[])
                self.assertEqual(invalid_candles(after),invalid_candles(before))

    def test_real_3211_missing_makeup_trading_day_remains_blocked(self):
        before,after=self.run_case("3211.TWO")
        self.assertEqual(invalid_candles(after),["2017-06-27"])
        report=after.attrs["official_close_verification"]
        june=next(m for m in report["months"] if m["month"]=="2017-06")
        self.assertEqual(june["source_missing_official_dates"],["2017-06-03"])
        self.assertEqual(len(report["ledger"]),1)
        self.assertEqual(len(after),len(before))

    def test_other_anomalies_without_action_anchor_remain(self):
        before,after=self.run_case("6530.TWO")
        self.assertEqual(invalid_candles(after),["2021-06-30","2021-07-28"])
        self.assertEqual(len(after.attrs["official_close_verification"]["ledger"]),2)
        self.assertEqual(len(before),len(after))

    def test_download_failure_keeps_original_and_reason(self):
        def fail(*args):raise OSError("offline official source")
        before,after=self.run_case("8358.TWO",fetch_month=fail)
        self.assertTrue(after.equals(before))
        self.assertIn("offline official source",after.attrs["official_close_verification"]["months"][0]["reason"])

    def test_tampered_action_payload_is_rejected(self):
        def tampered(value):
            bundle=actions(value);bundle["payload"]["stat"]="changed";return bundle
        before,after=self.run_case("8358.TWO",fetch_actions=tampered)
        self.assertTrue(after.equals(before))
        self.assertEqual(after.attrs["official_close_verification"]["ledger"],[])

    def test_wrong_event_date_or_prior_close_is_rejected(self):
        def wrong(value):
            bundle=actions(value)
            for table in bundle["payload"]["tables"]:
                fields=table.get("fields",[])
                if "除權息前收盤價" not in fields:continue
                for row in table.get("data",[]):
                    if str(row[fields.index("代號")]).strip()=="8358":row[fields.index("除權息前收盤價")]="999"
            return action_evidence(bundle["payload"],value)
        before,after=self.run_case("8358.TWO",fetch_actions=wrong)
        self.assertTrue(after.equals(before))

    def test_unproven_source_or_intraday_does_not_fetch_or_correct(self):
        for changes in ({"interval":"1wk"},{"auto_adjust":True},{"symbol":"2330.TW"}):
            frame=source("8358.TWO");frame.attrs["source_request"].update(changes)
            with patch("verified_daily_history.fetch_official_month",side_effect=AssertionError("must not fetch")):
                after=verify_daily_closes("8358.TWO",frame)
            self.assertTrue(after.equals(frame))
            self.assertEqual(after.attrs["official_close_verification"]["ledger"],[])

    def test_month_date_mismatch_blocks_even_matching_target(self):
        def missing(symbol,value):
            official,evidence,payload=month(symbol,value)
            return official.iloc[1:],evidence,payload
        before,after=self.run_case("8358.TWO",fetch_month=missing)
        self.assertTrue(after.equals(before))

    def test_valid_prices_and_source_frame_never_mutated(self):
        frame=source("8358.TWO");frame.loc[pd.Timestamp("2018-06-28"),"Close"]=40.
        frozen=frame.copy(deep=True)
        after=verify_daily_closes("8358.TWO",frame,fetch_month=lambda *args:self.fail("unexpected fetch"))
        assert_frame_equal(after,frozen)
        before=source("8358.TWO");frozen=before.copy(deep=True)
        verify_daily_closes("8358.TWO",before,fetch_month=month,fetch_actions=actions)
        assert_frame_equal(before,frozen)
