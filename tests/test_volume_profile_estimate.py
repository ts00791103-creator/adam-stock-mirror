import unittest
import numpy as np
import pandas as pd
from volume_profile_estimate import estimate_profile, evaluate_profile


def bars(n=21, price=10., volume=100.):
    return pd.DataFrame({"Open": [price]*n, "High": [price+1]*n,
                         "Low": [price-1]*n, "Close": [price]*n, "Volume": [volume]*n},
                        index=pd.date_range("2025-01-01", periods=n))


class VolumeProfileTests(unittest.TestCase):
    def test_uniform_allocation_and_conservation(self):
        p = estimate_profile(bars(2), bins=5)
        np.testing.assert_allclose(p["volumes"], [40]*5)
        self.assertAlmostEqual(sum(p["volumes"]), 200)
        self.assertAlmostEqual(p["poc"], 9.2)
        self.assertGreaterEqual(p["area_actual_pct"], 70)
        self.assertLessEqual(p["area_actual_pct"], 100)

    def test_flat_price_and_zero_range_at_max_edge(self):
        df = bars(2)
        df.loc[df.index[1], ["Open","High","Low","Close"]] = 11.
        p = estimate_profile(df, bins=5)
        self.assertAlmostEqual(sum(p["volumes"]),200)
        self.assertAlmostEqual(p["volumes"][-1],120)
        df[["Open","High","Low","Close"]] = 10.
        p = estimate_profile(df)
        self.assertEqual((p["val"],p["poc"],p["vah"]),(10.,10.,10.))

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError): estimate_profile(bars(volume=0))

    def test_invalid_ohlcv_and_dates_rejected(self):
        for column, value in [("High",1),("Low",20),("Close",np.nan),("Volume",-1)]:
            df=bars()
            df.loc[df.index[0],column]=value
            with self.assertRaises(ValueError): estimate_profile(df)
        with self.assertRaises(ValueError): estimate_profile(bars().iloc[::-1])
        df=bars();df.index=[df.index[0]]*len(df)
        with self.assertRaises(ValueError): estimate_profile(df)

    def test_no_signal_candle_in_reference_and_breakout(self):
        df=bars()
        df.iloc[-1]=[10,14,10,13,200]
        result=evaluate_profile(df,window=20,bins=5)
        self.assertEqual(result["signal"],"放量突破估算價值區")
        self.assertAlmostEqual(result["volume_ratio"],2)
        before=result["profile"]
        df.iloc[-1]=[10,40,10,30,900]
        self.assertEqual(before,evaluate_profile(df,window=20,bins=5)["profile"])

    def test_breakdown_and_weak_volume(self):
        df=bars();df.iloc[-1]=[10,10,6,7,200]
        self.assertEqual(evaluate_profile(df,window=20)["signal"],"放量跌破估算價值區")
        df.iloc[-1]=[10,14,10,13,100]
        self.assertEqual(evaluate_profile(df,window=20)["signal"],"未成立")

    def test_prior_close_already_above_not_new_breakout(self):
        df=bars()
        df.iloc[-2]=[14,14,14,14,1]
        df.iloc[-1]=[14,16,14,15,200]
        self.assertEqual(evaluate_profile(df,window=20)["signal"],"未成立")

    def test_missing_history_and_bad_parameters(self):
        with self.assertRaises(ValueError): evaluate_profile(bars(20),window=20)
        for bins in [0,4,101,10.5,True]:
            with self.assertRaises(ValueError): estimate_profile(bars(),bins=bins)
        for pct in [0,99,np.nan]:
            with self.assertRaises(ValueError): estimate_profile(bars(),area_pct=pct)
        for buffer in [-1,6,np.nan]:
            with self.assertRaises(ValueError): evaluate_profile(bars(),window=20,buffer_pct=buffer)
        for ratio in [.5,6,np.nan]:
            with self.assertRaises(ValueError): evaluate_profile(bars(),window=20,volume_multiple=ratio)

    def test_prefix_of_future_data_is_unchanged(self):
        df=bars(25)
        prefix=df.iloc[:21].copy()
        expected=evaluate_profile(prefix,window=20)
        df.iloc[21:]=[10,15,8,12,500]
        self.assertEqual(evaluate_profile(df.iloc[:21],window=20),expected)

    def test_value_area_is_contiguous_and_contains_poc(self):
        p=estimate_profile(bars(),bins=17,area_pct=80)
        indexes=[i for i,flag in enumerate(p["area_mask"]) if flag]
        self.assertEqual(indexes,list(range(min(indexes),max(indexes)+1)))
        self.assertLessEqual(p["val"],p["poc"])
        self.assertGreaterEqual(p["vah"],p["poc"])
        self.assertGreaterEqual(p["area_actual_pct"],80)


if __name__ == "__main__":
    unittest.main()
