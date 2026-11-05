"""Offline checks for historical source table and duplicate source identification."""
import ast
from pathlib import Path
import unittest
import pandas as pd
import numpy as np


def load_source_rows():
    tree = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    names = {"wave_source_rows", "fmt_time"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {"pd": pd}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "app.py", "exec"), scope)
    return scope["wave_source_rows"]


class WaveSourceRowsTests(unittest.TestCase):
    def setUp(self):
        self.source_rows = load_source_rows()
        recent = pd.DataFrame({"Close": [10., 12., 15., 13., 11.]},
                              index=pd.bdate_range("2026-10-26", periods=5))
        self.wave = {"name": "短波", "recent": recent, "start": 1, "end": 3,
                     "segment": np.array([12., 15., 13.]),
                     "projection": np.array([100., 102., 99.])}

    def test_source_dates_and_prices(self):
        row = self.source_rows([self.wave], "1d")[0]
        self.assertEqual(row["歷史起日"], "2026-10-27")
        self.assertEqual(row["歷史迄日"], "2026-10-29")
        self.assertEqual(row["歷史起價"], 12.)
        self.assertEqual(row["歷史迄價"], 13.)
        self.assertEqual(row["鏡像終點"], 99.)
        self.assertEqual(row["與其他波段相同來源"], "無")

    def test_duplicate_interval_is_identified(self):
        second = dict(self.wave, name="中波")
        rows = self.source_rows([self.wave, second], "1d")
        self.assertEqual(rows[1]["與其他波段相同來源"], "短波")

    def test_distinct_intervals_not_marked_as_duplicates(self):
        second = dict(self.wave, name="長波", start=0, end=4)
        rows = self.source_rows([self.wave, second], "1d")
        self.assertEqual(rows[1]["與其他波段相同來源"], "無")

    def test_source_table_precedes_chart(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertLess(source.index('st.subheader("亞當鏡像｜歷史波段來源")'),
                        source.index('    config = {\n        "scrollZoom": True,'))


if __name__ == "__main__":
    unittest.main()
