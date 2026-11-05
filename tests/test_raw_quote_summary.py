"""Check raw Yahoo data disclosure without Streamlit or network."""
import ast
from pathlib import Path
import unittest
import numpy as np
import pandas as pd


class RawQuoteSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(cls.source)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "raw_quote_summary")
        scope = {"np": np, "pd": pd}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), "app.py", "exec"), scope)
        cls.audit = staticmethod(scope["raw_quote_summary"])

    def test_clean_data(self):
        df = pd.DataFrame({"Close": [100., 101.]}, index=pd.to_datetime(["2026-11-02", "2026-11-03"]))
        self.assertEqual(self.audit(df), [])

    def test_missing_and_nonfinite_close(self):
        df = pd.DataFrame({"Close": [100., np.nan, np.inf]}, index=pd.date_range("2026-11-02", periods=3))
        self.assertTrue(any("2 根" in x and "缺漏" in x for x in self.audit(df)))

    def test_duplicate_dates(self):
        df = pd.DataFrame({"Close": [100., 101.]}, index=pd.to_datetime(["2026-11-02", "2026-11-02"]))
        self.assertTrue(any("1 筆重複" in x for x in self.audit(df)))

    def test_unsorted_dates(self):
        df = pd.DataFrame({"Close": [100., 101.]}, index=pd.to_datetime(["2026-11-03", "2026-11-02"]))
        self.assertTrue(any("未排序" in x for x in self.audit(df)))

    def test_raw_audit_precedes_cleanup(self):
        self.assertLess(self.source.index("    raw_notes = raw_quote_summary(df)"),
                        self.source.index('    df = df.dropna(subset=["Close"]).sort_index().copy()'))
        self.assertIn('df.attrs["raw_quote_notes"] = raw_notes', self.source)
        self.assertIn('for note in df.attrs.get("raw_quote_notes", []):', self.source)


if __name__ == "__main__":
    unittest.main()
