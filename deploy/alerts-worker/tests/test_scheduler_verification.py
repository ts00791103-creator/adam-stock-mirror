from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from alert_delivery import AlertLedger, deliver_once
from scripts import verify_scheduler as verify


class SchedulerVerificationTests(unittest.TestCase):
    def test_system_event_uses_real_delivery_dedup_without_stock_formatter(self):
        with tempfile.TemporaryDirectory() as temp, patch("alert_delivery.send_telegram") as stock_send:
            checkpoints, sent = [], []
            state = Path(temp)/"state.json"
            def checkpoint():
                checkpoints.append(AlertLedger(state).records[verify.EVENT_ID]["status"])
            def transport(event, token, chat):
                self.assertEqual(checkpoints, ["pending"])
                sent.append(event)
            event = {"提醒編號": verify.EVENT_ID}
            self.assertEqual(deliver_once([event], AlertLedger(state), "test", "test",
                checkpoint=checkpoint, transport=transport)[0]["status"], "sent")
            self.assertEqual(deliver_once([event], AlertLedger(state), "test", "test",
                checkpoint=checkpoint, transport=transport)[0]["status"], "duplicate_skipped")
            self.assertEqual(checkpoints, ["pending", "sent"])
            self.assertEqual(len(sent), 1)
            stock_send.assert_not_called()

    def test_expired_and_manual_invocations_never_send(self):
        with patch.object(verify, "datetime") as clock, patch.object(verify, "system_transport") as send:
            clock.now.return_value = datetime(2026, 11, 7, tzinfo=timezone.utc)
            self.assertEqual(verify.main(), 0)
            clock.now.return_value = datetime(2026, 11, 5, 23, 15, tzinfo=timezone.utc)
            with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}):
                with self.assertRaises(ValueError):
                    verify.main()
            send.assert_not_called()
