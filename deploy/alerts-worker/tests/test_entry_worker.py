from dataclasses import replace
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import pandas as pd
from entry_alerts import AlertSettings, evaluate_entry_alerts, telegram_text
from alert_delivery import AlertLedger, deliver_once, send_telegram
from scripts.run_entry_alerts import scan, main, commit_checkpoint


def bars(close=105.):
    return pd.DataFrame({"Open": 104., "High": 110., "Low": 100., "Close": close, "Volume": 1000000.},
                        index=pd.bdate_range("2026-09-01", periods=41))


def breakout():
    data = bars()
    data.iloc[-1] = [110., 114., 109., 112., 2000000.]
    return data


class EntryRuleTests(unittest.TestCase):
    def test_breakout_uses_box_before_signal_and_prior_volume(self):
        data = breakout()
        event = evaluate_entry_alerts(data, "2330.TW", str(data.index[-1].date()))[0]
        self.assertEqual(event["條件"], "箱頂突破")
        self.assertEqual(event["既有箱頂"], 110.)
        self.assertEqual(event["相對成交量"], 2.)
        self.assertEqual(len(event["提醒編號"]), 24)
        self.assertEqual(event, evaluate_entry_alerts(data, "2330.TW", str(data.index[-1].date()))[0])

    def test_rebound_requires_prior_near_bottom_and_positive_body(self):
        data = bars(close=101.)
        data.iloc[-2, data.columns.get_loc("Close")] = 100.5
        data.iloc[-1] = [101., 103., 100., 102., 1000000.]
        day = str(data.index[-1].date())
        self.assertEqual(evaluate_entry_alerts(data, "2330.TW", day)[0]["條件"], "箱底反彈")
        data.iloc[-1, data.columns.get_loc("Open")] = 103.
        self.assertEqual(evaluate_entry_alerts(data, "2330.TW", day), [])

    def test_weak_volume_overextended_and_old_data_do_not_trigger(self):
        data = breakout()
        day = str(data.index[-1].date())
        data.iloc[-1, data.columns.get_loc("Volume")] = 1200000
        self.assertEqual(evaluate_entry_alerts(data, "2330.TW", day), [])
        data.iloc[-1] = [110., 121., 109., 120., 3000000.]
        self.assertEqual(evaluate_entry_alerts(data, "2330.TW", day), [])
        with self.assertRaises(ValueError):
            evaluate_entry_alerts(data, "2330.TW", "2026-12-31")

    def test_bad_ohlc_and_invalid_settings_fail_closed(self):
        data = breakout()
        data.iloc[3, data.columns.get_loc("Close")] = 120.
        with self.assertRaises(ValueError):
            evaluate_entry_alerts(data, "2330.TW", str(data.index[-1].date()))
        with self.assertRaises(ValueError):
            replace(AlertSettings(), breakout_buffer_pct=6).validate()


class DeliveryTests(unittest.TestCase):
    def event(self):
        data = breakout()
        return evaluate_entry_alerts(data, "2330.TW", str(data.index[-1].date()))[0]

    def test_persisted_deduplication_and_no_real_network(self):
        with tempfile.TemporaryDirectory() as temp, patch("alert_delivery.send_telegram", return_value=True) as send:
            path = Path(temp)/"state.json"
            event = self.event()
            self.assertEqual(deliver_once([event], AlertLedger(path), "test", "test")[0]["status"], "sent")
            self.assertEqual(deliver_once([event], AlertLedger(path), "test", "test")[0]["status"], "duplicate_skipped")
            self.assertEqual(send.call_count, 1)
            self.assertEqual(AlertLedger(path).records[event["提醒編號"]]["status"], "sent")

    def test_ambiguous_delivery_not_automatically_resent(self):
        with tempfile.TemporaryDirectory() as temp, patch("alert_delivery.send_telegram", side_effect=OSError("secret")) as send:
            path = Path(temp)/"state.json"
            event = self.event()
            self.assertEqual(deliver_once([event], AlertLedger(path), "test", "test")[0]["status"], "uncertain")
            self.assertEqual(deliver_once([event], AlertLedger(path), "test", "test")[0]["status"], "duplicate_skipped")
            self.assertEqual(send.call_count, 1)

    def test_checkpoint_failure_prevents_send_and_secret_exception_redacted(self):
        with tempfile.TemporaryDirectory() as temp, patch("alert_delivery.send_telegram") as send:
            with self.assertRaises(RuntimeError):
                deliver_once([self.event()], AlertLedger(Path(temp)/"state.json"), "test", "test",
                             checkpoint=lambda: (_ for _ in ()).throw(RuntimeError("state push failed")))
            send.assert_not_called()
        with patch("alert_delivery.urlopen", side_effect=OSError("secret-token")):
            with self.assertRaises(RuntimeError) as caught:
                send_telegram(self.event(), "secret-token", "test")
            self.assertNotIn("secret-token", str(caught.exception))


class WorkerGuardTests(unittest.TestCase):
    def test_stale_source_is_not_a_negative_rule_result(self):
        result = scan(["2330.TW"], AlertSettings(), ["箱頂突破"],
                      datetime(2026, 11, 5, 15, tzinfo=ZoneInfo("Asia/Taipei")),
                      download=lambda *args, **kwargs: breakout())
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["events"], [])

    def test_send_requires_opt_in_and_original_repository_is_never_written(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)/"config.json"
            config.write_text(json.dumps({"enabled": False, "symbols": ["2330.TW"]}), encoding="utf-8")
            with patch("scripts.run_entry_alerts.datetime") as clock, \
                 patch.dict(os.environ, {"ALERTS_ENABLED": "false"}), \
                 patch("scripts.run_entry_alerts.deliver_once") as send:
                clock.now.return_value = datetime(2026, 11, 5, 15, tzinfo=ZoneInfo("Asia/Taipei"))
                with self.assertRaises(ValueError):
                    main(["--config", str(config), "--send"])
                send.assert_not_called()
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "ts00791103-creator/adam-stock-mirror", "GITHUB_REF_NAME": "main"}), \
             patch("scripts.run_entry_alerts.subprocess.run") as git:
            with self.assertRaises(RuntimeError):
                commit_checkpoint("state/alerts.json")
            git.assert_not_called()
