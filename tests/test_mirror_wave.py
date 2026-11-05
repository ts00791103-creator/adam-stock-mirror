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


    def test_rising_leg_reverses_to_falling_projection(self):
        import types
        ns = dict(self.calc)
        ns["find_pivots"] = Mock(return_value=[(4, "低"), (7, "高")])
        ns["internal_turns"] = Mock(return_value=[])
        fn = types.FunctionType(self.calc["mirror_wave"].__code__, ns)
        result = fn(self.frame, "短波", 3, "1d")
        self.assertEqual(result["segment"].tolist(), [90, 95, 100, 110])
        self.assertEqual(result["projection"].tolist(), [118, 108, 103, 98])
        self.assertEqual((result["high_i"], result["low_i"]), (0, 3))

    def test_projection_anchors_to_latest_close(self):
        import types
        ns = dict(self.calc)
        ns["find_pivots"] = Mock(return_value=[(2, "高"), (4, "低")])
        ns["internal_turns"] = Mock(return_value=[])
        fn = types.FunctionType(self.calc["mirror_wave"].__code__, ns)
        changed = self.frame.copy()
        changed.iloc[-1, 0] = 135
        result = fn(changed, "短波", 3, "1d")
        self.assertEqual(result["projection"].tolist(), [135, 150, 165])
        self.assertEqual(result["times"][0], changed.index[-1])

    def test_last_two_pivots_determine_mirror_leg(self):
        import types
        ns = dict(self.calc)
        ns["find_pivots"] = Mock(return_value=[(1, "低"), (2, "高"), (4, "低"), (7, "高")])
        ns["internal_turns"] = Mock(return_value=[])
        fn = types.FunctionType(self.calc["mirror_wave"].__code__, ns)
        result = fn(self.frame, "中波", 3, "1d")
        self.assertEqual((result["start"], result["end"]), (4, 7))
        self.assertEqual(result["segment"].tolist(), [90, 95, 100, 110])

    def test_flat_historical_leg_stays_flat(self):
        import types
        ns = dict(self.calc)
        ns["find_pivots"] = Mock(return_value=[(2, "高"), (4, "低")])
        ns["internal_turns"] = Mock(return_value=[])
        fn = types.FunctionType(self.calc["mirror_wave"].__code__, ns)
        flat = self.frame.copy()
        flat.iloc[2:5, 0] = 100
        result = fn(flat, "長波", 3, "1d")
        self.assertEqual(result["projection"].tolist(), [118, 118, 118])

    def test_wave_configurations_are_distinct(self):
        settings = self.calc["WAVES"]
        self.assertEqual(set(settings), {"短波", "中波", "長波"})
        self.assertEqual(len(set(settings.values())), 3)
        self.assertLess(settings["短波"][0], settings["中波"][0])
        self.assertLess(settings["中波"][0], settings["長波"][0])
        self.assertLess(settings["短波"][1], settings["中波"][1])
        self.assertLess(settings["中波"][1], settings["長波"][1])


    def test_real_pivots_alternate_and_exceed_threshold(self):
        # Repeated highs/lows and small pullbacks should not create extra swings.
        prices = [100, 101, 103, 106, 110, 110, 108, 103, 95, 90, 90,
                  92, 97, 104, 112, 120, 120, 118, 110, 101, 95, 92, 90]
        pivots = self.calc["find_pivots"](prices, 2, 0.05)
        self.assertGreaterEqual(len(pivots), 3)
        self.assertEqual([kind for _, kind in pivots[:3]], ["高", "低", "高"])
        self.assertEqual([prices[i] for i, _ in pivots[:3]], [110, 90, 120])
        for (i, kind), (j, next_kind) in zip(pivots, pivots[1:]):
            self.assertNotEqual(kind, next_kind)
            self.assertGreaterEqual(abs(prices[j] - prices[i]) / max(abs(prices[i]), 1e-9), 0.05)

    def test_real_pivots_ignore_small_reversals(self):
        prices = [100, 102, 105, 110, 108, 106, 109, 112, 110, 107,
                  100, 95, 90, 92, 95, 100, 105, 110, 115]
        pivots = self.calc["find_pivots"](prices, 2, 0.05)
        self.assertTrue(all(pivots[i][1] != pivots[i+1][1] for i in range(len(pivots)-1)))
        # The small pullback after 110 must not be accepted as a full reversal.
        self.assertNotIn((5, "低"), pivots)

    def test_actual_pivots_feed_mirror_without_mocking(self):
        prices = [100, 102, 105, 110, 120, 115, 108, 100, 90, 95,
                  105, 115, 130, 125, 115, 100, 85, 90, 100, 110,
                  125, 120, 105, 95, 90, 92, 94, 96, 98, 100]
        frame = pd.DataFrame({"Close": prices}, index=pd.bdate_range("2026-09-01", periods=len(prices)))
        result = self.calc["mirror_wave"](frame, "短波", 3, "1d")
        self.assertIsNotNone(result)
        self.assertEqual(result["projection"][0], frame["Close"].iloc[-1])
        self.assertEqual(result["segment"].tolist()[::-1][0], result["segment"].iloc[-1] if hasattr(result["segment"], "iloc") else result["segment"][-1])
        expected = frame["Close"].iloc[-1] + result["segment"][::-1] - result["segment"][-1]
        np.testing.assert_allclose(result["projection"], expected)
        self.assertEqual(len(result["times"]), len(result["projection"]))

    def test_daily_future_index_excludes_weekends(self):
        future = self.calc["future_index"](pd.Timestamp("2026-11-06"), 2, "1d")
        self.assertEqual([str(x.date()) for x in future], ["2026-11-09", "2026-11-10"])


if __name__ == "__main__":
    unittest.main()
