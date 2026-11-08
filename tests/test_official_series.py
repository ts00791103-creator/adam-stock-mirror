import copy
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import Mock
import pandas as pd
from pandas.testing import assert_frame_equal
from official_history import parse_official_month, OfficialHistoryError
from official_series import OfficialArchive, assemble_official_series, aggregate_official_weeks, compare_provider, parse_bundle

FIXTURES=Path(__file__).parent/"fixtures/official-series"

def bundle(symbol="3211.TWO",month="2017-06"):
    payload=json.loads((FIXTURES/f"{symbol}_{month}.json").read_text(encoding="utf8"))
    _,evidence=parse_official_month(payload,symbol,month)
    return {"symbol":symbol,"month":month,"payload":payload,"evidence":evidence,"retrieved_at_utc":"saved fixture, not fresh request"}

class OfficialSeriesTests(unittest.TestCase):
    def test_all_seven_previously_missing_days_are_real_official_rows(self):
        for code,month,day in [("3105","2025-08","2025-08-01"),("3211","2017-06","2017-06-03"),("5274","2017-06","2017-06-03"),("8086","2017-06","2017-06-03"),("4123","2017-09","2017-09-30"),("6223","2017-09","2017-09-30"),("6146","2021-04","2021-04-06")]:
            with self.subTest(code=code):
                data=bundle(code+".TWO",month)
                frame,report=assemble_official_series(code+".TWO",month+"-01",str(pd.Timestamp(month+"-01")+pd.offsets.MonthEnd(0))[:10],[data])
                self.assertIn(pd.Timestamp(day),frame.index)
                self.assertFalse(report["production_ready"])
    def test_saturday_is_in_same_week_without_fill_or_drop(self):
        frame,_=assemble_official_series("3211.TWO","2017-06-01","2017-06-30",[bundle()])
        weekly=aggregate_official_weeks(frame)
        days=frame.loc["2017-06-01":"2017-06-04"]
        row=weekly.loc["2017-05-29"]
        self.assertEqual(row.Volume,days.Volume.sum())
        self.assertEqual(row.Close,frame.loc["2017-06-03","Close"])
        self.assertEqual(row.Open,days.Open.iloc[0])
        self.assertEqual(row.High,days.High.max())
        self.assertEqual(row.Low,days.Low.min())
        self.assertEqual(weekly.Volume.sum(),frame.Volume.sum())
    def test_missing_month_and_mixed_market_never_assemble(self):
        with self.assertRaises(OfficialHistoryError):assemble_official_series("3211.TWO","2017-06-01","2017-07-31",[bundle()])
        with self.assertRaises(OfficialHistoryError):assemble_official_series("3211.TW","2017-06-01","2017-06-30",[bundle()])
        with self.assertRaises(OfficialHistoryError):assemble_official_series("3211.TWO","2017-06-01","2017-06-30",[bundle(),bundle()])
    def test_tampered_payload_or_evidence_is_rejected(self):
        for target in ("payload","evidence"):
            data=bundle()
            if target=="payload":data["payload"]["tables"][0]["data"][0][3]="999"
            else:data["evidence"]["volume_precision"]="exact shares"
            with self.assertRaises(OfficialHistoryError):parse_bundle(data)
    def test_comparison_never_inserts_or_converts_provider(self):
        official,_=assemble_official_series("3211.TWO","2017-06-01","2017-06-30",[bundle()])
        provider=official.drop(pd.Timestamp("2017-06-03")).copy()
        provider.loc[:,["Open","High","Low","Close"]]*=.5
        before=provider.copy(deep=True)
        report=compare_provider(provider,official)
        self.assertEqual(report["provider_missing_official_dates"],["2017-06-03"])
        self.assertTrue(report["price_differences"])
        self.assertFalse(report["local_patch_applied"])
        assert_frame_equal(provider,before)
    def test_unresolved_official_no_ohlc_stops_weekly(self):
        frame,_=assemble_official_series("3211.TWO","2017-06-01","2017-06-30",[bundle()])
        frame.attrs["official_series"]["unavailable_ohlc_rows"]=[{"date":"2017-06-05","reason":"unknown, not declared suspension"}]
        with self.assertRaises(OfficialHistoryError):aggregate_official_weeks(frame)
    def test_cache_replays_and_http_403_does_not_retry_host(self):
        data=bundle()
        frame,evidence=parse_official_month(data["payload"],"3211.TWO","2017-06")
        fetch=Mock(return_value=(frame,evidence,data["payload"]))
        with tempfile.TemporaryDirectory() as folder:
            archive=OfficialArchive(folder,fetcher=fetch)
            archive.get("3211.TWO","2017-06");archive.get("3211.TWO","2017-06")
            self.assertEqual(fetch.call_count,1)
        denied=Mock(side_effect=HTTPError("https://www.tpex.org.tw/",403,"Forbidden",{},None))
        with tempfile.TemporaryDirectory() as folder:
            archive=OfficialArchive(folder,fetcher=denied)
            with self.assertRaises(HTTPError):archive.get("3211.TWO","2017-06")
            with self.assertRaises(OfficialHistoryError):archive.get("5274.TWO","2017-06")
            self.assertEqual(denied.call_count,1)
    def test_period_before_official_endpoint_start_is_rejected(self):
        with self.assertRaises(OfficialHistoryError):assemble_official_series("2330.TW","2009-12-01","2009-12-31",[])
        with self.assertRaises(OfficialHistoryError):assemble_official_series("3211.TWO","1993-12-01","1993-12-31",[])
