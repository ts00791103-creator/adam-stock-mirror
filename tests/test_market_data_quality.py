"""Offline tests for OHLC quality gate without launching Streamlit."""
import ast
from pathlib import Path
import unittest
import numpy as np
import pandas as pd


def audit(df):
    source = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    fn = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "audit_ohlc_data")
    scope = {"np": np, "pd": pd}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), "app.py", "exec"), scope)
    return scope["audit_ohlc_data"](df)


class MarketDataQualityTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {"Open": [100., 101.], "High": [103., 104.],
             "Low": [99., 100.], "Close": [102., 103.]},
            index=pd.to_datetime(["2026-11-03", "2026-11-04"]))

    def test_valid_bars(self):
        self.assertEqual(audit(self.frame), [])

    def test_duplicate_and_out_of_order_dates(self):
        duplicate = self.frame.copy()
        duplicate.index = pd.to_datetime(["2026-11-03", "2026-11-03"])
        self.assertTrue(any("重複" in x for x in audit(duplicate)))
        self.assertTrue(any("順序" in x for x in audit(self.frame.iloc[::-1])))

    def test_missing_and_infinite_prices(self):
        frame = self.frame.copy()
        frame.iloc[0, 0] = np.nan
        frame.iloc[1, 1] = np.inf
        self.assertTrue(any("缺漏" in x for x in audit(frame)))

    def test_high_low_relationship(self):
        frame = self.frame.copy()
        frame.iloc[0, frame.columns.get_loc("High")] = 98.
        self.assertTrue(any("高低價" in x for x in audit(frame)))

    def test_nonpositive_prices(self):
        frame = self.frame.copy()
        frame.iloc[0, frame.columns.get_loc("Close")] = 0.
        self.assertTrue(any("非正數" in x for x in audit(frame)))

    def test_missing_column(self):
        self.assertTrue(any("缺少 OHLC" in x for x in audit(self.frame.drop(columns="Low"))))

    def test_quality_gate_runs_before_mirror_analysis(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        gate = source.index("    quality_issues = audit_ohlc_data(df)")
        mirror = source.index("    waves = []", gate)
        self.assertLess(gate, mirror)


if __name__ == "__main__":
    unittest.main()
