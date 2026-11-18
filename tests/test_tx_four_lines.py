import unittest
from datetime import datetime

from tx_four_lines import classify, read_replay_bars, replay


class FourLineTests(unittest.TestCase):
    def test_same_outer_edge_discriminates_wick_from_confirmation(self):
        bars = read_replay_bars()
        rows = {row["time"]: row for row in replay(bars)}
        self.assertEqual(len(rows), 285)
        wick = rows["2026-11-17T13:45:00+08:00"]
        self.assertEqual((wick["lower_outer"], wick["low"], wick["close"]), (39996, 39761, 40073))
        self.assertEqual(wick["lower_event"], "wick_return")
        self.assertFalse(wick["lower_one"] or wick["lower_two"])
        self.assertTrue(rows["2026-11-17T18:00:00+08:00"]["lower_one"])
        self.assertTrue(rows["2026-11-17T19:00:00+08:00"]["lower_two"])
        self.assertFalse(rows["2026-11-18T11:45:00+08:00"]["lower_two"])
        self.assertEqual(sum(row[f"{side}_event"] == "wick_return" for row in rows.values()
                             for side in ("lower", "upper")), 8)

    def test_missing_bar_clears_confirmation_and_prior_history(self):
        bars = read_replay_bars()
        i = next(i for i, bar in enumerate(bars) if bar["time"] == "2026-11-17T18:00:00+08:00")
        bars[i] = {**bars[i], "trades": 0}
        rows = replay(bars)
        self.assertEqual(rows[i]["lower_event"], "missing_bar")
        self.assertEqual(rows[i + 1]["lower_event"], "no_confirmed_box")
        self.assertNotIn("lower_two", rows[i + 1])

    def test_equal_outer_edge_resets_streak(self):
        self.assertEqual(classify(dict(trades=1, high=112, close=110), 100, 110, 1, 1), ("touch", 0))

    def test_replay_has_no_future_information_and_retains_expiry_end(self):
        bars = read_replay_bars()
        full = replay(bars)
        self.assertEqual(datetime.fromisoformat(bars[-1]["time"]).strftime("%H:%M"), "13:30")
        self.assertEqual(bars[-1]["minutes"], 45)
        self.assertTrue(all(replay(bars[:i]) == full[:i] for i in range(1,len(bars) + 1)))
