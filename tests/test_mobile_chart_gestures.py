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

    def test_vertical_price_scale_pan_is_wired(self):
        self.assertIn("chartElement.style.transform=transform", self.source)
        self.assertIn("overlay.style.transform=transform", self.source)
        self.assertIn("touchStart.pan+dy", self.source)
        self.assertIn("v1-visual-pan-y-", self.source)

    def test_buttons_removed_and_wrapper_captures_touch(self):
        self.assertNotIn('id="price-up"', self.source)
        self.assertNotIn('id="price-down"', self.source)
        self.assertIn("chartWrap.addEventListener('touchmove'", self.source)
        self.assertIn("capture:true,passive:true", self.source)

    def test_multitouch_keeps_pinch_zoom(self):
        self.assertIn("if(event.touches.length!==1){touchStart=null;return;}", self.source)
        self.assertIn("pinch:true", self.source)

    def test_mirror_wave_horizons_and_future_room(self):
        self.assertIn('"mirrorSummary": mirror_summary', self.source)
        self.assertIn("wave.bars", self.source)
        self.assertIn("Math.min(80,Math.max(12", self.source)
        self.assertIn("data.mirrorSummary||[]", self.source)

    def test_viewport_persistence_is_preserved(self):
        self.assertIn("setVisibleLogicalRange(saved)", self.source)
        self.assertIn("sessionStorage.setItem(storageKey", self.source)


if __name__ == "__main__":
    unittest.main()
