"""靜態驗證手機圖表觸控設定，實機手勢仍須另行驗收。"""
from pathlib import Path
import unittest


class MobileChartGestureConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "mobile_chart.py").read_text(encoding="utf-8")

    def test_both_touch_drag_axes_enabled(self):
        self.assertIn("horzTouchDrag:true,vertTouchDrag:true", self.source)

    def test_chart_consumes_touch_gestures(self):
        self.assertIn("touch-action:none", self.source)

    def test_viewport_persistence_is_preserved(self):
        self.assertIn("setVisibleLogicalRange(saved)", self.source)
        self.assertIn("sessionStorage.setItem(storageKey", self.source)


if __name__ == "__main__":
    unittest.main()
