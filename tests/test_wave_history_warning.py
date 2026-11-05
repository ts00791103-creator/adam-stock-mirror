"""Verify that incomplete history is visibly disclosed for each selected wave."""
import ast
from pathlib import Path
import unittest


class WaveHistoryWarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        ast.parse(cls.source)

    def test_warning_precedes_mirror_calculation(self):
        source = self.source
        loop = source.index("    for name in names:\n        required_bars = WAVES[name][1]")
        warning = source.index("        if available_bars < required_bars:", loop)
        calculation = source.index("        result = mirror_wave(", loop)
        self.assertLess(warning, calculation)

    def test_warning_reports_both_actual_and_required_counts(self):
        self.assertIn('f"⚠️ {name}歷史資料不足：目前 {available_bars} 根／"', self.source)
        self.assertIn('f"參考設定 {required_bars} 根。"', self.source)
        self.assertIn("不可視為完整波段", self.source)

    def test_wave_settings_remain_independent(self):
        tree = ast.parse(self.source)
        settings = next(n for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "WAVES" for t in n.targets))
        self.assertEqual(ast.literal_eval(settings.value),
                         {"短波": (3, 100), "中波": (7, 260), "長波": (14, 650)})


if __name__ == "__main__":
    unittest.main()
