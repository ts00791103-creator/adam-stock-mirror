"""手機圖表資料序列的離線測試，不啟動 Streamlit。"""
import ast
from pathlib import Path
import math
import unittest
import pandas as pd


def load_points():
    source = ast.parse((Path(__file__).resolve().parents[1] / "mobile_chart.py").read_text(encoding="utf-8"))
    nodes = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "_points"]
    if len(nodes) != 1:
        raise RuntimeError("找不到手機圖表 _points 函式")
    module = ast.Module(body=nodes, type_ignores=[])
    scope = {"pd": pd, "math": math}
    exec(compile(ast.fix_missing_locations(module), "mobile_chart.py", "exec"), scope)
    return scope["_points"]


class MobileChartDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.points = load_points()

    def test_timestamps_and_values(self):
        index = pd.to_datetime(["2026-11-02", "2026-11-03"])
        points = self.points(index, [100, 105.5])
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["time"], int(index[0].timestamp()))
        self.assertEqual(points[1]["value"], 105.5)

    def test_invalid_values_are_excluded(self):
        index = pd.date_range("2026-11-02", periods=5)
        points = self.points(index, [1, float("nan"), float("inf"), None, 5])
        self.assertEqual([p["value"] for p in points], [1.0, 5.0])

    def test_empty_series(self):
        self.assertEqual(self.points([], []), [])


if __name__ == "__main__":
    unittest.main()
