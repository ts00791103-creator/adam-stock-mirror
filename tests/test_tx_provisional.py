import random
import unittest
from tx_provisional import replay


def bars(prices):
    return [dict(high=x + 1, low=x - 1, close=x) for x in prices]


class ReplayTest(unittest.TestCase):
    def test_both_directions(self):
        for sign in (-1, 1):
            with self.subTest(sign=sign):
                data = bars([100 + sign * x for x in [0, -1, -5, -2, 0, 2, 0, -1, 4, 4, 3, 5]])
                self.assertEqual(replay(data[:8]), [])
                data[9]["low" if sign == 1 else "high"] = 100
                expected = dict(sign=sign, level=100+3*sign, trigger_at=8,
                                source_start=2, target=100+14*sign, invalidated_at=None)
                self.assertEqual(replay(data[:10]), [expected])
                self.assertEqual(replay(data), [dict(expected, invalidated_at=10)])

    def test_flat_and_touch_only(self):
        self.assertEqual(replay(bars([100]*20)), [])
        data = bars([100, 101, 105, 102, 100, 98, 100, 101, 97])
        self.assertEqual(replay(data), [])

    def test_prefix_consistency(self):
        rng = random.Random(44)
        data = bars([100 + rng.randrange(-20, 21) for _ in range(500)])
        full = replay(data)
        self.assertTrue(full)
        for end in range(len(data)+1):
            self.assertEqual(replay(data[:end]), [
                dict(s, invalidated_at=None) if s["invalidated_at"] is not None
                and s["invalidated_at"] >= end else s
                for s in full if s["trigger_at"] < end])
