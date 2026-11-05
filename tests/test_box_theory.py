"""離線箱型回歸測試：驗證上下界、突破方向及資料不足保護。"""
import unittest
import pandas as pd
from box_theory import detect_boxes


class BoxTheoryTests(unittest.TestCase):
    def test_not_enough_bars(self):
        frame = pd.DataFrame({"High": [11], "Low": [9], "Close": [10]})
        self.assertEqual(detect_boxes(frame, window=3), [])

    def test_upward_breakout(self):
        frame = pd.DataFrame({
            "High": [10, 10.5, 10.2, 12],
            "Low": [9, 9.5, 9.2, 11],
            "Close": [9.5, 10, 9.8, 11.5],
        })
        boxes = detect_boxes(frame, window=3, max_width_pct=20)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0]["status"], "上破")
        self.assertEqual(boxes[0]["start"], 0)
        self.assertEqual(boxes[0]["end"], 2)
        self.assertAlmostEqual(boxes[0]["top"], 10.5)
        self.assertAlmostEqual(boxes[0]["bottom"], 9)

    def test_downward_breakout(self):
        frame = pd.DataFrame({
            "High": [10, 10.5, 10.2, 8.8],
            "Low": [9, 9.5, 9.2, 8],
            "Close": [9.5, 10, 9.8, 8.5],
        })
        boxes = detect_boxes(frame, window=3, max_width_pct=20)
        self.assertEqual(boxes[0]["status"], "下破")

    def test_box_too_wide(self):
        frame = pd.DataFrame({
            "High": [15, 15, 15],
            "Low": [9, 9, 9],
            "Close": [10, 10, 10],
        })
        self.assertEqual(detect_boxes(frame, window=3, max_width_pct=12), [])


if __name__ == "__main__":
    unittest.main()
