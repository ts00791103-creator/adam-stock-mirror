"""亞當 A 模式離線單元測試；只擷取純計算函式，避免啟動 Streamlit UI。"""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock
import numpy as np
import pandas as pd


def load_mirror_functions():
    source = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    names = {"find_pivots", "future_index", "internal_turns", "mirror_wave"}
    selected = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in selected} != names:
        raise RuntimeError("找不到亞當鏡像計算函式")
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {
        "np": np, "pd": pd,
        "WAVES": {"短波": (3, 100), "中波": (7, 260), "長波": (14, 650)},
        "COLORS": {"短波": "green", "中波": "orange", "長波": "red"},
    }
    exec(compile(ast.fix_missing_locations(module), "app.py", "exec"), namespace)
    return namespace


class MirrorWaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calc = load_mirror_functions()

    def setUp(self):
        self.frame = pd.DataFrame(
            {"Close": [100, 110, 120, 105, 90, 95, 100, 110, 115, 118]},
            index=pd.bdate_range("2026-10-22", periods=10),
        )

    def test_a_mode_reverses_time_not_price(self):
        namespace = dict(self.calc)
        namespace["find_pivots"] = Mock(return_value=[(2, "高"), (4, "低")])
        namespace["internal_turns"] = Mock(return_value=[])
        fn = self.calc["mirror_wave"]
        # Function globals are isolated to avoid modifying Streamlit application state.
        import types
        isolated = types.FunctionType(fn.__code__, namespace)
        result = isolated(self.frame, "短波", 3, "1d")
        self.assertEqual(result["segment"].tolist(), [120, 105, 90])
        self.assertEqual(result["projection"].tolist(), [118, 133, 148])
        self.assertEqual(float(result["projection"][0]), 118)
        self.assertEqual(len(result["times"]), len(result["projection"]))
        self.assertEqual(result["high_i"], 2)
        self.assertEqual(result["low_i"], 0)

    def test_not_enough_confirmed_turns(self):
        import types
        namespace = dict(self.calc)
        namespace["find_pivots"] = Mock(return_value=[(2, "高")])
        isolated = types.FunctionType(self.calc["mirror_wave"].__code__, namespace)
        self.assertIsNone(isolated(self.frame, "短波", 3, "1d"))

    def test_wave_specific_settings(self):
        import types
        for name, (span, lookback) in self.calc["WAVES"].items():
            with self.subTest(wave=name):
                namespace = dict(self.calc)
                pivot = Mock(return_value=[])
                namespace["find_pivots"] = pivot
                isolated = types.FunctionType(self.calc["mirror_wave"].__code__, namespace)
                self.assertIsNone(isolated(self.frame, name, 4, "1d"))
                args = pivot.call_args.args
                self.assertEqual(args[1], span)
                self.assertAlmostEqual(args[2], 0.04)
                self.assertEqual(len(args[0]), min(lookback, len(self.frame)))

    def test_confirmed_pivots_need_right_side_bars(self):
        values = [100, 101, 102, 103, 104, 105, 106]
        # span=2: latest 2 bars cannot be a confirmed pivot.
        pivots = self.calc["find_pivots"](values, 2, 0)
        self.assertTrue(all(i < len(values) - 2 for i, _ in pivots))

    def test_daily_future_index_excludes_weekends(self):
        future = self.calc["future_index"](pd.Timestamp("2026-11-06"), 2, "1d")
        self.assertEqual([str(x.date()) for x in future], ["2026-11-09", "2026-11-10"])


if __name__ == "__main__":
    unittest.main()
