import unittest
import pandas as pd
from support_resistance import key_levels


def candles(prices):
    return pd.DataFrame({"Open": prices, "Close": prices,
                         "High": [p+1 for p in prices], "Low": [p-1 for p in prices]},
                        index=pd.date_range("2025-01-01", periods=len(prices)))


class LevelsTests(unittest.TestCase):
    def test_right_hand_confirmation_and_no_unconfirmed_endpoint(self):
        df = candles([10,11,12,20,12,11,10,9,8,7,20])
        result = key_levels(df)
        self.assertTrue(any(r["參考價"] == 21 for r in result))
        self.assertTrue(all(r["最近確認日"] <= df.index[-1].isoformat() for r in result))
        self.assertFalse(key_levels(candles([10,11,12,13,14,15,30])))

    def test_flat_market_does_not_invent_pivots(self):
        self.assertEqual(key_levels(candles([10]*20)), [])

    def test_corrupt_or_unsorted_data_rejected(self):
        df = candles([10]*20)
        df.iloc[0, df.columns.get_loc("High")] = 1
        with self.assertRaises(ValueError): key_levels(df)
        with self.assertRaises(ValueError): key_levels(candles([10]*20).iloc[::-1])

    def test_group_does_not_bridge_large_range(self):
        prices = [100,100,100,110,100,100,100,110.7,100,100,100,111.4,100,100,100,120]
        rows = key_levels(candles(prices))
        self.assertTrue(rows)
        for row in rows:
            self.assertLessEqual((row["區間上緣"]/row["區間下緣"]-1)*100, 0.800001)
            if row["類型"] == "支撐": self.assertLess(row["區間上緣"],120)
            if row["類型"] == "壓力": self.assertGreater(row["區間下緣"],120)


if __name__ == '__main__': unittest.main()
